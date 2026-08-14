from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import IntEnum
from typing import Any


class PermissionLevel(IntEnum):
    READ = 1
    WRITE = 2
    PRIVILEGED = 3


@dataclass(slots=True)
class Grant:
    subject: str
    capability: str
    level: PermissionLevel
    expires_at: datetime | None = None

    def active(self) -> bool:
        return self.expires_at is None or datetime.now(timezone.utc) < self.expires_at


class PermissionManager:
    def __init__(self) -> None:
        self._grants: dict[tuple[str, str], Grant] = {}

    def grant(self, subject: str, capability: str, level: PermissionLevel, ttl_seconds: int | None = None) -> Grant:
        expires_at = None
        if ttl_seconds is not None:
            expires_at = datetime.now(timezone.utc) + timedelta(seconds=max(1, ttl_seconds))
        grant = Grant(subject, capability, level, expires_at)
        self._grants[(subject, capability)] = grant
        return grant

    def revoke(self, subject: str, capability: str) -> bool:
        return self._grants.pop((subject, capability), None) is not None

    def check(self, subject: str, capability: str, required: PermissionLevel) -> bool:
        grant = self._grants.get((subject, capability))
        return bool(grant and grant.active() and grant.level >= required)

    def snapshot(self) -> list[dict[str, Any]]:
        return [
            {
                "subject": g.subject,
                "capability": g.capability,
                "level": g.level.name,
                "expires_at": g.expires_at.isoformat() if g.expires_at else None,
                "active": g.active(),
            }
            for g in self._grants.values()
        ]


permissions = PermissionManager()
