"""
db.py
-----
Lightweight SQLite persistence layer.

Stores each saved project together with its generated artifacts as a JSON blob,
so the schema stays simple and flexible even if you add / rename artifacts later.

Public API
==========
    init_db(db_path)          -> None    # create tables if needed
    save_project(...)         -> int     # insert; returns new row id
    list_projects(db_path)    -> list    # summary rows for the sidebar
    get_project(db_path, id)  -> dict|None
    delete_project(db_path, id) -> None
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from .utils import now_iso


def _connect(db_path: str) -> sqlite3.Connection:
    """Open a SQLite connection, ensuring the parent folder exists."""
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row  # dict-like row access
    return conn


def init_db(db_path: str) -> None:
    """Create the projects table if it does not already exist."""
    with _connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS projects (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                name          TEXT NOT NULL,
                created_at    TEXT NOT NULL,
                inputs_json   TEXT NOT NULL,
                outputs_json  TEXT NOT NULL
            )
            """
        )
        conn.commit()


def save_project(
    db_path: str,
    name: str,
    inputs: dict[str, Any],
    outputs: dict[str, str],
) -> int:
    """
    Persist a project and its generated outputs.

    Returns the new row id.
    """
    init_db(db_path)
    with _connect(db_path) as conn:
        cursor = conn.execute(
            """
            INSERT INTO projects (name, created_at, inputs_json, outputs_json)
            VALUES (?, ?, ?, ?)
            """,
            (
                name or "Untitled Project",
                now_iso(),
                json.dumps(inputs, ensure_ascii=False),
                json.dumps(outputs, ensure_ascii=False),
            ),
        )
        conn.commit()
        return int(cursor.lastrowid)


def list_projects(db_path: str) -> list[dict[str, Any]]:
    """Return lightweight summaries (id, name, created_at) newest-first."""
    init_db(db_path)
    with _connect(db_path) as conn:
        rows = conn.execute(
            "SELECT id, name, created_at FROM projects ORDER BY id DESC"
        ).fetchall()
        return [dict(row) for row in rows]


def get_project(db_path: str, project_id: int) -> dict[str, Any] | None:
    """Return a full project record (with parsed inputs/outputs) or None."""
    init_db(db_path)
    with _connect(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM projects WHERE id = ?", (project_id,)
        ).fetchone()
    if row is None:
        return None
    return {
        "id": row["id"],
        "name": row["name"],
        "created_at": row["created_at"],
        "inputs": json.loads(row["inputs_json"]),
        "outputs": json.loads(row["outputs_json"]),
    }


def delete_project(db_path: str, project_id: int) -> None:
    """Delete a project by id."""
    init_db(db_path)
    with _connect(db_path) as conn:
        conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))
        conn.commit()
