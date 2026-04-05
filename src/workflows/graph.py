from langgraph.graph import StateGraph, START, END
from src.schemas.state import ProjectState
from src.workflows.nodes import (
    intake_node,
    clarification_router,
    research_round1_node,
    research_feedback_node,
    research_round2_node,
    ux_design_node,
    ux_feedback_node,
    ux_revision_node,
    developer_node,
)

builder = StateGraph(ProjectState)

builder.add_node("intake", intake_node)
builder.add_node("research_round1", research_round1_node)
builder.add_node("research_feedback", research_feedback_node)
builder.add_node("research_round2", research_round2_node)
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
        "ready_for_research": "research_round1",
    },
)

builder.add_edge("research_round1", "research_feedback")
builder.add_edge("research_feedback", "research_round2")
builder.add_edge("research_round2", "ux_design")
builder.add_edge("ux_design", "ux_feedback")
builder.add_edge("ux_feedback", "ux_revision")
builder.add_edge("ux_revision", "developer")
builder.add_edge("developer", END)

graph = builder.compile()