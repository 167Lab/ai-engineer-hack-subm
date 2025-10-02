"""
Инструменты для работы с данными - интеграция с существующими анализаторами
"""
import json
import asyncio
from typing import Dict, Any, Optional, List
from langchain_core.tools import tool
import pandas as pd
import logging

# Импортируем существующие анализаторы
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent.parent))
from analyzers.data_analyzer import DataSourceAnalyzer

logger = logging.getLogger(__name__)


@tool
async def analyze_file_tool(
    file_path: Optional[str] = None,
    file_content: Optional[str] = None,
    file_name: Optional[str] = None,
    sample_size: int = 1000
) -> Dict[str, Any]:
    """
    Анализ файлового источника данных (CSV, JSON, XML)
    
    Args:
        file_path: Путь к файлу на сервере
        file_content: Содержимое загруженного файла
        file_name: Имя файла для определения формата
        sample_size: Размер выборки для анализа
        
    Returns:
        Результаты анализа включая метаданные, статистику и рекомендации
    """
    try:
        analyzer = DataSourceAnalyzer()
        result = await analyzer.analyze_file_source(
            file_path=file_path,
            file_content=file_content,
            file_name=file_name,
            sample_size=sample_size
        )
        return result
    except Exception as e:
        logger.error(f"Ошибка анализа файла: {e}")
        return {
            'status': 'error',
            'error': str(e),
            'metadata': {},
            'recommendations': {}
        }


