"""
Конфигурация Django приложения для мультиагентной системы
"""
from django.apps import AppConfig


class AgentsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.agents'
    verbose_name = 'AI Data Engineer Agents'
    
    def ready(self):
        """Инициализация приложения"""
        import logging
        logging.getLogger(__name__).info("MAS Agents app initialized")
