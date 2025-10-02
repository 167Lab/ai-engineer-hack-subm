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
            
            # Получение параметров из конфигурации
            source_type = config.get('source_config', {}).get('type', 'csv')
            target_type = config.get('target_config', {}).get('type', 'postgres')
            source_path = config.get('source_config', {}).get('path', '/opt/airflow/data/sample.csv')
            target_table = config.get('target_config', {}).get('table', 'processed_data')
            
            # Импорт операций БД для генерации специфичного кода
            from generators.db_operations import DatabaseOperations
            
            # Генерация кода загрузки в зависимости от типа БД
            if target_type == 'postgres':
                loader_function = DatabaseOperations.get_postgres_loader_code(dag_id, target_table)
            elif target_type == 'clickhouse':
                loader_function = DatabaseOperations.get_clickhouse_loader_code(dag_id, target_table)
            elif target_type == 'hdfs':
                loader_function = DatabaseOperations.get_hdfs_loader_code(dag_id, target_table)
            else:
                # Fallback для неизвестных типов
                loader_function = f"""
        # Сохранение в файл для {target_type}
        output_path = '/opt/airflow/data/output/{dag_id}_{target_table}.parquet'
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        df.to_parquet(output_path, index=False)
        logger.info(f"📁 Данные сохранены в файл: {{output_path}}")
"""
            
            # Подстановка параметров в шаблон
            transformed_path = f'/opt/airflow/data/temp/{dag_id}_transformed.parquet'
            dag_content = dag_template.format(
                dag_id=dag_id,
                source_type=source_type,
                target_type=target_type,
                source_path=source_path,
                target_table=target_table,
                transformed_path=transformed_path,
                schedule=config.get('schedule', '@daily'),
                owner=config.get('owner', 'etl-system'),
                description=config.get('description', f'Auto-generated ETL pipeline: {dag_id}'),
                start_date='2025, 9, 27',
                retries=config.get('retries', 1),
                retry_delay=config.get('retry_delay', 5),
                # Новые параметры для улучшенного шаблона
                extract_function=DatabaseOperations.get_enhanced_extract_code(source_type, source_path),
                transform_function=DatabaseOperations.get_enhanced_transform_code(),
                loader_function=loader_function
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
    
    def delete_dag_properly(self, dag_id: str) -> Dict[str, Any]:
        """
        Правильное удаление DAG - из базы данных И физического файла
        
        Args:
            dag_id: ID DAG для удаления
            
        Returns:
            dict: Результат операции с статусом и сообщением
        """
        try:
            from generators.dag_cleanup_utils import delete_dag_with_cleanup
            
            success = delete_dag_with_cleanup(dag_id)
            
            if success:
                return {
                    "status": "success",
                    "message": f"DAG '{dag_id}' полностью удален из системы",
                    "details": {
                        "database_deleted": True,
                        "file_deleted": True,
                        "cache_cleared": True
                    }
                }
            else:
                return {
                    "status": "error", 
                    "message": f"Ошибка при удалении DAG '{dag_id}'",
                    "details": {
                        "database_deleted": False,
                        "file_deleted": False,
                        "cache_cleared": False
                    }
                }
                
        except Exception as e:
            return {
                "status": "error",
                "message": f"Критическая ошибка удаления DAG '{dag_id}': {str(e)}",
                "details": {"exception": str(e)}
            }
    
    def _get_dag_template(self) -> str:
        """Получение улучшенного шаблона DAG с реальными операциями БД"""
        from generators.db_operations import DatabaseOperations, get_complete_dag_template
        return get_complete_dag_template()
    
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

def delete_dag_properly(dag_id: str) -> Dict[str, Any]:
    """Обертка для правильного удаления DAG"""
    return _airflow_service.delete_dag_properly(dag_id)