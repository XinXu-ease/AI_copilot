import uuid
import streamlit as st

from src.db.base import init_db
from src.schemas.state import ProjectState
from src.schemas.brief import ProjectBrief
from src.workflows.graph import graph

# 初始化数据库
init_db()

STAGE_DEFS = [
    ("brief", "PM Brief"),
    ("research_round1", "Research Round 1"),
    ("research_round2", "Research Round 2"),
    ("ux", "UX Design"),
    ("dev", "Developer Plan"),
]


def _get_value(data, key, default=None):
    if data is None:
        return default
    if isinstance(data, dict):
        return data.get(key, default)
    return getattr(data, key, default)


def _to_display_data(data):
    if hasattr(data, "model_dump"):
        return data.model_dump()
    return data


def _coerce_state(data) -> ProjectState:
    if isinstance(data, dict):
        return data
    return dict(data) if data else {}


def _render_stage_overview(state: ProjectState) -> None:
    current_phase = _get_value(state, "current_phase", "")
    brief = _get_value(state, "brief")
    stage_state = {
        "brief": bool(brief),
        "research_round1": bool(_get_value(state, "research_round1")),
        "research_round2": bool(_get_value(state, "research_round2")),
        "ux": bool(_get_value(state, "ux_v1") or _get_value(state, "ux_v2")),
        "dev": bool(_get_value(state, "dev_output")),
    }

    current_stage = "brief"
    if current_phase in {"research_round1_done", "research_feedback_done"}:
        current_stage = "research_round1"
    elif current_phase == "research_validated":
        current_stage = "research_round2"
    elif current_phase in {"ux_v1_done", "ux_feedback_done", "ux_validated"}:
        current_stage = "ux"
    elif current_phase == "completed":
        current_stage = "dev"

    st.subheader("Workflow Stages")
    columns = st.columns(len(STAGE_DEFS))
    for column, (stage_key, label) in zip(columns, STAGE_DEFS):
        if stage_state[stage_key]:
            status = "Completed"
        elif stage_key == current_stage:
            status = "In Progress"
        else:
            status = "Pending"
        column.metric(label, status)


def _render_clarification_form(state: ProjectState, clarification_questions: list) -> None:
    existing_answers = _get_value(state, "clarification_answers", [])

    st.subheader("PM Follow-up Questions")
    for question in clarification_questions:
        with st.chat_message("assistant"):
            st.write(question)

    with st.form("clarification_form"):
        answers = []
        for index, question in enumerate(clarification_questions):
            default_answer = existing_answers[index] if index < len(existing_answers) else ""
            answers.append(
                st.text_input(
                    question,
                    value=default_answer,
                    key=f"clarification_answer_{index}",
                )
            )

        submitted = st.form_submit_button("Continue to Research")

    if submitted:
        cleaned_answers = [answer.strip() for answer in answers]
        next_state = {**state, "clarification_answers": cleaned_answers}
        result = graph.invoke(next_state)
        st.session_state.project_state = _coerce_state(result)
        st.rerun()


st.set_page_config(page_title="AI Product Team Copilot", layout="wide")
st.title("AI Product Team Copilot")

if "project_state" not in st.session_state:
    st.session_state.project_state = None

idea = st.text_area("What do you want to build?", height=160)

if st.button("Start Project"):
    state: ProjectState = {
        "project_id": str(uuid.uuid4()),
        "brief": ProjectBrief(
            title="Untitled Project",
            idea_summary=idea,
            problem_statement="",
            target_users=[],
            existing_alternatives=[],
            constraints=[],
            desired_outputs=[],
            assumptions=[],
            missing_info=[],
        )
    }
    result = graph.invoke(state)
    st.session_state.project_state = _coerce_state(result)

if st.session_state.project_state:
    state = _coerce_state(st.session_state.project_state)
    st.session_state.project_state = state

    current_phase = _get_value(state, "current_phase")
    brief = _get_value(state, "brief")
    clarification_questions = _get_value(state, "clarification_questions", [])
    research_round1 = _get_value(state, "research_round1")
    research_round2 = _get_value(state, "research_round2")
    ux_v1 = _get_value(state, "ux_v1")
    dev_output = _get_value(state, "dev_output")

    _render_stage_overview(state)

    st.subheader("Current Phase")
    st.write(current_phase)

    if brief:
        st.subheader("Structured Brief")
        st.json(_to_display_data(brief))

    if current_phase == "brief_ready" and clarification_questions:
        _render_clarification_form(state, clarification_questions)

    if research_round1:
        st.subheader("Research Round 1")
        st.json(_to_display_data(research_round1))

    if research_round2:
        st.subheader("Research Round 2")
        st.json(_to_display_data(research_round2))

    if ux_v1:
        st.subheader("UX Output")
        st.json(_to_display_data(ux_v1))

    if dev_output:
        st.subheader("Developer Output")
        st.json(_to_display_data(dev_output))
