import json
from src.agents.base import BaseAgent
from src.prompts.pm import PM_SYSTEM_PROMPT, DVF_FEEDBACK_PROMPT, RESEARCH_FEEDBACK_PROMPT, UX_FEEDBACK_PROMPT
from src.schemas.brief import ProjectBrief
from src.services.llm_service import call_llm_json


class PMAgent(BaseAgent):
    name = "pm"

    def build_brief(self, raw_idea: str, history: list[str] | None = None) -> ProjectBrief:
        history_text = "\n".join(history or [])
        user_prompt = f"""
User raw idea:
{raw_idea}

Prior clarification history:
{history_text}

Task:
Generate a structured project brief.
If information is missing, still fill what you can and include missing_info.

Output schema:
{{
  "title": "string",
  "idea_summary": "string",
  "problem_statement": "string",
  "why_now": "string|null",
  "target_users": ["string"],
  "existing_alternatives": ["string"],
  "business_goal": "string|null",
  "constraints": ["string"],
  "desired_outputs": ["string"],
  "assumptions": ["string"],
  "missing_info": ["string"]
}}
"""
        data = call_llm_json(PM_SYSTEM_PROMPT, user_prompt)
        return ProjectBrief(**data)

    def generate_research_task(self, brief: ProjectBrief) -> dict:
        """Use LLM to generate a customized research task based on the brief."""
        user_prompt = f"""
Project brief:
{json.dumps(brief.model_dump(), indent=2)}

Task:
Generate a detailed research task that will help validate the idea across DVF dimensions (Desirability, Viability, Feasibility).

Output schema:
{{
  "task_type": "string",
  "objective": "string",
  "research_areas": ["string"],
  "desirability_focus": "string",
  "viability_focus": "string",
  "feasibility_focus": "string",
  "key_questions": ["string"],
  "constraints": ["string"]
}}
"""
        return call_llm_json(PM_SYSTEM_PROMPT, user_prompt)

    def generate_research_feedback(self, brief: ProjectBrief, research_output: dict) -> dict:
        """Generate structured feedback on research findings for all teams."""
        user_prompt = f"""
Project brief:
{json.dumps(brief.model_dump(), indent=2)}

Research output:
{json.dumps(research_output, indent=2)}

Task:
Evaluate this research through DVF and business lenses. Provide structured feedback for PM, UX, and Developer teams on:
1. What was researched well
2. Gaps in Desirability/Viability/Feasibility coverage
3. Evidence quality and assumptions vs. facts
4. Cross-team implications
5. What's needed for next phases
"""
        return call_llm_json(RESEARCH_FEEDBACK_PROMPT, user_prompt)

    def generate_ux_feedback(self, brief: ProjectBrief, research_output: dict, ux_output: dict) -> dict:
        """Generate structured feedback on UX deliverables for all teams."""
        user_prompt = f"""
Project brief:
{json.dumps(brief.model_dump(), indent=2)}

Research findings:
{json.dumps(research_output, indent=2)}

UX output:
{json.dumps(ux_output, indent=2)}

Task:
Evaluate this UX design through DVF and business lenses. Provide structured feedback for PM, Research, and Developer teams on:
1. How well UX maps to research and business goals
2. DVF coverage and implications
3. Scope and feasibility concerns
4. Cross-team dependencies and alignment
5. Feature prioritization from business perspective
"""
        return call_llm_json(UX_FEEDBACK_PROMPT, user_prompt)

    def prioritize_clarification_questions(self, brief: ProjectBrief) -> list[str]:
        """Analyze missing_info and LLM-select top 5 most important clarification questions."""
        if not brief.missing_info:
            return []
        
        user_prompt = f"""
Project brief:
{json.dumps(brief.model_dump(), indent=2)}

Task:
Analyze the project brief and identify the 5 most critical information gaps that need clarification from the user.

IMPORTANT GUIDELINES for question wording:
- Use simple, conversational language (avoid jargon and business terminology)
- Make questions feel friendly and approachable, not interrogative
- Each question should be 1-2 sentences maximum
- Frame questions from the user's perspective: what do THEY need to think about?
- Avoid technical or formal phrasing - imagine explaining to a non-technical founder
- Include context where helpful (e.g., "So we can understand your target market better...")
- End with clarity about what we're trying to learn

Selection criteria:
1. Business clarity - helps understand the core value proposition
2. User understanding - what problem are we really solving?
3. Scope definition - what's IN vs OUT of the MVP?
4. Market fit - who needs this and why?
5. Feasibility - practical constraints we should know about

Output exactly 5 friendly, user-focused questions (in order of importance).
Keep them concise, warm, and easy to answer.

Output schema:
{{
  "clarification_questions": ["string"],
  "reasoning": "string"
}}
"""
        result = call_llm_json(PM_SYSTEM_PROMPT, user_prompt)
        return result.get("clarification_questions", [])[:5]

    def generate_dvf_feedback(self, brief: ProjectBrief, research_json: dict) -> dict:
        """Use LLM to generate DVF (Desirability, Viability, Feasibility) feedback on research findings."""
        user_prompt = f"""
Project brief:
{json.dumps(brief.model_dump(), indent=2)}

Research findings:
{json.dumps(research_json, indent=2)}

Task:
Analyze the research findings from DVF perspective and provide structured feedback:
- Desirability: Is this solution something users actually want? What evidence supports/contradicts this?
- Viability: Can the business succeed with this? What are the business model concerns?
- Feasibility: Can we build this? What are the technical and resource challenges?

Output schema:
{{
  "desirability": {{
    "score": "1-10",
    "evidence": "string",
    "risks": ["string"],
    "recommendations": ["string"]
  }},
  "viability": {{
    "score": "1-10",
    "evidence": "string",
    "risks": ["string"],
    "recommendations": ["string"]
  }},
  "feasibility": {{
    "score": "1-10",
    "evidence": "string",
    "risks": ["string"],
    "recommendations": ["string"]
  }},
  "overall_assessment": "string"
}}
"""
        return call_llm_json(DVF_FEEDBACK_PROMPT, user_prompt)

    def run(self, raw_idea: str, history: list[str] | None = None) -> ProjectBrief:
        return self.build_brief(raw_idea=raw_idea, history=history)
