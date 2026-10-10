import json
import os
import sqlite3
import uuid
from datetime import datetime
from typing import Any

DATABASE_PATH = os.getenv("DATABASE_URL", "sqlite:///./ps03_ad_auditor.db")
if DATABASE_PATH.startswith("sqlite:///"):
    DATABASE_FILE = DATABASE_PATH.replace("sqlite:///", "", 1)
    if DATABASE_FILE.startswith("./"):
        DATABASE_FILE = os.path.join(os.path.dirname(__file__), DATABASE_FILE.lstrip("./"))
else:
    DATABASE_FILE = os.path.join(os.path.dirname(__file__), "ps03_ad_auditor.db")


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DATABASE_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS audit_records (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                created_at TEXT,
                status TEXT,
                payload TEXT
            )
            """
        )
        conn.commit()


def save_audit_record(user_id: str | None, status: str, payload: dict[str, Any]) -> dict[str, Any]:
    record_id = str(uuid.uuid4())
    created_at = datetime.utcnow().isoformat()
    with _connect() as conn:
        conn.execute(
            "INSERT INTO audit_records (id, user_id, created_at, status, payload) VALUES (?, ?, ?, ?, ?)",
            (record_id, user_id, created_at, status, json.dumps(payload)),
        )
        conn.commit()
    return {"id": record_id, "user_id": user_id, "status": status, "created_at": created_at}


def list_audit_records(user_id: str | None) -> list[dict[str, Any]]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT id, user_id, created_at, status, payload FROM audit_records WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,),
        ).fetchall()
    records: list[dict[str, Any]] = []
    for row in rows:
        records.append({
            "id": row["id"],
            "user_id": row["user_id"],
            "status": row["status"],
            "created_at": row["created_at"],
            "payload": json.loads(row["payload"] or "{}"),
        })
    return records


def delete_audit_record(record_id: str, user_id: str | None) -> bool:
    with _connect() as conn:
        cursor = conn.execute(
            "DELETE FROM audit_records WHERE id = ? AND user_id = ?",
            (record_id, user_id),
        )
        conn.commit()
    return cursor.rowcount > 0

