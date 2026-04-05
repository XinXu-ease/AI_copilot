from src.agents.base import BaseAgent
from src.prompts.developer import DEV_SYSTEM_PROMPT
from src.schemas.dev import DevOutput 
from src.services.llm_service import call_llm_json


class DeveloperAgent(BaseAgent):
    name = "developer"

    def run(self, brief: dict, ux_output: dict) -> DevOutput:
        user_prompt = f"""
Project brief:
{brief}

UX output:
{ux_output}

Generate an MVP implementation plan.

Return schema:
{{
  "mvp_features": ["string"],
  "tech_stack": ["string"],
  "frontend_modules": ["string"],
  "backend_modules": ["string"],
  "database_tables": [
    {{
      "name": "string",
      "purpose": "string",
      "key_fields": ["string"]
    }}
  ],
  "api_drafts": [
    {{
      "endpoint": "string",
      "method": "GET|POST|PUT|DELETE",
      "purpose": "string"
    }}
  ],
  "dev_tasks": [
    {{
      "task_name": "string",
      "owner_type": "frontend|backend|fullstack",
      "priority": "must|should|could"
    }}
  ],
  "implementation_risks": ["string"]
}}
"""
        data = call_llm_json(DEV_SYSTEM_PROMPT, user_prompt)
        return DevOutput(**data)