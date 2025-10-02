"""
Исполнитель ИИ-инженера
"""
import os
import yaml
import json
import logging
from typing import Dict, Any, Optional, List
from pathlib import Path
from datetime import datetime
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_core.runnables import RunnableConfig

from .llm_manager import LLMManager
from .state import MASState

logger = logging.getLogger(__name__)


class AgentExecutor:
    """
    Базовый класс для исполнения агентов в МАС
    """
    
    def __init__(self, 
                 agent_name: str,
                 config: Optional[RunnableConfig] = None,
                 llm_manager: Optional[LLMManager] = None):
        """
        Инициализация исполнителя агента
        
        Args:
            agent_name: Имя агента
            config: Конфигурация выполнения
            llm_manager: Менеджер LLM
        """
        self.agent_name = agent_name
        self.config = config or RunnableConfig()
        self.llm_manager = llm_manager or LLMManager()
        
        # Загружаем конфигурацию
        self.base_dir = Path(__file__).parent.parent
        self.general_config = self._load_general_config()
        
        # Загружаем промпт для агента (из объединенного файла секций)
        self.prompt = self._load_prompt()
        
        # Получаем LLM для агента
        self.llm = self.llm_manager.get_llm(agent_name)
        
        # Директории для логов и временных файлов
        self.logs_dir = self.base_dir / 'logs'
        self.temp_dir = Path('/tmp/mas_temp')
        self._ensure_directories()
    
    def _load_general_config(self) -> Dict[str, Any]:
        """Загрузка общей конфигурации"""
        config_path = self.base_dir / 'config' / 'general_config.yaml'
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Ошибка загрузки конфигурации: {e}")
            return {}
    
    def _load_prompt(self) -> str:
        """Загрузка промпта для агента из unified_prompt.yaml или legacy файла"""
        unified_path = self.base_dir / 'config' / 'prompts' / 'unified_prompt.yaml'
        if unified_path.exists():
            try:
                with open(unified_path, 'r', encoding='utf-8') as f:
                    unified = yaml.safe_load(f)
                    sections = unified.get('sections', {}) if isinstance(unified, dict) else {}
                    section = sections.get(self.agent_name)
                    if section:
                        return self._transform_prompt(section)
            except Exception as e:
                logger.error(f"Ошибка загрузки unified промпта: {e}")
        
        # Fallback: legacy отдельные файлы
        legacy_path = self.base_dir / 'config' / 'prompts' / f'{self.agent_name}_prompt.yaml'
        if legacy_path.exists():
            try:
                with open(legacy_path, 'r', encoding='utf-8') as f:
                    prompt_config = yaml.safe_load(f)
                    return self._transform_prompt(prompt_config)
            except Exception as e:
                logger.error(f"Ошибка загрузки промпта для {self.agent_name}: {e}")
        
        # Возвращаем промпт по умолчанию
        return self._get_default_prompt()
    
    def _transform_prompt(self, prompt_config: Dict[str, Any]) -> str:
        """Преобразование конфигурации промпта в строку"""
        if isinstance(prompt_config, str):
            return prompt_config
        
        system_prompt = prompt_config.get('system_prompt', '')
        
        # Добавляем дополнительные инструкции, если есть
        if 'instructions' in prompt_config:
            system_prompt += "\n\nИнструкции:\n"
            for instruction in prompt_config['instructions']:
                system_prompt += f"- {instruction}\n"
        
        # Добавляем формат вывода, если указан
        if 'output_format' in prompt_config:
            system_prompt += f"\n\nФормат вывода:\n{prompt_config['output_format']}"
        
        return system_prompt
    
    def _get_default_prompt(self) -> str:
        """Промпты-заглушки на случай, если с файлом что-то случилось"""
        prompts = {
            'input_analysis': """
Ты эксперт по анализу данных. Твоя задача:
1. Проанализировать метаданные и образец данных
2. Определить тип и структуру данных
3. Рекомендовать оптимальное хранилище
Отвечай на русском языке в формате JSON.
""",
            'ddl_generation': """
Ты эксперт по базам данных. Твоя задача:
1. Сгенерировать DDL скрипты для создания таблиц
2. Добавить рекомендации по индексам и партицированию
3. Оптимизировать структуру для выбранного хранилища
Отвечай на русском языке.
""",
            'pipeline_generation': """
Ты эксперт по созданию ETL пайплайнов. Твоя задача:
1. Сгенерировать Airflow DAG для обработки данных
2. Добавить необходимые трансформации
3. Настроить расписание и параметры
Генерируй валидный Python код.
""",
            'report_generation': """
Ты технический писатель. Твоя задача:
1. Создать подробный отчет о проделанной работе
2. Обосновать принятые решения
3. Предоставить рекомендации по оптимизации
Отвечай на русском языке в формате Markdown.
"""
        }
        return prompts.get(self.agent_name, "Ты - полезный ассистент.")
    
    def _ensure_directories(self):
        """Создание необходимых директорий"""
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
    
    def execute(self, state: MASState) -> Dict[str, Any]:
        """
        Выполнение логики агента
        
        Args:
            state: Текущее состояние МАС
            
        Returns:
            Обновленное состояние
        """
        logger.info(f"Выполнение агента: {self.agent_name}")
        
        # Подготовка сообщений для LLM
        messages = self._prepare_messages(state)
        
        # Логирование входных данных
        self._log_input(messages)
        
        try:
            # Вызов LLM
            response = self.llm_manager.invoke_with_retry(self.llm, messages)
            
            # Логирование ответа
            self._log_response(response)
            
            # Обработка ответа и обновление состояния
            updated_state = self._process_response(state, response)
            
            # Сохранение промежуточных результатов
            if self.general_config.get('agents_config', {}).get('save_intermediate', True):
                self._save_intermediate_results(updated_state)
            
            return updated_state
            
        except Exception as e:
            logger.error(f"Ошибка выполнения агента {self.agent_name}: {e}")
            
            # Добавляем ошибку в состояние
            if 'errors' not in state:
                state['errors'] = []
            
            state['errors'].append({
                'agent': self.agent_name,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            })
            
            return state
    
    def _prepare_messages(self, state: MASState) -> List[Any]:
        """
        Подготовка сообщений для LLM на основе состояния
        
        Args:
            state: Текущее состояние
            
        Returns:
            Список сообщений
        """
        messages = []
        
        # Системный промпт
        messages.append(SystemMessage(content=self.prompt))
        
        # Добавляем контекст из состояния
        context = self._build_context(state)
        if context:
            messages.append(HumanMessage(content=context))
        
        # Добавляем историю сообщений, если есть
        if 'messages' in state and state['messages']:
            for msg in state['messages'][-5:]:  # Последние 5 сообщений
                if isinstance(msg, (SystemMessage, HumanMessage, AIMessage)):
                    messages.append(msg)
        
        return messages
    
    def _build_context(self, state: MASState) -> str:
        """
        Построение контекста для агента из состояния
        
        Args:
            state: Текущее состояние
            
        Returns:
            Строка контекста
        """
        context_parts = []
        
        # Добавляем информацию о источнике данных
        if state.get('source_config'):
            context_parts.append(f"Конфигурация источника: {json.dumps(state['source_config'], ensure_ascii=False)}")
        
        # Добавляем метаданные
        if state.get('source_metadata'):
            context_parts.append(f"Метаданные: {json.dumps(state['source_metadata'], ensure_ascii=False)}")
        
        # Добавляем образец данных
        if state.get('data_sample'):
            context_parts.append(f"Образец данных: {state['data_sample']}")
        
        # Добавляем результаты предыдущих агентов
        if state.get('storage_recommendation'):
            context_parts.append(f"Рекомендованное хранилище: {state['storage_recommendation']}")
        
        if state.get('ddl_scripts'):
            context_parts.append(f"DDL скрипты: {state['ddl_scripts']}")
        
        # Добавляем обратную связь от пользователя
        if state.get('user_feedback'):
            context_parts.append(f"Обратная связь: {json.dumps(state['user_feedback'], ensure_ascii=False)}")
        
        return "\n\n".join(context_parts) if context_parts else ""
    
    def _process_response(self, state: MASState, response: Any) -> MASState:
        """
        Обработка ответа от LLM и обновление состояния
        
        Args:
            state: Текущее состояние
            response: Ответ от LLM
            
        Returns:
            Обновленное состояние
        """
        # Базовая обработка - добавляем ответ в историю сообщений
        if 'messages' not in state:
            state['messages'] = []
        
        state['messages'].append(response)
        
        # Обновляем информацию об агенте
        state['current_agent'] = self.agent_name
        
        if 'completed_agents' not in state:
            state['completed_agents'] = []
        
        if self.agent_name not in state['completed_agents']:
            state['completed_agents'].append(self.agent_name)
        
        # Специфичная обработка для каждого типа агента
        # (переопределяется в наследуемых классах)
        
        return state
    
    def _log_input(self, messages: List[Any]):
        """Логирование входных данных"""
        if not self.general_config.get('agents_config', {}).get('verbose', False):
            return
        
        log_file = self.logs_dir / f"{self.agent_name}_inputs.log"
        timestamp = datetime.now().isoformat()
        
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(f"\n--- {timestamp} ---\n")
            for msg in messages:
                f.write(f"{msg.__class__.__name__}: {msg.content}\n")
    
    def _log_response(self, response: Any):
        """Логирование ответа"""
        if not self.general_config.get('agents_config', {}).get('verbose', False):
            return
        
        log_file = self.logs_dir / f"{self.agent_name}_responses.log"
        timestamp = datetime.now().isoformat()
        
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(f"\n--- {timestamp} ---\n")
            f.write(f"{response.content if hasattr(response, 'content') else str(response)}\n")
    
    def _save_intermediate_results(self, state: MASState):
        """Сохранение промежуточных результатов"""
        result_file = self.temp_dir / f"{self.agent_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        # Конвертируем состояние в сериализуемый формат
        serializable_state = {}
        for key, value in state.items():
            if value is not None and not key.startswith('_'):
                try:
                    # Пробуем сериализовать
                    json.dumps(value)
                    serializable_state[key] = value
                except (TypeError, ValueError):
                    # Если не получается, сохраняем строковое представление
                    serializable_state[key] = str(value)
        
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(serializable_state, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Промежуточные результаты сохранены: {result_file}")
