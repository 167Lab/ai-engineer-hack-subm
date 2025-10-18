from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
import logging
import os
from include.utils.io import robust_read_csv  # доступно через PYTHONPATH=/opt/airflow/dags

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

with DAG(
    dag_id="etl_pipeline_016935",
    start_date=datetime(2025, 9, 27),
    schedule="@once",
    catchup=False,
    max_active_runs=1,
    tags=['generated', 'etl', 'csv', 'hdfs'],
    default_args={
    'owner': 'etl-system',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5)
}
) as dag:
    # сюда компилятор подставляет сгенерированный код задач из шаблонов узлов

    def extract_data():
        '''Извлечение данных из источника csv'''
        import pandas as pd
        import logging
        import os
        
        logger = logging.getLogger(__name__)
        logger.info(f"Начало извлечения данных из csv")
        
        try:
            # Проверка существования файла
            if not os.path.exists('/opt/airflow/data/uploads/part-00000-37dced01-2ad2-48c8-a56d-54b4d8760599-c000.csv'):
                raise FileNotFoundError(f"Файл источника данных не найден: /opt/airflow/data/uploads/part-00000-37dced01-2ad2-48c8-a56d-54b4d8760599-c000.csv")
            
            # Загрузка данных в зависимости от типа
            if 'csv' == 'csv':
                df = pd.read_csv('/opt/airflow/data/uploads/part-00000-37dced01-2ad2-48c8-a56d-54b4d8760599-c000.csv')
                logger.info(f"Загружено {len(df)} строк из CSV файла")
                
            elif 'csv' == 'json':
                df = pd.read_json('/opt/airflow/data/uploads/part-00000-37dced01-2ad2-48c8-a56d-54b4d8760599-c000.csv')
                logger.info(f"Загружено {len(df)} строк из JSON файла")
                
            elif 'csv' == 'xml':
                df = pd.read_xml('/opt/airflow/data/uploads/part-00000-37dced01-2ad2-48c8-a56d-54b4d8760599-c000.csv')
                logger.info(f"Загружено {len(df)} строк из XML файла")
                
            elif 'csv' == 'parquet':
                df = pd.read_parquet('/opt/airflow/data/uploads/part-00000-37dced01-2ad2-48c8-a56d-54b4d8760599-c000.csv')
                logger.info(f"Загружено {len(df)} строк из Parquet файла")
                
            else:
                raise ValueError(f"Неподдерживаемый тип источника: csv")
            
            # Базовая валидация данных
            if df.empty:
                raise ValueError("Источник данных пуст")
                
            logger.info(f"Информация о данных:")
            logger.info(f"   - Строк: {len(df)}")
            logger.info(f"   - Колонок: {len(df.columns)}")
            logger.info(f"   - Колонки: {', '.join(df.columns)}")
            
            # Создание директории для временных файлов
            temp_dir = '/opt/airflow/data/temp'
            os.makedirs(temp_dir, exist_ok=True)
            
            # Сохранение во временное расположение
            temp_path = '/opt/airflow/data/temp/etl_pipeline_016935_extracted.parquet'
            df.to_parquet(temp_path, index=False)
            logger.info("Данные сохранены во временный файл: %s" % temp_path)
            
            return temp_path
            
        except Exception as e:
            logger.error("Ошибка извлечения данных: %s" % str(e))
            raise


    def transform_data():
        '''Расширенная трансформация данных'''
        import pandas as pd
        import logging
        import os
        
        logger = logging.getLogger(__name__)
        logger.info("Начало трансформации данных")
        
        try:
            temp_path = '/opt/airflow/data/temp/etl_pipeline_016935_extracted.parquet'
            
            if not os.path.exists(temp_path):
                raise FileNotFoundError("Файл с извлеченными данными не найден: " + temp_path)
                
            df = pd.read_parquet(temp_path)
            initial_rows = len(df)
            logger.info("Загружено %d строк для трансформации" % initial_rows)
            
            # Детальная трансформация данных
            transformation_steps = []
            
            # 1. Обработка пустых значений
            null_counts = df.isnull().sum()
            if null_counts.sum() > 0:
                logger.info("Найдено пустых значений: %d" % null_counts.sum())
                
                # Стратегии обработки пустых значений по типам колонок
                for col in df.columns:
                    if df[col].dtype in ['int64', 'float64']:
                        df[col].fillna(df[col].mean(), inplace=True)
                    else:
                        df[col].fillna('Unknown', inplace=True)
                
                transformation_steps.append("Заполнены пустые значения")
            
            # 2. Удаление дубликатов (устойчиво к не-хэшируемым значениям)
            try:
                import numpy as np
                import json
                from pandas.util import hash_pandas_object

                def normalize_value(v):
                    if isinstance(v, np.ndarray):
                        return v.tolist()
                    if isinstance(v, (list, dict)):
                        return json.dumps(v, ensure_ascii=False, sort_keys=True)
                    return v

                normalized = df.applymap(normalize_value)
                row_hash = hash_pandas_object(normalized, index=False)
                duplicates = row_hash.duplicated().sum()
                if duplicates > 0:
                    df = df.loc[~row_hash.duplicated()].copy()
                    transformation_steps.append("Удалено %d дубликатов" % duplicates)
                    logger.info("Удалено %d дубликатов" % duplicates)
            except Exception as dup_err:
                logger.warning(f"Не удалось выполнить устойчивое удаление дубликатов: {dup_err}")
                try:
                    duplicates = df.astype(str).duplicated().sum()
                    if duplicates > 0:
                        df = df.astype(str).drop_duplicates().copy()
                        transformation_steps.append("Удалено %d дубликатов (по строковому представлению)" % duplicates)
                        logger.info("Удалено %d дубликатов (по строковому представлению)" % duplicates)
                except Exception as fallback_err:
                    logger.warning(f"Резервное удаление дубликатов также не удалось: {fallback_err}")
            
            # 3. Стандартизация данных
            # Приведение строковых колонок к нижнему регистру где это имеет смысл
            string_columns = df.select_dtypes(include=['object']).columns
            for col in string_columns:
                if col.lower() in ['email', 'city', 'department']:
                    df[col] = df[col].astype(str).str.strip().str.title()
                    transformation_steps.append("Стандартизирована колонка %s" % col)
            
            # 4. Добавление метаданных
            df['processed_at'] = pd.Timestamp.now()
            df['processing_batch_id'] = 'etl_pipeline_016935'
            transformation_steps.append("Добавлены метаданные обработки")
            
            final_rows = len(df)
            logger.info("Трансформация завершена: %d → %d строк" % (initial_rows, final_rows))
            
            if transformation_steps:
                logger.info("Выполненные трансформации:")
                for step in transformation_steps:
                    logger.info("   - %s" % step)
            
            # Сохранение трансформированных данных
            transformed_path = '/opt/airflow/data/temp/etl_pipeline_016935_transformed.parquet'
            df.to_parquet(transformed_path, index=False)
            logger.info("Трансформированные данные сохранены: %s" % transformed_path)
            
            return transformed_path
            
        except Exception as e:
            logger.error("Ошибка трансформации данных: %s" % str(e))
            raise

    def load_data():
        import pandas as pd
        import os
        transformed_path = '/opt/airflow/data/temp/etl_pipeline_016935_transformed.parquet'
        if not os.path.exists(transformed_path):
            raise FileNotFoundError(f'Файл с трансформированными данными не найден: {transformed_path}')
        df = pd.read_parquet(transformed_path)

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
            filename = f"etl_pipeline_016935_/data/processed/my_data_{timestamp}.csv"
            hdfs_path = f"{base_path}/{filename}"
            
            # Сохранение данных в различных форматах
            # CSV для совместимости
            csv_data = df.to_csv(index=False)
            hdfs_client.write(hdfs_path, csv_data, encoding='utf-8', overwrite=True)
            
            # Дополнительно Parquet для аналитики (если поддерживается)
            try:
                parquet_path = hdfs_path.replace('.csv', '.parquet')
                parquet_data = df.to_parquet(engine='pyarrow')
                hdfs_client.write(parquet_path, parquet_data, overwrite=True)
                logger.info(f"Дополнительно сохранен Parquet: {parquet_path}")
            except Exception as parquet_error:
                logger.warning(f"Не удалось сохранить Parquet: {parquet_error}")
            
            # Проверка записи
            file_info = hdfs_client.status(hdfs_path)
            file_size = file_info['length']
            
            logger.info(f"Успешно загружено {len(df)} строк в HDFS")
            logger.info(f"Путь: {hdfs_path}")
            logger.info(f"Размер файла: {file_size} байт")
            
            # Создание метаданных файла
            metadata = {
                'dag_id': 'etl_pipeline_016935',
                'table': '/data/processed/my_data',
                'rows': len(df),
                'columns': list(df.columns),
                'timestamp': timestamp,
                'file_size': file_size,
                'hdfs_path': hdfs_path
            }
            
            import json
            metadata_path = hdfs_path.replace('.csv', '_metadata.json')
            hdfs_client.write(metadata_path, json.dumps(metadata, indent=2), overwrite=True)
            logger.info(f"Метаданные сохранены: {metadata_path}")
            
        except Exception as e:
            logger.error("Ошибка загрузки в HDFS: %s" % str(e))
            raise


    extract_task = PythonOperator(task_id='extract_data', python_callable=extract_data)

    transform_task = PythonOperator(task_id='transform_data', python_callable=transform_data)

    load_data_task = PythonOperator(task_id='load_data', python_callable=load_data)


    # зависимости между задачами
    extract_task >> transform_task
    transform_task >> load_data_task
