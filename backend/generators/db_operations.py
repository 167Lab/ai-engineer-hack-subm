"""
Типовые операции с базами данных для ETL генератора
"""
import logging
from typing import Dict, Any, List
import pandas as pd

logger = logging.getLogger(__name__)


class DatabaseOperations:
    """Типовые операции для работы с различными базами данных в ETL pipeline"""
    
    @staticmethod
    def get_postgres_loader_code(dag_id: str, target_table: str) -> str:
        """Генерация кода для загрузки в PostgreSQL"""
        return f"""    # Реальная загрузка в PostgreSQL
    try:
        from sqlalchemy import create_engine
        import os
        
        # Получаем параметры подключения из переменных окружения или используем по умолчанию
        connection_string = os.getenv(
            'POSTGRES_CONNECTION_STRING', 
            "postgresql://airflow:airflow@postgres:5432/etl_data"
        )
        
        engine = create_engine(connection_string)
        
        # Загружаем данные в таблицу в схеме processed
        df.to_sql(
            '{target_table}', 
            engine, 
            schema='processed',
            if_exists='append',  # можно изменить на 'replace' для полной замены
            index=False,
            method='multi'  # оптимизация для больших данных
        )
        
        row_count = len(df)
        logger.info("Успешно загружено %d строк в PostgreSQL таблицу processed.{target_table}" % row_count)
        
        # Дополнительно можем выполнить проверку
        with engine.connect() as conn:
            result = conn.execute(f"SELECT COUNT(*) FROM processed.{target_table}").fetchone()
            total_rows = result[0]
            logger.info("Всего строк в таблице processed.{target_table}: %d" % total_rows)
            
    except Exception as e:
        logger.error("Ошибка загрузки в PostgreSQL: %s" % str(e))
        raise
"""

    @staticmethod
    def get_clickhouse_loader_code(dag_id: str, target_table: str) -> str:
        """Генерация кода для загрузки в ClickHouse"""
        return f"""
    # Реальная загрузка в ClickHouse
    try:
        from clickhouse_driver import Client
        import os
        
        # Параметры подключения
        clickhouse_host = os.getenv('CLICKHOUSE_HOST', 'clickhouse')
        clickhouse_port = int(os.getenv('CLICKHOUSE_PORT', '9000'))
        
        client = Client(host=clickhouse_host, port=clickhouse_port)
        
        # Автоматическое создание DDL на основе данных
        columns = []
        for col, dtype in df.dtypes.items():
            col_clean = col.replace(' ', '_').replace('-', '_')  # Очистка имен колонок
            if dtype == 'object':
                columns.append(f"`{{col_clean}}` String")
            elif dtype in ['int64', 'int32']:
                columns.append(f"`{{col_clean}}` Int64")
            elif dtype in ['float64', 'float32']:
                columns.append(f"`{{col_clean}}` Float64")
            elif 'datetime' in str(dtype):
                columns.append(f"`{{col_clean}}` DateTime")
            else:
                columns.append(f"`{{col_clean}}` String")
        
        # Создание таблицы если не существует
        create_table_query = f\"\"\"
        CREATE TABLE IF NOT EXISTS {target_table} (
            {{', '.join(columns)}}
        ) ENGINE = MergeTree()
        ORDER BY tuple()
        \"\"\"
        
        client.execute(create_table_query)
        logger.info(f"Создана/обновлена таблица {target_table} в ClickHouse")
        
        # Подготовка данных для вставки
        data_rows = df.values.tolist()
        
        # Вставка данных батчами для оптимизации
        batch_size = 1000
        total_rows = len(data_rows)
        
        for i in range(0, total_rows, batch_size):
            batch = data_rows[i:i + batch_size]
            client.execute(f"INSERT INTO {target_table} VALUES", batch)
            logger.info(f"Загружен батч {{i+1}}-{{min(i+batch_size, total_rows)}} из {{total_rows}}")
        
        logger.info(f"Успешно загружено {{total_rows}} строк в ClickHouse таблицу {target_table}")
        
        # Проверка загрузки
        result = client.execute(f"SELECT COUNT(*) FROM {target_table}")
        total_in_table = result[0][0]
        logger.info(f"Всего строк в таблице {target_table}: {{total_in_table}}")
        
    except Exception as e:
        logger.error("Ошибка загрузки в ClickHouse: %s" % str(e))
        raise
"""

    @staticmethod  
    def get_hdfs_loader_code(dag_id: str, target_table: str) -> str:
        """Генерация кода для загрузки в HDFS"""
        return f"""
    # Реальная загрузка в HDFS
    try:
        from hdfs import InsecureClient
        import os
        from datetime import datetime
        
        # Параметры подключения к HDFS
        hdfs_url = os.getenv('HDFS_URL', 'http://hadoop-namenode:9870')
        hdfs_user = os.getenv('HDFS_USER', 'airflow')
        
        hdfs_client = InsecureClient(hdfs_url, user=hdfs_user)
        
        # Создание директории если не существует
        base_path = '/data/processed'
        try:
            hdfs_client.makedirs(base_path)
        except Exception:
            pass  # Директория уже существует
        
        # Генерация уникального имени файла с временной меткой
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{dag_id}_{target_table}_{{timestamp}}.csv"
        hdfs_path = f"{{base_path}}/{{filename}}"
        
        # Сохранение данных в различных форматах
        # CSV для совместимости
        csv_data = df.to_csv(index=False)
        hdfs_client.write(hdfs_path, csv_data, encoding='utf-8', overwrite=True)
        
        # Дополнительно Parquet для аналитики (если поддерживается)
        try:
            parquet_path = hdfs_path.replace('.csv', '.parquet')
            parquet_data = df.to_parquet(engine='pyarrow')
            hdfs_client.write(parquet_path, parquet_data, overwrite=True)
            logger.info(f"Дополнительно сохранен Parquet: {{parquet_path}}")
        except Exception as parquet_error:
            logger.warning(f"Не удалось сохранить Parquet: {{parquet_error}}")
        
        # Проверка записи
        file_info = hdfs_client.status(hdfs_path)
        file_size = file_info['length']
        
        logger.info(f"Успешно загружено {{len(df)}} строк в HDFS")
        logger.info(f"Путь: {{hdfs_path}}")
        logger.info(f"Размер файла: {{file_size}} байт")
        
        # Создание метаданных файла
        metadata = {{
            'dag_id': '{dag_id}',
            'table': '{target_table}',
            'rows': len(df),
            'columns': list(df.columns),
            'timestamp': timestamp,
            'file_size': file_size,
            'hdfs_path': hdfs_path
        }}
        
        import json
        metadata_path = hdfs_path.replace('.csv', '_metadata.json')
        hdfs_client.write(metadata_path, json.dumps(metadata, indent=2), overwrite=True)
        logger.info(f"Метаданные сохранены: {{metadata_path}}")
        
    except Exception as e:
        logger.error("Ошибка загрузки в HDFS: %s" % str(e))
        raise
"""

    @classmethod
    def get_enhanced_extract_code(cls, source_type: str, source_path: str, dag_id: str) -> str:
        """Улучшенный код извлечения с обработкой ошибок"""
        return f"""
def extract_data():
    '''Извлечение данных из источника {source_type}'''
    import pandas as pd
    import logging
    import os
    
    logger = logging.getLogger(__name__)
    logger.info(f"Начало извлечения данных из {source_type}")
    
    try:
        # Проверка существования файла
        if not os.path.exists('{source_path}'):
            raise FileNotFoundError(f"Файл источника данных не найден: {source_path}")
        
        # Загрузка данных в зависимости от типа
        if '{source_type}' == 'csv':
            df = pd.read_csv('{source_path}')
            logger.info(f"Загружено {{len(df)}} строк из CSV файла")
            
        elif '{source_type}' == 'json':
            df = pd.read_json('{source_path}')
            logger.info(f"Загружено {{len(df)}} строк из JSON файла")
            
        elif '{source_type}' == 'xml':
            df = pd.read_xml('{source_path}')
            logger.info(f"Загружено {{len(df)}} строк из XML файла")
            
        elif '{source_type}' == 'parquet':
            df = pd.read_parquet('{source_path}')
            logger.info(f"Загружено {{len(df)}} строк из Parquet файла")
            
        else:
            raise ValueError(f"Неподдерживаемый тип источника: {source_type}")
        
        # Базовая валидация данных
        if df.empty:
            raise ValueError("Источник данных пуст")
            
        logger.info(f"Информация о данных:")
        logger.info(f"   - Строк: {{len(df)}}")
        logger.info(f"   - Колонок: {{len(df.columns)}}")
        logger.info(f"   - Колонки: {{', '.join(df.columns)}}")
        
        # Создание директории для временных файлов
        temp_dir = '/opt/airflow/data/temp'
        os.makedirs(temp_dir, exist_ok=True)
        
        # Сохранение во временное расположение
        temp_path = '/opt/airflow/data/temp/{dag_id}_extracted.parquet'
        df.to_parquet(temp_path, index=False)
        logger.info("💾 Данные сохранены во временный файл: %s" % temp_path)
        
        return temp_path
        
    except Exception as e:
        logger.error("Ошибка извлечения данных: %s" % str(e))
        raise
"""

    @classmethod
    def get_enhanced_transform_code(cls, dag_id: str) -> str:
        """Улучшенный код трансформации с дополнительной обработкой"""
        return """
def transform_data():
    '''Расширенная трансформация данных'''
    import pandas as pd
    import logging
    import os
    
    logger = logging.getLogger(__name__)
    logger.info("Начало трансформации данных")
    
    try:
        temp_path = '/opt/airflow/data/temp/{dag_id}_extracted.parquet'
        
        if not os.path.exists(temp_path):
            raise FileNotFoundError(f"Файл с извлеченными данными не найден: {temp_path}")
            
        df = pd.read_parquet(temp_path)
        initial_rows = len(df)
        logger.info(f"Загружено {initial_rows} строк для трансформации")
        
        # Детальная трансформация данных
        transformation_steps = []
        
        # 1. Обработка пустых значений
        null_counts = df.isnull().sum()
        if null_counts.sum() > 0:
            logger.info(f"Найдено пустых значений: {null_counts.sum()}")
            
            # Стратегии обработки пустых значений по типам колонок
            for col in df.columns:
                if df[col].dtype in ['int64', 'float64']:
                    df[col].fillna(df[col].mean(), inplace=True)
                else:
                    df[col].fillna('Unknown', inplace=True)
            
            transformation_steps.append(f"Заполнены пустые значения")
        
        # 2. Удаление дубликатов
        duplicates = df.duplicated().sum()
        if duplicates > 0:
            df = df.drop_duplicates()
            transformation_steps.append(f"Удалено {duplicates} дубликатов")
            logger.info(f"Удалено {duplicates} дубликатов")
        
        # 3. Стандартизация данных
        # Приведение строковых колонок к нижнему регистру где это имеет смысл
        string_columns = df.select_dtypes(include=['object']).columns
        for col in string_columns:
            if col.lower() in ['email', 'city', 'department']:
                df[col] = df[col].astype(str).str.strip().str.title()
                transformation_steps.append(f"Стандартизирована колонка {col}")
        
        # 4. Добавление метаданных
        df['processed_at'] = pd.Timestamp.now()
        df['processing_batch_id'] = '{{dag_id}}'
        transformation_steps.append("Добавлены метаданные обработки")
        
        final_rows = len(df)
        logger.info(f"Трансформация завершена: {initial_rows} → {final_rows} строк")
        
        if transformation_steps:
            logger.info("Выполненные трансформации:")
            for step in transformation_steps:
                logger.info(f"   - {step}")
        
        # Сохранение трансформированных данных
        transformed_path = '/opt/airflow/data/temp/{dag_id}_transformed.parquet'
        df.to_parquet(transformed_path, index=False)
        logger.info(f"💾 Трансформированные данные сохранены: {transformed_path}")
        
        return transformed_path
        
    except Exception as e:
        logger.error("Ошибка трансформации данных: %s" % str(e))
        raise
"""


