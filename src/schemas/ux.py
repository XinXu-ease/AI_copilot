from typing import List, Dict
from pydantic import BaseModel


class Persona(BaseModel):
    name: str
    summary: str
    goals: List[str] = []
    pain_points: List[str] = []
    behaviors: List[str] = []


class JourneyStep(BaseModel):
    stage: str
    user_goal: str
    actions: List[str] = []
    pain_points: List[str] = []
    opportunities: List[str] = []


class CoreFlow(BaseModel):
    name: str
    steps: List[str]


class ScreenSpec(BaseModel):
    screen_name: str
    purpose: str
    key_elements: List[str]
    interactions: List[str]


class UXOutput(BaseModel):
    personas: List[Persona] = []
    journey_map: List[JourneyStep] = []
    information_architecture: Dict[str, List[str]] = {}
    core_user_flows: List[CoreFlow] = []
    interaction_principles: List[str] = []
    mvp_screen_specs: List[ScreenSpec] = []