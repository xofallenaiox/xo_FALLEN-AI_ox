from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RuntimeConfig:
    environment: str
    host: str
    port: int
    model: str
    voice_enabled: bool
    telemetry_interval: float
    shutdown_timeout: float

    @classmethod
    def from_env(cls) -> "RuntimeConfig":
        return cls(
            environment=os.getenv("FALLEN_ENV", "development"),
            host=os.getenv("FALLEN_HOST", "127.0.0.1"),
            port=int(os.getenv("FALLEN_PORT", "8000")),
            model=os.getenv("OPENAI_MODEL", "gpt-5.6"),
            voice_enabled=os.getenv("FALLEN_VOICE_ENABLED", "true").lower() in {"1", "true", "yes", "on"},
            telemetry_interval=max(0.25, float(os.getenv("FALLEN_TELEMETRY_INTERVAL", "1.0"))),
            shutdown_timeout=max(1.0, float(os.getenv("FALLEN_SHUTDOWN_TIMEOUT", "10"))),
        )
