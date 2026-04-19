import time

from src.schemas.state import ProjectState, FeedbackBundle, DecisionLog
from src.schemas.pm import ResearchEvaluation, DVFAssessment
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






def _get_latest_research_eval(state: ProjectState) -> dict:
    evaluation = state.get("research_eval", {}) or {}
    if hasattr(evaluation, "model_dump"):
        return evaluation.model_dump()
    return evaluation if isinstance(evaluation, dict) else {}


def _build_dvf_assessments(research_feedback: dict) -> list[DVFAssessment]:
    assessments = []
    for item in research_feedback.get("dvf_assessments", []) or []:
        assessments.append(
            DVFAssessment(
                dimension=item.get("dimension", ""),
                statement=item.get("statement", ""),
                confidence=item.get("confidence", "medium"),
                evidence=item.get("evidence", ""),
            )
        )
    return assessments





def intake_node(state: ProjectState) -> dict:
    started_at = time.perf_counter()
    brief_obj = state.get("brief")
    brief = pm.build_brief(
        raw_idea=brief_obj.idea_summary if brief_obj else "",
        history=state.get("clarification_answers", []),
    )

    clarification_questions = []
    if not state.get("clarification_answers") and brief.missing_info:
        clarification_questions = pm.prioritize_clarification_questions(brief)

    return _with_node_timing(state, "intake", {
        "brief": brief,
        "clarification_questions": clarification_questions,
        "current_phase": "brief_ready",
    }, started_at)


def clarification_router(state: ProjectState) -> str:
    clarification_questions = state.get("clarification_questions", [])
    if clarification_questions and len(clarification_questions) > 0:
        return "need_clarification"
    return "ready_for_research"


def research_cycle_node(state: ProjectState) -> dict:
    started_at = time.perf_counter()
    brief = state.get("brief")
    existing_cycles = list(state.get("research_cycles", []) or [])
    iteration = len(existing_cycles) + 1

    task = pm.generate_research_task(
        brief,
        iteration=iteration,
        previous_research_output=state.get("research_output"),
        research_eval=_get_latest_research_eval(state),
        research_feedback=state.get("research_feedback", {}),
    )
    output = research_agent.run(task=task)
    output_dict = output.model_dump()

    cycle_item = {
        "iteration": iteration,
        "task": task,
        "output": output_dict,
    }

    payload = {
        "research_cycles": [*existing_cycles, cycle_item],
        "research_iteration": iteration,
        "research_output": output_dict,  # ✅ Elevate to top-level
        "current_phase": "research_in_progress",
    }

    return _with_node_timing(state, "research_cycle", payload, started_at)


def research_evaluator_node(state: ProjectState) -> dict:
    started_at = time.perf_counter()
    brief = state.get("brief")
    research_output = state.get("research_output", {})  # ✅ Now from top-level
    iteration = int(state.get("research_iteration", 1) or 1)

    evaluation = pm.evaluate_research_quality(
        brief=brief,
        research_output=research_output,
        iteration=iteration,
    )
    research_feedback = pm.generate_research_feedback(
        brief=brief,
        research_output=research_output,
    )
    dvf_assessments = _build_dvf_assessments(research_feedback)

    research_eval = ResearchEvaluation(
        passes_gate=evaluation.get("passes_gate", False),
        overall_score=float(evaluation.get("overall_score", 0)),
        next_action=evaluation.get("next_action", "iterate_research"),
        evidence_quality=float(evaluation.get("evidence_quality", 0)),
        coverage_score=float(evaluation.get("coverage_score", 0)),
        consistency_score=float(evaluation.get("consistency_score", 0)),
        actionability_score=float(evaluation.get("actionability_score", 0)),
        risk_awareness_score=float(evaluation.get("risk_awareness_score", 0)),
        strengths=evaluation.get("strengths", []),
        fail_reasons=evaluation.get("fail_reasons", []),
        targeted_revision_actions=evaluation.get("targeted_revision_actions", []),
        risks_identified=evaluation.get("fail_reasons", []),
        assumptions_needing_validation=research_output.get("open_questions", []),
        dvf_assessments=dvf_assessments,
        iteration=iteration,
        max_rounds=evaluation.get("max_rounds"),
    )

    existing_decisions = state.get("decisions_log", []) or []
    decisions = list(existing_decisions)
    dvf_summary = " / ".join([f"{a.dimension}: {a.confidence}" for a in dvf_assessments])

    if research_eval.passes_gate:
        decisions.append(
            DecisionLog(
                phase="research",
                decision="Proceed to UX design",
                rationale=f"Research quality gate passed ({research_eval.overall_score}/10). DVF: {dvf_summary}.",
            )
        )
    elif research_eval.next_action == "force_proceed_with_risk":
        decisions.append(
            DecisionLog(
                phase="research",
                decision="Proceed with risk",
                rationale=f"Reached max research rounds ({iteration}). DVF: {dvf_summary}.",
            )
        )

    # ✅ Pre-build research_context: insights + opportunities + risks
    research_context = {
        "insights": research_output.get("insights", []),
        "opportunities": research_output.get("opportunities", []),
        "risks": research_eval.risks_identified if research_eval.risks_identified else [],
    }

    research_eval_dict = research_eval.model_dump()
    payload = {
        "research_eval": research_eval_dict,
        "research_feedback": research_feedback,
        "research_context": research_context,  # ✅ Pre-built for downstream
        "decisions_log": decisions,
        "current_phase": "research_evaluated",
    }

    return _with_node_timing(state, "research_evaluator", payload, started_at)


