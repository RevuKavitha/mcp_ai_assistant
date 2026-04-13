from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Dict, List


class NotesStore:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS notes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    content TEXT NOT NULL,
                    tags TEXT DEFAULT '',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.commit()

    def add_note(self, content: str, tags: str = "") -> Dict[str, Any]:
        with self._connect() as conn:
            cur = conn.execute(
                "INSERT INTO notes(content, tags) VALUES(?, ?)",
                (content, tags),
            )
            conn.commit()
            return {"id": cur.lastrowid, "content": content, "tags": tags}

    def search_notes(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        sql = (
            "SELECT id, content, tags, created_at FROM notes "
            "WHERE content LIKE ? OR tags LIKE ? "
            "ORDER BY created_at DESC LIMIT ?"
        )
        term = f"%{query}%"
        with self._connect() as conn:
            rows = conn.execute(sql, (term, term, limit)).fetchall()
        return [dict(row) for row in rows]

    def recent_notes(self, limit: int = 5) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id, content, tags, created_at FROM notes ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]
