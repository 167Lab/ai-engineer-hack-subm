import asyncio
from langgraph.graph import StateGraph
# Correcting the import path based on Django app structure
from .nodes import AnalystNode, TechWriterNode, ReviewerNode

class MASIntegration:
    def __init__(self):
        # Using StateGraph which is more common and flexible
        self.workflow = StateGraph(dict)
        self._setup()

    def _setup(self):
        self.workflow.add_node("analyst", self._execute_analyst)
        self.workflow.add_node("tech_writer", self._execute_tech_writer)
        self.workflow.add_node("reviewer", self._execute_reviewer)
        
        self.workflow.add_edge("analyst", "tech_writer")
        self.workflow.add_edge("tech_writer", "reviewer")
        
        self.workflow.set_entry_point("analyst")
        self.workflow.set_finish_point("reviewer")
        
        self.graph = self.workflow.compile()

    def _execute_analyst(self, state):
        payload = state.get("source_data", {})
        analyst = AnalystNode()
        result = analyst(payload)
        return {"analysis_result": result}

    def _execute_tech_writer(self, state):
        analysis_result = state.get("analysis_result", {})
        tech_writer = TechWriterNode()
        result = tech_writer(analysis_result)
        return {"tech_writer_result": result}
        
    def _execute_reviewer(self, state):
        tech_writer_result = state.get("tech_writer_result", {})
        reviewer = ReviewerNode()
        result = reviewer(tech_writer_result)
        return {"final_result": result}

    async def analyze_data_source(self, payload: dict):
        # LangGraph's invoke is synchronous, but astream is async.
        # We'll run the sync invoke in an async-friendly way.
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None,
            lambda: self.graph.invoke({
                "source_data": payload,
                "task": "analyze_and_recommend"
            })
        )

# helper для синхронного контекста (если вдруг вызов из sync-кода)
def run_async(coro):
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    else:
        # If there's a running loop, we create a task.
        # This is suitable for calling from async views.
        return loop.create_task(coro)
