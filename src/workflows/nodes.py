import time

from src.schemas.state import ProjectState, FeedbackBundle, DecisionLog
from src.agents.pm_agent import PMAgent
from src.agents.researcher_agent import ResearchAgent
from src.agents.ux_agent import UXAgent
from src.agents.developer_agent import DeveloperAgent

pm = PMAgent()
research_agent = ResearchAgent()
ux_agent = UXAgent()
developer_agent = DeveloperAgent()


def _with_node_timing(state: ProjectState, node_name: str, payload: dict, started_at: float) -> dict:
    existing_metrics = state.get("execution_metrics", {}) or {}
    node_durations = dict(existing_metrics.get("node_durations_seconds", {}))
    elapsed = round(time.perf_counter() - started_at, 4)
    node_durations[node_name] = round(node_durations.get(node_name, 0.0) + elapsed, 4)
    return {
        **payload,
        "execution_metrics": {
            **existing_metrics,
            "node_durations_seconds": node_durations,
        },
    }


def _get_latest_research_cycle(state: ProjectState) -> dict | None:
    cycles = state.get("research_cycles", []) or []
    if not cycles:
        return None
    return max(cycles, key=lambda item: int(item.get("iteration", 0) or 0))


def _get_latest_research_output(state: ProjectState) -> dict:
    latest_cycle = _get_latest_research_cycle(state)
    if latest_cycle:
        output = latest_cycle.get("output", {})
        if isinstance(output, dict):
            return output
    return {}


def intake_node(state: ProjectState) -> dict:
    started_at = time.perf_counter()
    brief_obj = state.get("brief")
    brief = pm.build_brief(
        raw_idea=brief_obj.idea_summary if brief_obj else "",
        history=state.get("clarification_answers", []),
    )
    
    # If user has already answered clarification questions, move forward
    clarification_questions = []
    if not state.get("clarification_answers") and brief.missing_info:
        # First time asking - prioritize top 5 most critical questions
        clarification_questions = pm.prioritize_clarification_questions(brief)
    
    return _with_node_timing(state, "intake", {
        "brief": brief,
        "clarification_questions": clarification_questions,
        "current_phase": "brief_ready"
    }, started_at)


def clarification_router(state: ProjectState) -> str:
    clarification_questions = state.get("clarification_questions", [])
    # If there are clarification questions, we need clarification
    if clarification_questions and len(clarification_questions) > 0:
        return "need_clarification"
    return "ready_for_research"


def research_cycle_node(state: ProjectState) -> dict:
    started_at = time.perf_counter()
    brief = state.get("brief")
    existing_cycles = list(state.get("research_cycles", []) or [])
    iteration = len(existing_cycles) + 1
    task = pm.generate_research_task(brief)
    output = research_agent.run(task=task)
    output_dict = output.model_dump()

    cycle_item = {
        "iteration": iteration,
        "output": output_dict,
    }

    payload = {
        "research_cycles": [*existing_cycles, cycle_item],
        "research_iteration": iteration,
        "current_phase": "research_in_progress",
    }

    return _with_node_timing(state, "research_cycle", payload, started_at)


