from datetime import datetime
from typing import Any

from app.db import get_connection


def log_action(
    user_id: int,
    username: str,
    action: str,
    table_name: str | None = None,
    record_id: int | None = None,
    details: str | None = None
) -> None:
    """Log an action to the audit log for accountability."""
    with get_connection() as connection:
        cursor = connection.cursor()
        cursor.execute(
            """INSERT INTO audit_logs 
               (user_id, username, action, table_name, record_id, details, timestamp)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                user_id,
                username,
                action,
                table_name,
                record_id,
                details,
                datetime.now().isoformat()
            )
        )
        connection.commit()


def get_audit_logs(limit: int = 100) -> list[dict[str, Any]]:
    """Get audit logs for viewing activity."""
    with get_connection() as connection:
        cursor = connection.cursor()
        cursor.execute(
            """SELECT log_id, user_id, username, action, table_name, record_id, 
                      details, timestamp FROM audit_logs 
               ORDER BY timestamp DESC LIMIT ?""",
            (limit,)
        )
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def get_user_audit_logs(user_id: int, limit: int = 50) -> list[dict[str, Any]]:
    """Get audit logs for a specific user."""
    with get_connection() as connection:
        cursor = connection.cursor()
        cursor.execute(
            """SELECT log_id, user_id, username, action, table_name, record_id, 
                      details, timestamp FROM audit_logs 
               WHERE user_id = ?
               ORDER BY timestamp DESC LIMIT ?""",
            (user_id, limit)
        )
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
