"""
Интеграция с LLM (Ollama)
"""
import logging
from typing import Dict, Any
import json


logger = logging.getLogger(__name__)


class OllamaIntegration:
    """Интеграция с Ollama LLM для анализа данных"""
    
    def __init__(self, model_name: str = "llama3.1:7b", base_url: str = "http://localhost:11434"):
        self.model_name = model_name
        self.base_url = base_url
        
    async def analyze_data_structure(self, sample_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Анализ структуры данных с помощью LLM
        
        Args:
            sample_data: Данные для анализа
            
        Returns:
            Результат анализа от LLM
        """
        try:
            # Пока что возвращаем заглушку
            # В будущем здесь будет реальный вызов Ollama API
            logger.info("Анализ данных с помощью LLM (заглушка)")
            
            # Симуляция анализа LLM
            mock_analysis = {
                "llm_recommendations": {
                    "field_analysis": self._analyze_fields(sample_data),
                    "storage_suggestions": self._suggest_storage(sample_data),
                    "optimization_tips": self._generate_optimization_tips(sample_data)
                },
                "confidence_score": 0.75,
                "analysis_timestamp": "2025-09-27T12:00:00Z"
            }
            
            return mock_analysis
            
        except Exception as e:
            logger.error(f"Ошибка анализа данных с LLM: {e}")
            return {
                "llm_recommendations": {
                    "error": str(e),
                    "fallback_message": "Анализ LLM недоступен, используются базовые рекомендации"
                },
                "confidence_score": 0.0
            }
    
    async def generate_ddl(self, analysis_result: Dict[str, Any], target_db: str = "postgresql") -> str:
        """
        Генерация DDL скрипта на основе анализа
        
        Args:
            analysis_result: Результаты анализа данных
            target_db: Тип целевой базы данных
            
        Returns:
            DDL скрипт
        """
        try:
            logger.info(f"Генерация DDL для {target_db} (заглушка)")
            
            # Извлечение метаданных
            metadata = analysis_result.get('metadata', {})
            columns = metadata.get('columns', {})
            
            if not columns:
                return "-- Не удалось получить информацию о колонках для генерации DDL"
            
            # Базовая генерация DDL
            table_name = "generated_table"
            ddl_lines = [f"-- DDL скрипт для {target_db}"]
            
            if target_db.lower() == "postgresql":
                ddl_lines.extend([
                    f"CREATE TABLE IF NOT EXISTS {table_name} (",
                ])
                
                column_definitions = []
                for col_name, col_info in columns.items():
                    pg_type = self._map_to_postgresql_type(col_info.get('dtype', 'object'))
                    nullable = "NULL" if col_info.get('null_percentage', 0) > 0 else "NOT NULL"
                    column_definitions.append(f"    {col_name} {pg_type} {nullable}")
                
                ddl_lines.append(",\n".join(column_definitions))
                ddl_lines.append(");")
                
            elif target_db.lower() == "clickhouse":
                ddl_lines.extend([
                    f"CREATE TABLE IF NOT EXISTS {table_name} (",
                ])
                
                column_definitions = []
                for col_name, col_info in columns.items():
                    ch_type = self._map_to_clickhouse_type(col_info.get('dtype', 'object'))
                    column_definitions.append(f"    {col_name} {ch_type}")
                
                ddl_lines.append(",\n".join(column_definitions))
                ddl_lines.append(") ENGINE = MergeTree() ORDER BY tuple();")
            
            return "\n".join(ddl_lines)
            
        except Exception as e:
            logger.error(f"Ошибка генерации DDL: {e}")
            return f"-- Ошибка генерации DDL: {e}"
    
    def _analyze_fields(self, sample_data: Dict[str, Any]) -> Dict[str, str]:
        """Анализ полей данных"""
        metadata = sample_data.get('metadata', {})
        columns = metadata.get('columns', {})
        
        field_analysis = {}
        for col_name, col_info in columns.items():
            dtype = col_info.get('dtype', 'unknown')
            null_percentage = col_info.get('null_percentage', 0)
            unique_count = col_info.get('unique_count', 0)
            
            if 'id' in col_name.lower():
                field_analysis[col_name] = "Вероятно идентификатор - подходит для первичного ключа"
            elif dtype in ['int64', 'float64'] and unique_count > 100:
                field_analysis[col_name] = "Числовое поле с высокой кардинальностью - подходит для аналитики"
            elif dtype == 'object' and null_percentage > 50:
                field_analysis[col_name] = "Текстовое поле с большим количеством пропусков - требует очистки"
            elif 'date' in col_name.lower() or 'time' in col_name.lower():
                field_analysis[col_name] = "Временное поле - подходит для партицирования"
            else:
                field_analysis[col_name] = f"Стандартное поле типа {dtype}"
        
        return field_analysis
    
    def _suggest_storage(self, sample_data: Dict[str, Any]) -> str:
        """Предложение типа хранилища"""
        metadata = sample_data.get('metadata', {})
        row_count = metadata.get('row_count', 0)
        column_count = metadata.get('column_count', 0)
        
        if row_count > 1000000:
            return "ClickHouse - оптимален для больших объемов аналитических данных"
        elif row_count < 100000 and column_count < 20:
            return "PostgreSQL - подходит для небольших транзакционных данных"
        else:
            return "HDFS + Parquet - универсальное решение для хранения и обработки"
    
    def _generate_optimization_tips(self, sample_data: Dict[str, Any]) -> list:
        """Генерация советов по оптимизации"""
        tips = [
            "Рассмотрите создание индексов для часто используемых полей",
            "Используйте партицирование для временных данных",
            "Реализуйте очистку данных для полей с высоким процентом пропусков"
        ]
        
        # Анализ данных для специфичных советов
        metadata = sample_data.get('metadata', {})
        data_quality = sample_data.get('data_quality', {})
        
        if data_quality.get('completeness_score', 1.0) < 0.8:
            tips.append("Низкое качество данных - добавьте этапы валидации и очистки")
        
        if data_quality.get('duplicate_rows', 0) > 0:
            tips.append("Обнаружены дубликаты - реализуйте дедупликацию")
        
        return tips
    
    def _map_to_postgresql_type(self, pandas_dtype: str) -> str:
        """Маппинг pandas типов в PostgreSQL"""
        type_mapping = {
            'int64': 'INTEGER',
            'float64': 'NUMERIC',
            'object': 'TEXT',
            'bool': 'BOOLEAN',
            'datetime64[ns]': 'TIMESTAMP'
        }
        return type_mapping.get(pandas_dtype, 'TEXT')
    
    def _map_to_clickhouse_type(self, pandas_dtype: str) -> str:
        """Маппинг pandas типов в ClickHouse"""
        type_mapping = {
            'int64': 'Int64',
            'float64': 'Float64', 
            'object': 'String',
            'bool': 'Bool',
            'datetime64[ns]': 'DateTime'
        }
        return type_mapping.get(pandas_dtype, 'String')