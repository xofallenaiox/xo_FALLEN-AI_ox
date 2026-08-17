"""Authentication, session, CSRF, and rate-limit helpers for FALLEN."""

from __future__ import annotations

import asyncio
import os
import secrets
import time
from collections import defaultdict, deque
from typing import Annotated

from dotenv import load_dotenv
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

load_dotenv()

MIN_SECRET_LENGTH = 32
API_TOKEN = os.getenv("FALLEN_API_TOKEN", "").strip()
SESSION_SECRET = os.getenv("FALLEN_SESSION_SECRET", "").strip()

for name, value in (
    ("FALLEN_API_TOKEN", API_TOKEN),
    ("FALLEN_SESSION_SECRET", SESSION_SECRET),
):
    if len(value) < MIN_SECRET_LENGTH:
        raise RuntimeError(
            f"{name} must be set to a random value of at least "
            f"{MIN_SECRET_LENGTH} characters."
        )

bearer_scheme = HTTPBearer(auto_error=False)


def token_matches(candidate: str | None) -> bool:
    """Compare an API token using a constant-time comparison."""
    return bool(candidate) and secrets.compare_digest(candidate, API_TOKEN)


async def require_auth(
    request: Request,
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(bearer_scheme),
    ],
) -> str:
    """Authenticate a browser session or a valid bearer token."""
    if request.session.get("authenticated") is True:
        return "local_user"

    if credentials and credentials.scheme.lower() == "bearer":
        if token_matches(credentials.credentials):
            return "local_user"

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required.",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def require_csrf(request: Request) -> None:
    """Require the CSRF token for state-changing session-authenticated requests."""
    if request.session.get("authenticated") is not True:
        return

    expected = request.session.get("csrf_token")
    supplied = request.headers.get("X-FALLEN-CSRF")
    if not expected or not supplied or not secrets.compare_digest(supplied, expected):
        raise HTTPException(status_code=403, detail="CSRF validation failed.")


class RateLimiter:
    """Single-process sliding-window rate limiter."""

    def __init__(self) -> None:
        self._requests: dict[str, deque[float]] = defaultdict(deque)
        self._lock = asyncio.Lock()

    async def enforce(self, key: str, limit: int, window: float) -> None:
        now = time.monotonic()
        cutoff = now - window
        async with self._lock:
            timestamps = self._requests[key]
            while timestamps and timestamps[0] <= cutoff:
                timestamps.popleft()
            if len(timestamps) >= limit:
                retry_after = max(1, int(timestamps[0] + window - now))
                raise HTTPException(
                    status_code=429,
                    detail="Rate limit exceeded.",
                    headers={"Retry-After": str(retry_after)},
                )
            timestamps.append(now)
