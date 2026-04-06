import json
from src.agents.base import BaseAgent
from src.prompts.researcher import RESEARCH_SYSTEM_PROMPT
from src.schemas.research import ResearchOutput
from src.services.llm_service import call_llm_json


class ResearchAgent(BaseAgent):
    name = "research"

    def run(self, task: dict) -> ResearchOutput:
        user_prompt = f"""
You are a research agent. Based on this task, provide research findings in JSON format.

Task:
{json.dumps(task, indent=2) if isinstance(task, dict) else str(task)}

Return ONLY valid JSON with this exact structure. CRITICAL RULES:
1. strengths and weaknesses fields MUST be ARRAYS of individual strings, NOT single concatenated strings
2. evidence_type MUST be exactly one of these strings: "observed", "inferred", "hypothesis"
3. confidence MUST be exactly one of these strings: "low", "medium", "high"
4. All list fields must be arrays, no exceptions

Example for competitors with proper array format:
{{
  "name": "CompetitorName",
  "positioning": "Their position",
  "strengths": ["Strength 1", "Strength 2", "Strength 3"],
  "weaknesses": ["Weakness 1", "Weakness 2"],
  "notes": "Additional notes"
}}

Full response structure:
{{
  "market_summary": ["market insight 1", "market insight 2"],
  "competitors": [
    {{
      "name": "string",
      "positioning": "string",
      "strengths": ["strength1", "strength2"],
      "weaknesses": ["weakness1", "weakness2"],
      "notes": "string or null"
    }}
  ],
  "user_pain_points": ["pain1", "pain2"],
  "insights": [
    {{
      "statement": "string",
      "evidence_type": "observed",
      "confidence": "high"
    }}
  ],
  "opportunities": [
    {{
      "title": "string",
      "rationale": "string",
      "linked_insights": ["insight1"]
    }}
  ],
  "open_questions": ["question1", "question2"]
}}

Return ONLY JSON, no markdown, no explanation.
"""
        data = call_llm_json(RESEARCH_SYSTEM_PROMPT, user_prompt)
        return ResearchOutput(**data)
    