"""
Агент генерации DDL скриптов
"""
import json
import logging
from typing import Dict, Any, List, Optional
from langchain_core.messages import HumanMessage, AIMessage

from ..core.agent_executor import AgentExecutor
from ..core.state import MASState

logger = logging.getLogger(__name__)


class DDLGeneratorAgent(AgentExecutor):
    """
    Агент для генерации DDL скриптов на основе анализа данных
    """
    
    def __init__(self, **kwargs):
        super().__init__(agent_name='ddl_generation', **kwargs)
        
    def execute(self, state: MASState) -> MASState:
        """
        Генерация DDL скриптов для выбранного хранилища
        
        Args:
            state: Текущее состояние МАС
            
        Returns:
            Обновленное состояние с DDL скриптами
        """
        logger.info("Начало генерации DDL скриптов")
        
        try:
            # Получаем необходимые данные из состояния
            storage = state.get('storage_recommendation', 'postgres')
            metadata = state.get('source_metadata', {})
            profile = state.get('data_profile', {})
            
            if not metadata or not metadata.get('columns'):
                raise ValueError("Отсутствуют метаданные для генерации DDL")
            
            # Подготавливаем контекст для LLM
            context = self._prepare_ddl_context(storage, metadata, profile)
            
            # Вызываем LLM для генерации DDL
            messages = [
                HumanMessage(content=f"""
Сгенерируй DDL скрипты для хранилища {storage} на основе следующих данных:

{context}

Требования:
1. Создай основную таблицу с правильными типами данных
2. Добавь индексы для оптимизации запросов
3. Если это ClickHouse - добавь партицирование для временных данных
4. Если это PostgreSQL - добавь первичные ключи и внешние ключи где необходимо
5. Добавь комментарии к таблице и колонкам

Ответь в формате JSON:
{{
    "main_table": {{
        "name": "имя_таблицы",
        "ddl": "CREATE TABLE ...",
        "engine": "движок (для ClickHouse)"
    }},
    "indexes": [
        {{"name": "имя_индекса", "ddl": "CREATE INDEX ..."}}
    ],
    "partitioning": "партицирование (если применимо)",
    "comments": ["список комментариев и рекомендаций"],
    "optimization_notes": ["заметки по оптимизации"]
}}
""")
            ]
            
            response = self.llm_manager.invoke_with_retry(self.llm, messages)
            
            # Парсим ответ и генерируем DDL скрипты
            ddl_info = self._parse_ddl_response(response.content, storage, metadata)
            
            # Сохраняем DDL скрипты в состоянии
            state['ddl_scripts'] = self._format_ddl_scripts(ddl_info)
            state['ddl_recommendations'] = {
                'indexes': ddl_info.get('indexes', []),
                'partitioning': ddl_info.get('partitioning', ''),
                'optimization_notes': ddl_info.get('optimization_notes', [])
            }
            
            # Добавляем сообщение в историю
            if 'messages' not in state:
                state['messages'] = []
            
            state['messages'].append(AIMessage(content=f"""
DDL скрипты сгенерированы для {storage}.
Таблица: {ddl_info.get('main_table', {}).get('name', 'data_table')}
Количество индексов: {len(ddl_info.get('indexes', []))}
Партицирование: {'Да' if ddl_info.get('partitioning') else 'Нет'}
"""))
            
            # Обновляем информацию об агенте
            state['current_agent'] = self.agent_name
            
            if 'completed_agents' not in state:
                state['completed_agents'] = []
            
            if self.agent_name not in state['completed_agents']:
                state['completed_agents'].append(self.agent_name)
            
            logger.info(f"DDL скрипты успешно сгенерированы для {storage}")
            
            # Сохраняем промежуточные результаты
            self._save_intermediate_results(state)
            
            return state
            
        except Exception as e:
            logger.error(f"Ошибка генерации DDL: {e}")
            
            if 'errors' not in state:
                state['errors'] = []
            
            state['errors'].append({
                'agent': self.agent_name,
                'error': str(e),
                'stage': 'ddl_generation'
            })
            
            # Генерируем базовый DDL как fallback
            state['ddl_scripts'] = [self._generate_fallback_ddl(state)]
            
            return state
    
    def _prepare_ddl_context(self, 
                           storage: str,
                           metadata: Dict[str, Any],
                           profile: Dict[str, Any]) -> str:
        """
        Подготовка контекста для генерации DDL
        
        Args:
            storage: Тип хранилища
            metadata: Метаданные источника
            profile: Профиль данных
            
        Returns:
            Контекст для LLM
        """
        context_parts = []
        
        context_parts.append(f"Целевое хранилище: {storage}")
        context_parts.append(f"\nКолонки и их типы:")
        
        # Информация о колонках
        for col_name, col_info in metadata.get('columns', {}).items():
            dtype = col_info.get('dtype', 'unknown')
            null_pct = col_info.get('null_percentage', 0)
            unique_count = col_info.get('unique_count', 0)
            
            # Определяем SQL тип на основе pandas dtype
            sql_type = self._map_dtype_to_sql(dtype, storage)
            
            context_parts.append(
                f"- {col_name}: {dtype} -> {sql_type}, "
                f"nulls: {null_pct:.1f}%, unique: {unique_count}"
            )
        
        # Характеристики данных
        if profile.get('data_characteristics'):
            chars = profile['data_characteristics']
            context_parts.append("\nХарактеристики данных:")
            if chars.get('has_temporal_data'):
                context_parts.append("- Есть временные данные (требуется партицирование)")
            if chars.get('mostly_numeric'):
                context_parts.append("- Преимущественно числовые данные")
            
        # Подсказки по оптимизации
        if profile.get('optimization_hints'):
            context_parts.append("\nРекомендации по оптимизации:")
            for hint in profile['optimization_hints']:
                context_parts.append(f"- {hint}")
        
        return "\n".join(context_parts)
    
    def _map_dtype_to_sql(self, dtype: str, storage: str) -> str:
        """
        Маппинг pandas dtype в SQL тип для конкретного хранилища
        
        Args:
            dtype: Pandas dtype
            storage: Тип хранилища
            
        Returns:
            SQL тип данных
        """
        dtype_lower = str(dtype).lower()
        
        if storage == 'postgres':
            if 'int' in dtype_lower:
                if '64' in dtype_lower:
                    return 'BIGINT'
                elif '32' in dtype_lower:
                    return 'INTEGER'
                else:
                    return 'SMALLINT'
            elif 'float' in dtype_lower:
                return 'DOUBLE PRECISION'
            elif 'bool' in dtype_lower:
                return 'BOOLEAN'
            elif 'datetime' in dtype_lower:
                return 'TIMESTAMP'
            elif 'date' in dtype_lower:
                return 'DATE'
            else:
                return 'TEXT'
                
        elif storage == 'clickhouse':
            if 'int' in dtype_lower:
                if '64' in dtype_lower:
                    return 'Int64'
                elif '32' in dtype_lower:
                    return 'Int32'
                else:
                    return 'Int16'
            elif 'float' in dtype_lower:
                return 'Float64'
            elif 'bool' in dtype_lower:
                return 'UInt8'
            elif 'datetime' in dtype_lower:
                return 'DateTime'
            elif 'date' in dtype_lower:
                return 'Date'
            else:
                return 'String'
        
        else:  # HDFS - используем Hive типы
            if 'int' in dtype_lower:
                return 'BIGINT'
            elif 'float' in dtype_lower:
                return 'DOUBLE'
            elif 'bool' in dtype_lower:
                return 'BOOLEAN'
            elif 'datetime' in dtype_lower or 'date' in dtype_lower:
                return 'TIMESTAMP'
            else:
                return 'STRING'
    
    def _parse_ddl_response(self, 
                          response: str,
                          storage: str,
                          metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Парсинг ответа LLM с DDL
        
        Args:
            response: Ответ от LLM
            storage: Тип хранилища
            metadata: Метаданные
            
        Returns:
            Распарсенная информация DDL
        """
        import re
        
        # Пытаемся найти JSON в ответе
        json_match = re.search(r'\{[\s\S]*\}', response)
        
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass
        
        # Если не удалось распарсить, генерируем базовый DDL
        return self._generate_basic_ddl(storage, metadata)
    
    def _generate_basic_ddl(self, storage: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Генерация базового DDL
        
        Args:
            storage: Тип хранилища
            metadata: Метаданные
            
        Returns:
            Базовая DDL информация
        """
        table_name = "data_table"
        columns = []
        
        for col_name, col_info in metadata.get('columns', {}).items():
            dtype = col_info.get('dtype', 'unknown')
            sql_type = self._map_dtype_to_sql(dtype, storage)
            nullable = col_info.get('null_count', 0) > 0
            
            if storage == 'postgres':
                null_clause = '' if nullable else ' NOT NULL'
                columns.append(f"    {col_name} {sql_type}{null_clause}")
            elif storage == 'clickhouse':
                nullable_type = f"Nullable({sql_type})" if nullable else sql_type
                columns.append(f"    {col_name} {nullable_type}")
        
        if storage == 'postgres':
            ddl = f"""CREATE TABLE {table_name} (
{',\n'.join(columns)}
);"""
        elif storage == 'clickhouse':
            ddl = f"""CREATE TABLE {table_name} (
{',\n'.join(columns)}
) ENGINE = MergeTree()
ORDER BY tuple();"""
        else:
            ddl = f"""CREATE EXTERNAL TABLE {table_name} (
{',\n'.join(columns)}
) STORED AS PARQUET;"""
        
        return {
            'main_table': {
                'name': table_name,
                'ddl': ddl,
                'engine': 'MergeTree' if storage == 'clickhouse' else None
            },
            'indexes': [],
            'partitioning': '',
            'comments': ['Базовый DDL сгенерирован автоматически'],
            'optimization_notes': []
        }
    
    def _format_ddl_scripts(self, ddl_info: Dict[str, Any]) -> List[Dict[str, str]]:
        """
        Форматирование DDL скриптов для сохранения
        
        Args:
            ddl_info: Информация о DDL
            
        Returns:
            Список отформатированных DDL скриптов
        """
        scripts = []
        
        # Основная таблица
        if 'main_table' in ddl_info:
            scripts.append({
                'type': 'table',
                'name': ddl_info['main_table'].get('name', 'data_table'),
                'script': ddl_info['main_table'].get('ddl', ''),
                'description': 'Основная таблица для данных'
            })
        
        # Индексы
        for index in ddl_info.get('indexes', []):
            scripts.append({
                'type': 'index',
                'name': index.get('name', 'index'),
                'script': index.get('ddl', ''),
                'description': 'Индекс для оптимизации запросов'
            })
        
        return scripts
    
    def _generate_fallback_ddl(self, state: MASState) -> Dict[str, str]:
        """
        Генерация fallback DDL при ошибке
        
        Args:
            state: Текущее состояние
            
        Returns:
            Базовый DDL скрипт
        """
        storage = state.get('storage_recommendation', 'postgres')
        
        if storage == 'postgres':
            script = """CREATE TABLE data_table (
    id SERIAL PRIMARY KEY,
    data JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);"""
        elif storage == 'clickhouse':
            script = """CREATE TABLE data_table (
    id UInt64,
    data String,
    created_at DateTime DEFAULT now()
) ENGINE = MergeTree()
ORDER BY id;"""
        else:
            script = """CREATE EXTERNAL TABLE data_table (
    id BIGINT,
    data STRING,
    created_at TIMESTAMP
) STORED AS PARQUET;"""
        
        return {
            'type': 'table',
            'name': 'data_table',
            'script': script,
            'description': 'Fallback таблица (сгенерирована из-за ошибки)'
        }
