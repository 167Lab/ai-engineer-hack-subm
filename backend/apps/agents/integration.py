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
            data_sample=request_data.get('data_sample', []),
            source_metadata=request_data.get('source_metadata', {}),
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
        DEPRECATED: Используется только для обратной совместимости
        """
        state = initial_state
        logger.info(f"🚀 Starting sequential pipeline, exec={state.get('execution_id')}")
        
        logger.info(f"🔸 Stage 1/4: input_analysis starting...")
        state = self.input_analyzer.execute(state)
        logger.info(f"🔸 Stage 1/4: input_analysis complete")
        
        logger.info(f"🔸 Stage 2/4: ddl_generation starting...")
        state = self.ddl_generator.execute(state)
        logger.info(f"🔸 Stage 2/4: ddl_generation complete")
        
        logger.info(f"🔸 Stage 3/4: pipeline_generation starting...")
        state = self.pipeline_generator.execute(state)
        logger.info(f"🔸 Stage 3/4: pipeline_generation complete")
        
        logger.info(f"🔸 Stage 4/4: report_generation starting...")
        state = self.report_generator.execute(state)
        logger.info(f"🔸 Stage 4/4: report_generation complete")
        
        logger.info(f"🚀 Sequential pipeline complete, exec={state.get('execution_id')}")
        return state
    
    async def run_input_analysis(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Запуск только анализа входных данных (Stage 1)
        Возвращает рекомендации по хранилищу
        """
        try:
            logger.info(f"🎯 Starting input analysis only")
            
            # Создаем начальное состояние
            state = self._create_initial_state(request_data)
            
            # Запускаем только input_analysis
            logger.info(f"🔸 Running input_analysis...")
            state = self.input_analyzer.execute(state)
            logger.info(f"✅ input_analysis complete")
            
            # Сохраняем состояние в сессии для последующих этапов
            session_id = state.get('execution_id')
            self._save_session(session_id, state)
            
            # Форматируем результат
            return {
                'status': 'success',
                'session_id': session_id,
                'execution_id': session_id,
                'stage': 'input_analysis',
                'storage_recommendation': state.get('storage_recommendation'),
                'data_characteristics': state.get('data_characteristics'),
                'optimization_recommendations': state.get('optimization_recommendations'),
                'alternative_storages': state.get('alternative_storages'),
                'raw_response': state.get('input_analysis_response')
            }
            
        except Exception as e:
            logger.error(f"Ошибка input_analysis: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'stage': 'input_analysis'
            }
    
    async def run_ddl_and_pipeline(self, session_id: str, user_choices: Dict[str, Any]) -> Dict[str, Any]:
        """
        Запуск генерации DDL и пайплайна (Stages 2-3)
        После того как пользователь выбрал хранилище и параметры
        """
        try:
            logger.info(f"🎯 Starting DDL and pipeline generation for session {session_id}")
            
            # Загружаем состояние из сессии
            state = self._load_session(session_id)
            if not state:
                return {
                    'status': 'error',
                    'error': 'Session not found',
                    'session_id': session_id
                }
            
            # Добавляем выбор пользователя в состояние
            state['selected_storage'] = user_choices.get('storage_type')
            state['pipeline_params'] = user_choices.get('pipeline_params', {})
            state['user_choices'] = user_choices
            
            # Запускаем DDL generation
            logger.info(f"🔸 Running ddl_generation...")
            state = self.ddl_generator.execute(state)
            logger.info(f"✅ ddl_generation complete")
            
            # Запускаем pipeline generation
            logger.info(f"🔸 Running pipeline_generation...")
            state = self.pipeline_generator.execute(state)
            logger.info(f"✅ pipeline_generation complete")
            
            # Сохраняем обновленное состояние
            self._save_session(session_id, state)
            
            # Форматируем результат
            return {
                'status': 'success',
                'session_id': session_id,
                'execution_id': state.get('execution_id'),
                'stages': ['ddl_generation', 'pipeline_generation'],
                'ddl_result': state.get('ddl_result'),
                'pipeline_result': state.get('pipeline_result'),
                'dag_config': state.get('dag_config'),
                'raw_responses': {
                    'ddl': state.get('ddl_generation_response'),
                    'pipeline': state.get('pipeline_generation_response')
                }
            }
            
        except Exception as e:
            logger.error(f"Ошибка DDL/Pipeline generation: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'stages': ['ddl_generation', 'pipeline_generation']
            }
    
    async def run_report_generation(self, session_id: str) -> Dict[str, Any]:
        """
        Запуск генерации отчета (Stage 4)
        Отдельный процесс после всех остальных этапов
        """
        try:
            logger.info(f"🎯 Starting report generation for session {session_id}")
            
            # Загружаем состояние из сессии
            state = self._load_session(session_id)
            if not state:
                return {
                    'status': 'error',
                    'error': 'Session not found',
                    'session_id': session_id
                }
            
            # Запускаем report generation
            logger.info(f"🔸 Running report_generation...")
            state = self.report_generator.execute(state)
            logger.info(f"✅ report_generation complete")
            
            # Сохраняем обновленное состояние
            self._save_session(session_id, state)
            
            # Форматируем результат
            return {
                'status': 'success',
                'session_id': session_id,
                'execution_id': state.get('execution_id'),
                'stage': 'report_generation',
                'report': state.get('final_report'),
                'raw_response': state.get('report_generation_response')
            }
            
        except Exception as e:
            logger.error(f"Ошибка report generation: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'stage': 'report_generation'
            }
    
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
    
    def _load_session(self, session_id: str) -> Optional[MASState]:
        """
        Загрузка состояния сессии
        
        Args:
            session_id: ID сессии
            
        Returns:
            Сохраненное состояние или None если не найдено
        """
        import json
        
        session_file = Path(f'/tmp/mas_sessions/{session_id}.json')
        
        if not session_file.exists():
            logger.warning(f"Session file not found: {session_id}")
            return None
        
        try:
            with open(session_file, 'r', encoding='utf-8') as f:
                state_dict = json.load(f)
            
            # Преобразуем словарь обратно в MASState
            state = MASState(**state_dict)
            return state
        except Exception as e:
            logger.error(f"Failed to load session {session_id}: {e}")
            return None
    
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