@tool
def extract_metadata_tool(
    source_type: str,
    file_path: Optional[str] = None,
    file_content: Optional[str] = None,
    connection_params: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Извлечение метаданных из источника данных
    
    Args:
        source_type: Тип источника (csv, json, xml, postgres, clickhouse)
        file_path: Путь к файлу
        file_content: Содержимое файла
        connection_params: Параметры подключения к БД
        
    Returns:
        Метаданные источника: схема, типы данных, статистика
    """
    metadata = {
        'source_type': source_type,
        'columns': {},
        'statistics': {}
    }
    
    try:
        if source_type in ['csv', 'json', 'xml']:
            # Для файлов используем pandas
            df = None
            
            if file_content:
                import io
                if source_type == 'csv':
                    df = pd.read_csv(io.StringIO(file_content), nrows=100)
                elif source_type == 'json':
                    df = pd.read_json(io.StringIO(file_content), lines=True, nrows=100)
            elif file_path:
                if source_type == 'csv':
                    df = pd.read_csv(file_path, nrows=100)
                elif source_type == 'json':
                    df = pd.read_json(file_path, lines=True, nrows=100)
                elif source_type == 'xml':
                    df = pd.read_xml(file_path)
            
            if df is not None:
                # Извлекаем метаданные
                metadata['row_count'] = len(df)
                metadata['column_count'] = len(df.columns)
                
                for col in df.columns:
                    metadata['columns'][col] = {
                        'dtype': str(df[col].dtype),
                        'null_count': int(df[col].isnull().sum()),
                        'unique_count': int(df[col].nunique()),
                        'sample_values': df[col].dropna().head(3).tolist()
                    }
                
                metadata['statistics'] = {
                    'total_nulls': int(df.isnull().sum().sum()),
                    'memory_usage': int(df.memory_usage(deep=True).sum()),
                    'duplicated_rows': int(df.duplicated().sum())
                }
                
        elif source_type in ['postgres', 'clickhouse']:
            # Для баз данных нужна отдельная логика
            metadata['connection_params'] = connection_params
            metadata['requires_db_connection'] = True
            
    except Exception as e:
        logger.error(f"Ошибка извлечения метаданных: {e}")
        metadata['error'] = str(e)
    
    return metadata


@tool
def extract_sample_tool(
    source_type: str,
    file_path: Optional[str] = None,
    file_content: Optional[str] = None,
    sample_size: int = 10
) -> Dict[str, Any]:
    """
    Извлечение образца данных для анализа
    
    Args:
        source_type: Тип источника данных
        file_path: Путь к файлу
        file_content: Содержимое файла
        sample_size: Размер образца (количество строк)
        
    Returns:
        Образец данных в виде словаря
    """
    sample_data = {
        'source_type': source_type,
        'sample_size': sample_size,
        'data': []
    }
    
    try:
        if source_type in ['csv', 'json', 'xml']:
            df = None
            
            if file_content:
                import io
                if source_type == 'csv':
                    df = pd.read_csv(io.StringIO(file_content), nrows=sample_size)
                elif source_type == 'json':
                    df = pd.read_json(io.StringIO(file_content), lines=True, nrows=sample_size)
            elif file_path:
                if source_type == 'csv':
                    df = pd.read_csv(file_path, nrows=sample_size)
                elif source_type == 'json':
                    df = pd.read_json(file_path, lines=True, nrows=sample_size)
                elif source_type == 'xml':
                    df = pd.read_xml(file_path).head(sample_size)
            
            if df is not None:
                sample_data['data'] = df.to_dict('records')
                sample_data['columns'] = list(df.columns)
                sample_data['dtypes'] = {col: str(df[col].dtype) for col in df.columns}
                
    except Exception as e:
        logger.error(f"Ошибка извлечения образца данных: {e}")
        sample_data['error'] = str(e)
    
    return sample_data


@tool
def get_data_profile_tool(
    metadata: Dict[str, Any],
    sample_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Создание профиля данных на основе метаданных и образца
    
    Args:
        metadata: Метаданные источника
        sample_data: Образец данных
        
    Returns:
        Профиль данных с рекомендациями по хранилищу
    """
    profile = {
        'data_characteristics': {},
        'storage_recommendations': [],
        'optimization_hints': []
    }
    
    try:
        # Анализ характеристик данных
        if metadata.get('columns'):
            total_columns = len(metadata['columns'])
            
            # Подсчет типов колонок
            column_types = {}
            for col_name, col_info in metadata['columns'].items():
                dtype = col_info.get('dtype', 'unknown')
                if 'int' in dtype:
                    col_type = 'integer'
                elif 'float' in dtype:
                    col_type = 'numeric'
                elif 'object' in dtype or 'str' in dtype:
                    col_type = 'text'
                elif 'datetime' in dtype or 'date' in dtype:
                    col_type = 'temporal'
                else:
                    col_type = 'other'
                
                column_types[col_type] = column_types.get(col_type, 0) + 1
            
            profile['data_characteristics'] = {
                'total_columns': total_columns,
                'column_types': column_types,
                'has_temporal_data': column_types.get('temporal', 0) > 0,
                'mostly_numeric': column_types.get('numeric', 0) + column_types.get('integer', 0) > total_columns / 2,
                'has_text_data': column_types.get('text', 0) > 0
            }
            
            # Рекомендации по хранилищу
            if profile['data_characteristics']['has_temporal_data'] and \
               profile['data_characteristics']['mostly_numeric']:
                profile['storage_recommendations'].append({
                    'storage': 'clickhouse',
                    'reason': 'Временные ряды с числовыми данными - оптимально для ClickHouse',
                    'priority': 1
                })
            
            if column_types.get('text', 0) > total_columns / 2:
                profile['storage_recommendations'].append({
                    'storage': 'postgres',
                    'reason': 'Преимущественно текстовые данные - PostgreSQL обеспечит гибкость',
                    'priority': 1
                })
            
            # Если данные большие и неструктурированные
            if metadata.get('statistics', {}).get('memory_usage', 0) > 100_000_000:  # > 100 MB
                profile['storage_recommendations'].append({
                    'storage': 'hdfs',
                    'reason': 'Большой объем данных - рекомендуется HDFS для хранения',
                    'priority': 2
                })
            
            # Подсказки по оптимизации
            if profile['data_characteristics']['has_temporal_data']:
                profile['optimization_hints'].append('Рекомендуется партицирование по дате')
            
            high_cardinality_cols = [
                col for col, info in metadata['columns'].items()
                if info.get('unique_count', 0) > metadata.get('row_count', 1) * 0.9
            ]
            
            if high_cardinality_cols:
                profile['optimization_hints'].append(
                    f'Колонки с высокой кардинальностью ({", ".join(high_cardinality_cols[:3])}) - рекомендуются индексы'
                )
            
            # Если нет явных рекомендаций, даем универсальную
            if not profile['storage_recommendations']:
                profile['storage_recommendations'].append({
                    'storage': 'postgres',
                    'reason': 'Универсальное решение для структурированных данных',
                    'priority': 3
                })
                
    except Exception as e:
        logger.error(f"Ошибка создания профиля данных: {e}")
        profile['error'] = str(e)
    
    return profile
