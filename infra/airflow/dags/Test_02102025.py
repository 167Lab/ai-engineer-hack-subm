
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
import pandas as pd
import logging
import os

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def extract_data():
    '''Извлечение данных из источника csv'''
    import pandas as pd
    import logging
    import os
    
    logger = logging.getLogger(__name__)
    logger.info(f"🔄 Начало извлечения данных из csv")
    
    try:
        # Проверка существования файла
        if not os.path.exists('/opt/airflow/data/sample.csv'):
            raise FileNotFoundError(f"Файл источника данных не найден: /opt/airflow/data/sample.csv")
        
        # Загрузка данных в зависимости от типа
        if 'csv' == 'csv':
            df = pd.read_csv('/opt/airflow/data/sample.csv')
            logger.info(f"📄 Загружено {len(df)} строк из CSV файла")
            
        elif 'csv' == 'json':
            df = pd.read_json('/opt/airflow/data/sample.csv')
            logger.info(f"📄 Загружено {len(df)} строк из JSON файла")
            
        elif 'csv' == 'xml':
            df = pd.read_xml('/opt/airflow/data/sample.csv')
            logger.info(f"📄 Загружено {len(df)} строк из XML файла")
            
        elif 'csv' == 'parquet':
            df = pd.read_parquet('/opt/airflow/data/sample.csv')
            logger.info(f"📄 Загружено {len(df)} строк из Parquet файла")
            
        else:
            raise ValueError(f"Неподдерживаемый тип источника: csv")
        
        # Базовая валидация данных
        if df.empty:
            raise ValueError("Источник данных пуст")
            
        logger.info(f"📊 Информация о данных:")
        logger.info(f"   - Строк: {len(df)}")
        logger.info(f"   - Колонок: {len(df.columns)}")
        logger.info(f"   - Колонки: {', '.join(df.columns)}")
        
        # Создание директории для временных файлов
        temp_dir = '/opt/airflow/data/temp'
        os.makedirs(temp_dir, exist_ok=True)
        
        # Сохранение во временное расположение
        temp_path = '/opt/airflow/data/temp/{dag_id}_extracted.parquet'
        df.to_parquet(temp_path, index=False)
        logger.info("Данные сохранены во временный файл: %s" % temp_path)
        
        return temp_path
        
    except Exception as e:
        logger.error("❌ Ошибка извлечения данных: %s" % str(e))
        raise



def transform_data():
    '''Расширенная трансформация данных'''
    import pandas as pd
    import logging
    import os
    
    logger = logging.getLogger(__name__)
    logger.info("🔄 Начало трансформации данных")
    
    try:
        temp_path = '/opt/airflow/data/temp/{{dag_id}}_extracted.parquet'
        
        if not os.path.exists(temp_path):
            raise FileNotFoundError(f"Файл с извлеченными данными не найден: {temp_path}")
            
        df = pd.read_parquet(temp_path)
        initial_rows = len(df)
        logger.info(f"📊 Загружено {initial_rows} строк для трансформации")
        
        # Детальная трансформация данных
        transformation_steps = []
        
        # 1. Обработка пустых значений
        null_counts = df.isnull().sum()
        if null_counts.sum() > 0:
            logger.info(f"🧹 Найдено пустых значений: {null_counts.sum()}")
            
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
            logger.info(f"🔄 Удалено {duplicates} дубликатов")
        
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
        logger.info(f"✅ Трансформация завершена: {initial_rows} → {final_rows} строк")
        
        if transformation_steps:
            logger.info("🔧 Выполненные трансформации:")
            for step in transformation_steps:
                logger.info(f"   - {step}")
        
        # Сохранение трансформированных данных
        transformed_path = '/opt/airflow/data/temp/{{dag_id}}_transformed.parquet'
        df.to_parquet(transformed_path, index=False)
        logger.info(f"Трансформированные данные сохранены: {transformed_path}")
        
        return transformed_path
        
    except Exception as e:
        logger.error("❌ Ошибка трансформации данных: %s" % str(e))
        raise


def load_data():
    '''Загрузка данных в целевое хранилище postgres'''
    import pandas as pd
    import logging
    import os
    
    logger = logging.getLogger(__name__)
    logger.info("🔄 Начало загрузки данных в postgres")
    
    transformed_path = '/opt/airflow/data/temp/{dag_id}_transformed.parquet'
    
    if not os.path.exists(transformed_path):
        raise FileNotFoundError(f"Файл с трансформированными данными не найден: /opt/airflow/data/temp/Test_02102025_transformed.parquet")
        
    df = pd.read_parquet(transformed_path)
    logger.info("📊 Загружено %d строк для записи в целевое хранилище" % len(df))
    
    # Реальная загрузка в PostgreSQL
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
            'processed_data', 
            engine, 
            schema='processed',
            if_exists='append',  # можно изменить на 'replace' для полной замены
            index=False,
            method='multi'  # оптимизация для больших данных
        )
        
        row_count = len(df)
        logger.info("✅ Успешно загружено %d строк в PostgreSQL таблицу processed.processed_data" % row_count)
        
        # Дополнительно можем выполнить проверку
        with engine.connect() as conn:
            result = conn.execute(f"SELECT COUNT(*) FROM processed.processed_data").fetchone()
            total_rows = result[0]
            logger.info("📊 Всего строк в таблице processed.processed_data: %d" % total_rows)
            
    except Exception as e:
        logger.error("❌ Ошибка загрузки в PostgreSQL: %s" % str(e))
        raise

    
    logger.info("✅ Загрузка данных завершена успешно")

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
    'Test_02102025',
    default_args=default_args,
    description='Auto-generated ETL pipeline: Test_02102025',
    schedule_interval='@daily',
    catchup=False,
    tags=['generated', 'etl', 'csv', 'postgres']
) as dag:
    
    # Задача извлечения данных
    extract_task = PythonOperator(
        task_id='extract_data',
        python_callable=extract_data,
        doc_md='''### 📥 Извлечение данных
        
        **Источник**: csv
        **Путь**: /opt/airflow/data/sample.csv
        
        Извлекает данные из источника с валидацией и базовой проверкой качества.
        '''
    )
    
    # Задача трансформации данных  
    transform_task = PythonOperator(
        task_id='transform_data',
        python_callable=transform_data,
        doc_md='''### 🔧 Трансформация данных
        
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
        
        **Целевая система**: postgres
        **Таблица**: processed_data
        
        Загружает обработанные данные в целевую систему с проверкой результата.
        '''
    )
    
    # Определение зависимостей задач
    extract_task >> transform_task >> load_task
