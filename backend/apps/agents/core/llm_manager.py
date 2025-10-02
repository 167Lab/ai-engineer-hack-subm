"""
Менеджер LLM с поддержкой только локальных моделей через Ollama (на будущее предусмотрен гибридный режим: Ollama + облачные провайдеры)
"""
import os
import logging
from typing import Optional, Dict, Any, List
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage, HumanMessage
import yaml
from pathlib import Path

logger = logging.getLogger(__name__)


class LLMManager:
    """
    Менеджер для управления локальной LLM (Ollama)
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Инициализация менеджера LLM
        
        Args:
            config_path: Путь к файлу конфигурации
        """
        self.config = self._load_config(config_path)
        self.llm_config = self.config.get('llm_config', {})
        # Всегда используем Ollama
        self.provider = 'ollama'
        self.models_cache: Dict[str, BaseChatModel] = {}
        
    def _load_config(self, config_path: Optional[str] = None) -> Dict[str, Any]:
        """Загрузка конфигурации из файла"""
        if not config_path:
            config_path = Path(__file__).parent.parent / 'config' / 'general_config.yaml'
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Ошибка загрузки конфигурации: {e}")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Конфигурация по умолчанию"""
        return {
            'llm_config': {
                'provider': 'ollama',
                'ollama': {
                    'enabled': True,
                    'url': 'http://localhost:11434',
                    'models': {
                        'input_analysis': 'qwen2.5:14b',
                        'ddl_generation': 'qwen2.5:14b',
                        'pipeline_generation': 'qwen2.5:14b',
                        'report_generation': 'qwen2.5:14b'
                    },
                    'temperature': 0.75,
                    'max_tokens': 4096
                }
            }
        }
    
    def get_llm(self, agent_type: str, use_tools: bool = False) -> BaseChatModel:
        """
        Получение LLM для конкретного агента
        
        Args:
            agent_type: Тип агента (input_analysis, ddl_generation, etc.)
            use_tools: Использовать ли инструменты
            
        Returns:
            Экземпляр LLM
        """
        cache_key = f"{agent_type}_{use_tools}"
        
        if cache_key in self.models_cache:
            return self.models_cache[cache_key]
        
        llm = None
        
        # Всегда используем Ollama
        llm = self._try_ollama(agent_type)
        
        if not llm:
            logger.error(f"Не удалось инициализировать LLM для агента {agent_type}")
            llm = self._get_fallback_llm(agent_type)
        
        if llm and use_tools:
            # Здесь в будущем можно добавить привязку инструментов
            pass
        
        if llm:
            self.models_cache[cache_key] = llm
            
        return llm
    
    def _try_ollama(self, agent_type: str) -> Optional[BaseChatModel]:
        """Попытка инициализации Ollama"""
        ollama_config = self.llm_config.get('ollama', {})
        
        if not ollama_config.get('enabled', False):
            return None
        
        try:
            from langchain_ollama import ChatOllama
            
            model_name = ollama_config['models'].get(agent_type, 'llama3.2:latest')
            
            llm = ChatOllama(
                model=model_name,
                base_url=ollama_config.get('url', 'http://localhost:11434'),
                temperature=ollama_config.get('temperature', 0.7),
                num_predict=ollama_config.get('max_tokens', 4096),
            )
            
            # Проверка доступности модели
            test_response = llm.invoke([HumanMessage(content="test")])
            logger.info(f"Модель {model_name} успешно инициализирована для {agent_type}")
            return llm
            
        except Exception as e:
            logger.warning(f"Не удалось инициализировать модель для {agent_type}: {e}")
            return None
    
    # Удалены облачные провайдеры — используется только Ollama
    
    def _get_fallback_llm(self, agent_type: str) -> BaseChatModel:
        """
        Fallback LLM на случай недоступности основных моделей
        Используем простую заглушку для тестирования
        """
        from langchain_core.language_models import FakeListChatModel
        
        logger.warning(f"Используется заглушка FakeListChatModel для {agent_type}")
        
        responses = [
            "Анализирую данные...",
            "Генерирую DDL скрипты...",
            "Создаю пайплайн...",
            "Формирую отчет..."
        ]
        
        return FakeListChatModel(responses=responses)
    
    def invoke_with_retry(self, 
                         llm: BaseChatModel, 
                         messages: List[BaseMessage],
                         retry_count: int = 3) -> Any:
        """
        Вызов LLM с повторными попытками при ошибках
        
        Args:
            llm: Экземпляр LLM
            messages: Список сообщений
            retry_count: Количество попыток
            
        Returns:
            Ответ от LLM
        """
        last_error = None
        
        for attempt in range(retry_count):
            try:
                response = llm.invoke(messages)
                return response
            except Exception as e:
                last_error = e
                logger.warning(f"Попытка {attempt + 1}/{retry_count} не удалась: {e}")
                
                # Без гибридного режима дополнительных переключений нет
        
        raise last_error
    
    def get_model_info(self, agent_type: str) -> Dict[str, Any]:
        """
        Получение информации о модели для агента
        
        Args:
            agent_type: Тип агента
            
        Returns:
            Информация о модели
        """
        config = self.llm_config.get('ollama', {})
        return {
            'provider': 'ollama',
            'model': config.get('models', {}).get(agent_type, 'qwen2.5:14b'),
            'temperature': config.get('temperature', 0.75),
            'max_tokens': config.get('max_tokens', 4096)
        }
