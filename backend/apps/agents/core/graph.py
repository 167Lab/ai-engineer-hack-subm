"""
Граф мультиагентной системы на LangGraph
"""
import logging
from typing import Dict, Any, Literal
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from langchain_core.messages import HumanMessage

from .state import MASState
from .llm_manager import LLMManager
from ..agents import (
    InputAnalyzerAgent,
    DDLGeneratorAgent,
    PipelineGeneratorAgent,
    ReportGeneratorAgent
)
from ..tools import (
    analyze_file_tool,
    extract_metadata_tool,
    extract_sample_tool,
    get_data_profile_tool,
    analyze_database_tool,
    test_connection_tool,
    get_table_schema_tool
)

logger = logging.getLogger(__name__)


def create_mas_graph(llm_manager: LLMManager = None) -> StateGraph:
    """
    Создание графа мультиагентной системы
    
    Args:
        llm_manager: Менеджер LLM для агентов
        
    Returns:
        Скомпилированный граф LangGraph
    """
    if not llm_manager:
        llm_manager = LLMManager()
    
    # Создаем граф состояний
    graph = StateGraph(MASState)
    
    # Инициализация агентов
    input_analyzer = InputAnalyzerAgent(llm_manager=llm_manager)
    ddl_generator = DDLGeneratorAgent(llm_manager=llm_manager)
    pipeline_generator = PipelineGeneratorAgent(llm_manager=llm_manager)
    report_generator = ReportGeneratorAgent(llm_manager=llm_manager)
    
    # Создание узла инструментов
    tools = [
        analyze_file_tool,
        extract_metadata_tool,
        extract_sample_tool,
        get_data_profile_tool,
        analyze_database_tool,
        test_connection_tool,
        get_table_schema_tool
    ]
    tool_node = ToolNode(tools)
    
    # Добавление узлов в граф
    graph.add_node("input_analysis", input_analyzer.execute)
    graph.add_node("ddl_generation", ddl_generator.execute)
    graph.add_node("pipeline_generation", pipeline_generator.execute)
    graph.add_node("report_generation", report_generator.execute)
    graph.add_node("tools", tool_node)
    
    # Функция маршрутизации после анализа входных данных
    def route_after_input_analysis(state: MASState) -> Literal["ddl_generation", "end"]:
        """Определяет следующий шаг после анализа входных данных"""
        if state.get('storage_recommendation'):
            # Если есть рекомендация по хранилищу, переходим к генерации DDL
            return "ddl_generation"
        elif state.get('errors') and len(state['errors']) > 0:
            # Если есть критические ошибки, завершаем
            return "end"
        else:
            # По умолчанию продолжаем
            return "ddl_generation"
    
    # Функция маршрутизации после генерации DDL
    def route_after_ddl(state: MASState) -> Literal["pipeline_generation", "end"]:
        """Определяет следующий шаг после генерации DDL"""
        if state.get('ddl_scripts'):
            # Если DDL скрипты сгенерированы, переходим к пайплайнам
            return "pipeline_generation"
        else:
            # Если нет DDL, завершаем
            return "end"
    
    # Функция маршрутизации после генерации пайплайна
    def route_after_pipeline(state: MASState) -> Literal["report_generation", "end"]:
        """Определяет следующий шаг после генерации пайплайна"""
        if state.get('pipeline_code'):
            # Если пайплайн сгенерирован, создаем отчет
            return "report_generation"
        else:
            # Если нет пайплайна, все равно создаем отчет
            return "report_generation"
    
    # Функция проверки необходимости вызова инструментов
    def should_call_tools(state: MASState) -> Literal["tools", "continue"]:
        """Проверяет, нужно ли вызвать инструменты"""
        # Если последнее сообщение содержит вызов инструмента
        if state.get('messages'):
            last_message = state['messages'][-1]
            if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
                return "tools"
        return "continue"
    
    # Определение ребер графа
    graph.add_edge(START, "input_analysis")
    
    # Условные переходы после анализа
    graph.add_conditional_edges(
        "input_analysis",
        route_after_input_analysis,
        {
            "ddl_generation": "ddl_generation",
            "end": END
        }
    )
    
    # Условные переходы после генерации DDL
    graph.add_conditional_edges(
        "ddl_generation",
        route_after_ddl,
        {
            "pipeline_generation": "pipeline_generation",
            "end": END
        }
    )
    
    # Условные переходы после генерации пайплайна
    graph.add_conditional_edges(
        "pipeline_generation",
        route_after_pipeline,
        {
            "report_generation": "report_generation",
            "end": END
        }
    )
    
    # После генерации отчета - завершение
    graph.add_edge("report_generation", END)
    
    # Компиляция графа
    compiled_graph = graph.compile()
    
    return compiled_graph


