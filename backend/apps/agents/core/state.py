"""
Определение состояния мультиагентной системы
"""
from typing import TypedDict, Any, Dict, List, Optional, Annotated
from langgraph.graph.message import add_messages


class MASState(TypedDict):
    """
    Состояние мультиагентной системы для анализа данных и генерации пайплайнов
    """
    # История сообщений между агентами
    messages: Annotated[List[Any], add_messages]
    
    # Входные данные
    source_config: Optional[Dict[str, Any]]  # Конфигурация источника данных
    source_type: Optional[str]  # Тип источника: csv, json, xml, postgres, clickhouse
    connection_params: Optional[Dict[str, Any]]  # Параметры подключения
    
    # Результаты анализа
    source_metadata: Optional[Dict[str, Any]]  # Метаданные источника
    data_sample: Optional[Any]  # Образец данных для анализа
    data_profile: Optional[Dict[str, Any]]  # Профиль данных (статистика, типы)
    
    # Рекомендации по хранилищу
    storage_recommendation: Optional[str]  # Рекомендуемое хранилище
    storage_reasoning: Optional[str]  # Обоснование выбора
    storage_alternatives: Optional[List[Dict[str, Any]]]  # Альтернативные варианты
    
    # DDL скрипты
    ddl_scripts: Optional[List[Dict[str, str]]]  # Список DDL скриптов
    ddl_recommendations: Optional[Dict[str, Any]]  # Рекомендации по оптимизации
    
    # Пайплайн
    pipeline_code: Optional[str]  # Код Airflow DAG
    pipeline_config: Optional[Dict[str, Any]]  # Конфигурация пайплайна
    transformations: Optional[List[str]]  # Список трансформаций
    
    # Отчет
    report: Optional[str]  # Итоговый отчет в формате Markdown
    report_sections: Optional[Dict[str, str]]  # Разделы отчета
    
    # Управление потоком
    current_agent: Optional[str]  # Текущий активный агент
    next_agent: Optional[str]  # Следующий агент в очереди
    completed_agents: List[str]  # Список завершенных агентов
    
    # Обратная связь от пользователя
    user_feedback: Optional[Dict[str, Any]]  # Корректировки от пользователя
    user_confirmations: Optional[Dict[str, bool]]  # Подтверждения этапов
    
    # Ошибки и предупреждения
    errors: List[Dict[str, Any]]  # Список ошибок
    warnings: List[Dict[str, Any]]  # Список предупреждений
    
    # Метаданные выполнения
    execution_id: Optional[str]  # ID сессии выполнения
    start_time: Optional[str]  # Время начала анализа
    end_time: Optional[str]  # Время окончания
    execution_stats: Optional[Dict[str, Any]]  # Статистика выполнения
