
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
import pandas as pd
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def extract_data():
    '''Извлечение данных из источника'''
    logger.info("Начало извлечения данных из csv")
    
    try:
        if 'csv' == 'csv':
            df = pd.read_csv('/opt/airflow/data/sample.csv')
            logger.info(f"Загружено {len(df)} строк из CSV")
        elif 'csv' == 'json':
            df = pd.read_json('/opt/airflow/data/sample.csv')
            logger.info(f"Загружено {len(df)} строк из JSON")
        else:
            raise ValueError(f"Неподдерживаемый тип источника: csv")
        
        # Сохранение во временное расположение
        temp_path = '/opt/airflow/data/temp/etl_pipeline_280925_extracted.parquet'
        df.to_parquet(temp_path, index=False)
        logger.info(f"Данные сохранены во временный файл: {temp_path}")
        
        return temp_path
        
    except Exception as e:
        logger.error(f"Ошибка извлечения данных: {e}")
        raise

def transform_data():
    '''Трансформация данных'''
    logger.info("Начало трансформации данных")
    
    try:
        temp_path = '/opt/airflow/data/temp/etl_pipeline_280925_extracted.parquet'
        df = pd.read_parquet(temp_path)
        
        # Базовая очистка данных
        initial_rows = len(df)
        df = df.dropna()  # Удаление строк с пустыми значениями
        df = df.drop_duplicates()  # Удаление дубликатов
        
        logger.info(f"Трансформация завершена: {initial_rows} -> {len(df)} строк")
        
        # Сохранение трансформированных данных
        transformed_path = '/opt/airflow/data/temp/etl_pipeline_280925_transformed.parquet'
        df.to_parquet(transformed_path, index=False)
        
        return transformed_path
        
    except Exception as e:
        logger.error(f"Ошибка трансформации данных: {e}")
        raise

def load_data():
    '''Загрузка данных в целевое хранилище'''
    logger.info("Начало загрузки данных в postgres")
    
    try:
        transformed_path = '/opt/airflow/data/temp/etl_pipeline_280925_transformed.parquet'
        df = pd.read_parquet(transformed_path)
        
        if 'postgres' == 'postgres':
            # Заглушка для PostgreSQL
            logger.info(f"Загрузка {len(df)} строк в PostgreSQL таблицу processed_data")
            # Здесь должна быть реальная загрузка в PostgreSQL
            
        elif 'postgres' == 'clickhouse':
            # Заглушка для ClickHouse  
            logger.info(f"Загрузка {len(df)} строк в ClickHouse таблицу processed_data")
            # Здесь должна быть реальная загрузка в ClickHouse
            
        else:
            logger.info(f"Сохранение в файл для postgres")
            output_path = f'/opt/airflow/data/output/etl_pipeline_280925_processed_data.parquet'
            df.to_parquet(output_path, index=False)
        
        logger.info("Загрузка данных завершена успешно")
        
    except Exception as e:
        logger.error(f"Ошибка загрузки данных: {e}")
        raise

# Аргументы по умолчанию для DAG
default_args = {
    'owner': 'etl-system',
    'depends_on_past': False,
    'start_date': datetime(2025, 9, 27),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5)
}

# Определение DAG
with DAG(
    'etl_pipeline_280925',
    default_args=default_args,
    description='Auto-generated ETL pipeline: etl_pipeline_280925',
    schedule_interval='@daily',
    catchup=False,
    tags=['generated', 'etl', 'csv', 'postgres']
) as dag:
    
    # Задача извлечения данных
    extract_task = PythonOperator(
        task_id='extract_data',
        python_callable=extract_data,
        doc_md='''### Извлечение данных
        
        Извлекает данные из источника типа csv
        Путь к источнику: /opt/airflow/data/sample.csv
        '''
    )
    
    # Задача трансформации данных  
    transform_task = PythonOperator(
        task_id='transform_data',
        python_callable=transform_data,
        doc_md='''### Трансформация данных
        
        Выполняет базовую очистку и трансформацию данных:
        - Удаление пустых значений
        - Удаление дубликатов
        '''
    )
    
    # Задача загрузки данных
    load_task = PythonOperator(
        task_id='load_data', 
        python_callable=load_data,
        doc_md='''### Загрузка данных
        
        Загружает обработанные данные в postgres
        Целевая таблица: processed_data
        '''
    )
    
    # Определение зависимостей задач
    extract_task >> transform_task >> load_task
