import uuid
import streamlit as st

from src.schemas.state import ProjectState
from src.schemas.brief import ProjectBrief
from src.workflows.graph import graph

st.set_page_config(page_title="AI Product Team Copilot", layout="wide")
st.title("AI Product Team Copilot")

if "project_state" not in st.session_state:
    st.session_state.project_state = None

idea = st.text_area("What do you want to build?", height=160)

if st.button("Start Project"):
    state = ProjectState(
        project_id=str(uuid.uuid4()),
        brief=ProjectBrief(
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
    )
    result = graph.invoke(state)
    st.session_state.project_state = result

if st.session_state.project_state:
    state = st.session_state.project_state

    st.subheader("Current Phase")
    st.write(state["current_phase"])

    if state["brief"]:
        st.subheader("Structured Brief")
        st.json(state["brief"])

    if state["current_phase"] == "brief_ready" and state["brief"]["missing_info"]:
        st.subheader("PM Follow-up Questions")
        for q in state["brief"]["missing_info"]:
            st.write(f"- {q}")

    if state.get("research_round1"):
        st.subheader("Research Round 1")
        st.json(state["research_round1"])

    if state.get("research_round2"):
        st.subheader("Research Round 2")
        st.json(state["research_round2"])

    if state.get("ux_v1"):
        st.subheader("UX Output")
        st.json(state["ux_v1"])

    if state.get("dev_output"):
        st.subheader("Developer Output")
        st.json(state["dev_output"])