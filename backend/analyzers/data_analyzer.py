"""
Модуль анализа файловых источников данных
"""
import pandas as pd
import numpy as np
from typing import Dict, Any, List
from pathlib import Path
import json


class DataSourceAnalyzer:
    """Анализатор файловых источников данных (CSV, JSON, XML)"""
    
    def __init__(self):
        self.supported_formats = ['csv', 'json', 'xml']
        
    async def analyze_file_source(self, file_path: str = None, file_content: str = None, file_name: str = None, sample_size: int = 1000) -> Dict[str, Any]:
        """
        Анализ файлового источника данных
        
        Args:
            file_path: Путь к файлу (для файлов на сервере)
            file_content: Содержимое файла (для загруженных файлов)
            file_name: Имя файла (для определения формата)
            sample_size: Размер выборки для анализа
            
        Returns:
            Dict с результатами анализа
        """
        try:
            # Определяем формат файла
            if file_name:
                file_ext = Path(file_name).suffix.lower()
            elif file_path:
                file_ext = Path(file_path).suffix.lower()
            else:
                raise ValueError("Необходимо указать либо file_path, либо file_name")
            
            # Загружаем данные
            if file_content:
                # Анализируем содержимое файла
                from io import StringIO
                df = self._read_from_content(file_content, file_ext, sample_size)
            elif file_path:
                # Анализируем файл по пути
                df = self._read_from_path(file_path, file_ext, sample_size)
            else:
                raise ValueError("Необходимо указать либо file_path, либо file_content")
            
            return self._analyze_dataframe(df)
            
        except Exception as e:
            return {
                'error': str(e),
                'analysis_status': 'failed'
            }
    
    def _read_from_content(self, content: str, file_ext: str, sample_size: int) -> pd.DataFrame:
        """Чтение данных из содержимого файла"""
        from io import StringIO
        
        if file_ext == '.csv':
            return pd.read_csv(StringIO(content), nrows=sample_size)
        elif file_ext == '.json':
            return pd.read_json(StringIO(content), lines=True, nrows=sample_size)
        elif file_ext == '.xml':
            return pd.read_xml(StringIO(content), rows=sample_size)
        else:
            raise ValueError(f"Неподдерживаемый формат файла: {file_ext}")
    
    def _read_from_path(self, file_path: str, file_ext: str, sample_size: int) -> pd.DataFrame:
        """Чтение данных из файла по пути"""
        if file_ext == '.csv':
            return pd.read_csv(file_path, nrows=sample_size)
        elif file_ext == '.json':
            return pd.read_json(file_path, lines=True, nrows=sample_size)
        elif file_ext == '.xml':
            return pd.read_xml(file_path, rows=sample_size)
        else:
            raise ValueError(f"Неподдерживаемый формат файла: {file_ext}")
    
    def _analyze_dataframe(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Анализ DataFrame
        
        Args:
            df: DataFrame для анализа
            
        Returns:
            Dict с результатами анализа
        """
        analysis = {
            'analysis_status': 'success',
            'metadata': {
                'row_count': len(df),
                'column_count': len(df.columns),
                'columns': {}
            },
            'data_quality': {},
            'recommendations': {}
        }
        
        # Анализ колонок
        for column in df.columns:
            col_analysis = {
                'dtype': str(df[column].dtype),
                'null_count': int(df[column].isnull().sum()),
                'null_percentage': float((df[column].isnull().sum() / len(df)) * 100),
                'unique_count': int(df[column].nunique()),
                'sample_values': df[column].dropna().head(5).tolist()
            }
            
            if df[column].dtype == 'object':
                col_analysis['max_length'] = int(df[column].str.len().max()) if not df[column].str.len().empty else 0
                col_analysis['avg_length'] = float(df[column].str.len().mean()) if not df[column].str.len().empty else 0.0
            
            analysis['metadata']['columns'][column] = col_analysis
        
        # Оценка качества данных
        analysis['data_quality'] = {
            'total_nulls': int(df.isnull().sum().sum()),
            'duplicate_rows': int(df.duplicated().sum()),
            'completeness_score': float(1 - (df.isnull().sum().sum() / (len(df) * len(df.columns))))
        }
        
        # Генерация рекомендаций
        analysis['recommendations'] = self._generate_storage_recommendations(analysis)
        
        return analysis
    
    def _generate_storage_recommendations(self, analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Генерация рекомендаций по хранению данных
        
        Args:
            analysis: Результаты анализа
            
        Returns:
            Список рекомендаций
        """
        recommendations = []
        
        row_count = analysis['metadata']['row_count']
        column_count = analysis['metadata']['column_count']
        completeness_score = analysis['data_quality']['completeness_score']
        
        # Рекомендация по основному хранилищу
        if row_count < 100000 and completeness_score > 0.95:
            recommendations.append({
                'storage_type': 'PostgreSQL',
                'confidence': 0.9,
                'reasoning': 'Небольшой объем данных с высоким качеством подходит для PostgreSQL',
                'suggested_optimizations': [
                    'Создать индексы для часто используемых полей',
                    'Использовать констрейнты для валидации данных'
                ]
            })
        elif row_count > 1000000:
            recommendations.append({
                'storage_type': 'ClickHouse', 
                'confidence': 0.85,
                'reasoning': 'Большой объем данных требует колоночного хранения ClickHouse',
                'suggested_optimizations': [
                    'Партицирование по дате если есть временные данные',
                    'Использовать MergeTree движок',
                    'Сжатие данных LZ4'
                ]
            })
        else:
            recommendations.append({
                'storage_type': 'HDFS',
                'confidence': 0.7,
                'reasoning': 'Средний объем данных можно хранить в HDFS для последующей обработки',
                'suggested_optimizations': [
                    'Сохранить в формате Parquet для эффективности',
                    'Использовать партицирование по годам/месяцам'
                ]
            })
            
        # Дополнительные рекомендации по качеству данных
        if completeness_score < 0.8:
            recommendations.append({
                'storage_type': 'Data Quality Pipeline',
                'confidence': 0.95,
                'reasoning': 'Низкое качество данных требует предварительной очистки',
                'suggested_optimizations': [
                    'Добавить этап очистки и валидации данных',
                    'Заполнить пропущенные значения',
                    'Удалить дубликаты'
                ]
            })
            
        return recommendations