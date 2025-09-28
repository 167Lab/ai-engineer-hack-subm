"""
Модуль анализа источников данных в базах данных
"""
import psycopg2
from typing import Dict, Any, List, Optional
import logging


logger = logging.getLogger(__name__)


class DatabaseSourceAnalyzer:
    """Анализатор источников данных в базах данных (PostgreSQL, ClickHouse)"""
    
    def __init__(self):
        self.postgres_conn = None
        self.clickhouse_client = None
    
    async def analyze_postgres_table(self, connection_params: Dict[str, Any], table_name: str) -> Dict[str, Any]:
        """
        Анализ таблицы PostgreSQL
        
        Args:
            connection_params: Параметры подключения к БД
            table_name: Имя таблицы для анализа
            
        Returns:
            Dict с результатами анализа
        """
        try:
            # Базовые параметры подключения
            conn_params = {
                'host': connection_params.get('host', 'localhost'),
                'port': connection_params.get('port', 5432),
                'database': connection_params.get('database', 'postgres'),
                'user': connection_params.get('user', 'postgres'),
                'password': connection_params.get('password', '')
            }
            
            conn = psycopg2.connect(**conn_params)
            cursor = conn.cursor()
            
            # Получение метаданных таблицы
            cursor.execute("""
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns 
                WHERE table_name = %s
                ORDER BY ordinal_position
            """, (table_name,))
            columns_info = cursor.fetchall()
            
            if not columns_info:
                raise ValueError(f"Таблица '{table_name}' не найдена")
            
            # Получение статистики данных
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            row_count = cursor.fetchone()[0]
            
            # Получение образца данных (первые 1000 строк)
            cursor.execute(f"SELECT * FROM {table_name} LIMIT 1000")
            sample_data = cursor.fetchall()
            
            # Получение информации о индексах
            cursor.execute("""
                SELECT indexname, indexdef 
                FROM pg_indexes 
                WHERE tablename = %s
            """, (table_name,))
            indexes_info = cursor.fetchall()
            
            conn.close()
            
            # Формирование результата анализа
            analysis = {
                'analysis_status': 'success',
                'source_type': 'PostgreSQL',
                'metadata': {
                    'table_name': table_name,
                    'row_count': row_count,
                    'column_count': len(columns_info),
                    'columns': self._format_postgres_columns(columns_info),
                    'indexes': [{'name': idx[0], 'definition': idx[1]} for idx in indexes_info]
                },
                'sample_data': sample_data[:10],  # Ограничить образец
                'data_quality': self._assess_postgres_data_quality(cursor, table_name, columns_info),
                'recommendations': self._generate_postgres_recommendations(row_count, columns_info)
            }
            
            return analysis
            
        except Exception as e:
            logger.error(f"Ошибка анализа PostgreSQL таблицы {table_name}: {e}")
            return {
                'analysis_status': 'failed',
                'error': str(e),
                'source_type': 'PostgreSQL'
            }
    
    async def analyze_clickhouse_table(self, connection_params: Dict[str, Any], table_name: str) -> Dict[str, Any]:
        """
        Анализ таблицы ClickHouse
        
        Args:
            connection_params: Параметры подключения к БД
            table_name: Имя таблицы для анализа
            
        Returns:
            Dict с результатами анализа
        """
        try:
            # Пока что заглушка для ClickHouse
            # В будущем можно добавить clickhouse-driver
            return {
                'analysis_status': 'success',
                'source_type': 'ClickHouse',
                'metadata': {
                    'table_name': table_name,
                    'note': 'ClickHouse анализ не реализован полностью'
                },
                'recommendations': [{
                    'storage_type': 'ClickHouse',
                    'confidence': 0.8,
                    'reasoning': 'Данные уже в ClickHouse, рекомендуется оптимизация структуры'
                }]
            }
            
        except Exception as e:
            logger.error(f"Ошибка анализа ClickHouse таблицы {table_name}: {e}")
            return {
                'analysis_status': 'failed',
                'error': str(e),
                'source_type': 'ClickHouse'
            }
    
    def _format_postgres_columns(self, columns_info: List[tuple]) -> Dict[str, Any]:
        """Форматирование информации о колонках PostgreSQL"""
        columns = {}
        for col in columns_info:
            column_name, data_type, is_nullable, column_default = col
            columns[column_name] = {
                'data_type': data_type,
                'nullable': is_nullable == 'YES',
                'default': column_default,
                'suggested_optimization': self._suggest_column_optimization(data_type, is_nullable)
            }
        return columns
    
    def _suggest_column_optimization(self, data_type: str, is_nullable: str) -> str:
        """Предложение оптимизаций для колонки"""
        if 'varchar' in data_type.lower():
            return 'Рассмотрите использование TEXT для длинных строк'
        elif 'integer' in data_type.lower() and is_nullable == 'NO':
            return 'Подходит для индексации'
        elif 'timestamp' in data_type.lower():
            return 'Рекомендуется партицирование по этой колонке'
        return 'Оптимизация не требуется'
    
    def _assess_postgres_data_quality(self, cursor, table_name: str, columns_info: List[tuple]) -> Dict[str, Any]:
        """Оценка качества данных в PostgreSQL таблице"""
        try:
            quality_info = {
                'completeness_score': 1.0,
                'issues': []
            }
            
            # Проверка на NULL значения
            for col in columns_info:
                column_name = col[0]
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {table_name} WHERE {column_name} IS NULL")
                    null_count = cursor.fetchone()[0]
                    if null_count > 0:
                        quality_info['issues'].append(f"Колонка '{column_name}' содержит {null_count} NULL значений")
                except:
                    continue
                    
            return quality_info
            
        except Exception as e:
            return {
                'completeness_score': 0.5,
                'issues': [f'Не удалось оценить качество данных: {e}']
            }
    
    def _generate_postgres_recommendations(self, row_count: int, columns_info: List[tuple]) -> List[Dict[str, Any]]:
        """Генерация рекомендаций для PostgreSQL таблицы"""
        recommendations = []
        
        if row_count > 1000000:
            recommendations.append({
                'optimization_type': 'Partitioning',
                'confidence': 0.85,
                'reasoning': 'Большая таблица может выиграть от партицирования',
                'implementation': 'Рассмотрите партицирование по дате или другому логическому ключу'
            })
        
        # Проверка колонок для индексации
        potential_index_cols = []
        for col in columns_info:
            column_name, data_type, is_nullable = col[0], col[1], col[2]
            if 'id' in column_name.lower() or data_type in ['integer', 'bigint', 'uuid']:
                potential_index_cols.append(column_name)
        
        if potential_index_cols:
            recommendations.append({
                'optimization_type': 'Indexing',
                'confidence': 0.9,
                'reasoning': 'Найдены колонки, которые могут улучшить производительность при индексации',
                'implementation': f'Создайте индексы для колонок: {", ".join(potential_index_cols)}'
            })
        
        return recommendations