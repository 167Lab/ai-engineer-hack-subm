"""
Сервисы для работы с Apache Airflow
"""
import os
import requests
from typing import Dict, Any, Tuple, List
from pathlib import Path
import logging
from jinja2 import Environment, FileSystemLoader


logger = logging.getLogger(__name__)


class AirflowService:
    """Сервис для работы с Airflow API и файлами DAG"""
    
    def __init__(self, airflow_url: str = "http://airflow-webserver:8080", username: str = "admin", password: str = "admin"):
        self.airflow_url = airflow_url
        self.auth = (username, password)
        self.dags_folder = "/opt/airflow/dags"  # Путь внутри контейнера
        self.template_env = Environment(loader=FileSystemLoader('templates/airflow/'))
    
    def render_dag_py(self, config: Dict[str, Any]) -> Tuple[str, str]:
        """
        Генерация Python кода DAG по конфигурации
        
        Args:
            config: Конфигурация DAG
            
        Returns:
            Tuple (dag_py_content, dag_id)
        """
        try:
            dag_id = config["dag_name"]
            
            # Базовый шаблон DAG
            dag_template = self._get_dag_template()
            
            # Подстановка параметров в шаблон
            dag_content = dag_template.format(
                dag_id=dag_id,
                source_type=config.get('source_config', {}).get('type', 'csv'),
                target_type=config.get('target_config', {}).get('type', 'postgres'),
                source_path=config.get('source_config', {}).get('path', '/opt/airflow/data/sample.csv'),
                target_table=config.get('target_config', {}).get('table', 'processed_data'),
                schedule=config.get('schedule', '@daily'),
                owner=config.get('owner', 'etl-system'),
                description=config.get('description', f'Auto-generated ETL pipeline: {dag_id}'),
                start_date='2025, 9, 27',
                retries=config.get('retries', 1),
                retry_delay=config.get('retry_delay', 5)
            )
            
            return dag_content, dag_id
            
        except Exception as e:
            logger.error(f"Ошибка генерации DAG: {e}")
            raise
    
    def deploy_dag_to_airflow(self, dag_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Деплой DAG в Airflow
        
        Args:
            dag_data: Данные о DAG для деплоя
            
        Returns:
            Информация о статусе деплоя
        """
        try:
            dag_name = dag_data["dag_name"]
            
            # Сначала генерируем DAG
            dag_content, dag_id = self.render_dag_py(dag_data)
            
            # Записываем файл DAG (если запущено в Docker, файл попадет в монтированный том)
            dag_file_path = f"{self.dags_folder}/{dag_id}.py"
            
            # Создаем директорию если не существует
            Path(self.dags_folder).mkdir(parents=True, exist_ok=True)
            
            with open(dag_file_path, 'w', encoding='utf-8') as f:
                f.write(dag_content)
            
            logger.info(f"DAG файл записан: {dag_file_path}")
            
            # Проверяем доступность Airflow API
            api_status = self._check_airflow_api()
            
            return {
                "dag_name": dag_name,
                "dag_id": dag_id,
                "status": "deployed",
                "file_path": dag_file_path,
                "airflow_api_status": api_status,
                "airflow_dag_url": f"http://localhost:8080/dags/{dag_id}/graph",
                "airflow_ui_url": "http://localhost:8080",
                "message": f"DAG {dag_id} успешно развернут",
                "instructions": {
                    'step1': 'Откройте Airflow UI: http://localhost:8080',
                    'step2': f'Найдите DAG с ID: {dag_id}',
                    'step3': 'Включите DAG переключателем',
                    'step4': 'Нажмите "Trigger DAG" для запуска'
                }
            }
            
        except Exception as e:
            logger.error(f"Ошибка деплоя DAG {dag_name}: {e}")
            return {
                "dag_name": dag_name,
                "status": "failed",
                "error": str(e),
                "message": f"Не удалось развернуть DAG {dag_name}"
            }
    
    def get_recs_for_source(self, source_id: str) -> List[Dict[str, Any]]:
        """
        Получение рекомендаций для источника данных
        
        Args:
            source_id: Идентификатор источника данных
            
        Returns:
            Список рекомендаций
        """
        # Пока возвращаем заглушку
        # В будущем здесь можно реализовать кеширование и получение рекомендаций из БД
        return [
            {
                "recommendation_type": "storage",
                "target": "PostgreSQL",
                "confidence": 0.85,
                "reasoning": f"Для источника {source_id} рекомендуется PostgreSQL на основе анализа"
            },
            {
                "recommendation_type": "schedule",
                "target": "@daily",
                "confidence": 0.9,
                "reasoning": "Ежедневное обновление оптимально для данного типа данных"
            }
        ]
    
    def _get_dag_template(self) -> str:
        """Получение базового шаблона DAG"""
        return """
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
    logger.info("Начало извлечения данных из {source_type}")
    
    try:
        if '{source_type}' == 'csv':
            df = pd.read_csv('{source_path}')
            logger.info(f"Загружено {{len(df)}} строк из CSV")
        elif '{source_type}' == 'json':
            df = pd.read_json('{source_path}')
            logger.info(f"Загружено {{len(df)}} строк из JSON")
        else:
            raise ValueError(f"Неподдерживаемый тип источника: {source_type}")
        
        # Сохранение во временное расположение
        temp_path = '/opt/airflow/data/temp/{dag_id}_extracted.parquet'
        df.to_parquet(temp_path, index=False)
        logger.info(f"Данные сохранены во временный файл: {{temp_path}}")
        
        return temp_path
        
    except Exception as e:
        logger.error(f"Ошибка извлечения данных: {{e}}")
        raise

def transform_data():
    '''Трансформация данных'''
    logger.info("Начало трансформации данных")
    
    try:
        temp_path = '/opt/airflow/data/temp/{dag_id}_extracted.parquet'
        df = pd.read_parquet(temp_path)
        
        # Базовая очистка данных
        initial_rows = len(df)
        df = df.dropna()  # Удаление строк с пустыми значениями
        df = df.drop_duplicates()  # Удаление дубликатов
        
        logger.info(f"Трансформация завершена: {{initial_rows}} -> {{len(df)}} строк")
        
        # Сохранение трансформированных данных
        transformed_path = '/opt/airflow/data/temp/{dag_id}_transformed.parquet'
        df.to_parquet(transformed_path, index=False)
        
        return transformed_path
        
    except Exception as e:
        logger.error(f"Ошибка трансформации данных: {{e}}")
        raise

def load_data():
    '''Загрузка данных в целевое хранилище'''
    logger.info("Начало загрузки данных в {target_type}")
    
    try:
        transformed_path = '/opt/airflow/data/temp/{dag_id}_transformed.parquet'
        df = pd.read_parquet(transformed_path)
        
        if '{target_type}' == 'postgres':
            # Заглушка для PostgreSQL
            logger.info(f"Загрузка {{len(df)}} строк в PostgreSQL таблицу {target_table}")
            # Здесь должна быть реальная загрузка в PostgreSQL
            
        elif '{target_type}' == 'clickhouse':
            # Заглушка для ClickHouse  
            logger.info(f"Загрузка {{len(df)}} строк в ClickHouse таблицу {target_table}")
            # Здесь должна быть реальная загрузка в ClickHouse
            
        else:
            logger.info(f"Сохранение в файл для {target_type}")
            output_path = f'/opt/airflow/data/output/{dag_id}_{target_table}.parquet'
            df.to_parquet(output_path, index=False)
        
        logger.info("Загрузка данных завершена успешно")
        
    except Exception as e:
        logger.error(f"Ошибка загрузки данных: {{e}}")
        raise

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
        
        Извлекает данные из источника типа {source_type}
        Путь к источнику: {source_path}
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
        
        Загружает обработанные данные в {target_type}
        Целевая таблица: {target_table}
        '''
    )
    
    # Определение зависимостей задач
    extract_task >> transform_task >> load_task
"""
    
    def _check_airflow_api(self) -> str:
        """Проверка доступности Airflow API"""
        try:
            # Сначала проверяем /health endpoint без авторизации
            response = requests.get(f"{self.airflow_url}/health", timeout=10)
            if response.status_code == 200:
                health_data = response.json()
                if health_data.get('metadatabase', {}).get('status') == 'healthy':
                    return '✅ API доступен, база данных работает'
                else:
                    return '⚠️ API доступен, но есть проблемы с базой данных'
            else:
                return f'⚠️ API отвечает с кодом {response.status_code}'
                
        except Exception as e:
            logger.warning(f"Airflow API недоступен: {e}")
            return f'❌ API недоступен: {str(e)}'


# Экспорт функций для обратной совместимости с существующим кодом
_airflow_service = AirflowService()

def render_dag_py(config: Dict[str, Any]) -> Tuple[str, str]:
    """Обертка для рендеринга DAG"""
    return _airflow_service.render_dag_py(config)

def deploy_dag_to_airflow(dag_data: Dict[str, Any]) -> Dict[str, Any]:
    """Обертка для деплоя DAG"""
    return _airflow_service.deploy_dag_to_airflow(dag_data)

def get_recs_for_source(source_id: str) -> List[Dict[str, Any]]:
    """Обертка для получения рекомендаций"""
    return _airflow_service.get_recs_for_source(source_id)