import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from src.config.settings import settings


def _db_path() -> Path:
    return Path(settings.HISTORY_DB_PATH)


def _connect() -> sqlite3.Connection:
    path = _db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    return connection


def _normalize_value(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return _normalize_value(value.model_dump())
    if isinstance(value, dict):
        return {key: _normalize_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_normalize_value(item) for item in value]
    if isinstance(value, tuple):
        return [_normalize_value(item) for item in value]
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def serialize_state(state: dict[str, Any]) -> dict[str, Any]:
    return _normalize_value(state)


def init_history_db() -> None:
    with _connect() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS project_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                current_phase TEXT,
                current_stage TEXT,
                workflow_status TEXT,
                payload_json TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_project_history_project_id_created_at
            ON project_history(project_id, created_at)
            """
        )


def store_project_snapshot(project_id: str, state: dict[str, Any], event_type: str = "snapshot") -> None:
    payload = serialize_state(state)
    with _connect() as connection:
        connection.execute(
            """
            INSERT INTO project_history (
                project_id,
                event_type,
                current_phase,
                current_stage,
                workflow_status,
                payload_json
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                project_id,
                event_type,
                payload.get("current_phase"),
                payload.get("current_stage") or payload.get("current_phase"),
                payload.get("workflow_status"),
                json.dumps(payload, ensure_ascii=False),
            ),
        )


def get_project_history(project_id: str) -> list[dict[str, Any]]:
    with _connect() as connection:
        rows = connection.execute(
            """
            SELECT id, project_id, event_type, current_phase, current_stage, workflow_status, payload_json, created_at
            FROM project_history
            WHERE project_id = ?
            ORDER BY id ASC
            """,
            (project_id,),
        ).fetchall()

    history = []
    for row in rows:
        history.append(
            {
                "id": row["id"],
                "project_id": row["project_id"],
                "event_type": row["event_type"],
                "current_phase": row["current_phase"],
                "current_stage": row["current_stage"],
                "workflow_status": row["workflow_status"],
                "payload": json.loads(row["payload_json"]),
                "created_at": row["created_at"],
            }
        )
    return history