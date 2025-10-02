"""
Streaming анализатор для обработки больших файлов без загрузки в память
Использует chunk-based processing и оптимизированные алгоритмы
"""
import pandas as pd
import logging
import os
import json
import xml.etree.ElementTree as ET
from typing import Dict, Any, Optional
import asyncio
from pathlib import Path

logger = logging.getLogger(__name__)


class StreamingAnalyzer:
    """
    Анализатор для больших файлов с потоковой обработкой
    Не загружает весь файл в память, обрабатывает по частям
    """
    
    def __init__(self, chunk_size: int = 10000):
        """
        Args:
            chunk_size: Размер чанка для обработки (строк)
        """
        self.chunk_size = chunk_size
        
    def analyze_file_stream(
        self, 
        file_path: str, 
        source_type: str, 
        sample_size: int = 1000,
        original_filename: str = None
    ) -> Dict[str, Any]:
        """
        Streaming анализ файла по частям
        
        Args:
            file_path: Путь к временному файлу
            source_type: Тип файла (csv, json, xml)
            sample_size: Количество строк для анализа
            original_filename: Исходное имя файла
            
        Returns:
            Результат анализа с метаданными и статистикой
        """
        logger.info(f"🔍 Начало streaming анализа: {original_filename} ({source_type})")
        
        try:
            # Получаем размер файла
            file_size = os.path.getsize(file_path)
            logger.info(f"📊 Размер файла: {file_size:,} bytes")
            
            # Выбираем метод анализа в зависимости от типа файла
            if source_type == 'csv':
                result = await self._analyze_csv_stream(file_path, sample_size)
            elif source_type == 'json':
                result = await self._analyze_json_stream(file_path, sample_size)
            elif source_type == 'xml':
                result = await self._analyze_xml_stream(file_path, sample_size)
            else:
                raise ValueError(f"Неподдерживаемый тип файла: {source_type}")
            
            # Добавляем метаданные
            result['file_metadata'] = {
                'original_filename': original_filename or Path(file_path).name,
                'file_size': file_size,
                'source_type': source_type,
                'sample_size': sample_size,
                'analysis_method': 'streaming',
                'chunk_size': self.chunk_size
            }
            
            logger.info(f"✅ Streaming анализ завершен: {result.get('total_rows', 0)} строк проанализировано")
            return result
            
        except Exception as e:
            logger.exception(f"❌ Ошибка streaming анализа: {e}")
            raise
    
    async def _analyze_csv_stream(self, file_path: str, sample_size: int) -> Dict[str, Any]:
        """Streaming анализ CSV файла"""
        logger.info("📊 CSV streaming анализ...")
        
        # Читаем файл по чанкам
        chunk_iter = pd.read_csv(file_path, chunksize=self.chunk_size)
        
        total_rows = 0
        columns = None
        dtypes = None
        sample_data = []
        null_counts = {}
        numeric_stats = {}
        
        try:
            for i, chunk in enumerate(chunk_iter):
                total_rows += len(chunk)
                
                # Сохраняем информацию о колонках с первого чанка
                if columns is None:
                    columns = list(chunk.columns)
                    dtypes = {col: str(dtype) for col, dtype in chunk.dtypes.items()}
                    null_counts = {col: 0 for col in columns}
                    numeric_stats = {}
                
                # Собираем статистику по null значениям
                chunk_nulls = chunk.isnull().sum()
                for col in columns:
                    null_counts[col] += chunk_nulls[col]
                
                # Собираем образцы данных (только из первых чанков)
                if len(sample_data) < sample_size:
                    sample_chunk = chunk.head(min(sample_size - len(sample_data), len(chunk)))
                    sample_data.extend(sample_chunk.to_dict('records'))
                
                # Статистика по числовым колонкам (только из первого чанка для производительности)
                if i == 0:
                    numeric_columns = chunk.select_dtypes(include=['number']).columns
                    for col in numeric_columns:
                        if col not in numeric_stats:
                            numeric_stats[col] = {
                                'min': float(chunk[col].min()),
                                'max': float(chunk[col].max()),
                                'mean': float(chunk[col].mean()),
                                'std': float(chunk[col].std()) if chunk[col].std() == chunk[col].std() else 0  # NaN check
                            }
                
                logger.info(f"📈 Обработан чанк {i+1}: {len(chunk)} строк (всего: {total_rows:,})")
                
                # Прерываем если достигнут лимит для анализа
                if total_rows >= sample_size * 10:  # Анализируем в 10 раз больше чем sample
                    logger.info(f"🛑 Достигнут лимит анализа: {total_rows:,} строк")
                    break
        
        except pd.errors.EmptyDataError:
            logger.warning("⚠️ Пустой CSV файл")
            return {
                'total_rows': 0,
                'columns': [],
                'error': 'Пустой файл'
            }
        
        return {
            'total_rows': total_rows,
            'columns': columns,
            'column_types': dtypes,
            'sample_data': sample_data[:sample_size],
            'null_counts': null_counts,
            'numeric_statistics': numeric_stats,
            'data_quality_score': self._calculate_quality_score(null_counts, total_rows),
            'estimated_memory_usage': total_rows * len(columns) * 8,  # Приблизительная оценка
        }
    
    async def _analyze_json_stream(self, file_path: str, sample_size: int) -> Dict[str, Any]:
        """Streaming анализ JSON файла"""
        logger.info("📊 JSON streaming анализ...")
        
        try:
            sample_data = []
            total_records = 0
            
            # Попробуем определить структуру JSON файла
            with open(file_path, 'r', encoding='utf-8') as file:
                # Читаем первые несколько KB для определения структуры
                preview = file.read(8192)
                file.seek(0)  # Возвращаемся к началу
                
                # Определяем тип JSON структуры
                if preview.strip().startswith('['):
                    # JSON Array
                    data = json.load(file)
                    if isinstance(data, list):
                        total_records = len(data)
                        sample_data = data[:sample_size]
                    else:
                        sample_data = [data]
                        total_records = 1
                        
                elif preview.strip().startswith('{'):
                    # JSON Lines или один JSON объект
                    file.seek(0)
                    try:
                        # Пробуем загрузить как один объект
                        data = json.load(file)
                        sample_data = [data]
                        total_records = 1
                    except json.JSONDecodeError:
                        # Это JSON Lines - читаем построчно
                        file.seek(0)
                        for line_num, line in enumerate(file):
                            if line.strip():
                                try:
                                    record = json.loads(line)
                                    if len(sample_data) < sample_size:
                                        sample_data.append(record)
                                    total_records += 1
                                    
                                    # Ограничиваем чтение для больших файлов
                                    if line_num > sample_size * 100:
                                        logger.info(f"🛑 Ограничение чтения JSON Lines: {line_num} строк")
                                        break
                                        
                                except json.JSONDecodeError as e:
                                    logger.warning(f"⚠️ Ошибка парсинга JSON строки {line_num}: {e}")
                                    continue
                else:
                    raise ValueError("Неопознанная структура JSON файла")
            
            # Анализируем структуру данных
            columns = set()
            column_types = {}
            
            for record in sample_data:
                if isinstance(record, dict):
                    for key, value in record.items():
                        columns.add(key)
                        if key not in column_types:
                            column_types[key] = type(value).__name__
                        
            return {
                'total_rows': total_records,
                'columns': list(columns),
                'column_types': column_types,
                'sample_data': sample_data,
                'data_structure': 'json_array' if preview.strip().startswith('[') else 'json_lines' if total_records > 1 else 'json_object',
                'estimated_memory_usage': len(str(sample_data)) * (total_records // len(sample_data)) if sample_data else 0,
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка анализа JSON файла: {e}")
            raise
    
    async def _analyze_xml_stream(self, file_path: str, sample_size: int) -> Dict[str, Any]:
        """Streaming анализ XML файла"""
        logger.info("📊 XML streaming анализ...")
        
        try:
            # Используем iterparse для streaming обработки больших XML файлов
            sample_data = []
            total_records = 0
            root_elements = set()
            
            # Первый проход - определяем структуру
            for event, elem in ET.iterparse(file_path, events=('start', 'end')):
                if event == 'start' and elem.tag not in root_elements:
                    root_elements.add(elem.tag)
                
                if event == 'end' and len(sample_data) < sample_size:
                    # Конвертируем XML элемент в словарь
                    record = self._xml_to_dict(elem)
                    if record:  # Если элемент содержит данные
                        sample_data.append(record)
                    total_records += 1
                
                # Очищаем элемент из памяти
                if event == 'end':
                    elem.clear()
                
                # Ограничиваем для больших файлов
                if total_records > sample_size * 100:
                    logger.info(f"🛑 Ограничение чтения XML: {total_records} элементов")
                    break
            
            # Анализируем колонки из sample данных
            columns = set()
            column_types = {}
            
            for record in sample_data:
                if isinstance(record, dict):
                    for key, value in record.items():
                        columns.add(key)
                        if key not in column_types:
                            column_types[key] = type(value).__name__
            
            return {
                'total_rows': total_records,
                'columns': list(columns),
                'column_types': column_types,
                'sample_data': sample_data,
                'root_elements': list(root_elements),
                'estimated_memory_usage': len(str(sample_data)) * (total_records // len(sample_data)) if sample_data else 0,
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка анализа XML файла: {e}")
            raise
    
    def _xml_to_dict(self, element) -> Dict[str, Any]:
        """Конвертирует XML элемент в словарь"""
        result = {}
        
        # Добавляем атрибуты
        if element.attrib:
            result.update(element.attrib)
        
        # Добавляем текстовое содержимое
        if element.text and element.text.strip():
            result['_text'] = element.text.strip()
        
        # Добавляем дочерние элементы
        for child in element:
            child_dict = self._xml_to_dict(child)
            if child.tag in result:
                # Если элемент уже есть, создаем список
                if not isinstance(result[child.tag], list):
                    result[child.tag] = [result[child.tag]]
                result[child.tag].append(child_dict)
            else:
                result[child.tag] = child_dict
        
        return result
    
    def _calculate_quality_score(self, null_counts: Dict[str, int], total_rows: int) -> float:
        """Вычисляет оценку качества данных (0-100)"""
        if not null_counts or total_rows == 0:
            return 100.0
        
        total_nulls = sum(null_counts.values())
        total_cells = total_rows * len(null_counts)
        null_ratio = total_nulls / total_cells if total_cells > 0 else 0
        
        # Качество = 100% - % пустых значений
        quality_score = (1 - null_ratio) * 100
        return round(quality_score, 2)
