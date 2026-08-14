from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from enum import IntEnum
from typing import Any


DEFAULT_SUBJECT = "local_user"


class PermissionLevel(IntEnum):
    READ = 1
    WRITE = 2
    PRIVILEGED = 3

    @classmethod
    def parse(cls, value: str | int | "PermissionLevel") -> "PermissionLevel":
        if isinstance(value, cls):
            return value
        if isinstance(value, int):
            return cls(value)
        return cls[value.upper()]


@dataclass(slots=True)
class Grant:
    subject: str
    capability: str
    level: PermissionLevel
    expires_at: datetime | None = None

    def active(self) -> bool:
        return self.expires_at is None or datetime.now(timezone.utc) < self.expires_at

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["level"] = self.level.name
        data["expires_at"] = self.expires_at.isoformat() if self.expires_at else None
        data["active"] = self.active()
        return data


class PermissionManager:
    def __init__(self, default_subject: str = DEFAULT_SUBJECT) -> None:
        self.default_subject = default_subject
        self._grants: dict[tuple[str, str], Grant] = {}

    def grant(
        self,
        capability: str,
        level: str | int | PermissionLevel = PermissionLevel.READ,
        *,
        ttl_seconds: int | None = None,
        subject: str | None = None,
    ) -> dict[str, Any]:
        subject = subject or self.default_subject
        expires_at = None
        if ttl_seconds is not None:
            expires_at = datetime.now(timezone.utc) + timedelta(seconds=max(1, ttl_seconds))
        grant = Grant(subject, capability, PermissionLevel.parse(level), expires_at)
        self._grants[(subject, capability)] = grant
        return grant.to_dict()

    def revoke(self, capability: str, *, subject: str | None = None) -> bool:
        return self._grants.pop((subject or self.default_subject, capability), None) is not None

    def check(
        self,
        capability: str,
        required: PermissionLevel = PermissionLevel.READ,
        *,
        subject: str | None = None,
    ) -> bool:
        grant = self._grants.get((subject or self.default_subject, capability))
        return bool(grant and grant.active() and grant.level >= PermissionLevel.parse(required))

    def list(self, *, subject: str | None = None) -> list[dict[str, Any]]:
        subject = subject or self.default_subject
        return [grant.to_dict() for (grant_subject, _), grant in self._grants.items() if grant_subject == subject]

    def snapshot(self) -> list[dict[str, Any]]:
        return [grant.to_dict() for grant in self._grants.values()]


permission_manager = PermissionManager()
permissions = permission_manager
