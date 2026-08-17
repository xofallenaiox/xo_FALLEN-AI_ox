"""Secure cloud-to-Windows-agent task broker."""

from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any


TASK_TTL_SECONDS = 120


@dataclass(frozen=True, slots=True)
class AgentTask:
    task_id: str
    agent_id: str
    tool: str
    arguments: dict[str, Any]
    status: str
    requires_confirmation: bool
    created_at: float
    approved_at: float | None
    result: dict[str, Any] | None


class AgentStore:
    """SQLite-backed single-instance agent registry and task queue."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA busy_timeout = 10000")
        return db

    def _initialize(self) -> None:
        with self._connect() as db:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS agents (
                    agent_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    token_hash TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    last_seen REAL NOT NULL
                );

                CREATE TABLE IF NOT EXISTS agent_tasks (
                    task_id TEXT PRIMARY KEY,
                    agent_id TEXT NOT NULL,
                    tool TEXT NOT NULL,
                    arguments TEXT NOT NULL,
                    status TEXT NOT NULL,
                    requires_confirmation INTEGER NOT NULL,
                    created_at REAL NOT NULL,
                    approved_at REAL,
                    result TEXT,
                    FOREIGN KEY(agent_id) REFERENCES agents(agent_id)
                );

                CREATE INDEX IF NOT EXISTS idx_agent_tasks_poll
                    ON agent_tasks(agent_id, status, created_at);

                CREATE TABLE IF NOT EXISTS audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT NOT NULL,
                    actor TEXT NOT NULL,
                    target TEXT,
                    details TEXT NOT NULL,
                    created_at REAL NOT NULL
                );
                """
            )

    @staticmethod
    def _hash_token(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    def register_agent(self, name: str) -> tuple[str, str]:
        agent_id = secrets.token_urlsafe(18)
        token = secrets.token_urlsafe(48)
        now = time.time()
        with self._connect() as db:
            db.execute(
                """
                INSERT INTO agents(agent_id, name, token_hash, created_at, last_seen)
                VALUES (?, ?, ?, ?, ?)
                """,
                (agent_id, name, self._hash_token(token), now, now),
            )
            db.commit()
        self.audit("agent.registered", agent_id, agent_id, {"name": name})
        return agent_id, token

    def authenticate(self, agent_id: str, token: str) -> bool:
        with self._connect() as db:
            row = db.execute(
                "SELECT token_hash FROM agents WHERE agent_id = ?",
                (agent_id,),
            ).fetchone()
        if row is None:
            return False
        return hmac.compare_digest(
            self._hash_token(token),
            row["token_hash"],
        )

    def heartbeat(self, agent_id: str) -> None:
        with self._connect() as db:
            db.execute(
                "UPDATE agents SET last_seen = ? WHERE agent_id = ?",
                (time.time(), agent_id),
            )
            db.commit()

    def list_agents(self) -> list[dict[str, Any]]:
        with self._connect() as db:
            rows = db.execute(
                """
                SELECT agent_id, name, created_at, last_seen
                FROM agents ORDER BY created_at DESC
                """
            ).fetchall()

        now = time.time()
        return [
            {
                "agent_id": row["agent_id"],
                "name": row["name"],
                "created_at": row["created_at"],
                "last_seen": row["last_seen"],
                "online": now - row["last_seen"] <= 30,
            }
            for row in rows
        ]

    def create_task(
        self,
        agent_id: str,
        tool: str,
        arguments: dict[str, Any],
        *,
        requires_confirmation: bool,
    ) -> str:
        task_id = secrets.token_urlsafe(18)
        status = "pending_confirmation" if requires_confirmation else "queued"
        now = time.time()

        with self._connect() as db:
            exists = db.execute(
                "SELECT 1 FROM agents WHERE agent_id = ?",
                (agent_id,),
            ).fetchone()
            if exists is None:
                raise ValueError("Unknown agent.")
            db.execute(
                """
                INSERT INTO agent_tasks(
                    task_id, agent_id, tool, arguments, status,
                    requires_confirmation, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    task_id,
                    agent_id,
                    tool,
                    json.dumps(arguments, separators=(",", ":")),
                    status,
                    int(requires_confirmation),
                    now,
                ),
            )
            db.commit()

        self.audit(
            "agent.task_created",
            "cloud",
            task_id,
            {
                "agent_id": agent_id,
                "tool": tool,
                "requires_confirmation": requires_confirmation,
            },
        )
        return task_id


    def list_pending_confirmations(self) -> list[AgentTask]:
        now = time.time()
        with self._connect() as db:
            db.execute(
                """
                UPDATE agent_tasks
                SET status = 'expired'
                WHERE status = 'pending_confirmation'
                  AND created_at < ?
                """,
                (now - TASK_TTL_SECONDS,),
            )
            db.commit()

            rows = db.execute(
                """
                SELECT * FROM agent_tasks
                WHERE status = 'pending_confirmation'
                ORDER BY created_at ASC
                """
            ).fetchall()

        return [self._row_to_task(row) for row in rows]

    def approve_task(self, task_id: str) -> bool:
        with self._connect() as db:
            cur = db.execute(
                """
                UPDATE agent_tasks
                SET status = 'queued', approved_at = ?
                WHERE task_id = ? AND status = 'pending_confirmation'
                """,
                (time.time(), task_id),
            )
            db.commit()
        if cur.rowcount:
            self.audit("agent.task_approved", "local_user", task_id, {})
            return True
        return False

    def cancel_task(self, task_id: str) -> bool:
        with self._connect() as db:
            cur = db.execute(
                """
                UPDATE agent_tasks
                SET status = 'cancelled'
                WHERE task_id = ?
                  AND status IN ('pending_confirmation', 'queued')
                """,
                (task_id,),
            )
            db.commit()
        if cur.rowcount:
            self.audit("agent.task_cancelled", "local_user", task_id, {})
            return True
        return False

    def claim_next(self, agent_id: str) -> AgentTask | None:
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                """
                SELECT * FROM agent_tasks
                WHERE agent_id = ? AND status = 'queued'
                ORDER BY created_at LIMIT 1
                """,
                (agent_id,),
            ).fetchone()
            if row is None:
                db.commit()
                return None

            db.execute(
                "UPDATE agent_tasks SET status = 'running' WHERE task_id = ?",
                (row["task_id"],),
            )
            db.commit()

        return self._row_to_task(row, status="running")

    def complete_task(
        self,
        task_id: str,
        *,
        agent_id: str,
        success: bool,
        result: dict[str, Any],
    ) -> bool:
        new_status = "completed" if success else "failed"
        with self._connect() as db:
            cur = db.execute(
                """
                UPDATE agent_tasks
                SET status = ?, result = ?
                WHERE task_id = ? AND agent_id = ? AND status = 'running'
                """,
                (
                    new_status,
                    json.dumps(result, default=str),
                    task_id,
                    agent_id,
                ),
            )
            db.commit()

        if cur.rowcount:
            self.audit(
                f"agent.task_{new_status}",
                "agent",
                task_id,
                {"result": result},
            )
            return True
        return False

    def get_task(self, task_id: str) -> AgentTask | None:
        with self._connect() as db:
            row = db.execute(
                "SELECT * FROM agent_tasks WHERE task_id = ?",
                (task_id,),
            ).fetchone()
        return self._row_to_task(row) if row else None

    def audit(
        self,
        event_type: str,
        actor: str,
        target: str | None,
        details: dict[str, Any],
    ) -> None:
        with self._connect() as db:
            db.execute(
                """
                INSERT INTO audit_log(event_type, actor, target, details, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    event_type,
                    actor,
                    target,
                    json.dumps(details, default=str),
                    time.time(),
                ),
            )
            db.commit()

    @staticmethod
    def _row_to_task(
        row: sqlite3.Row,
        *,
        status: str | None = None,
    ) -> AgentTask:
        return AgentTask(
            task_id=row["task_id"],
            agent_id=row["agent_id"],
            tool=row["tool"],
            arguments=json.loads(row["arguments"]),
            status=status or row["status"],
            requires_confirmation=bool(row["requires_confirmation"]),
            created_at=row["created_at"],
            approved_at=row["approved_at"],
            result=json.loads(row["result"]) if row["result"] else None,
        )
