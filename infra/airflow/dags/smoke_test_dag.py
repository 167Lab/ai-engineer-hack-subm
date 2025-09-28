from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator

def test_hdfs_connection():
    """
    Проверяет соединение с HDFS через прямое подключение
    """
    from hdfs import InsecureClient
    
    try:
        # Подключаемся к HDFS NameNode (можно настроить через Airflow UI: Admin->Connections)
        client = InsecureClient('http://hadoop-namenode:9870', user='airflow')
        
        test_path = '/tmp/smoke_test.txt'
        test_content = 'Hello HDFS from Airflow!'
        
        # Записываем тестовый файл
        client.write(test_path, test_content, encoding='utf-8', overwrite=True)
        
        # Читаем файл обратно для проверки
        with client.read(test_path, encoding='utf-8') as reader:
            read_content = reader.read()
        
        assert read_content == test_content
        print(f"HDFS test successful: read back '{read_content}'")
        
    except Exception as e:
        print(f"HDFS test failed: {e}")
        raise

default_args = {
    'owner': 'etl-system',
    'depends_on_past': False,
    'start_date': datetime(2025, 9, 23),
    'retries': 1,
    'retry_delay': timedelta(minutes=1) # Уменьшено для быстрых проверок
}

with DAG(
    'smoke_test_pipeline',
    default_args=default_args,
    description='Infrastructure smoke test',
    schedule_interval=None,
    catchup=False,
    tags=['test', 'infrastructure']
) as dag:
    
    test_postgres = BashOperator(
        task_id='test_postgres_connection',
        bash_command="pg_isready -h postgres -p 5432 -U airflow"
    )
    
    test_clickhouse = BashOperator(
        task_id='test_clickhouse_connection',
        bash_command='curl -s http://clickhouse:8123/ping | grep -q "Ok."'
    )
    
    test_hdfs = PythonOperator(
        task_id='test_hdfs_connection',
        python_callable=test_hdfs_connection
    )
    
    [test_postgres, test_clickhouse] >> test_hdfs
