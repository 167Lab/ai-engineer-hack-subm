"""
Production Monitoring Service для операций с DAG
Логирование, метрики, алерты для системы управления DAG
"""
import logging
import time
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from django.conf import settings


@dataclass
class DAGOperationMetrics:
    """Метрики операции с DAG"""
    operation_type: str  # 'delete', 'cleanup', 'deploy'
    dag_id: Optional[str]
    timestamp: datetime
    duration_ms: int
    status: str  # 'success', 'error', 'partial'
    files_affected: int
    details: Dict[str, Any]
    error_message: Optional[str] = None


class DAGMonitoringService:
    """
    Сервис мониторинга операций с DAG
    - Централизованное логирование
    - Сбор метрик
    - Алертинг при критических ошибках
    - Отчеты о состоянии системы
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.metrics_storage: List[DAGOperationMetrics] = []
        self._setup_logging()
    
    def _setup_logging(self):
        """Настройка специализированного логирования для DAG операций"""
        # Создаем отдельный logger для DAG операций
        dag_logger = logging.getLogger('dag_operations')
        dag_logger.setLevel(logging.INFO)
        
        # Создаем handler для файла (если в продакшене)
        if hasattr(settings, 'DAG_MONITORING_LOG_FILE'):
            log_file = settings.DAG_MONITORING_LOG_FILE
            os.makedirs(os.path.dirname(log_file), exist_ok=True)
            
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(logging.INFO)
            
            formatter = logging.Formatter(
                '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            file_handler.setFormatter(formatter)
            
            dag_logger.addHandler(file_handler)
    
    def start_operation(self, operation_type: str, dag_id: Optional[str] = None) -> str:
        """
        Начало мониторинга операции
        
        Returns:
            operation_id: Уникальный ID операции для отслеживания
        """
        operation_id = f"{operation_type}_{int(time.time() * 1000)}"
        
        self.logger.info(
            f"START [{operation_type}] dag_id={dag_id}, operation_id={operation_id}"
        )
        
        return operation_id
    
    def complete_operation(
        self, 
        operation_id: str,
        operation_type: str,
        status: str,
        duration_ms: int,
        dag_id: Optional[str] = None,
        files_affected: int = 0,
        details: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None
    ):
        """Завершение мониторинга операции"""
        
        details = details or {}
        
        # Создаем метрику
        metric = DAGOperationMetrics(
            operation_type=operation_type,
            dag_id=dag_id,
            timestamp=datetime.now(),
            duration_ms=duration_ms,
            status=status,
            files_affected=files_affected,
            details=details,
            error_message=error_message
        )
        
        # Сохраняем метрику
        self.metrics_storage.append(metric)
        
        # Логируем завершение
        status_emoji = "OK" if status == "success" else "ERROR" if status == "error" else "WARN"
        
        log_message = (
            f"{status_emoji} COMPLETE [{operation_type}] "
            f"status={status}, duration={duration_ms}ms, "
            f"files={files_affected}, dag_id={dag_id}"
        )
        
        if error_message:
            log_message += f", error={error_message}"
        
        if status == "success":
            self.logger.info(log_message)
        elif status == "error":
            self.logger.error(log_message)
        else:
            self.logger.warning(log_message)
        
        # Проверяем критичность для алертинга
        if status == "error" and operation_type == "delete":
            self._send_critical_alert(metric)
    
    def _send_critical_alert(self, metric: DAGOperationMetrics):
        """Отправка критических алертов"""
        alert_message = (
            f"CRITICAL: DAG operation failed\n"
            f"Operation: {metric.operation_type}\n"
            f"DAG ID: {metric.dag_id}\n"
            f"Error: {metric.error_message}\n"
            f"Time: {metric.timestamp}\n"
            f"Duration: {metric.duration_ms}ms"
        )
        
        self.logger.critical(alert_message)
        
        # Здесь можно добавить отправку в Slack, email, etc.
        # if hasattr(settings, 'SLACK_WEBHOOK_URL'):
        #     self._send_slack_alert(alert_message)
    
    def get_health_report(self, hours: int = 24) -> Dict[str, Any]:
        """
        Отчет о состоянии системы за последние часы
        
        Args:
            hours: Количество часов для анализа
            
        Returns:
            Словарь с метриками здоровья системы
        """
        cutoff_time = datetime.now() - timedelta(hours=hours)
        recent_metrics = [
            m for m in self.metrics_storage 
            if m.timestamp >= cutoff_time
        ]
        
        if not recent_metrics:
            return {
                "status": "no_data",
                "message": f"Нет данных за последние {hours} часов",
                "period_hours": hours,
                "metrics_count": 0
            }
        
        # Анализ метрик
        total_operations = len(recent_metrics)
        successful_operations = len([m for m in recent_metrics if m.status == "success"])
        failed_operations = len([m for m in recent_metrics if m.status == "error"])
        
        success_rate = (successful_operations / total_operations * 100) if total_operations > 0 else 0
        
        # Группировка по типу операций
        operations_by_type = {}
        for metric in recent_metrics:
            op_type = metric.operation_type
            if op_type not in operations_by_type:
                operations_by_type[op_type] = {"total": 0, "success": 0, "error": 0}
            
            operations_by_type[op_type]["total"] += 1
            if metric.status == "success":
                operations_by_type[op_type]["success"] += 1
            elif metric.status == "error":
                operations_by_type[op_type]["error"] += 1
        
        # Определение общего статуса
        if success_rate >= 95:
            overall_status = "healthy"
        elif success_rate >= 80:
            overall_status = "warning"
        else:
            overall_status = "critical"
        
        return {
            "status": overall_status,
            "period_hours": hours,
            "total_operations": total_operations,
            "success_rate": round(success_rate, 2),
            "successful_operations": successful_operations,
            "failed_operations": failed_operations,
            "operations_by_type": operations_by_type,
            "recent_errors": [
                {
                    "timestamp": m.timestamp.isoformat(),
                    "operation": m.operation_type,
                    "dag_id": m.dag_id,
                    "error": m.error_message
                }
                for m in recent_metrics if m.status == "error"
            ][-5:],  # Последние 5 ошибок
            "generated_at": datetime.now().isoformat()
        }
    
    def cleanup_old_metrics(self, days: int = 7):
        """Очистка старых метрик для экономии памяти"""
        cutoff_time = datetime.now() - timedelta(days=days)
        
        old_count = len(self.metrics_storage)
        self.metrics_storage = [
            m for m in self.metrics_storage 
            if m.timestamp >= cutoff_time
        ]
        new_count = len(self.metrics_storage)
        
        cleaned_count = old_count - new_count
        if cleaned_count > 0:
            self.logger.info(f"Очищено {cleaned_count} старых метрик (старше {days} дней)")


# Глобальный экземпляр сервиса
_monitoring_service = DAGMonitoringService()


def get_monitoring_service() -> DAGMonitoringService:
    """Получение глобального экземпляра сервиса мониторинга"""
    return _monitoring_service


class DAGOperationContext:
    """
    Context manager для автоматического мониторинга операций с DAG
    
    Использование:
        with DAGOperationContext('delete', 'my_dag_id') as ctx:
            # выполняем операцию
            result = delete_dag_operation()
            ctx.set_result(files_affected=1, details={'method': 'cli'})
    """
    
    def __init__(self, operation_type: str, dag_id: Optional[str] = None):
        self.operation_type = operation_type
        self.dag_id = dag_id
        self.operation_id: Optional[str] = None
        self.start_time: Optional[float] = None
        self.monitoring = get_monitoring_service()
        
        # Результаты операции
        self.status = "success"
        self.files_affected = 0
        self.details: Dict[str, Any] = {}
        self.error_message: Optional[str] = None
    
    def __enter__(self):
        self.start_time = time.time()
        self.operation_id = self.monitoring.start_operation(
            self.operation_type, 
            self.dag_id
        )
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration_ms = int((time.time() - self.start_time) * 1000)
        
        # Если было исключение, записываем как ошибку
        if exc_type is not None:
            self.status = "error"
            self.error_message = str(exc_val)
        
        self.monitoring.complete_operation(
            operation_id=self.operation_id,
            operation_type=self.operation_type,
            status=self.status,
            duration_ms=duration_ms,
            dag_id=self.dag_id,
            files_affected=self.files_affected,
            details=self.details,
            error_message=self.error_message
        )
    
    def set_result(
        self, 
        files_affected: int = 0, 
        details: Optional[Dict[str, Any]] = None,
        status: str = "success"
    ):
        """Установка результатов операции"""
        self.files_affected = files_affected
        self.details.update(details or {})
        self.status = status
    
    def set_error(self, error_message: str):
        """Установка ошибки операции"""
        self.status = "error"
        self.error_message = error_message
