from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any


DB_PATH = Path(__file__).resolve().parent / "fallen_memory.db"


class MemoryStore:
    def __init__(self, path: Path = DB_PATH) -> None:
        self.path = path
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """CREATE TABLE IF NOT EXISTS memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    kind TEXT NOT NULL,
                    content TEXT NOT NULL,
                    metadata TEXT,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )"""
            )
            conn.commit()

    def add(self, kind: str, content: str, metadata: str | None = None) -> int:
        with self._connect() as conn:
            cur = conn.execute(
                "INSERT INTO memories(kind, content, metadata) VALUES (?, ?, ?)",
                (kind, content, metadata),
            )
            conn.commit()
            return int(cur.lastrowid)

    def search(self, query: str, limit: int = 20) -> list[dict[str, Any]]:
        pattern = f"%{query}%"
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id, kind, content, metadata, created_at "
                "FROM memories WHERE content LIKE ? OR kind LIKE ? "
                "ORDER BY id DESC LIMIT ?",
                (pattern, pattern, max(1, min(limit, 100))),
            ).fetchall()
        return [dict(row) for row in rows]

    def delete(self, memory_id: int) -> bool:
        with self._connect() as conn:
            cur = conn.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
            conn.commit()
            return cur.rowcount > 0


memory = MemoryStore()