def research_evaluator_node(state: ProjectState) -> dict:
    started_at = time.perf_counter()
    brief = state.get("brief")
    research_output = _get_latest_research_output(state)
    iteration = int(state.get("research_iteration", 1) or 1)

    evaluation = pm.evaluate_research_quality(
        brief=brief,
        research_output=research_output,
        iteration=iteration,
    )

    dvf_feedback = pm.generate_dvf_feedback(brief, research_output)
    dvf_summary = [
        f"Desirability (Score {dvf_feedback['desirability']['score']}/10): {dvf_feedback['desirability']['evidence']}",
        f"Viability (Score {dvf_feedback['viability']['score']}/10): {dvf_feedback['viability']['evidence']}",
        f"Feasibility (Score {dvf_feedback['feasibility']['score']}/10): {dvf_feedback['feasibility']['evidence']}",
        f"Overall: {dvf_feedback['overall_assessment']}",
    ]

    existing_decisions = state.get("decisions_log", [])
    decisions = list(existing_decisions)
    if evaluation.get("passes_gate"):
        decisions.append(
            DecisionLog(
                phase="research",
                decision="Proceed to UX design",
                rationale=f"Research quality gate passed ({evaluation.get('overall_score')}/10).",
            )
        )
    elif evaluation.get("next_action") == "force_proceed_with_risk":
        decisions.append(
            DecisionLog(
                phase="research",
                decision="Proceed with risk",
                rationale=(
                    f"Reached max research rounds ({evaluation.get('max_rounds')}) "
                    f"with score {evaluation.get('overall_score')}/10."
                ),
            )
        )

    insights = research_output.get("insights", []) if isinstance(research_output, dict) else []
    opportunities_data = research_output.get("opportunities", []) if isinstance(research_output, dict) else []
    validated_insights = [item.get("statement", "") for item in insights if isinstance(item, dict) and item.get("statement")]
    opportunities = [item.get("title", "") for item in opportunities_data if isinstance(item, dict) and item.get("title")]

    payload = {
        "research_eval": evaluation,
        "dvf_summary": dvf_summary,
        "validated_insights": validated_insights,
        "opportunities": opportunities,
        "decisions_log": decisions,
        "current_phase": "research_evaluated",
    }

    if evaluation.get("next_action") == "force_proceed_with_risk":
        payload["risk_flag"] = "research_quality_below_threshold"

    return _with_node_timing(state, "research_evaluator", payload, started_at)


def research_evaluator_router(state: ProjectState) -> str:
    evaluation = state.get("research_eval", {}) or {}
    next_action = evaluation.get("next_action")

    if next_action == "proceed_to_ux":
        return "proceed_to_ux"
    if next_action == "force_proceed_with_risk":
        return "force_proceed"
    return "iterate_research"


def ux_design_node(state: ProjectState) -> dict:
    started_at = time.perf_counter()
    brief = state.get("brief")
    dvf_summary = state.get("dvf_summary", [])

    research_output = _get_latest_research_output(state)
    
    ux = ux_agent.run(
        brief=brief.model_dump() if brief else {},
        research_output=research_output,
        dvf_summary=dvf_summary,
    )
    return _with_node_timing(
        state,
        "ux_design",
        {"ux_v1": ux, "current_phase": "ux_v1_done"},
        started_at,
    )


def ux_feedback_node(state: ProjectState) -> dict:
    """Generate structured feedback on UX design."""
    started_at = time.perf_counter()
    ux_v1 = state.get("ux_v1")
    brief = state.get("brief")
    
    ux_output = ux_v1.model_dump() if ux_v1 else {}
    research_output = _get_latest_research_output(state)
    
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
    return _with_node_timing(
        state,
        "ux_feedback",
        {"ux_feedback": feedback, "current_phase": "ux_feedback_done"},
        started_at,
    )


def ux_revision_node(state: ProjectState) -> dict:
    started_at = time.perf_counter()
    brief = state.get("brief")
    dvf_summary = state.get("dvf_summary", [])

    research_output = _get_latest_research_output(state)
    
    ux = ux_agent.run(
        brief=brief.model_dump() if brief else {},
        research_output=research_output,
        dvf_summary=dvf_summary,
    )
    return _with_node_timing(
        state,
        "ux_revision",
        {"ux_v2": ux, "current_phase": "ux_validated"},
        started_at,
    )


def developer_node(state: ProjectState) -> dict:
    started_at = time.perf_counter()
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
    return _with_node_timing(state, "developer", {
        "dev_output": dev,
        "decisions_log": decisions,
        "current_phase": "completed",
        "next_action": "Review final report and export artifacts",
    }, started_at)