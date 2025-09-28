"""
Этот модуль определяет подключения Airflow как код.
Его можно использовать в DAG для динамического создания подключений
или запустить один раз для их добавления в метаданные Airflow.
"""
from airflow.models.connection import Connection

# Закомментировано, так как требует полного контекста Airflow.
# from airflow import settings

def create_connections():
    """Возвращает список объектов Connection для проекта."""
    connections = [
        Connection(
            conn_id='postgres_default',
            conn_type='postgres',
            host='postgres',
            schema='etl_db',
            login='airflow',
            password='airflow',
            port=5432
        ),
        Connection(
            conn_id='clickhouse_default',
            conn_type='http',
            host='clickhouse',
            port=8123
        ),
        Connection(
            conn_id='hdfs_default',
            conn_type='webhdfs',
            host='hadoop-namenode',
            port=9870
        )
    ]
    return connections

# Пример того, как можно было бы добавить эти подключения
# def add_connections():
#     session = settings.Session()
#     for conn in create_connections():
#         existing_conn = session.query(Connection).filter_by(conn_id=conn.conn_id).first()
#         if not existing_conn:
#             session.add(conn)
#             print(f"Connection {conn.conn_id} added.")
#         else:
#             print(f"Connection {conn.conn_id} already exists.")
#     session.commit()
#     session.close()

# if __name__ == "__main__":
#     # Этот код нужно запускать в контексте Airflow, например, через `airflow bash`
#     # add_connections()
#     pass
