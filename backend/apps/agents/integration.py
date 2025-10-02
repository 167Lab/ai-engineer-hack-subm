"""
Интеграция LLM (Ollama) с Django API с последовательными этапами
"""
import asyncio
import logging
import uuid
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path

from .core import (
    MASState,
    LLMManager,
    AgentExecutor,
)

logger = logging.getLogger(__name__)


class LLMIntegration:
    """
    Интеграция последовательного пайплайна на одной локальной LLM
    """
    
    def __init__(self):
        """Инициализация интеграции LLM"""
        self.llm_manager = LLMManager()
        # Поэтапные исполнители без зависимостей от пакета agents/*
        self.input_analyzer = AgentExecutor(agent_name='input_analysis', llm_manager=self.llm_manager)
        self.ddl_generator = AgentExecutor(agent_name='ddl_generation', llm_manager=self.llm_manager)
        self.pipeline_generator = AgentExecutor(agent_name='pipeline_generation', llm_manager=self.llm_manager)
        self.report_generator = AgentExecutor(agent_name='report_generation', llm_manager=self.llm_manager)
        
    async def analyze_data_source(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Главная точка входа для анализа источников данных
        
        Args:
            request_data: Данные запроса от API
            
        Returns:
            Результаты анализа и рекомендации
        """
        try:
            logger.info(f"Начало анализа источника данных: {request_data.get('source_type', 'unknown')}")
            
            # Создаем начальное состояние
            initial_state = self._create_initial_state(request_data)
            
            # Запускаем этапы последовательно в одном процессе
            result = await self._run_sequential(initial_state)
            
            # Форматируем результат для API
            response = self._format_response(result)
            
            logger.info("Анализ успешно завершен")
            return response
            
        except Exception as e:
            logger.error(f"Ошибка анализа источника данных: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'message': 'Произошла ошибка при анализе источника данных'
            }
    
    async def analyze_with_feedback(self, 
                                   request_data: Dict[str, Any],
                                   session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Анализ с поддержкой обратной связи (для интеграции с фронтендом)
        
        Args:
            request_data: Данные запроса
            session_id: ID сессии для продолжения анализа
            
        Returns:
            Результат текущего этапа анализа
        """
        try:
            if session_id and self._has_session(session_id):
                # Продолжаем существующую сессию
                state = self._load_session(session_id)
                
                # Применяем обратную связь, если есть
                if 'user_feedback' in request_data:
                    state['user_feedback'] = request_data['user_feedback']
                    state['waiting_for_feedback'] = False
            else:
                # Создаем новую сессию
                session_id = str(uuid.uuid4())
                state = self._create_initial_state(request_data)
                state['interactive_mode'] = True
                state['session_id'] = session_id
            
            # Выполняем один шаг последовательного пайплайна (в будущем добавим ожидание и комментарии от пользователя)
            state = self._run_next_stage(state)
            
            # Сохраняем состояние сессии
            self._save_session(session_id, state)
            
            # Форматируем ответ
            response = self._format_interactive_response(state, session_id)
            
            return response
            
        except Exception as e:
            logger.error(f"Ошибка интерактивного анализа: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'session_id': session_id
            }
    
    def _create_initial_state(self, request_data: Dict[str, Any]) -> MASState:
        """
        Создание начального состояния для МАС
        
        Args:
            request_data: Данные запроса
            
        Returns:
            Начальное состояние МАС
        """
        state = MASState(
            messages=[],
            source_config=request_data,
            source_type=request_data.get('source_type'),
            connection_params=request_data.get('connection_params', {}),
            execution_id=str(uuid.uuid4()),
            start_time=datetime.now().isoformat(),
            completed_agents=[],
            errors=[],
            warnings=[]
        )
        
        return state
    
    async def _run_sequential(self, initial_state: MASState) -> MASState:
        """
        Последовательный запуск этапов: анализ -> DDL -> пайплайн -> отчет
        """
        state = initial_state
        state = self.input_analyzer.execute(state)
        state = self.ddl_generator.execute(state)
        state = self.pipeline_generator.execute(state)
        state = self.report_generator.execute(state)
        return state
    
    def _run_next_stage(self, state: MASState) -> MASState:
        """Выполнить следующий этап на основе состояния"""
        current = state.get('current_agent')
        if current is None:
            return self.input_analyzer.execute(state)
        if current == 'input_analysis':
            return self.ddl_generator.execute(state)
        if current == 'ddl_generation':
            return self.pipeline_generator.execute(state)
        if current == 'pipeline_generation':
            return self.report_generator.execute(state)
        return state
    
    def _format_response(self, state: MASState) -> Dict[str, Any]:
        """
        Форматирование финального ответа для API
        
        Args:
            state: Финальное состояние МАС
            
        Returns:
            Отформатированный ответ
        """
        response = {
            'status': 'success' if not state.get('errors') else 'completed_with_errors',
            'execution_id': state.get('execution_id'),
            'analysis_result': {
                'metadata': state.get('source_metadata', {}),
                'data_profile': state.get('data_profile', {}),
                'storage_recommendation': state.get('storage_recommendation'),
                'storage_reasoning': state.get('storage_reasoning'),
                'storage_alternatives': state.get('storage_alternatives', [])
            },
            'ddl_scripts': state.get('ddl_scripts', []),
            'pipeline_config': state.get('pipeline_config', {}),
            'pipeline_code': state.get('pipeline_code', ''),
            'report': state.get('report', ''),
            'execution_stats': state.get('execution_stats', {}),
            'errors': state.get('errors', []),
            'warnings': state.get('warnings', [])
        }
        
        return response
    
    def _format_interactive_response(self, state: MASState, session_id: str) -> Dict[str, Any]:
        """
        Форматирование ответа для интерактивного режима
        
        Args:
            state: Текущее состояние
            session_id: ID сессии
            
        Returns:
            Отформатированный ответ для текущего этапа
        """
        current_stage = state.get('current_agent', 'unknown')
        waiting_for_feedback = state.get('waiting_for_feedback', False)
        
        response = {
            'status': 'waiting_for_feedback' if waiting_for_feedback else 'processing',
            'session_id': session_id,
            'current_stage': current_stage,
            'completed_stages': state.get('completed_agents', []),
            'data': {}
        }
        
        # Добавляем данные в зависимости от текущего этапа
        if current_stage == 'input_analysis':
            response['data'] = {
                'metadata': state.get('source_metadata', {}),
                'data_profile': state.get('data_profile', {}),
                'storage_recommendation': state.get('storage_recommendation'),
                'storage_reasoning': state.get('storage_reasoning'),
                'storage_alternatives': state.get('storage_alternatives', [])
            }
        elif current_stage == 'ddl_generation':
            response['data'] = {
                'ddl_scripts': state.get('ddl_scripts', []),
                'ddl_recommendations': state.get('ddl_recommendations', {})
            }
        elif current_stage == 'pipeline_generation':
            response['data'] = {
                'pipeline_config': state.get('pipeline_config', {}),
                'pipeline_code': state.get('pipeline_code', ''),
                'transformations': state.get('transformations', [])
            }
        elif current_stage == 'report_generation':
            response['data'] = {
                'report': state.get('report', ''),
                'report_sections': state.get('report_sections', {}),
                'execution_stats': state.get('execution_stats', {})
            }
        
        # Добавляем информацию об ошибках, если есть
        if state.get('errors'):
            response['errors'] = state['errors']
        
        # Если анализ завершен
        if 'report_generation' in state.get('completed_agents', []):
            response['status'] = 'completed'
            response['data']['full_results'] = self._format_response(state)
        
        return response
    
    def _has_session(self, session_id: str) -> bool:
        """
        Проверка наличия сессии
        
        Args:
            session_id: ID сессии
            
        Returns:
            True если сессия существует
        """
        session_file = Path(f'/tmp/mas_sessions/{session_id}.json')
        return session_file.exists()
    
    def _load_session(self, session_id: str) -> MASState:
        """
        Загрузка состояния сессии
        
        Args:
            session_id: ID сессии
            
        Returns:
            Сохраненное состояние
        """
        import json
        
        session_file = Path(f'/tmp/mas_sessions/{session_id}.json')
        
        with open(session_file, 'r', encoding='utf-8') as f:
            state_dict = json.load(f)
        
        # Преобразуем словарь обратно в MASState
        state = MASState(**state_dict)
        return state
    
    def _save_session(self, session_id: str, state: MASState):
        """
        Сохранение состояния сессии
        
        Args:
            session_id: ID сессии
            state: Текущее состояние
        """
        import json
        
        session_dir = Path('/tmp/mas_sessions')
        session_dir.mkdir(exist_ok=True)
        
        session_file = session_dir / f'{session_id}.json'
        
        # Конвертируем состояние в сериализуемый формат
        state_dict = {}
        for key, value in state.items():
            if value is not None and not key.startswith('_'):
                try:
                    json.dumps(value)  # Проверяем сериализуемость
                    state_dict[key] = value
                except (TypeError, ValueError):
                    # Пропускаем несериализуемые объекты или сохраняем как строку
                    if hasattr(value, 'content'):
                        state_dict[key] = str(value.content)
                    else:
                        state_dict[key] = str(value)
        
        with open(session_file, 'w', encoding='utf-8') as f:
            json.dump(state_dict, f, ensure_ascii=False, indent=2)
    
    async def get_pipeline_code(self, execution_id: str) -> Optional[str]:
        """
        Получение сгенерированного кода пайплайна по ID выполнения
        
        Args:
            execution_id: ID выполнения
            
        Returns:
            Код пайплайна или None
        """
        # Здесь можно реализовать загрузку из БД или файловой системы
        # Пока возвращаем заглушку
        return None
    
    async def get_report(self, execution_id: str) -> Optional[str]:
        """
        Получение сгенерированного отчета по ID выполнения
        
        Args:
            execution_id: ID выполнения
            
        Returns:
            Отчет в формате Markdown или None
        """
        # Здесь можно реализовать загрузку из БД или файловой системы
        # Пока возвращаем заглушку
        return None
