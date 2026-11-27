import asyncio
from typing import Dict, Any, Callable

try:
    from langgraph.graph import StateGraph, START, END
    _HAS_LANGGRAPH = True
except ImportError:
    _HAS_LANGGRAPH = False
    START = "START"
    END = "END"
    class StateGraph:
        def __init__(self, state_schema: Any):
            self.state_schema = state_schema
            self.nodes: Dict[str, Callable] = {}
        def add_node(self, name: str, fn: Callable):
            self.nodes[name] = fn
        def add_edge(self, src: str, dst: str):
            pass
        def compile(self):
            nodes = self.nodes
            class CompiledGraph:
                async def ainvoke(self, state: Dict[str, Any]) -> Dict[str, Any]:
                    # Run retrieve_context
                    res1 = await nodes["retrieve_context"](state)
                    state.update(res1)
                    # Run specialist agents in parallel
                    sec_res, perf_res, qual_res = await asyncio.gather(
                        nodes["security_agent"](state),
                        nodes["performance_agent"](state),
                        nodes["quality_agent"](state),
                    )
                    state.update(sec_res)
                    state.update(perf_res)
                    state.update(qual_res)
                    # Run aggregator
                    agg_res = await nodes["aggregator"](state)
                    state.update(agg_res)
                    return state
            return CompiledGraph()

from app.agents.state import AgentReviewState
from app.agents.nodes import (
    retrieve_context_node,
    security_agent_node,
    performance_agent_node,
    quality_agent_node,
    aggregator_node,
)


def create_review_graph():
    """
    Compiles the parallel multi-agent review pipeline.
    Graph Topology:
        START -> retrieve_context
             |--> security_agent    --|
             |--> performance_agent --|--> aggregator -> END
             |--> quality_agent     --|
    """
    workflow = StateGraph(AgentReviewState)

    workflow.add_node("retrieve_context", retrieve_context_node)
    workflow.add_node("security_agent", security_agent_node)
    workflow.add_node("performance_agent", performance_agent_node)
    workflow.add_node("quality_agent", quality_agent_node)
    workflow.add_node("aggregator", aggregator_node)

    workflow.add_edge(START, "retrieve_context")
    workflow.add_edge("retrieve_context", "security_agent")
    workflow.add_edge("retrieve_context", "performance_agent")
    workflow.add_edge("retrieve_context", "quality_agent")
    workflow.add_edge("security_agent", "aggregator")
    workflow.add_edge("performance_agent", "aggregator")
    workflow.add_edge("quality_agent", "aggregator")
    workflow.add_edge("aggregator", END)

    return workflow.compile()


review_graph = create_review_graph()
