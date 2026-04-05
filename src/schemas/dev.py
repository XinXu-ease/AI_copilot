from typing import List
from pydantic import BaseModel


class DBTableDraft(BaseModel):
    name: str
    purpose: str
    key_fields: List[str]


class APIDraft(BaseModel):
    endpoint: str
    method: str
    purpose: str


class DevTask(BaseModel):
    task_name: str
    owner_type: str  # frontend / backend / fullstack
    priority: str    # must / should / could


class DevOutput(BaseModel):
    mvp_features: List[str] = []
    tech_stack: List[str] = []
    frontend_modules: List[str] = []
    backend_modules: List[str] = []
    database_tables: List[DBTableDraft] = []
    api_drafts: List[APIDraft] = []
    dev_tasks: List[DevTask] = []
    implementation_risks: List[str] = []