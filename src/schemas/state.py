from typing import Any, List, Optional, Dict, TypedDict
from pydantic import BaseModel
from .brief import ProjectBrief
from .pm import ResearchEvaluation, DVFAssessment
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
    dvf_assessments: Optional[List[DVFAssessment]] = None


class ProjectState(TypedDict, total=False):
    project_id: str
    current_phase: str
    current_stage: str
    workflow_status: str
    workflow_error: Optional[str]

    brief: Optional[ProjectBrief]

    clarification_questions: List[str]
    clarification_answers: List[str]

    research_cycles: List[Dict[str, Any]]  # [{"iteration": int, "task": dict, "output": dict}, ...]
    research_iteration: int
    research_output: Optional[Dict[str, Any]]  # Latest research output - single source for downstream
    research_eval: Optional[ResearchEvaluation | Dict[str, Any]]  # Single source of truth
    research_feedback: Dict[str, Any]  # Single source of truth
    research_context: Optional[Dict[str, Any]]  # Pre-built context: insights + opportunities + risks for UX/Dev

    ux_v1: Optional[UXOutput]
    ux_feedback: List[FeedbackBundle]
    ux_v2: Optional[UXOutput]

    dev_output: Optional[DevOutput]

    decisions_log: List[DecisionLog]
    next_action: Optional[str]
    execution_metrics: Dict[str, Any]
