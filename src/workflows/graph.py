from langgraph.graph import StateGraph, START, END
from src.schemas.state import ProjectState
from src.workflows.nodes import (
    intake_node,
    clarification_router,
    research_cycle_node,
    research_evaluator_node,
    research_evaluator_router,
    ux_design_node,
    ux_feedback_node,
    ux_revision_node,
    developer_node,
)

builder = StateGraph(ProjectState)

builder.add_node("intake", intake_node)
builder.add_node("research_cycle", research_cycle_node)
builder.add_node("research_evaluator", research_evaluator_node)
builder.add_node("ux_design", ux_design_node)
builder.add_node("ux_feedback", ux_feedback_node)
builder.add_node("ux_revision", ux_revision_node)
builder.add_node("developer", developer_node)

builder.add_edge(START, "intake")

builder.add_conditional_edges(
    "intake",
    clarification_router,
    {
        "need_clarification": END,       # first version先停在这里让前端继续问用户
        "ready_for_research": "research_cycle",
    },
)

builder.add_edge("research_cycle", "research_evaluator")
builder.add_conditional_edges(
    "research_evaluator",
    research_evaluator_router,
    {
        "iterate_research": "research_cycle",
        "proceed_to_ux": "ux_design",
        "force_proceed": "ux_design",
    },
)
builder.add_edge("ux_design", "ux_feedback")
builder.add_edge("ux_feedback", "ux_revision")
builder.add_edge("ux_revision", "developer")
builder.add_edge("developer", END)

graph = builder.compile()