def create_interactive_mas_graph(llm_manager: LLMManager = None) -> StateGraph:
    """
    Создание интерактивного графа МАС с возможностью обратной связи
    
    Args:
        llm_manager: Менеджер LLM
        
    Returns:
        Скомпилированный граф с поддержкой интерактивности
    """
    if not llm_manager:
        llm_manager = LLMManager()
    
    # Создаем граф состояний
    graph = StateGraph(MASState)
    
    # Инициализация агентов
    input_analyzer = InputAnalyzerAgent(llm_manager=llm_manager)
    ddl_generator = DDLGeneratorAgent(llm_manager=llm_manager)
    pipeline_generator = PipelineGeneratorAgent(llm_manager=llm_manager)
    report_generator = ReportGeneratorAgent(llm_manager=llm_manager)
    
    # Добавление узлов
    graph.add_node("input_analysis", input_analyzer.execute)
    graph.add_node("ddl_generation", ddl_generator.execute)
    graph.add_node("pipeline_generation", pipeline_generator.execute)
    graph.add_node("report_generation", report_generator.execute)
    
    # Узлы для обработки обратной связи
    graph.add_node("wait_for_feedback", wait_for_user_feedback)
    graph.add_node("process_feedback", process_user_feedback)
    
    # Функция ожидания обратной связи
    async def wait_for_user_feedback(state: MASState) -> MASState:
        """Ожидание обратной связи от пользователя"""
        # Здесь будет логика для интеграции с фронтендом
        # Пока просто помечаем, что ждем feedback
        state['waiting_for_feedback'] = True
        state['feedback_stage'] = state.get('current_agent', 'unknown')
        return state
    
    # Функция обработки обратной связи
    async def process_user_feedback(state: MASState) -> MASState:
        """Обработка полученной обратной связи"""
        if state.get('user_feedback'):
            feedback = state['user_feedback']
            stage = feedback.get('stage', '')
            
            # Применяем корректировки в зависимости от этапа
            if stage == 'input_analysis' and 'storage_override' in feedback:
                state['storage_recommendation'] = feedback['storage_override']
            elif stage == 'ddl_generation' and 'ddl_corrections' in feedback:
                state['ddl_scripts'] = feedback['ddl_corrections']
            elif stage == 'pipeline_generation' and 'pipeline_corrections' in feedback:
                state['pipeline_code'] = feedback['pipeline_corrections']
            
            # Очищаем флаг ожидания
            state['waiting_for_feedback'] = False
            state['user_feedback'] = None
        
        return state
    
    # Функция маршрутизации с учетом обратной связи
    def route_with_feedback(state: MASState) -> str:
        """Маршрутизация с возможностью запроса обратной связи"""
        # Если включен режим с обратной связью
        if state.get('interactive_mode', False):
            # После каждого агента запрашиваем обратную связь
            current = state.get('current_agent', '')
            
            if not state.get('waiting_for_feedback'):
                return "wait_for_feedback"
            elif state.get('user_feedback'):
                return "process_feedback"
            else:
                # Продолжаем к следующему агенту
                if current == 'input_analysis':
                    return "ddl_generation"
                elif current == 'ddl_generation':
                    return "pipeline_generation"
                elif current == 'pipeline_generation':
                    return "report_generation"
                else:
                    return END
        else:
            # Без обратной связи - стандартный поток
            return "continue"
    
    # Определение ребер с учетом интерактивности
    graph.add_edge(START, "input_analysis")
    
    # Добавляем условные переходы для каждого агента
    for agent in ["input_analysis", "ddl_generation", "pipeline_generation"]:
        graph.add_conditional_edges(
            agent,
            route_with_feedback,
            {
                "wait_for_feedback": "wait_for_feedback",
                "continue": agent + "_next" if agent != "pipeline_generation" else "report_generation"
            }
        )
    
    graph.add_edge("report_generation", END)
    
    # Компиляция графа
    compiled_graph = graph.compile()
    
    return compiled_graph


async def wait_for_user_feedback(state: MASState) -> MASState:
    """Ожидание обратной связи от пользователя"""
    state['waiting_for_feedback'] = True
    state['feedback_stage'] = state.get('current_agent', 'unknown')
    logger.info(f"Ожидание обратной связи на этапе: {state['feedback_stage']}")
    return state


async def process_user_feedback(state: MASState) -> MASState:
    """Обработка полученной обратной связи"""
    if state.get('user_feedback'):
        feedback = state['user_feedback']
        stage = feedback.get('stage', '')
        
        logger.info(f"Обработка обратной связи для этапа: {stage}")
        
        # Применяем корректировки
        if stage == 'input_analysis' and 'storage_override' in feedback:
            state['storage_recommendation'] = feedback['storage_override']
            logger.info(f"Изменено хранилище на: {feedback['storage_override']}")
            
        elif stage == 'ddl_generation' and 'ddl_corrections' in feedback:
            state['ddl_scripts'] = feedback['ddl_corrections']
            logger.info("Применены корректировки DDL")
            
        elif stage == 'pipeline_generation' and 'pipeline_corrections' in feedback:
            state['pipeline_code'] = feedback['pipeline_corrections']
            logger.info("Применены корректировки пайплайна")
        
        # Очищаем флаги
        state['waiting_for_feedback'] = False
        state['user_feedback'] = None
    
    return state
