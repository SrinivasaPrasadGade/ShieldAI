"""
SQLite-backed persistent async task store for ShieldAI.

Replaces in-memory task storage. Tasks survive server restarts,
have TTL expiry, stale task recovery, and structured error capture.
"""

import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, Any

from models.database import get_sqlite_connection
from logging_config import get_logger

logger = get_logger("shield_ai.task_store")

# DDL for async_tasks table — called during DB init
TASK_STORE_DDL = """
CREATE TABLE IF NOT EXISTS async_tasks (
    task_id     TEXT PRIMARY KEY,
    task_type   TEXT NOT NULL,
    status      TEXT NOT NULL DEFAULT 'pending',
    result      TEXT,
    error       TEXT,
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL,
    expires_at  TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_tasks_status ON async_tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_expires ON async_tasks(expires_at);
"""


def init_task_store():
    """Initialize the async_tasks table in SQLite."""
    with get_sqlite_connection() as conn:
        conn.executescript(TASK_STORE_DDL)
    logger.info("task_store_initialized")


def create_task(task_type: str, ttl_hours: int = 24) -> str:
    """
    Create a new async task and return its task_id.

    Args:
        task_type: Type of task (e.g., 'currency_verify', 'evidence_package')
        ttl_hours: Hours before the task result expires

    Returns:
        Generated UUID task_id
    """
    task_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    expires_at = (datetime.now(timezone.utc) + timedelta(hours=ttl_hours)).isoformat()

    with get_sqlite_connection() as conn:
        conn.execute(
            """INSERT INTO async_tasks (task_id, task_type, status, created_at, updated_at, expires_at)
               VALUES (?, ?, 'pending', ?, ?, ?)""",
            (task_id, task_type, now, now, expires_at),
        )

    logger.info("task_created", task_id=task_id, task_type=task_type)
    return task_id


def update_task(
    task_id: str,
    status: str,
    result: Optional[dict] = None,
    error: Optional[str] = None,
) -> None:
    """
    Update an existing task's status and optionally its result or error.

    Args:
        task_id: The task's UUID
        status: New status ('processing', 'complete', 'failed')
        result: Optional result dict (JSON-serialized for storage)
        error: Optional error message
    """
    now = datetime.now(timezone.utc).isoformat()
    result_json = json.dumps(result) if result else None

    with get_sqlite_connection() as conn:
        conn.execute(
            """UPDATE async_tasks
               SET status = ?, result = ?, error = ?, updated_at = ?
               WHERE task_id = ?""",
            (status, result_json, error, now, task_id),
        )

    logger.info("task_updated", task_id=task_id, status=status)


def get_task(task_id: str) -> Optional[dict]:
    """
    Retrieve a task by ID.

    Returns:
        Task dict with parsed result, or None if not found / expired.
    """
    with get_sqlite_connection() as conn:
        row = conn.execute(
            "SELECT * FROM async_tasks WHERE task_id = ?", (task_id,)
        ).fetchone()

    if not row:
        return None

    task = dict(row)

    # Parse JSON result if present
    if task.get("result"):
        try:
            task["result"] = json.loads(task["result"])
        except (json.JSONDecodeError, TypeError):
            pass

    return task


def cleanup_expired() -> int:
    """
    Remove tasks that have passed their TTL expiry.

    Returns:
        Number of tasks cleaned up
    """
    now = datetime.now(timezone.utc).isoformat()

    with get_sqlite_connection() as conn:
        cursor = conn.execute(
            "DELETE FROM async_tasks WHERE expires_at < ?", (now,)
        )
        count = cursor.rowcount

    if count > 0:
        logger.info("tasks_cleaned_up", count=count)
    return count


def recover_stale(timeout_minutes: int = 15) -> int:
    """
    Mark tasks stuck in 'processing' state as 'failed'.
    This handles cases where the server crashed mid-processing.

    Args:
        timeout_minutes: Minutes after which a 'processing' task is considered stale

    Returns:
        Number of tasks recovered
    """
    cutoff = (datetime.now(timezone.utc) - timedelta(minutes=timeout_minutes)).isoformat()
    now = datetime.now(timezone.utc).isoformat()

    with get_sqlite_connection() as conn:
        cursor = conn.execute(
            """UPDATE async_tasks
               SET status = 'failed', error = 'Task timed out (stale recovery)', updated_at = ?
               WHERE status = 'processing' AND updated_at < ?""",
            (now, cutoff),
        )
        count = cursor.rowcount

    if count > 0:
        logger.warning("stale_tasks_recovered", count=count, timeout_minutes=timeout_minutes)
    return count
