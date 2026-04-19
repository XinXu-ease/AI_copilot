from typing import Optional, Dict, Any
from src.agents.base import BaseAgent
from src.prompts.developer import DEV_SYSTEM_PROMPT
from src.schemas.dev import DevOutput 
from src.services.llm_service import call_llm_json


class DeveloperAgent(BaseAgent):
    name = "developer"

    def run(self, brief: dict, ux_output: dict, research_output: Optional[Dict[str, Any]] = None) -> DevOutput:
        # ✅ Format comprehensive research context for the prompt
        research_context = ""
        
        # Extract insights and opportunities from research_output
        insights_text = ""
        opportunities_text = ""
        risks_text = ""
        
        if research_output:
            insights = research_output.get("insights", [])
            opportunities = research_output.get("opportunities", [])
            risks = research_output.get("risks", [])
            
            if insights:
                insights_text = """
Key Research Insights:
"""
                for insight in insights[:10]:
                    stmt = insight.get("statement", "")
                    evidence_type = insight.get("evidence_type", "")
                    conf = insight.get("confidence", "")
                    insights_text += f"\n- {stmt} ({evidence_type}, {conf} confidence)"
            
            if opportunities:
                opportunities_text = """
Market Opportunities:
"""
                for opp in opportunities[:5]:
                    title = opp.get("title", "")
                    rationale = opp.get("rationale", "")
                    opportunities_text += f"\n- {title}: {rationale}\n"
            
            if risks:
                risks_text = """
Identified Risks:
"""
                for risk in risks[:3]:
                    risks_text += f"\n- {risk}"
        
        research_context = f"{insights_text}{opportunities_text}{risks_text}"
        
        user_prompt = f"""
Project brief:
{brief}

UX output:
{ux_output}

{research_context}

Generate an MVP implementation plan that aligns with the research findings and UX design.
Consider the identified research insights and risks when planning the tech stack and feature scope.

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