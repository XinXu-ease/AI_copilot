import uuid
import json
import sys
import os
import logging
import threading
from typing import Any
from flask import Flask, request, jsonify, make_response
from flask_cors import CORS

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('api.log')
    ]
)
logger = logging.getLogger(__name__)

from src.db.history_store import get_project_history, init_history_db, store_project_snapshot
from src.schemas.state import ProjectState
from src.schemas.brief import ProjectBrief
from src.workflows.graph import graph

init_history_db()

app = Flask(__name__)

# 强制配置 CORS - 允许所有源
CORS(app, 
     origins="*",
     allow_headers=["Content-Type", "Authorization"],
     methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
     supports_credentials=True
)

# 添加 CORS 响应头到所有请求
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    response.headers.add('Access-Control-Max-Age', '3600')
    logger.debug(f"Response headers set for {request.path}")
    return response

logger.info("Flask app created with CORS enabled")

# In-memory store for project states (in production, use database)
project_states = {}
project_state_lock = threading.Lock()


def _store_project_state(project_id: str, state: ProjectState) -> None:
    with project_state_lock:
        project_states[project_id] = state
    store_project_snapshot(project_id, state, event_type=state.get("workflow_status", "snapshot"))


def _get_project_state(project_id: str) -> ProjectState | None:
    with project_state_lock:
        return project_states.get(project_id)


def _coerce_state(data) -> ProjectState:
    """Convert data to ProjectState dict."""
    if isinstance(data, dict):
        return data
    return dict(data) if data else {}


def _serialize_state(state: ProjectState) -> dict:
    """Serialize ProjectState for JSON response."""
    result = {}
    for key, value in state.items():
        if hasattr(value, 'model_dump'):
            result[key] = value.model_dump()
        elif isinstance(value, list) and value and hasattr(value[0], 'model_dump'):
            result[key] = [item.model_dump() for item in value]
        else:
            result[key] = value
    return result


def _serialize_history_entry(entry: dict[str, Any]) -> dict:
    return {
        **entry,
        "payload": _serialize_state(entry.get("payload", {})),
    }


def _stage_from_phase(current_phase: str | None) -> str:
    mapping = {
        "brief_ready": "brief",
        "research_in_progress": "research",
        "research_evaluated": "research",
        "research_round1_done": "research",
        "research_feedback_done": "research",
        "research_validated": "research",
        "ux_v1_done": "ux",
        "ux_feedback_done": "ux",
        "ux_validated": "ux",
        "completed": "dev",
    }
    return mapping.get(current_phase or "", "brief")


def _normalize_snapshot(snapshot: Any) -> ProjectState:
    if isinstance(snapshot, dict):
        return snapshot
    return dict(snapshot) if snapshot else {}


def _run_workflow(project_id: str, initial_state: ProjectState) -> None:
    """Run the LangGraph workflow in the background and persist each snapshot."""
    try:
        logger.info(f"Background workflow started for project {project_id}")
        current_state = dict(initial_state)

        _store_project_state(project_id, {
            **current_state,
            "workflow_status": "running",
            "current_stage": _stage_from_phase(current_state.get("current_phase")),
        })

        for snapshot in graph.stream(current_state, stream_mode="values"):
            state_snapshot = _normalize_snapshot(snapshot)
            if not state_snapshot:
                continue

            current_state = {**current_state, **state_snapshot}
            current_stage = _stage_from_phase(current_state.get("current_phase"))
            workflow_status = "running"

            clarification_questions = current_state.get("clarification_questions", []) or []
            clarification_answers = current_state.get("clarification_answers", []) or []
            if current_stage == "brief" and clarification_questions and not clarification_answers:
                workflow_status = "awaiting_clarification"
            elif current_phase := current_state.get("current_phase"):
                if current_phase == "completed" or current_stage == "dev":
                    workflow_status = "completed"

            _store_project_state(project_id, {
                **current_state,
                "workflow_status": workflow_status,
                "current_stage": current_stage,
            })

            if workflow_status == "awaiting_clarification":
                logger.info(f"Project {project_id} waiting for clarification")
                return

        final_stage = _stage_from_phase(current_state.get("current_phase"))
        _store_project_state(project_id, {
            **current_state,
            "workflow_status": "completed",
            "current_stage": final_stage,
        })
        logger.info(f"Background workflow completed for project {project_id}")
    except Exception as e:
        logger.error(f"Workflow execution failed for project {project_id}: {str(e)}", exc_info=True)
        existing = _get_project_state(project_id) or {}
        _store_project_state(project_id, {
            **existing,
            "workflow_status": "error",
            "workflow_error": str(e),
        })


