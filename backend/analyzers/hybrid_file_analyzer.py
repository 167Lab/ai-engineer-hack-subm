"""
Гибридный анализатор файлов - интеграция Stack Overflow решения с нашим chunked upload
Объединяет преимущества: MultipartFormDataStreamProvider + Chunked Upload + Memory-Safe анализ
"""
import os
import logging
import tempfile
import json
import pandas as pd
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, Any, Optional, Iterator
from collections import defaultdict

logger = logging.getLogger(__name__)


class HybridFileAnalyzer:
    """
    Гибридный анализатор, использующий лучшие практики из Stack Overflow + наши улучшения
    """
    
    def __init__(self, chunk_size: int = 8192, pandas_chunk_size: int = 10000):
        self.chunk_size = chunk_size          # Размер чанка для чтения файла (байт)
        self.pandas_chunk_size = pandas_chunk_size  # Размер чанка для pandas (строк)
        self.max_memory_usage = 100 * 1024 * 1024   # 100 МБ лимит в памяти
        
    def analyze_uploaded_file(
        self, 
        file_path: str, 
        source_type: str,
        sample_size: int = 1000,
        original_filename: str = None
    ) -> Dict[str, Any]:
        """
        Основной метод анализа с автоматическим выбором стратегии
        
        Args:
            file_path: Путь к файлу (может быть временный из chunked upload)
            source_type: Тип файла (csv, json, xml)
            sample_size: Количество записей для анализа
            original_filename: Исходное имя файла
            
        Returns:
            dict: Результаты анализа без загрузки всего файла в память
        """
        try:
            file_size = os.path.getsize(file_path)
            logger.info(f"🔍 Анализ файла: {original_filename or file_path} ({file_size} bytes), тип: {source_type}")
            
            # Выбираем стратегию на основе размера файла и типа
            if file_size > self.max_memory_usage:
                logger.info(f"📁 Большой файл ({file_size / 1024 / 1024:.1f} МБ) - используем memory-safe анализ")
                return self._analyze_large_file(file_path, source_type, sample_size, original_filename)
            else:
                logger.info(f"📄 Обычный файл ({file_size / 1024:.1f} КБ) - используем оптимизированный анализ")
                return self._analyze_regular_file(file_path, source_type, sample_size, original_filename)
                
        except Exception as e:
            logger.error(f"❌ Ошибка анализа файла {original_filename}: {e}")
            return {
                "error": f"Ошибка анализа файла: {str(e)}",
                "total_rows": 0,
                "columns": [],
                "column_types": {},
                "data_quality_score": 0
            }
    
    def _analyze_large_file(self, file_path: str, source_type: str, sample_size: int, original_filename: str) -> Dict[str, Any]:
        """
        Memory-safe анализ больших файлов (Stack Overflow подход + наши улучшения)
        НИКОГДА не загружает весь файл в память
        """
        logger.info(f"🧠 Memory-safe анализ большого файла: {source_type.upper()}")
        
        if source_type.lower() == 'csv':
            return self._analyze_large_csv(file_path, sample_size, original_filename)
        elif source_type.lower() == 'json':
            return self._analyze_large_json(file_path, sample_size, original_filename)
        elif source_type.lower() == 'xml':
            return self._analyze_large_xml(file_path, sample_size, original_filename)
        else:
            raise ValueError(f"Неподдерживаемый тип файла для memory-safe анализа: {source_type}")
    
    def _analyze_regular_file(self, file_path: str, source_type: str, sample_size: int, original_filename: str) -> Dict[str, Any]:
        """
        Оптимизированный анализ для файлов умеренного размера
        """
        logger.info(f"⚡ Быстрый анализ обычного файла: {source_type.upper()}")
        
        if source_type.lower() == 'csv':
            return self._analyze_regular_csv(file_path, sample_size, original_filename)
        elif source_type.lower() == 'json':
            return self._analyze_regular_json(file_path, sample_size, original_filename)
        elif source_type.lower() == 'xml':
            return self._analyze_regular_xml(file_path, sample_size, original_filename)
        else:
            raise ValueError(f"Неподдерживаемый тип файла: {source_type}")
    
    def _analyze_large_csv(self, file_path: str, sample_size: int, original_filename: str) -> Dict[str, Any]:
        """
        Memory-safe анализ больших CSV файлов
        Использует pandas.read_csv с chunksize - проверенный подход
        """
        total_rows = 0
        column_types = {}
        null_counts = defaultdict(int)
        sample_data = []
        
        try:
            # Читаем файл по чанкам - это НЕ загружает весь файл в память
            chunk_iter = pd.read_csv(file_path, chunksize=self.pandas_chunk_size)
            
            for i, chunk in enumerate(chunk_iter):
                # Инициализируем типы колонок из первого чанка
                if i == 0:
                    column_types = {col: str(dtype) for col, dtype in chunk.dtypes.items()}
                    logger.info(f"📊 Найдено {len(column_types)} колонок в CSV")
                
                # Подсчитываем строки
                chunk_rows = len(chunk)
                total_rows += chunk_rows
                
                # Подсчитываем null значения
                chunk_nulls = chunk.isnull().sum()
                for col, count in chunk_nulls.items():
                    null_counts[col] += count
                
                # Собираем образец данных только до достижения sample_size
                if len(sample_data) < sample_size:
                    needed = sample_size - len(sample_data)
                    sample_chunk = chunk.head(min(needed, chunk_rows))
                    # НЕ используем to_dict('records') - это память!
                    # Вместо этого берем только минимум информации
                    for _, row in sample_chunk.iterrows():
                        if len(sample_data) >= sample_size:
                            break
                        sample_data.append({col: str(val) for col, val in row.items()})
                
                # Логируем прогресс каждые 10 чанков
                if i % 10 == 0:
                    logger.info(f"📈 Обработано чанков: {i+1}, строк: {total_rows}")
                    
                # Останавливаемся если нужно только для анализа структуры
                if total_rows > 100000 and len(sample_data) >= sample_size:
                    logger.info(f"🛑 Ранняя остановка после {total_rows} строк для анализа структуры")
                    break
            
            # Вычисляем качество данных
            total_cells = total_rows * len(column_types) if column_types else 1
            total_nulls = sum(null_counts.values()) 
            data_quality_score = max(0, 100 - (total_nulls / total_cells * 100)) if total_cells > 0 else 100
            
            logger.info(f"✅ CSV анализ завершен: {total_rows} строк, {len(column_types)} колонок, качество: {data_quality_score:.1f}%")
            
            return {
                "total_rows": total_rows,
                "columns": list(column_types.keys()),
                "column_types": column_types,
                "null_counts": dict(null_counts),
                "data_quality_score": data_quality_score,
                "sample_data": sample_data[:sample_size],  # Ограничиваем образец
                "file_size_bytes": os.path.getsize(file_path),
                "analysis_method": "chunked_csv_streaming"
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка анализа CSV: {e}")
            raise
    
    def _analyze_large_json(self, file_path: str, sample_size: int, original_filename: str) -> Dict[str, Any]:
        """
        Memory-safe анализ больших JSON файлов
        НЕ использует json.load() - читает построчно или по частям
        """
        total_records = 0
        column_types = {}
        null_counts = defaultdict(int)
        sample_data = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                # Определяем формат JSON
                first_char = file.read(1)
                file.seek(0)
                
                if first_char == '[':
                    # JSON Array - читаем построчно, а НЕ json.load()!
                    return self._stream_json_array(file, sample_size, original_filename)
                elif first_char == '{':
                    # JSON Lines или single object - читаем построчно
                    return self._stream_json_lines(file, sample_size, original_filename)
                else:
                    raise ValueError("Неизвестный формат JSON файла")
                    
        except Exception as e:
            logger.error(f"❌ Ошибка анализа JSON: {e}")
            raise
    
    def _stream_json_array(self, file, sample_size: int, original_filename: str) -> Dict[str, Any]:
        """
        Потоковое чтение JSON array БЕЗ загрузки в память
        """
        import ijson  # Потоковый JSON парсер - нужно добавить в requirements
        
        total_records = 0
        column_types = {}
        null_counts = defaultdict(int)
        sample_data = []
        
        try:
            # ijson читает JSON по частям, не загружая весь файл
            parser = ijson.parse(file)
            current_object = {}
            in_array = False
            
            for prefix, event, value in parser:
                if prefix == '' and event == 'start_array':
                    in_array = True
                elif prefix.count('.') == 1 and event in ('string', 'number', 'boolean', 'null'):
                    # Это поле объекта в массиве
                    field_name = prefix.split('.')[1]
                    current_object[field_name] = value
                    
                    # Отслеживаем типы
                    if field_name not in column_types:
                        column_types[field_name] = type(value).__name__
                    
                    # Подсчитываем null
                    if value is None:
                        null_counts[field_name] += 1
                        
                elif prefix.count('.') == 0 and event == 'end_map':
                    # Конец объекта в массиве
                    total_records += 1
                    
                    if len(sample_data) < sample_size:
                        sample_data.append(current_object.copy())
                    
                    current_object.clear()
                    
                    if total_records % 10000 == 0:
                        logger.info(f"📈 JSON обработано записей: {total_records}")
                    
                    # Ранний выход для анализа структуры
                    if total_records > 100000 and len(sample_data) >= sample_size:
                        break
            
            data_quality_score = self._calculate_quality_score(total_records, column_types, null_counts)
            
            logger.info(f"✅ JSON анализ завершен: {total_records} записей, {len(column_types)} полей")
            
            return {
                "total_rows": total_records,
                "columns": list(column_types.keys()),
                "column_types": column_types,
                "null_counts": dict(null_counts),
                "data_quality_score": data_quality_score,
                "sample_data": sample_data,
                "file_size_bytes": os.path.getsize(file.name),
                "analysis_method": "streaming_json_ijson"
            }
            
        except ImportError:
            logger.warning("⚠️ ijson не установлен, используем fallback метод")
            return self._analyze_json_fallback(file.name, sample_size, original_filename)
    
    def _stream_json_lines(self, file, sample_size: int, original_filename: str) -> Dict[str, Any]:
        """
        Потоковое чтение JSON Lines формата
        """
        total_records = 0
        column_types = {}
        null_counts = defaultdict(int)
        sample_data = []
        
        for line_num, line in enumerate(file):
            line = line.strip()
            if not line:
                continue
                
            try:
                # Парсим только одну строку за раз - минимум памяти
                record = json.loads(line)
                total_records += 1
                
                # Анализируем структуру
                for field, value in record.items():
                    if field not in column_types:
                        column_types[field] = type(value).__name__
                    
                    if value is None:
                        null_counts[field] += 1
                
                # Собираем образец
                if len(sample_data) < sample_size:
                    sample_data.append(record)
                
                if total_records % 10000 == 0:
                    logger.info(f"📈 JSON Lines обработано: {total_records} строк")
                
                if total_records > 100000 and len(sample_data) >= sample_size:
                    break
                    
            except json.JSONDecodeError as e:
                logger.warning(f"⚠️ Некорректная JSON строка {line_num}: {e}")
                continue
        
        data_quality_score = self._calculate_quality_score(total_records, column_types, null_counts)
        
        logger.info(f"✅ JSON Lines анализ завершен: {total_records} записей")
        
        return {
            "total_rows": total_records,
            "columns": list(column_types.keys()),
            "column_types": column_types,
            "null_counts": dict(null_counts),
            "data_quality_score": data_quality_score,
            "sample_data": sample_data,
            "file_size_bytes": os.path.getsize(file.name),
            "analysis_method": "streaming_json_lines"
        }
    
    def _analyze_large_xml(self, file_path: str, sample_size: int, original_filename: str) -> Dict[str, Any]:
        """
        Memory-safe анализ больших XML файлов с iterparse
        """
        total_records = 0
        column_types = {}
        null_counts = defaultdict(int)
        sample_data = []
        
        try:
            # Используем iterparse для потокового чтения XML
            context = ET.iterparse(file_path, events=("start", "end"))
            context = iter(context)
            event, root = next(context)
            
            # Пытаемся найти повторяющиеся элементы (записи)
            record_tag = None
            
            for event, elem in context:
                if event == "end":
                    # Определяем тег записи из первого элемента
                    if record_tag is None and len(list(elem)) > 0:
                        record_tag = elem.tag
                        logger.info(f"📊 Найден тег записи XML: {record_tag}")
                    
                    # Обрабатываем записи
                    if elem.tag == record_tag:
                        total_records += 1
                        
                        # Анализируем структуру записи
                        record = {}
                        for child in elem:
                            field_name = child.tag
                            field_value = child.text
                            
                            if field_name not in column_types:
                                column_types[field_name] = 'string'  # XML обычно строки
                            
                            if field_value is None or field_value == '':
                                null_counts[field_name] += 1
                            
                            record[field_name] = field_value
                        
                        # Собираем образец
                        if len(sample_data) < sample_size:
                            sample_data.append(record)
                        
                        if total_records % 10000 == 0:
                            logger.info(f"📈 XML обработано записей: {total_records}")
                        
                        if total_records > 100000 and len(sample_data) >= sample_size:
                            break
                    
                    # Очищаем элемент из памяти
                    elem.clear()
                    root.clear()
            
            data_quality_score = self._calculate_quality_score(total_records, column_types, null_counts)
            
            logger.info(f"✅ XML анализ завершен: {total_records} записей")
            
            return {
                "total_rows": total_records,
                "columns": list(column_types.keys()),
                "column_types": column_types,
                "null_counts": dict(null_counts),
                "data_quality_score": data_quality_score,
                "sample_data": sample_data,
                "file_size_bytes": os.path.getsize(file_path),
                "analysis_method": "streaming_xml_iterparse"
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка анализа XML: {e}")
            raise
    
    def _calculate_quality_score(self, total_records: int, column_types: dict, null_counts: dict) -> float:
        """
        Вычисляет оценку качества данных
        """
        if total_records == 0 or not column_types:
            return 100.0
        
        total_cells = total_records * len(column_types)
        total_nulls = sum(null_counts.values())
        
        completeness = max(0, 100 - (total_nulls / total_cells * 100)) if total_cells > 0 else 100
        return round(completeness, 2)
    
    # Fallback методы для маленьких файлов (можно оставить более простую логику)
    def _analyze_regular_csv(self, file_path: str, sample_size: int, original_filename: str) -> Dict[str, Any]:
        """Быстрый анализ небольших CSV"""
        df = pd.read_csv(file_path, nrows=sample_size)  # Читаем только нужное количество строк
        
        return {
            "total_rows": len(df),
            "columns": list(df.columns),
            "column_types": {col: str(dtype) for col, dtype in df.dtypes.items()},
            "null_counts": df.isnull().sum().to_dict(),
            "data_quality_score": round(100 - (df.isnull().sum().sum() / (len(df) * len(df.columns)) * 100), 2),
            "sample_data": df.to_dict('records'),
            "file_size_bytes": os.path.getsize(file_path),
            "analysis_method": "regular_csv_pandas"
        }
    
    def _analyze_regular_json(self, file_path: str, sample_size: int, original_filename: str) -> Dict[str, Any]:
        """Быстрый анализ небольших JSON"""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)  # Можно загрузить маленький файл полностью
            
        if isinstance(data, list):
            sample_data = data[:sample_size]
            total_records = len(data)
        else:
            sample_data = [data]
            total_records = 1
        
        # Анализируем структуру
        column_types = {}
        null_counts = defaultdict(int)
        
        for record in sample_data:
            for field, value in record.items():
                if field not in column_types:
                    column_types[field] = type(value).__name__
                if value is None:
                    null_counts[field] += 1
        
        return {
            "total_rows": total_records,
            "columns": list(column_types.keys()),
            "column_types": column_types,
            "null_counts": dict(null_counts),
            "data_quality_score": self._calculate_quality_score(total_records, column_types, null_counts),
            "sample_data": sample_data,
            "file_size_bytes": os.path.getsize(file_path),
            "analysis_method": "regular_json_load"
        }
    
    def _analyze_regular_xml(self, file_path: str, sample_size: int, original_filename: str) -> Dict[str, Any]:
        """Быстрый анализ небольших XML"""
        # Для небольших XML можно использовать стандартный парсинг
        tree = ET.parse(file_path)
        root = tree.getroot()
        
        # Простой анализ структуры
        records = []
        for child in root:
            record = {subchild.tag: subchild.text for subchild in child}
            records.append(record)
        
        sample_data = records[:sample_size]
        column_types = {}
        null_counts = defaultdict(int)
        
        for record in sample_data:
            for field, value in record.items():
                column_types[field] = 'string'
                if value is None:
                    null_counts[field] += 1
        
        return {
            "total_rows": len(records),
            "columns": list(column_types.keys()),
            "column_types": column_types,
            "null_counts": dict(null_counts),
            "data_quality_score": self._calculate_quality_score(len(records), column_types, null_counts),
            "sample_data": sample_data,
            "file_size_bytes": os.path.getsize(file_path),
            "analysis_method": "regular_xml_etree"
        }
    
    def _analyze_json_fallback(self, file_path: str, sample_size: int, original_filename: str) -> Dict[str, Any]:
        """
        Fallback анализ JSON без ijson - для случаев когда ijson недоступен
        """
        logger.info("📄 Используем fallback JSON анализ")
        
        # Читаем файл построчно и пробуем парсить как JSON Lines
        total_records = 0
        column_types = {}
        null_counts = defaultdict(int)
        sample_data = []
        
        with open(file_path, 'r', encoding='utf-8') as file:
            for line_num, line in enumerate(file):
                line = line.strip()
                if not line:
                    continue
                
                try:
                    record = json.loads(line)
                    total_records += 1
                    
                    for field, value in record.items():
                        if field not in column_types:
                            column_types[field] = type(value).__name__
                        if value is None:
                            null_counts[field] += 1
                    
                    if len(sample_data) < sample_size:
                        sample_data.append(record)
                    
                    # Ограничиваем для больших файлов
                    if line_num > 50000:
                        logger.info(f"🛑 Fallback анализ остановлен после {line_num} строк")
                        break
                        
                except json.JSONDecodeError:
                    continue
        
        return {
            "total_rows": total_records,
            "columns": list(column_types.keys()),
            "column_types": column_types,
            "null_counts": dict(null_counts),
            "data_quality_score": self._calculate_quality_score(total_records, column_types, null_counts),
            "sample_data": sample_data,
            "file_size_bytes": os.path.getsize(file_path),
            "analysis_method": "fallback_json_lines"
        }
