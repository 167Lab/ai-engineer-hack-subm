import os
import psycopg2
from clickhouse_driver import Client as ClickHouseClient
from typing import Dict, Any

# Connection parameters from environment variables with defaults for Docker Compose setup
POSTGRES_DB = os.environ.get("POSTGRES_DB", "postgres")
POSTGRES_USER = os.environ.get("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.environ.get("POSTGRES_PASSWORD", "postgres")
POSTGRES_HOST = os.environ.get("POSTGRES_HOST", "postgres")
POSTGRES_PORT = os.environ.get("POSTGRES_PORT", "5432")

CLICKHOUSE_HOST = os.environ.get("CLICKHOUSE_HOST", "clickhouse")
CLICKHOUSE_PORT = os.environ.get("CLICKHOUSE_PORT", "9000")

def get_postgres_connection():
    """Establishes and returns a connection to the PostgreSQL database."""
    try:
        conn = psycopg2.connect(
            dbname=POSTGRES_DB,
            user=POSTGRES_USER,
            password=POSTGRES_PASSWORD,
            host=POSTGRES_HOST,
            port=POSTGRES_PORT
        )
        print("PostgreSQL connection successful.")
        return conn
    except psycopg2.OperationalError as e:
        print(f"Error connecting to PostgreSQL: {e}")
        return None

def get_clickhouse_client() -> ClickHouseClient:
    """Establishes and returns a client for the ClickHouse database."""
    try:
        client = ClickHouseClient(host=CLICKHOUSE_HOST, port=CLICKHOUSE_PORT)
        if client.execute('SELECT 1'):
            print("ClickHouse connection successful.")
            return client
    except Exception as e:
        print(f"Error connecting to ClickHouse: {e}")
    return None

def execute_postgres_query(query: str, params=None):
    """Executes a query on PostgreSQL and returns the results."""
    conn = get_postgres_connection()
    if not conn:
        return None
    
    results = None
    try:
        with conn.cursor() as cur:
            cur.execute(query, params)
            if cur.description:
                results = cur.fetchall()
            conn.commit()
    except Exception as e:
        print(f"Error executing PostgreSQL query: {e}")
        conn.rollback()
    finally:
        conn.close()
        
    return results

def execute_clickhouse_query(query: str, params=None):
    """Executes a query on ClickHouse and returns the results."""
    client = get_clickhouse_client()
    if not client:
        return None
        
    try:
        return client.execute(query, params)
    except Exception as e:
        print(f"Error executing ClickHouse query: {e}")
        return None
