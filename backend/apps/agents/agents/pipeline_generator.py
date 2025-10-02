"""
Агент генерации пайплайнов Airflow
"""
import json
import logging
from typing import Dict, Any, List
from datetime import datetime
from langchain_core.messages import HumanMessage, AIMessage

from ..core.agent_executor import AgentExecutor  
from ..core.state import MASState

logger = logging.getLogger(__name__)


class PipelineGeneratorAgent(AgentExecutor):
    """
    Агент для генерации Airflow DAG пайплайнов
    """
    
    def __init__(self, **kwargs):
        super().__init__(agent_name='pipeline_generation', **kwargs)
        
    def execute(self, state: MASState) -> MASState:
        """
        Генерация Airflow DAG для обработки данных
        
        Args:
            state: Текущее состояние МАС
            
        Returns:
            Обновленное состояние с кодом пайплайна
        """
        logger.info("Начало генерации пайплайна")
        
        try:
            # Получаем необходимые данные из состояния
            source_config = state.get('source_config', {})
            source_type = source_config.get('source_type', '')
            storage = state.get('storage_recommendation', 'postgres')
            metadata = state.get('source_metadata', {})
            ddl_scripts = state.get('ddl_scripts', [])
            
            # Подготавливаем контекст для LLM
            context = self._prepare_pipeline_context(
                source_type, storage, metadata, ddl_scripts
            )
            
            # Вызываем LLM для генерации пайплайна
            messages = [
                HumanMessage(content=f"""
Сгенерируй Airflow DAG для ETL пайплайна со следующими параметрами:

{context}

Требования к пайплайну:
1. Извлечение данных из источника {source_type}
2. Трансформация данных (очистка, валидация)
3. Загрузка в {storage}
4. Обработка ошибок и логирование
5. Настройка расписания и retry политики

Ответь в формате JSON:
{{
    "dag_id": "уникальный_id_dag",
    "schedule": "расписание_cron",
    "transformations": ["список трансформаций"],
    "dag_code": "полный код Python DAG",
    "config": {{
        "retries": число,
        "retry_delay": минуты,
        "email_on_failure": bool
    }},
    "dependencies": ["список зависимостей Python"],
    "notes": ["заметки по настройке и использованию"]
}}
""")
            ]
            
            response = self.llm_manager.invoke_with_retry(self.llm, messages)
            
            # Парсим ответ и генерируем код пайплайна
            pipeline_info = self._parse_pipeline_response(response.content)
            
            # Генерируем финальный код DAG
            dag_code = self._generate_dag_code(pipeline_info, state)
            
            # Сохраняем в состоянии
            state['pipeline_code'] = dag_code
            state['pipeline_config'] = {
                'dag_id': pipeline_info.get('dag_id', f'etl_pipeline_{datetime.now().strftime("%Y%m%d")}'),
                'schedule': pipeline_info.get('schedule', '0 0 * * *'),
                'config': pipeline_info.get('config', {}),
                'dependencies': pipeline_info.get('dependencies', [])
            }
            state['transformations'] = pipeline_info.get('transformations', [])
            
            # Добавляем сообщение в историю
            if 'messages' not in state:
                state['messages'] = []
            
            state['messages'].append(AIMessage(content=f"""
Пайплайн Airflow DAG сгенерирован.
DAG ID: {state['pipeline_config']['dag_id']}
Расписание: {state['pipeline_config']['schedule']}
Трансформации: {', '.join(state['transformations'][:3])}
"""))
            
            # Обновляем информацию об агенте
            state['current_agent'] = self.agent_name
            
            if 'completed_agents' not in state:
                state['completed_agents'] = []
            
            if self.agent_name not in state['completed_agents']:
                state['completed_agents'].append(self.agent_name)
            
            logger.info(f"Пайплайн успешно сгенерирован: {state['pipeline_config']['dag_id']}")
            
            # Сохраняем промежуточные результаты
            self._save_intermediate_results(state)
            
            return state
            
        except Exception as e:
            logger.error(f"Ошибка генерации пайплайна: {e}")
            
            if 'errors' not in state:
                state['errors'] = []
            
            state['errors'].append({
                'agent': self.agent_name,
                'error': str(e),
                'stage': 'pipeline_generation'
            })
            
            # Генерируем базовый пайплайн как fallback
            state['pipeline_code'] = self._generate_fallback_pipeline(state)
            state['pipeline_config'] = {
                'dag_id': f'etl_fallback_{datetime.now().strftime("%Y%m%d")}',
                'schedule': '0 0 * * *',
                'config': {'retries': 1, 'retry_delay': 5}
            }
            
            return state
    
    def _prepare_pipeline_context(self,
                                 source_type: str,
                                 storage: str,
                                 metadata: Dict[str, Any],
                                 ddl_scripts: List[Dict[str, str]]) -> str:
        """
        Подготовка контекста для генерации пайплайна
        """
        context_parts = []
        
        context_parts.append(f"Источник данных: {source_type}")
        context_parts.append(f"Целевое хранилище: {storage}")
        
        # Информация о данных
        if metadata:
            context_parts.append(f"\nХарактеристики данных:")
            context_parts.append(f"- Количество колонок: {metadata.get('column_count', 0)}")
            context_parts.append(f"- Количество строк (образец): {metadata.get('row_count', 0)}")
            
            if metadata.get('statistics'):
                stats = metadata['statistics']
                context_parts.append(f"- Общее количество null: {stats.get('total_nulls', 0)}")
                context_parts.append(f"- Дублированные строки: {stats.get('duplicated_rows', 0)}")
        
        # Информация о целевой таблице
        if ddl_scripts:
            table_name = ddl_scripts[0].get('name', 'data_table')
            context_parts.append(f"\nЦелевая таблица: {table_name}")
        
        # Необходимые трансформации
        context_parts.append("\nНеобходимые трансформации:")
        context_parts.append("- Очистка данных (удаление null)")
        context_parts.append("- Дедупликация")
        context_parts.append("- Валидация типов данных")
        
        if storage == 'clickhouse':
            context_parts.append("- Подготовка для колоночного хранения")
        elif storage == 'postgres':
            context_parts.append("- Нормализация данных")
        
        return "\n".join(context_parts)
    
    def _parse_pipeline_response(self, response: str) -> Dict[str, Any]:
        """
        Парсинг ответа LLM с информацией о пайплайне
        """
        import re
        
        # Пытаемся найти JSON в ответе
        json_match = re.search(r'\{[\s\S]*\}', response)
        
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass
        
        # Возвращаем базовую конфигурацию
        return {
            'dag_id': f'etl_pipeline_{datetime.now().strftime("%Y%m%d")}',
            'schedule': '0 0 * * *',
            'transformations': ['clean', 'deduplicate', 'validate'],
            'config': {
                'retries': 2,
                'retry_delay': 5,
                'email_on_failure': False
            }
        }
    
    def _generate_dag_code(self, 
                          pipeline_info: Dict[str, Any],
                          state: MASState) -> str:
        """
        Генерация финального кода Airflow DAG
        """
        source_config = state.get('source_config', {})
        source_type = source_config.get('source_type', 'csv')
        storage = state.get('storage_recommendation', 'postgres')
        ddl_scripts = state.get('ddl_scripts', [])
        table_name = ddl_scripts[0].get('name', 'data_table') if ddl_scripts else 'data_table'
        
        dag_id = pipeline_info.get('dag_id', f'etl_pipeline_{datetime.now().strftime("%Y%m%d")}')
        schedule = pipeline_info.get('schedule', '0 0 * * *')
        config = pipeline_info.get('config', {})
        
        dag_code = f'''"""
Автоматически сгенерированный ETL пайплайн
Источник: {source_type}
Назначение: {storage}
Сгенерировано: {datetime.now().isoformat()}
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from airflow.providers.postgres.operators.postgres import PostgresOperator
from airflow.providers.http.sensors.http import HttpSensor
import pandas as pd
import logging
import json

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Конфигурация DAG
default_args = {{
    'owner': 'ai-data-engineer',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': {config.get('email_on_failure', False)},
    'email_on_retry': False,
    'retries': {config.get('retries', 2)},
    'retry_delay': timedelta(minutes={config.get('retry_delay', 5)})
}}

def extract_data(**context):
    """Извлечение данных из источника"""
    logger.info("Начало извлечения данных из {source_type}")
    
    try:
        # Логика извлечения данных
        if '{source_type}' == 'csv':
            df = pd.read_csv('/opt/airflow/data/input.csv')
        elif '{source_type}' == 'json':
            df = pd.read_json('/opt/airflow/data/input.json', lines=True)
        elif '{source_type}' == 'postgres':
            # Подключение к источнику PostgreSQL
            import psycopg2
            conn = psycopg2.connect(
                host='postgres',
                database='source_db',
                user='airflow',
                password='airflow'
            )
            df = pd.read_sql('SELECT * FROM source_table', conn)
            conn.close()
        else:
            raise ValueError(f"Неподдерживаемый тип источника: {source_type}")
        
        logger.info(f"Извлечено {{len(df)}} записей")
        
        # Сохранение во временный файл
        temp_path = f'/opt/airflow/data/temp/{{context["ds"]}}_extracted.parquet'
        df.to_parquet(temp_path, index=False)
        
        # Передача пути следующей задаче
        context['task_instance'].xcom_push(key='extracted_path', value=temp_path)
        
        return f"Извлечено {{len(df)}} записей"
        
    except Exception as e:
        logger.error(f"Ошибка извлечения: {{e}}")
        raise

def transform_data(**context):
    """Трансформация данных"""
    logger.info("Начало трансформации данных")
    
    try:
        # Получение пути к данным
        ti = context['task_instance']
        extracted_path = ti.xcom_pull(task_ids='extract_data', key='extracted_path')
        
        df = pd.read_parquet(extracted_path)
        initial_count = len(df)
        
        # Применение трансформаций
        # 1. Очистка данных
        df = df.dropna()
        logger.info(f"Удалено {{initial_count - len(df)}} строк с null значениями")
        
        # 2. Дедупликация
        before_dedup = len(df)
        df = df.drop_duplicates()
        logger.info(f"Удалено {{before_dedup - len(df)}} дубликатов")
        
        # 3. Валидация и преобразование типов
        # Здесь можно добавить специфичные преобразования
        
        # Сохранение трансформированных данных
        transformed_path = f'/opt/airflow/data/temp/{{context["ds"]}}_transformed.parquet'
        df.to_parquet(transformed_path, index=False)
        
        ti.xcom_push(key='transformed_path', value=transformed_path)
        ti.xcom_push(key='record_count', value=len(df))
        
        return f"Трансформировано {{len(df)}} записей"
        
    except Exception as e:
        logger.error(f"Ошибка трансформации: {{e}}")
        raise

def load_data(**context):
    """Загрузка данных в целевое хранилище"""
    logger.info("Начало загрузки данных в {storage}")
    
    try:
        ti = context['task_instance']
        transformed_path = ti.xcom_pull(task_ids='transform_data', key='transformed_path')
        record_count = ti.xcom_pull(task_ids='transform_data', key='record_count')
        
        df = pd.read_parquet(transformed_path)
        
        if '{storage}' == 'postgres':
            import psycopg2
            from sqlalchemy import create_engine
            
            engine = create_engine('postgresql://airflow:airflow@postgres/airflow')
            df.to_sql('{table_name}', engine, if_exists='append', index=False)
            logger.info(f"Загружено {{record_count}} записей в PostgreSQL")
            
        elif '{storage}' == 'clickhouse':
            from clickhouse_driver import Client
            
            client = Client('clickhouse')
            # Здесь нужна реальная логика загрузки в ClickHouse
            logger.info(f"Загружено {{record_count}} записей в ClickHouse")
            
        elif '{storage}' == 'hdfs':
            # Сохранение в HDFS
            hdfs_path = f'/data/{{context["ds"]}}/{table_name}.parquet'
            # Здесь нужна реальная логика работы с HDFS
            logger.info(f"Загружено {{record_count}} записей в HDFS: {{hdfs_path}}")
        
        return f"Успешно загружено {{record_count}} записей"
        
    except Exception as e:
        logger.error(f"Ошибка загрузки: {{e}}")
        raise

def validate_pipeline(**context):
    """Валидация результатов пайплайна"""
    logger.info("Валидация результатов")
    
    ti = context['task_instance']
    record_count = ti.xcom_pull(task_ids='transform_data', key='record_count')
    
    if record_count and record_count > 0:
        logger.info(f"Пайплайн успешно завершен. Обработано {{record_count}} записей")
        return "Валидация пройдена"
    else:
        raise ValueError("Нет данных после трансформации")

# Определение DAG
with DAG(
    '{dag_id}',
    default_args=default_args,
    description='ETL пайплайн для обработки данных',
    schedule_interval='{schedule}',
    catchup=False,
    tags=['etl', 'generated', '{source_type}', '{storage}']
) as dag:
    
    # Задачи
    extract_task = PythonOperator(
        task_id='extract_data',
        python_callable=extract_data,
        provide_context=True
    )
    
    transform_task = PythonOperator(
        task_id='transform_data',
        python_callable=transform_data,
        provide_context=True
    )
    
    load_task = PythonOperator(
        task_id='load_data',
        python_callable=load_data,
        provide_context=True
    )
    
    validate_task = PythonOperator(
        task_id='validate_pipeline',
        python_callable=validate_pipeline,
        provide_context=True
    )
    
    # Определение зависимостей
    extract_task >> transform_task >> load_task >> validate_task
'''
        
        return dag_code
    
    def _generate_fallback_pipeline(self, state: MASState) -> str:
        """
        Генерация fallback пайплайна при ошибке
        """
        return '''"""
Fallback ETL пайплайн (сгенерирован из-за ошибки)
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator

default_args = {
    'owner': 'ai-data-engineer',
    'start_date': datetime(2024, 1, 1),
    'retries': 1,
    'retry_delay': timedelta(minutes=5)
}

with DAG(
    'etl_fallback',
    default_args=default_args,
    description='Fallback ETL pipeline',
    schedule_interval='@daily',
    catchup=False
) as dag:
    
    task = BashOperator(
        task_id='placeholder_task',
        bash_command='echo "Fallback pipeline - требуется настройка"'
    )
'''
