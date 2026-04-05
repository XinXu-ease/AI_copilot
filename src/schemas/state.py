from typing import List, Optional, Dict, TypedDict
from pydantic import BaseModel
from .brief import ProjectBrief
from .research import ResearchOutput
from .ux import UXOutput
from .dev import DevOutput


class DecisionLog(BaseModel):
    phase: str
    decision: str
    rationale: str


class FeedbackBundle(BaseModel):
    source_agent: str
    comments: List[str] = []
    cross_team_feedback: Optional[Dict[str, List[str]]] = None


class ProjectState(TypedDict, total=False):
    project_id: str
    current_phase: str

    brief: Optional[ProjectBrief]

    clarification_questions: List[str]  # Top 5 prioritized questions (LLM-selected)
    clarification_answers: List[str]

    research_round1: Optional[ResearchOutput]
    research_feedback: List[FeedbackBundle]
    research_round2: Optional[ResearchOutput]

    validated_insights: List[str]
    opportunities: List[str]

    dvf_summary: List[str]

    ux_v1: Optional[UXOutput]
    ux_feedback: List[FeedbackBundle]
    ux_v2: Optional[UXOutput]

    dev_output: Optional[DevOutput]

    decisions_log: List[DecisionLog]
    next_action: Optional[str]