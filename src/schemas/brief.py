from typing import List, Optional
from pydantic import BaseModel, Field


class ProjectBrief(BaseModel):
    title: str = Field(..., description="Short project title")
    idea_summary: str
    problem_statement: str
    why_now: Optional[str] = None
    target_users: List[str] = []
    existing_alternatives: List[str] = []
    business_goal: Optional[str] = None
    constraints: List[str] = []
    desired_outputs: List[str] = []
    assumptions: List[str] = []
    missing_info: List[str] = []