def _start_background_workflow(project_id: str, state: ProjectState) -> None:
    thread = threading.Thread(
        target=_run_workflow,
        args=(project_id, state),
        daemon=True,
        name=f"project-workflow-{project_id[:8]}",
    )
    thread.start()


@app.route('/api/project/start', methods=['POST', 'OPTIONS'])
def start_project():
    """Start a new project."""
    if request.method == 'OPTIONS':
        return '', 204
        
    try:
        logger.info("Received project start request")
        data = request.json
        idea = data.get('idea', '')
        
        if not idea:
            logger.warning("Empty idea provided")
            return jsonify({"success": False, "error": "Project idea cannot be empty"}), 400
        
        logger.info(f"Starting project with idea: {idea[:100]}...")
        
        project_id = str(uuid.uuid4())
        state: ProjectState = {
            "project_id": project_id,
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
        
        # Store the initial state and run the workflow asynchronously
        initial_state = {
            **state,
            "workflow_status": "running",
            "current_stage": "brief",
        }
        _store_project_state(project_id, initial_state)
        _start_background_workflow(project_id, initial_state)
        logger.info(f"Project {project_id} created successfully and workflow started")
        
        # Return serialized state
        return jsonify({
            "success": True,
            "project_id": project_id,
            "state": _serialize_state(initial_state)
        })
    except Exception as e:
        logger.error(f"Error starting project: {str(e)}", exc_info=True)
        return jsonify({
            "success": False, 
            "error": f"Server error: {str(e)}"
        }), 500


@app.route('/api/project/<project_id>', methods=['GET'])
def get_project(project_id):
    """Get project state."""
    try:
        logger.info(f"Retrieving project {project_id}")
        state = _get_project_state(project_id)
        if state is None:
            logger.warning(f"Project {project_id} not found")
            return jsonify({"success": False, "error": "Project not found"}), 404
        logger.info(f"Project {project_id} retrieved successfully")
        return jsonify({
            "success": True,
            "state": _serialize_state(state)
        })
    except Exception as e:
        logger.error(f"Error retrieving project {project_id}: {str(e)}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 400


@app.route('/api/project/<project_id>/history', methods=['GET'])
def get_project_history_endpoint(project_id):
    try:
        logger.info(f"Retrieving history for project {project_id}")
        history = get_project_history(project_id)
        return jsonify({
            "success": True,
            "history": [_serialize_history_entry(entry) for entry in history],
        })
    except Exception as e:
        logger.error(f"Error retrieving history for project {project_id}: {str(e)}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 400


@app.route('/api/project/<project_id>/clarification', methods=['POST', 'OPTIONS'])
def submit_clarification(project_id):
    """Submit clarification answers."""
    if request.method == 'OPTIONS':
        return '', 204
        
    try:
        logger.info(f"Submitting clarification for project {project_id}")
        state = _get_project_state(project_id)
        if state is None:
            logger.warning(f"Project {project_id} not found for clarification")
            return jsonify({"success": False, "error": "Project not found"}), 404
        
        data = request.json
        answers = data.get('answers', [])
        
        logger.info(f"Received {len(answers)} clarification answers")
        
        # Update state with answers
        next_state = {**state, "clarification_answers": answers}
        next_state = {
            **next_state,
            "workflow_status": "running",
            "workflow_error": None,
        }
        _store_project_state(project_id, next_state)
        _start_background_workflow(project_id, next_state)
        logger.info(f"Clarification workflow restarted for project {project_id}")
        
        return jsonify({
            "success": True,
            "state": _serialize_state(next_state)
        })
    except Exception as e:
        logger.error(f"Error submitting clarification for project {project_id}: {str(e)}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 400


@app.route('/health', methods=['GET', 'OPTIONS'])
def health():
    """Health check endpoint."""
    if request.method == 'OPTIONS':
        return '', 204
    logger.info("Health check requested")
    return jsonify({"status": "healthy", "timestamp": str(uuid.uuid4())})


@app.errorhandler(404)
def not_found(error):
    logger.warning(f"404 error: {request.path}")
    return jsonify({"success": False, "error": "Endpoint not found"}), 404


@app.errorhandler(500)
def internal_error(error):
    logger.error(f"500 error: {str(error)}", exc_info=True)
    return jsonify({"success": False, "error": "Internal server error"}), 500


if __name__ == '__main__':
    logger.info("=" * 60)
    logger.info("AI Product Team Copilot - API Server")
    logger.info("=" * 60)
    logger.info("Starting Flask API server...")
    logger.info("Frontend should request from: http://localhost:5000/api")
    logger.info("=" * 60)
    try:
        app.run(debug=True, port = int(os.getenv("PORT", "5000")), host='0.0.0.0')
    except Exception as e:
        logger.error(f"Failed to start server: {e}", exc_info=True)
