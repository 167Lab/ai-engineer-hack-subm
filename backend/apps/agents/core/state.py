"""
Definition of the execution state for the single-LLM pipeline.

Note: This file intentionally avoids any LangGraph dependencies.
"""

from typing import TypedDict, Any, Dict, List, Optional


class MASState(TypedDict, total=False):
    # Conversation/messages history (LLM exchanges or logs)
    messages: List[Any]

    # Input
    source_config: Optional[Dict[str, Any]]
    source_type: Optional[str]
    connection_params: Optional[Dict[str, Any]]

    # Analysis results
    source_metadata: Optional[Dict[str, Any]]
    data_sample: Optional[Any]
    data_profile: Optional[Dict[str, Any]]

    # Storage recommendation
    storage_recommendation: Optional[str]
    storage_reasoning: Optional[str]
    storage_alternatives: Optional[List[Dict[str, Any]]]

    # DDL
    ddl_scripts: Optional[List[Dict[str, str]]]
    ddl_recommendations: Optional[Dict[str, Any]]

    # Pipeline
    pipeline_code: Optional[str]
    pipeline_config: Optional[Dict[str, Any]]
    transformations: Optional[List[str]]

    # Report
    report: Optional[str]
    report_sections: Optional[Dict[str, str]]

    # Flow control
    current_agent: Optional[str]
    next_agent: Optional[str]
    completed_agents: List[str]

    # Feedback
    user_feedback: Optional[Dict[str, Any]]
    user_confirmations: Optional[Dict[str, bool]]

    # Errors/warnings
    errors: List[Dict[str, Any]]
    warnings: List[Dict[str, Any]]

    # Execution metadata
    execution_id: Optional[str]
    start_time: Optional[str]
    end_time: Optional[str]
    execution_stats: Optional[Dict[str, Any]]