def get_complete_dag_template() -> str:
    """Получение полного шаблона DAG с реальными операциями"""
    return """
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
import pandas as pd
import logging
import os

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

{extract_function}

{transform_function}

def load_data():
    '''Загрузка данных в целевое хранилище {target_type}'''
    import pandas as pd
    import logging
    import os
    
    logger = logging.getLogger(__name__)
    logger.info("Начало загрузки данных в {target_type}")
    
    transformed_path = '/opt/airflow/data/temp/{{dag_id}}_transformed.parquet'
    
    if not os.path.exists(transformed_path):
        raise FileNotFoundError(f"Файл с трансформированными данными не найден: {transformed_path}")
        
    df = pd.read_parquet(transformed_path)
    logger.info("Загружено %d строк для записи в целевое хранилище" % len(df))
    
{loader_function}
    
    logger.info("Загрузка данных завершена успешно")

# Аргументы по умолчанию для DAG
default_args = {{
    'owner': '{owner}',
    'depends_on_past': False,
    'start_date': datetime({start_date}),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': {retries},
    'retry_delay': timedelta(minutes={retry_delay})
}}

# Определение DAG
with DAG(
    '{dag_id}',
    default_args=default_args,
    description='{description}',
    schedule_interval='{schedule}',
    catchup=False,
    tags=['generated', 'etl', '{source_type}', '{target_type}']
) as dag:
    
    # Задача извлечения данных
    extract_task = PythonOperator(
        task_id='extract_data',
        python_callable=extract_data,
        doc_md='''### Извлечение данных
        
        **Источник**: {source_type}
        **Путь**: {source_path}
        
        Извлекает данные из источника с валидацией и базовой проверкой качества.
        '''
    )
    
    # Задача трансформации данных  
    transform_task = PythonOperator(
        task_id='transform_data',
        python_callable=transform_data,
        doc_md='''### Трансформация данных
        
        Выполняет комплексную очистку и трансформацию данных:
        - Обработка пустых значений
        - Удаление дубликатов  
        - Стандартизация форматов
        - Добавление метаданных обработки
        '''
    )
    
    # Задача загрузки данных
    load_task = PythonOperator(
        task_id='load_data', 
        python_callable=load_data,
        doc_md='''### 📤 Загрузка данных
        
        **Целевая система**: {target_type}
        **Таблица**: {target_table}
        
        Загружает обработанные данные в целевую систему с проверкой результата.
        '''
    )
    
    # Определение зависимостей задач
    extract_task >> transform_task >> load_task
"""