def research_evaluator_router(state: ProjectState) -> str:
    evaluation = _get_latest_research_eval(state)
    next_action = evaluation.get("next_action")

    if next_action == "proceed_to_ux":
        return "proceed_to_ux"
    if next_action == "force_proceed_with_risk":
        return "force_proceed"
    return "iterate_research"


def ux_design_node(state: ProjectState) -> dict:
    started_at = time.perf_counter()
    brief = state.get("brief")
    research_output = state.get("research_output", {})  # ✅ From top-level

    ux = ux_agent.run(
        brief=brief.model_dump() if brief else {},
        research_output=research_output,
    )
    return _with_node_timing(
        state,
        "ux_design",
        {"ux_v1": ux, "current_phase": "ux_v1_done"},
        started_at,
    )


def ux_feedback_node(state: ProjectState) -> dict:
    """Generate structured feedback on UX design with DVF evaluation."""
    started_at = time.perf_counter()
    ux_v1 = state.get("ux_v1")
    brief = state.get("brief")
    research_context = state.get("research_context", {})  # ✅ Pre-built from research_evaluator

    ux_output = ux_v1.model_dump() if ux_v1 else {}

    feedback_dict = pm.generate_ux_feedback(
        brief=brief,
        research_output=research_context,
        ux_output=ux_output,
    )

    dvf_assessments = None
    if feedback_dict.get("dvf_assessments"):
        dvf_assessments = [
            DVFAssessment(
                dimension=a.get("dimension", ""),
                statement=a.get("statement", ""),
                confidence=a.get("confidence", "medium"),
                evidence=a.get("evidence", ""),
            )
            for a in feedback_dict.get("dvf_assessments", [])
        ]

    feedback = [
        FeedbackBundle(
            source_agent="pm",
            comments=feedback_dict.get("actionable_revisions", []) +
            feedback_dict.get("feature_priority_feedback", []),
            cross_team_feedback={
                "research": feedback_dict.get("cross_team_feedback", {}).get("research_comments", []),
                "developer": feedback_dict.get("cross_team_feedback", {}).get("developer_comments", []),
            },
            dvf_assessments=dvf_assessments,
        ),
    ]

    payload = {
        "ux_feedback": feedback,
        "current_phase": "ux_feedback_done",
    }
    return _with_node_timing(
        state,
        "ux_feedback",
        payload,
        started_at,
    )


def ux_revision_node(state: ProjectState) -> dict:
    started_at = time.perf_counter()
    brief = state.get("brief")
    research_output = state.get("research_output", {})  # ✅ From top-level
    ux_feedback = state.get("ux_feedback", []) or []

    feedback_context = ""
    if ux_feedback:
        latest_feedback = ux_feedback[-1] if isinstance(ux_feedback, list) else ux_feedback
        comments = latest_feedback.get("comments", []) if isinstance(latest_feedback, dict) else latest_feedback.comments
        if comments:
            feedback_context = "\nPM Feedback:\n" + "\n".join([f"- {c}" for c in comments[:5]])

    ux = ux_agent.run(
        brief=brief.model_dump() if brief else {},
        research_output=research_output,
        feedback_context=feedback_context,
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
    existing_decisions = state.get("decisions_log", []) or []

    ux_payload = (ux_v2 or ux_v1).model_dump() if (ux_v2 or ux_v1) else {}

    dev = developer_agent.run(
        brief=brief.model_dump() if brief else {},
        ux_output=ux_payload,
        research_output=state.get("research_output", {}),  # ✅ From top-level
    )
    decisions = existing_decisions + [
        DecisionLog(
            phase="development",
            decision="Generated MVP implementation plan",
            rationale="UX structure is sufficient for scoped MVP planning.",
        )
    ]
    return _with_node_timing(state, "developer", {
        "dev_output": dev,
        "decisions_log": decisions,
        "current_phase": "completed",
        "next_action": "Review final report and export artifacts",
    }, started_at)
