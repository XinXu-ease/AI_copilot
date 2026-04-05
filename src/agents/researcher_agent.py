import json
import re
from src.agents.base import BaseAgent
from src.prompts.researcher import RESEARCH_SYSTEM_PROMPT
from src.schemas.research import ResearchOutput
from src.services.llm_service import call_llm_json


def repair_research_json(data: dict) -> dict:
    """
    Fix common LLM mistakes in JSON output:
    - Convert concatenated strings (e.g., "item1, item2, item3") back into proper arrays
    """
    if not isinstance(data, dict):
        return data
    
    # List of fields that should be arrays
    array_fields = ['market_summary', 'user_pain_points', 'open_questions']
    
    # Fix top-level array fields
    for field in array_fields:
        if field in data and isinstance(data[field], str):
            # Split on commas and clean up
            items = [item.strip() for item in data[field].split(',') if item.strip()]
            data[field] = items if items else []
    
    # Fix competitors array
    if 'competitors' in data and isinstance(data['competitors'], list):
        for competitor in data['competitors']:
            if isinstance(competitor, dict):
                for field in ['strengths', 'weaknesses']:
                    if field in competitor and isinstance(competitor[field], str):
                        # Split on commas and periods, clean up
                        items = re.split(r'[,;]|(?<=[.!?])\s+', competitor[field])
                        items = [item.strip() for item in items if item.strip()]
                        competitor[field] = items if items else []
    
    # Fix insights array
    if 'insights' in data and isinstance(data['insights'], list):
        for insight in data['insights']:
            if isinstance(insight, dict):
                # Ensure evidence_type and confidence are valid enums
                if 'evidence_type' in insight and isinstance(insight['evidence_type'], str):
                    if insight['evidence_type'] not in ['observed', 'inferred', 'hypothesis']:
                        insight['evidence_type'] = 'inferred'
                if 'confidence' in insight and isinstance(insight['confidence'], str):
                    if insight['confidence'] not in ['low', 'medium', 'high']:
                        insight['confidence'] = 'medium'
    
    # Fix opportunities array
    if 'opportunities' in data and isinstance(data['opportunities'], list):
        for opp in data['opportunities']:
            if isinstance(opp, dict) and 'linked_insights' in opp:
                if isinstance(opp['linked_insights'], str):
                    items = [item.strip() for item in opp['linked_insights'].split(',') if item.strip()]
                    opp['linked_insights'] = items if items else []
    
    return data


class ResearchAgent(BaseAgent):
    name = "research"

    def run(self, task: dict) -> ResearchOutput:
        user_prompt = f"""
You are a research agent. Analyze this task and return ONLY a valid JSON response with NO other text.

TASK:
{json.dumps(task, indent=2) if isinstance(task, dict) else str(task)}

*** CRITICAL INSTRUCTIONS ***
YOU MUST return VALID JSON. Pay EXTREME attention to array fields:
- "strengths": MUST be a JSON array like ["item1", "item2", "item3"]
- "weaknesses": MUST be a JSON array like ["item1", "item2", "item3"]
- NEVER concatenate array items with commas into a single string
- NEVER do this: "strengths": "item1, item2, item3"
- ALWAYS do this: "strengths": ["item1", "item2", "item3"]

VALID ENUM VALUES ONLY:
- evidence_type: must be EXACTLY one of: "observed", "inferred", or "hypothesis"
- confidence: must be EXACTLY one of: "low", "medium", or "high"

COMPLETE EXAMPLE (follow this format exactly):
{{
  "market_summary": [
    "The coffee brewing market is growing 15% annually",
    "Specialty coffee enthusiasts seek precision and consistency"
  ],
  "competitors": [
    {{
      "name": "Brew Master App",
      "positioning": "Premium brewing guide for enthusiasts",
      "strengths": [
        "Detailed brewing tutorials",
        "Community support",
        "Brewing timer features"
      ],
      "weaknesses": [
        "Limited social features",
        "No equipment marketplace"
      ],
      "notes": "Focused on premium segment"
    }},
    {{
      "name": "Quick Brew",
      "positioning": "Fast and simple brewing",
      "strengths": [
        "Simple interface",
        "Quick setup"
      ],
      "weaknesses": [
        "Less educational",
        "Limited customization"
      ],
      "notes": "Mass market approach"
    }}
  ],
  "user_pain_points": [
    "Inconsistent brewing results",
    "Don't know which equipment to buy",
    "Want to learn advanced techniques"
  ],
  "insights": [
    {{
      "statement": "Users value both education and convenience",
      "evidence_type": "observed",
      "confidence": "high"
    }},
    {{
      "statement": "Premium segment willing to pay for quality content",
      "evidence_type": "inferred",
      "confidence": "medium"
    }}
  ],
  "opportunities": [
    {{
      "title": "Equipment recommendation engine",
      "rationale": "Users struggle with equipment selection decisions",
      "linked_insights": ["insight_1", "insight_2"]
    }}
  ],
  "open_questions": [
    "How much are users willing to pay for premium content?",
    "Should we include social features?"
  ]
}}

Return ONLY the JSON object, no markdown, no code blocks, no explanation.
"""
        data = call_llm_json(RESEARCH_SYSTEM_PROMPT, user_prompt)
        # Repair common JSON issues before validation
        data = repair_research_json(data)
        return ResearchOutput(**data)
    