from src.agents.base import BaseAgent
from src.prompts.ux import UX_SYSTEM_PROMPT
from src.schemas.ux import UXOutput
from src.services.llm_service import call_llm_json


class UXAgent(BaseAgent):
    name = "ux"

    def run(self, brief: dict, research_output: dict, dvf_summary: list[str]) -> UXOutput:
        user_prompt = f"""
Project brief:
{brief}

Validated research:
{research_output}

DVF summary:
{dvf_summary}

Generate UX deliverables for an MVP.

Return schema:
{{
  "personas": [
    {{
      "name": "string",
      "summary": "string",
      "goals": ["string"],
      "pain_points": ["string"],
      "behaviors": ["string"]
    }}
  ],
  "journey_map": [
    {{
      "stage": "string",
      "user_goal": "string",
      "actions": ["string"],
      "pain_points": ["string"],
      "opportunities": ["string"]
    }}
  ],
  "information_architecture": {{
    "SectionName": ["Item1", "Item2"]
  }},
  "core_user_flows": [
    {{
      "name": "string",
      "steps": ["string"]
    }}
  ],
  "interaction_principles": ["string"],
  "mvp_screen_specs": [
    {{
      "screen_name": "string",
      "purpose": "string",
      "key_elements": ["string"],
      "interactions": ["string"]
    }}
  ]
}}
"""
        data = call_llm_json(UX_SYSTEM_PROMPT, user_prompt)
        return UXOutput(**data)