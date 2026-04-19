from typing import List, Optional
from pydantic import BaseModel


class CompetitorItem(BaseModel):
    name: str
    positioning: str
    strengths: List[str] = []
    weaknesses: List[str] = []
    notes: Optional[str] = None


class InsightItem(BaseModel):
    statement: str
    evidence_type: str  # observed / inferred / hypothesis
    confidence: str     # low / medium / high


class OpportunityItem(BaseModel):
    title: str
    rationale: str
    linked_insights: List[str] = []


class ResearchOutput(BaseModel):
    """Output from Research Agent"""
    market_summary: List[str] = []
    competitors: List[CompetitorItem] = []
    user_pain_points: List[str] = []
    insights: List[InsightItem] = []
    opportunities: List[OpportunityItem] = []
    open_questions: List[str] = []
