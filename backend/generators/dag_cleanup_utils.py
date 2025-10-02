"""
Утилиты для правильного управления DAG файлами в Airflow
"""
import os
import subprocess
import logging
from services.dag_monitoring import DAGOperationContext

logger = logging.getLogger(__name__)

class DAGManager:
    """Управление DAG файлами - правильное удаление и очистка"""
    
    def __init__(self, dags_folder="/opt/airflow/dags"):
        self.dags_folder = dags_folder
        
    def delete_dag_completely(self, dag_id: str) -> bool:
        """
        Полное удаление DAG:
        1. Удаление из базы данных Airflow
        2. Удаление физического файла
        3. Очистка кэша Python
        
        Args:
            dag_id: ID DAG для удаления
            
        Returns:
            bool: True если успешно удалено
        """
        # Используем контекст мониторинга для отслеживания операции
        with DAGOperationContext('delete', dag_id) as monitor_ctx:
            try:
                files_deleted = 0
                
                # Шаг 1: Удаление из БД через Airflow CLI
                logger.info(f"🗑️ Удаление DAG {dag_id} из базы данных...")
                result = subprocess.run(
                    ['/home/airflow/.local/bin/airflow', 'dags', 'delete', dag_id, '-y'],
                    capture_output=True,
                    text=True,
                    user='airflow'  # Запускаем от пользователя airflow
                )
                
                if result.returncode != 0:
                    logger.error(f"❌ Ошибка удаления из БД: {result.stderr}")
                    monitor_ctx.set_error(f"CLI delete failed: {result.stderr}")
                    return False
                    
                logger.info(f"✅ DAG {dag_id} удален из базы данных")
                
                # Шаг 2: Поиск и удаление физического файла
                dag_file_path = os.path.join(self.dags_folder, f"{dag_id}.py")
                
                if os.path.exists(dag_file_path):
                    os.remove(dag_file_path)
                    files_deleted += 1
                    logger.info(f"✅ Физический файл {dag_file_path} удален")
                else:
                    logger.warning(f"⚠️ Файл {dag_file_path} не найден")
                
                # Шаг 3: Очистка __pycache__ 
                cache_files_deleted = 0
                pycache_folder = os.path.join(self.dags_folder, '__pycache__')
                if os.path.exists(pycache_folder):
                    for file in os.listdir(pycache_folder):
                        if file.startswith(dag_id):
                            pycache_file = os.path.join(pycache_folder, file)
                            os.remove(pycache_file)
                            cache_files_deleted += 1
                            logger.info(f"🧹 Очищен кэш: {file}")
                
                total_files = files_deleted + cache_files_deleted
                
                # Записываем результат в мониторинг
                monitor_ctx.set_result(
                    files_affected=total_files,
                    details={
                        'py_files_deleted': files_deleted,
                        'cache_files_deleted': cache_files_deleted,
                        'database_deleted': True,
                        'method': 'cli_and_filesystem'
                    }
                )
                
                logger.info(f"🎉 DAG {dag_id} полностью удален!")
                return True
                
            except Exception as e:
                logger.error(f"❌ Ошибка при удалении DAG {dag_id}: {e}")
                monitor_ctx.set_error(str(e))
                return False
    
    def list_orphaned_files(self) -> list:
        """
        Поиск 'осиротевших' файлов DAG, которые есть физически, 
        но не зарегистрированы в Airflow
        
        Returns:
            list: Список файлов без соответствующих DAG в БД
        """
        # Получаем список всех DAG файлов
        dag_files = []
        for file in os.listdir(self.dags_folder):
            if file.endswith('.py') and not file.startswith('__'):
                dag_files.append(file.replace('.py', ''))
        
        # Получаем список DAG из Airflow
        try:
            result = subprocess.run(
                ['/home/airflow/.local/bin/airflow', 'dags', 'list'],
                capture_output=True,
                text=True,
                user='airflow'
            )
            
            if result.returncode != 0:
                logger.error(f"Ошибка получения списка DAG: {result.stderr}")
                return []
                
            # Парсим вывод команды
            registered_dags = []
            for line in result.stdout.split('\n'):
                line = line.strip()
                if line and not line.startswith('[') and not line.startswith('DAGS'):
                    registered_dags.append(line.split()[0])  # Первая колонка - DAG ID
            
            # Находим разность
            orphaned = [f for f in dag_files if f not in registered_dags]
            
            if orphaned:
                logger.info(f"🔍 Найдены осиротевшие файлы: {orphaned}")
            
            return orphaned
            
        except Exception as e:
            logger.error(f"Ошибка поиска осиротевших файлов: {e}")
            return []
    
    def cleanup_all_orphaned(self) -> int:
        """
        Удаление всех осиротевших файлов DAG
        
        Returns:
            int: Количество удаленных файлов
        """
        orphaned_files = self.list_orphaned_files()
        deleted_count = 0
        
        for file_id in orphaned_files:
            file_path = os.path.join(self.dags_folder, f"{file_id}.py")
            try:
                os.remove(file_path)
                logger.info(f"🗑️ Удален осиротевший файл: {file_path}")
                deleted_count += 1
            except Exception as e:
                logger.error(f"❌ Ошибка удаления {file_path}: {e}")
        
        return deleted_count


def delete_dag_with_cleanup(dag_id: str) -> bool:
    """
    Функция-хелпер для полного удаления DAG
    
    Args:
        dag_id: ID DAG для удаления
        
    Returns:
        bool: Успешность операции
    """
    manager = DAGManager()
    return manager.delete_dag_completely(dag_id)


if __name__ == "__main__":
    # Пример использования
    logging.basicConfig(level=logging.INFO)
    
    import sys
    if len(sys.argv) < 2:
        print("Использование: python dag_cleanup_utils.py <dag_id>")
        sys.exit(1)
    
    dag_id = sys.argv[1]
    success = delete_dag_with_cleanup(dag_id)
    
    if success:
        print(f"✅ DAG '{dag_id}' успешно удален")
        sys.exit(0)
    else:
        print(f"❌ Ошибка при удалении DAG '{dag_id}'")
        sys.exit(1)
