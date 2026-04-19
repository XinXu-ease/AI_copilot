from typing import List, Optional
from pydantic import BaseModel


class DVFAssessment(BaseModel):
    """
    PM assessment of current research reliability across one DVF dimension.
    """
    dimension: str  # "desirability", "viability", or "feasibility"
    statement: str
    confidence: str  # "high", "medium", "low"
    evidence: str


class ResearchEvaluation(BaseModel):
    """
    PM quality-gate decision for the current research round.

    This is separate from research feedback:
    - ResearchEvaluation decides whether the workflow proceeds or iterates.
    - Research feedback gives the next ResearchAgent run concrete improvements.
    """
    passes_gate: bool
    overall_score: float  # 0-10
    next_action: str  # "proceed_to_ux", "iterate_research", "force_proceed_with_risk"

    evidence_quality: float  # 0-10
    coverage_score: float    # 0-10
    consistency_score: float  # 0-10
    actionability_score: float = 0.0  # 0-10
    risk_awareness_score: float = 0.0  # 0-10

    strengths: List[str] = []
    fail_reasons: List[str] = []
    targeted_revision_actions: List[str] = []
    risks_identified: List[str] = []
    assumptions_needing_validation: List[str] = []
    dvf_assessments: List[DVFAssessment] = []

    iteration: int
    max_rounds: Optional[int] = None
