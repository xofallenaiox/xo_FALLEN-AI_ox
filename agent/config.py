"""Windows agent configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass
from urllib.parse import urlparse


@dataclass(frozen=True, slots=True)
class AgentConfig:
    cloud_url: str
    agent_id: str
    token: str
    poll_interval: float = 1.5
    request_timeout: float = 20.0

    @classmethod
    def from_environment(cls) -> "AgentConfig":
        cloud_url = os.getenv("FALLEN_CLOUD_URL", "").rstrip("/")
        agent_id = os.getenv("FALLEN_AGENT_ID", "").strip()
        token = os.getenv("FALLEN_AGENT_TOKEN", "").strip()

        parsed = urlparse(cloud_url)
        is_local = parsed.hostname in {"127.0.0.1", "localhost", "::1"}
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise RuntimeError("FALLEN_CLOUD_URL must be a valid HTTP(S) URL.")
        if not is_local and parsed.scheme != "https":
            raise RuntimeError("FALLEN_CLOUD_URL must use HTTPS for remote servers.")
        if not agent_id or len(token) < 32:
            raise RuntimeError(
                "FALLEN_AGENT_ID and FALLEN_AGENT_TOKEN must be configured."
            )

        poll_interval = float(os.getenv("FALLEN_AGENT_POLL_INTERVAL", "1.5"))
        request_timeout = float(os.getenv("FALLEN_AGENT_TIMEOUT", "20"))
        if not 0.5 <= poll_interval <= 60:
            raise RuntimeError("FALLEN_AGENT_POLL_INTERVAL must be between 0.5 and 60.")
        if not 1 <= request_timeout <= 120:
            raise RuntimeError("FALLEN_AGENT_TIMEOUT must be between 1 and 120.")

        return cls(
            cloud_url=cloud_url,
            agent_id=agent_id,
            token=token,
            poll_interval=poll_interval,
            request_timeout=request_timeout,
        )
