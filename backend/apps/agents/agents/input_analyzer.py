"""
Агент анализа входных данных
"""
import json
import logging
from typing import Dict, Any, List
from langchain_core.messages import HumanMessage, AIMessage

from ..core.agent_executor import AgentExecutor
from ..core.state import MASState
from ..tools import (
    extract_metadata_tool,
    extract_sample_tool,
    get_data_profile_tool
)

logger = logging.getLogger(__name__)


class InputAnalyzerAgent(AgentExecutor):
    """
    Агент для анализа входных данных и выбора оптимального хранилища
    """
    
    def __init__(self, **kwargs):
        super().__init__(agent_name='input_analysis', **kwargs)
        
    def execute(self, state: MASState) -> MASState:
        """
        Выполнение анализа входных данных
        
        Args:
            state: Текущее состояние МАС
            
        Returns:
            Обновленное состояние с результатами анализа
        """
        logger.info("Начало анализа входных данных")
        
        try:
            # Извлекаем параметры источника из состояния
            source_config = state.get('source_config', {})
            source_type = source_config.get('source_type', state.get('source_type', ''))
            connection_params = source_config.get('connection_params', state.get('connection_params', {}))
            
            if not source_type:
                raise ValueError("Не указан тип источника данных")
            
            # 1. Извлекаем метаданные
            logger.info(f"Извлечение метаданных для источника типа: {source_type}")
            
            metadata = extract_metadata_tool.invoke({
                'source_type': source_type,
                'file_path': connection_params.get('file_path'),
                'file_content': connection_params.get('file_content'),
                'connection_params': connection_params
            })
            
            state['source_metadata'] = metadata
            
            # 2. Извлекаем образец данных
            logger.info("Извлечение образца данных")
            
            sample = extract_sample_tool.invoke({
                'source_type': source_type,
                'file_path': connection_params.get('file_path'),
                'file_content': connection_params.get('file_content'),
                'sample_size': 10
            })
            
            state['data_sample'] = sample
            
            # 3. Создаем профиль данных
            logger.info("Создание профиля данных")
            
            profile = get_data_profile_tool.invoke({
                'metadata': metadata,
                'sample_data': sample
            })
            
            state['data_profile'] = profile
            
            # 4. Используем LLM для анализа и рекомендаций
            logger.info("Анализ данных с помощью LLM")
            
            # Подготавливаем контекст для LLM
            context = self._prepare_analysis_context(metadata, sample, profile)
            
            # Вызываем LLM для анализа
            messages = [
                HumanMessage(content=f"""
Проанализируй следующие данные и предоставь рекомендации:

{context}

Ответь в формате JSON со следующими полями:
{{
    "storage_recommendation": "postgres/clickhouse/hdfs",
    "reasoning": "подробное обоснование выбора",
    "data_characteristics": {{
        "volume": "small/medium/large",
        "velocity": "batch/streaming/real-time",
        "variety": "structured/semi-structured/unstructured",
        "main_use_case": "transactional/analytical/archival"
    }},
    "optimization_recommendations": ["список рекомендаций"],
    "potential_issues": ["список потенциальных проблем"],
    "alternative_storages": [
        {{"storage": "название", "reason": "причина", "priority": 1-3}}
    ]
}}
""")
            ]
            
            response = self.llm_manager.invoke_with_retry(self.llm, messages)
            
            # Парсим ответ LLM
            try:
                llm_analysis = self._parse_llm_response(response.content)
                
                # Обновляем состояние с результатами анализа
                state['storage_recommendation'] = llm_analysis.get('storage_recommendation', 'postgres')
                state['storage_reasoning'] = llm_analysis.get('reasoning', '')
                state['storage_alternatives'] = llm_analysis.get('alternative_storages', [])
                
                # Добавляем дополнительную информацию
                if 'data_characteristics' in llm_analysis:
                    state['data_profile']['characteristics'] = llm_analysis['data_characteristics']
                
                if 'optimization_recommendations' in llm_analysis:
                    state['data_profile']['optimization_hints'].extend(
                        llm_analysis['optimization_recommendations']
                    )
                
                logger.info(f"Рекомендованное хранилище: {state['storage_recommendation']}")
                
            except Exception as e:
                logger.error(f"Ошибка парсинга ответа LLM: {e}")
                # Используем рекомендации из профиля данных
                if profile.get('storage_recommendations'):
                    top_recommendation = profile['storage_recommendations'][0]
                    state['storage_recommendation'] = top_recommendation['storage']
                    state['storage_reasoning'] = top_recommendation['reason']
                else:
                    state['storage_recommendation'] = 'postgres'
                    state['storage_reasoning'] = 'Выбрано по умолчанию из-за ошибки анализа'
            
            # Добавляем сообщение в историю
            if 'messages' not in state:
                state['messages'] = []
            
            state['messages'].append(AIMessage(content=f"""
Анализ входных данных завершен.
Рекомендованное хранилище: {state['storage_recommendation']}
Обоснование: {state['storage_reasoning']}
"""))
            
            # Обновляем информацию об агенте
            state['current_agent'] = self.agent_name
            
            if 'completed_agents' not in state:
                state['completed_agents'] = []
            
            if self.agent_name not in state['completed_agents']:
                state['completed_agents'].append(self.agent_name)
            
            # Сохраняем промежуточные результаты
            self._save_intermediate_results(state)
            
            return state
            
        except Exception as e:
            logger.error(f"Ошибка анализа входных данных: {e}")
            
            if 'errors' not in state:
                state['errors'] = []
            
            state['errors'].append({
                'agent': self.agent_name,
                'error': str(e),
                'stage': 'input_analysis'
            })
            
            # Устанавливаем значения по умолчанию
            state['storage_recommendation'] = 'postgres'
            state['storage_reasoning'] = f'Выбрано по умолчанию из-за ошибки: {str(e)}'
            
            return state
    
    def _prepare_analysis_context(self, 
                                  metadata: Dict[str, Any],
                                  sample: Dict[str, Any],
                                  profile: Dict[str, Any]) -> str:
        """
        Подготовка контекста для анализа LLM
        
        Args:
            metadata: Метаданные источника
            sample: Образец данных
            profile: Профиль данных
            
        Returns:
            Строка с контекстом для анализа
        """
        context_parts = []
        
        # Метаданные
        if metadata:
            context_parts.append(f"Метаданные источника:")
            context_parts.append(f"- Тип источника: {metadata.get('source_type', 'неизвестно')}")
            context_parts.append(f"- Количество колонок: {metadata.get('column_count', 0)}")
            context_parts.append(f"- Количество строк в образце: {metadata.get('row_count', 0)}")
            
            if 'columns' in metadata:
                context_parts.append("\nИнформация о колонках:")
                for col_name, col_info in list(metadata['columns'].items())[:10]:  # Первые 10 колонок
                    context_parts.append(f"- {col_name}: {col_info.get('dtype', 'unknown')}, "
                                       f"null: {col_info.get('null_percentage', 0):.1f}%, "
                                       f"unique: {col_info.get('unique_count', 0)}")
        
        # Образец данных
        if sample and 'data' in sample:
            context_parts.append(f"\nОбразец данных (первые 3 записи):")
            for i, record in enumerate(sample['data'][:3], 1):
                context_parts.append(f"Запись {i}: {json.dumps(record, ensure_ascii=False)[:200]}")
        
        # Профиль данных
        if profile:
            if 'data_characteristics' in profile:
                chars = profile['data_characteristics']
                context_parts.append("\nХарактеристики данных:")
                context_parts.append(f"- Временные данные: {'Да' if chars.get('has_temporal_data') else 'Нет'}")
                context_parts.append(f"- Преимущественно числовые: {'Да' if chars.get('mostly_numeric') else 'Нет'}")
                context_parts.append(f"- Есть текстовые данные: {'Да' if chars.get('has_text_data') else 'Нет'}")
            
            if 'optimization_hints' in profile:
                context_parts.append(f"\nПодсказки по оптимизации:")
                for hint in profile['optimization_hints']:
                    context_parts.append(f"- {hint}")
        
        return "\n".join(context_parts)
    
    def _parse_llm_response(self, response: str) -> Dict[str, Any]:
        """
        Парсинг ответа LLM
        
        Args:
            response: Строка ответа от LLM
            
        Returns:
            Распарсенный словарь
        """
        # Пытаемся найти JSON в ответе
        import re
        
        # Ищем JSON блок
        json_match = re.search(r'\{[\s\S]*\}', response)
        
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass
        
        # Если не удалось распарсить JSON, пытаемся извлечь информацию из текста
        result = {
            'storage_recommendation': 'postgres',
            'reasoning': response,
            'alternative_storages': []
        }
        
        # Простой поиск рекомендаций в тексте
        if 'clickhouse' in response.lower():
            result['storage_recommendation'] = 'clickhouse'
        elif 'hdfs' in response.lower():
            result['storage_recommendation'] = 'hdfs'
        
        return result
