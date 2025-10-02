"""
Менеджер LLM с поддержкой локальных (Ollama) и облачных моделей
"""
import os
import logging
from typing import Optional, Dict, Any, List
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage
import yaml
from pathlib import Path

logger = logging.getLogger(__name__)


class LLMManager:
    """
    Менеджер для управления LLM с поддержкой гибридного подхода
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Инициализация менеджера LLM
        
        Args:
            config_path: Путь к файлу конфигурации
        """
        self.config = self._load_config(config_path)
        self.llm_config = self.config.get('llm_config', {})
        self.provider = self.llm_config.get('provider', 'ollama')
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
                        'input_analysis': 'llama3.2:latest',
                        'ddl_generation': 'llama3.2:latest',
                        'pipeline_generation': 'llama3.2:latest',
                        'report_generation': 'llama3.2:latest'
                    },
                    'temperature': 0.7,
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
        
        if self.provider == 'hybrid':
            # Гибридный режим: пробуем сначала Ollama, затем облачные
            llm = self._try_ollama(agent_type) or self._try_cloud(agent_type)
        elif self.provider == 'ollama':
            llm = self._try_ollama(agent_type)
        elif self.provider in ['openai', 'groq', 'anthropic']:
            llm = self._try_cloud(agent_type)
        
        if not llm:
            logger.error(f"Не удалось инициализировать LLM для агента {agent_type}")
            llm = self._get_fallback_llm(agent_type)
        
        if llm and use_tools:
            # Здесь можно добавить привязку инструментов
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
            logger.info(f"Ollama модель {model_name} успешно инициализирована для {agent_type}")
            return llm
            
        except Exception as e:
            logger.warning(f"Не удалось инициализировать Ollama для {agent_type}: {e}")
            return None
    
    def _try_cloud(self, agent_type: str) -> Optional[BaseChatModel]:
        """Попытка инициализации облачной модели"""
        cloud_config = self.llm_config.get('cloud', {})
        
        if not cloud_config.get('enabled', False):
            return None
        
        provider = cloud_config.get('provider', 'groq')
        api_key = os.getenv(cloud_config.get('api_key', '').replace('${', '').replace('}', ''))
        
        if not api_key:
            logger.warning(f"API ключ для {provider} не найден")
            return None
        
        try:
            model_name = cloud_config['models'].get(agent_type, 'llama-3.3-70b-versatile')
            
            if provider == 'groq':
                from langchain_groq import ChatGroq
                llm = ChatGroq(
                    model=model_name,
                    api_key=api_key,
                    temperature=cloud_config.get('temperature', 0.7),
                    max_tokens=cloud_config.get('max_tokens', 4096),
                )
            elif provider == 'openai':
                from langchain_openai import ChatOpenAI
                llm = ChatOpenAI(
                    model=model_name,
                    api_key=api_key,
                    temperature=cloud_config.get('temperature', 0.7),
                    max_tokens=cloud_config.get('max_tokens', 4096),
                )
            elif provider == 'anthropic':
                from langchain_anthropic import ChatAnthropic
                llm = ChatAnthropic(
                    model=model_name,
                    api_key=api_key,
                    temperature=cloud_config.get('temperature', 0.7),
                    max_tokens=cloud_config.get('max_tokens', 4096),
                )
            else:
                logger.error(f"Неподдерживаемый облачный провайдер: {provider}")
                return None
            
            logger.info(f"{provider} модель {model_name} успешно инициализирована для {agent_type}")
            return llm
            
        except Exception as e:
            logger.warning(f"Не удалось инициализировать {provider} для {agent_type}: {e}")
            return None
    
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
                
                # Если это была Ollama и включен гибридный режим, пробуем облачную модель
                if self.provider == 'hybrid' and attempt < retry_count - 1:
                    logger.info("Переключаемся на облачную модель...")
                    # Здесь можно добавить логику переключения
        
        raise last_error
    
    def get_model_info(self, agent_type: str) -> Dict[str, Any]:
        """
        Получение информации о модели для агента
        
        Args:
            agent_type: Тип агента
            
        Returns:
            Информация о модели
        """
        if self.provider == 'ollama':
            config = self.llm_config.get('ollama', {})
            return {
                'provider': 'ollama',
                'model': config['models'].get(agent_type, 'llama3.2:latest'),
                'temperature': config.get('temperature', 0.7),
                'max_tokens': config.get('max_tokens', 4096)
            }
        elif self.provider in ['openai', 'groq', 'anthropic']:
            config = self.llm_config.get('cloud', {})
            return {
                'provider': config.get('provider', 'groq'),
                'model': config['models'].get(agent_type, 'llama-3.3-70b-versatile'),
                'temperature': config.get('temperature', 0.7),
                'max_tokens': config.get('max_tokens', 4096)
            }
        else:
            return {
                'provider': 'unknown',
                'model': 'unknown',
                'temperature': 0.7,
                'max_tokens': 4096
            }
