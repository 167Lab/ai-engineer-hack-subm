"""
Инструменты для работы с базами данных
"""
import logging
from typing import Dict, Any, Optional, List
from langchain_core.tools import tool
import asyncio

# Импортируем существующие анализаторы
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent.parent))
from analyzers.database_analyzer import DatabaseSourceAnalyzer

logger = logging.getLogger(__name__)


@tool
async def analyze_database_tool(
    db_type: str,
    connection_params: Dict[str, Any],
    table_name: str
) -> Dict[str, Any]:
    """
    Анализ таблицы в базе данных
    
    Args:
        db_type: Тип БД (postgres, clickhouse)
        connection_params: Параметры подключения
        table_name: Имя таблицы для анализа
        
    Returns:
        Результаты анализа таблицы
    """
    try:
        analyzer = DatabaseSourceAnalyzer()
        
        if db_type == 'postgres':
            result = await analyzer.analyze_postgres_table(connection_params, table_name)
        elif db_type == 'clickhouse':
            result = await analyzer.analyze_clickhouse_table(connection_params, table_name)
        else:
            return {
                'status': 'error',
                'error': f'Неподдерживаемый тип БД: {db_type}'
            }
        
        return result
        
    except Exception as e:
        logger.error(f"Ошибка анализа БД: {e}")
        return {
            'status': 'error',
            'error': str(e),
            'metadata': {},
            'recommendations': {}
        }


@tool
def test_connection_tool(
    db_type: str,
    connection_params: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Тестирование подключения к базе данных
    
    Args:
        db_type: Тип БД (postgres, clickhouse)
        connection_params: Параметры подключения
        
    Returns:
        Статус подключения и информация о БД
    """
    result = {
        'db_type': db_type,
        'connected': False,
        'error': None,
        'db_info': {}
    }
    
    try:
        if db_type == 'postgres':
            import psycopg2
            
            conn = psycopg2.connect(
                host=connection_params.get('host', 'localhost'),
                port=connection_params.get('port', 5432),
                database=connection_params.get('database', 'postgres'),
                user=connection_params.get('user', 'postgres'),
                password=connection_params.get('password', '')
            )
            
            cursor = conn.cursor()
            cursor.execute("SELECT version()")
            version = cursor.fetchone()[0]
            
            cursor.execute("SELECT current_database()")
            current_db = cursor.fetchone()[0]
            
            result['connected'] = True
            result['db_info'] = {
                'version': version,
                'current_database': current_db
            }
            
            conn.close()
            
        elif db_type == 'clickhouse':
            from clickhouse_driver import Client
            
            client = Client(
                host=connection_params.get('host', 'localhost'),
                port=connection_params.get('port', 9000),
                database=connection_params.get('database', 'default'),
                user=connection_params.get('user', 'default'),
                password=connection_params.get('password', '')
            )
            
            version = client.execute("SELECT version()")[0][0]
            databases = client.execute("SHOW DATABASES")
            
            result['connected'] = True
            result['db_info'] = {
                'version': version,
                'databases': [db[0] for db in databases]
            }
            
    except Exception as e:
        logger.error(f"Ошибка подключения к {db_type}: {e}")
        result['error'] = str(e)
    
    return result


@tool
def get_table_schema_tool(
    db_type: str,
    connection_params: Dict[str, Any],
    table_name: str
) -> Dict[str, Any]:
    """
    Получение схемы таблицы из базы данных
    
    Args:
        db_type: Тип БД (postgres, clickhouse)
        connection_params: Параметры подключения
        table_name: Имя таблицы
        
    Returns:
        Схема таблицы с информацией о колонках
    """
    schema = {
        'db_type': db_type,
        'table_name': table_name,
        'columns': [],
        'indexes': [],
        'constraints': []
    }
    
    try:
        if db_type == 'postgres':
            import psycopg2
            
            conn = psycopg2.connect(
                host=connection_params.get('host', 'localhost'),
                port=connection_params.get('port', 5432),
                database=connection_params.get('database', 'postgres'),
                user=connection_params.get('user', 'postgres'),
                password=connection_params.get('password', '')
            )
            
            cursor = conn.cursor()
            
            # Получение информации о колонках
            cursor.execute("""
                SELECT 
                    column_name,
                    data_type,
                    character_maximum_length,
                    numeric_precision,
                    numeric_scale,
                    is_nullable,
                    column_default
                FROM information_schema.columns
                WHERE table_name = %s
                ORDER BY ordinal_position
            """, (table_name,))
            
            columns = cursor.fetchall()
            
            for col in columns:
                column_info = {
                    'name': col[0],
                    'type': col[1],
                    'max_length': col[2],
                    'precision': col[3],
                    'scale': col[4],
                    'nullable': col[5] == 'YES',
                    'default': col[6]
                }
                schema['columns'].append(column_info)
            
            # Получение информации об индексах
            cursor.execute("""
                SELECT 
                    indexname,
                    indexdef
                FROM pg_indexes
                WHERE tablename = %s
            """, (table_name,))
            
            indexes = cursor.fetchall()
            schema['indexes'] = [{'name': idx[0], 'definition': idx[1]} for idx in indexes]
            
            # Получение информации о первичных ключах
            cursor.execute("""
                SELECT 
                    kcu.column_name
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu
                    ON tc.constraint_name = kcu.constraint_name
                WHERE tc.table_name = %s
                    AND tc.constraint_type = 'PRIMARY KEY'
                ORDER BY kcu.ordinal_position
            """, (table_name,))
            
            pk_columns = cursor.fetchall()
            if pk_columns:
                schema['constraints'].append({
                    'type': 'PRIMARY KEY',
                    'columns': [col[0] for col in pk_columns]
                })
            
            conn.close()
            
        elif db_type == 'clickhouse':
            from clickhouse_driver import Client
            
            client = Client(
                host=connection_params.get('host', 'localhost'),
                port=connection_params.get('port', 9000),
                database=connection_params.get('database', 'default'),
                user=connection_params.get('user', 'default'),
                password=connection_params.get('password', '')
            )
            
            # Получение структуры таблицы
            columns = client.execute(f"DESCRIBE TABLE {table_name}")
            
            for col in columns:
                column_info = {
                    'name': col[0],
                    'type': col[1],
                    'default_type': col[2] if len(col) > 2 else None,
                    'default_expression': col[3] if len(col) > 3 else None,
                    'comment': col[4] if len(col) > 4 else None
                }
                schema['columns'].append(column_info)
            
            # Получение информации о движке таблицы
            table_info = client.execute(f"SHOW CREATE TABLE {table_name}")
            if table_info:
                schema['create_statement'] = table_info[0][0]
                
    except Exception as e:
        logger.error(f"Ошибка получения схемы таблицы: {e}")
        schema['error'] = str(e)
    
    return schema
