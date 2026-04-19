from typing import Optional, Dict, Any
from src.agents.base import BaseAgent
from src.prompts.ux import UX_SYSTEM_PROMPT
from src.schemas.ux import UXOutput
from src.services.llm_service import call_llm_json


class UXAgent(BaseAgent):
    name = "ux"

    def run(self, brief: dict, research_output: dict, feedback_context: Optional[str] = None) -> UXOutput:
        # ✅ Extract insights and opportunities from research_output
        research_context_text = ""
        insights = research_output.get("insights", [])
        opportunities = research_output.get("opportunities", [])
        
        if insights:
            research_context_text += "\nKey Research Insights:\n"
            for insight in insights[:8]:
                stmt = insight.get("statement", "")
                conf = insight.get("confidence", "")
                research_context_text += f"- {stmt} ({conf} confidence)\n"
        
        if opportunities:
            research_context_text += "\nMarket Opportunities:\n"
            for opp in opportunities[:5]:
                title = opp.get("title", "")
                rationale = opp.get("rationale", "")
                research_context_text += f"- {title}: {rationale}\n"
        
        feedback_text = feedback_context or ""
        
        user_prompt = f"""
Project brief:
{brief}

Validated research:
{research_output}

{research_context_text}
{feedback_text}

Generate UX deliverables for an MVP based on the research findings.

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