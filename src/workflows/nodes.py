from src.schemas.state import ProjectState, FeedbackBundle, DecisionLog
from src.agents.pm_agent import PMAgent
from src.agents.researcher_agent import ResearchAgent
from src.agents.ux_agent import UXAgent
from src.agents.developer_agent import DeveloperAgent

pm = PMAgent()
research_agent = ResearchAgent()
ux_agent = UXAgent()
developer_agent = DeveloperAgent()


def intake_node(state: ProjectState) -> dict:
    brief_obj = state.get("brief")
    brief = pm.build_brief(
        raw_idea=brief_obj.idea_summary if brief_obj else "",
        history=state.get("clarification_answers", []),
    )
    
    # If user has already answered clarification questions, clear missing_info to proceed
    clarification_questions = []
    if state.get("clarification_answers"):
        # User has responded to questions - clear missing_info and move forward
        brief.missing_info = []
    elif brief.missing_info:
        # First time asking - prioritize top 5 most critical questions
        clarification_questions = pm.prioritize_clarification_questions(brief)
    
    return {
        "brief": brief,
        "clarification_questions": clarification_questions,
        "current_phase": "brief_ready"
    }


def clarification_router(state: ProjectState) -> str:
    brief = state.get("brief")
    missing_info = brief.missing_info if brief else []
    if brief and missing_info:
        return "need_clarification"
    return "ready_for_research"


def research_round1_node(state: ProjectState) -> dict:
    brief = state.get("brief")
    task = pm.generate_research_task(brief)
    output = research_agent.run(task=task)
    return {"research_round1": output, "current_phase": "research_round1_done"}


def research_feedback_node(state: ProjectState) -> dict:
    """Generate structured feedback on research findings."""
    research_round1 = state.get("research_round1")
    research_output = research_round1.model_dump() if research_round1 else {}
    brief = state.get("brief")
    feedback_dict = pm.generate_research_feedback(
        brief=brief,
        research_output=research_output
    )
    
    # Convert structured feedback into FeedbackBundle format
    feedback = [
        FeedbackBundle(
            source_agent="pm",
            comments=feedback_dict.get("actionable_next_steps", []) + 
                    [f"Desirability gaps: {', '.join(feedback_dict.get('desirability_gaps', []))}" if feedback_dict.get("desirability_gaps") else ""],
            cross_team_feedback={"ux": feedback_dict.get("cross_team_feedback", {}).get("ux_comments", []),
                               "developer": feedback_dict.get("cross_team_feedback", {}).get("developer_comments", [])}
        ),
    ]
    return {"research_feedback": feedback, "current_phase": "research_feedback_done"}


def research_round2_node(state: ProjectState) -> dict:
    brief = state.get("brief")
    task = pm.generate_research_task(brief)
    output = research_agent.run(task=task)
    dvf_feedback = pm.generate_dvf_feedback(brief, output.model_dump())
    
    # Convert DVF feedback to summary list
    dvf_summary = [
        f"Desirability (Score {dvf_feedback['desirability']['score']}/10): {dvf_feedback['desirability']['evidence']}",
        f"Viability (Score {dvf_feedback['viability']['score']}/10): {dvf_feedback['viability']['evidence']}",
        f"Feasibility (Score {dvf_feedback['feasibility']['score']}/10): {dvf_feedback['feasibility']['evidence']}",
        f"Overall: {dvf_feedback['overall_assessment']}"
    ]
    
    existing_decisions = state.get("decisions_log", [])
    decisions = existing_decisions + [
        DecisionLog(
            phase="research",
            decision="Proceed to UX design",
            rationale="Research is sufficient for MVP-oriented UX structure."
        )
    ]
    validated_insights = [i.statement for i in output.insights]
    opportunities = [o.title for o in output.opportunities]
    return {
        "research_round2": output,
        "dvf_summary": dvf_summary,
        "validated_insights": validated_insights,
        "opportunities": opportunities,
        "decisions_log": decisions,
        "current_phase": "research_validated",
    }


def ux_design_node(state: ProjectState) -> dict:
    brief = state.get("brief")
    research_round2 = state.get("research_round2")
    research_round1 = state.get("research_round1")
    dvf_summary = state.get("dvf_summary", [])
    
    research_output = (research_round2 or research_round1).model_dump() if (research_round2 or research_round1) else {}
    
    ux = ux_agent.run(
        brief=brief.model_dump() if brief else {},
        research_output=research_output,
        dvf_summary=dvf_summary,
    )
    return {"ux_v1": ux, "current_phase": "ux_v1_done"}


def ux_feedback_node(state: ProjectState) -> dict:
    """Generate structured feedback on UX design."""
    ux_v1 = state.get("ux_v1")
    research_round2 = state.get("research_round2")
    research_round1 = state.get("research_round1")
    brief = state.get("brief")
    
    ux_output = ux_v1.model_dump() if ux_v1 else {}
    research_output = (research_round2 or research_round1).model_dump() if (research_round2 or research_round1) else {}
    
    feedback_dict = pm.generate_ux_feedback(
        brief=brief,
        research_output=research_output,
        ux_output=ux_output
    )
    
    # Convert structured feedback into FeedbackBundle format
    feedback = [
        FeedbackBundle(
            source_agent="pm",
            comments=feedback_dict.get("actionable_revisions", []) + 
                    feedback_dict.get("feature_priority_feedback", []),
            cross_team_feedback={"research": feedback_dict.get("cross_team_feedback", {}).get("research_comments", []),
                               "developer": feedback_dict.get("cross_team_feedback", {}).get("developer_comments", [])}
        ),
    ]
    return {"ux_feedback": feedback, "current_phase": "ux_feedback_done"}


def ux_revision_node(state: ProjectState) -> dict:
    brief = state.get("brief")
    research_round2 = state.get("research_round2")
    research_round1 = state.get("research_round1")
    dvf_summary = state.get("dvf_summary", [])
    
    research_output = (research_round2 or research_round1).model_dump() if (research_round2 or research_round1) else {}
    
    ux = ux_agent.run(
        brief=brief.model_dump() if brief else {},
        research_output=research_output,
        dvf_summary=dvf_summary,
    )
    return {"ux_v2": ux, "current_phase": "ux_validated"}


def developer_node(state: ProjectState) -> dict:
    ux_v2 = state.get("ux_v2")
    ux_v1 = state.get("ux_v1")
    brief = state.get("brief")
    existing_decisions = state.get("decisions_log", [])
    
    ux_payload = (ux_v2 or ux_v1).model_dump() if (ux_v2 or ux_v1) else {}
    dev = developer_agent.run(
        brief=brief.model_dump() if brief else {},
        ux_output=ux_payload,
    )
    decisions = existing_decisions + [
        DecisionLog(
            phase="development",
            decision="Generated MVP implementation plan",
            rationale="UX structure is sufficient for scoped MVP planning."
        )
    ]
    return {
        "dev_output": dev,
        "decisions_log": decisions,
        "current_phase": "completed",
        "next_action": "Review final report and export artifacts",
    }