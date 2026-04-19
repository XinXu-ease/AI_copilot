import json
from src.agents.base import BaseAgent
from src.prompts.researcher import RESEARCH_SYSTEM_PROMPT
from src.schemas.research import ResearchOutput
from src.services.llm_service import call_llm_json_with_tools
from src.services.research_tools import (
  competitor_scan,
  market_scan,
  user_pain_scan,
  web_search,
)


RESEARCH_TOOLS = [
  {
    "type": "function",
    "function": {
      "name": "web_search",
      "description": "Run a targeted web search query for custom research needs.",
      "parameters": {
        "type": "object",
        "properties": {
          "query": {
            "type": "string",
            "description": "Specific web search query.",
          },
          "max_results": {
            "type": "integer",
            "description": "Maximum number of source snippets to return (1-8).",
            "minimum": 1,
            "maximum": 8,
          },
        },
        "required": ["query"],
      },
    },
  },
  {
    "type": "function",
    "function": {
      "name": "market_scan",
      "description": "Search market size, trend, and growth signals for a product category.",
      "parameters": {
        "type": "object",
        "properties": {
          "product": {"type": "string", "description": "Product or market category."},
          "region": {"type": "string", "description": "Region scope, default global."},
          "max_results": {"type": "integer", "minimum": 1, "maximum": 8},
        },
        "required": ["product"],
      },
    },
  },
  {
    "type": "function",
    "function": {
      "name": "competitor_scan",
      "description": "Search direct competitors, alternatives, and positioning signals.",
      "parameters": {
        "type": "object",
        "properties": {
          "product": {"type": "string", "description": "Product or problem space."},
          "max_results": {"type": "integer", "minimum": 1, "maximum": 8},
        },
        "required": ["product"],
      },
    },
  },
  {
    "type": "function",
    "function": {
      "name": "user_pain_scan",
      "description": "Search user complaints, pain points, and unmet needs for a product area.",
      "parameters": {
        "type": "object",
        "properties": {
          "product": {"type": "string", "description": "Product or problem space."},
          "target_users": {"type": "string", "description": "Optional target user segment."},
          "max_results": {"type": "integer", "minimum": 1, "maximum": 8},
        },
        "required": ["product"],
      },
    },
  },
]

RESEARCH_TOOL_HANDLERS = {
  "web_search": web_search,
  "market_scan": market_scan,
  "competitor_scan": competitor_scan,
  "user_pain_scan": user_pain_scan,
}


class ResearchAgent(BaseAgent):
    name = "research"

    def run(self, task: dict) -> ResearchOutput:
        user_prompt = f"""
You are a research agent. Based on this task, provide research findings in JSON format.

Autonomous tool policy:
- Decide which tools to call based on the product type and task scope.
- If the task includes web_search_queries, call web_search for those queries before producing the final JSON.
- Prefer market_scan for market sizing/trends, competitor_scan for landscape, and user_pain_scan for user needs.
- Use web_search for custom deep dives when specialized tools are not enough.
- Call 1-4 tools as needed and avoid redundant calls.

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
        data = call_llm_json_with_tools(
            RESEARCH_SYSTEM_PROMPT,
            user_prompt,
            tools=RESEARCH_TOOLS,
            tool_handlers=RESEARCH_TOOL_HANDLERS,
        )
        return ResearchOutput(**data)
    
