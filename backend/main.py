"""FALLEN Cloud Brain API and same-origin HUD service."""

from __future__ import annotations

import json
import os
import secrets
from pathlib import Path
from typing import Annotated

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from .agent_service import AgentStore
from .ai_orchestrator import AIOrchestrator
from .permissions import get_tool_policy
from .security import (
    RateLimiter,
    SESSION_SECRET,
    require_auth,
    require_csrf,
    token_matches,
)
from .telemetry import snapshot
from .voice import speak

load_dotenv()

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.getenv("FALLEN_DATA_DIR", str(ROOT / "data")))
DATA_DIR.mkdir(parents=True, exist_ok=True)
FRONTEND_DIR = ROOT / "frontend"

ENROLLMENT_TOKEN = os.getenv("FALLEN_AGENT_ENROLLMENT_TOKEN", "").strip()
if len(ENROLLMENT_TOKEN) < 32:
    raise RuntimeError(
        "FALLEN_AGENT_ENROLLMENT_TOKEN must contain at least 32 random characters."
    )
AGENT_ENROLLMENT_TOKEN = ENROLLMENT_TOKEN

store = AgentStore(DATA_DIR / "fallen_cloud.db")
orchestrator = AIOrchestrator(store)

app = FastAPI(title="FALLEN Cloud Brain", version="1.1.0")

allowed_hosts = [
    item.strip()
    for item in os.getenv("FALLEN_ALLOWED_HOSTS", "127.0.0.1,localhost").split(",")
    if item.strip()
]
allowed_origins = [
    item.strip()
    for item in os.getenv(
        "FALLEN_ALLOWED_ORIGINS",
        "http://127.0.0.1:5500,http://localhost:5500",
    ).split(",")
    if item.strip()
]

app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts)
app.add_middleware(
    SessionMiddleware,
    secret_key=SESSION_SECRET,
    session_cookie="fallen_session",
    max_age=3600,
    same_site="strict",
    https_only=os.getenv("FALLEN_COOKIE_SECURE", "false").lower() == "true",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type", "X-FALLEN-CSRF", "X-FALLEN-Agent-ID"],
)

login_limiter = RateLimiter()
enrollment_limiter = RateLimiter()
agent_bearer = HTTPBearer(auto_error=False)


class SessionRequest(BaseModel):
    token: str = Field(min_length=32, max_length=256)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=12_000)
    agent_id: str = Field(min_length=1, max_length=100)


class AgentRegistration(BaseModel):
    enrollment_token: str = Field(min_length=32, max_length=256)
    name: str = Field(min_length=1, max_length=100)


class AgentResult(BaseModel):
    task_id: str = Field(min_length=1, max_length=100)
    success: bool
    result: dict = Field(default_factory=dict)


async def require_agent(
    request: Request,
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(agent_bearer),
    ],
) -> str:
    """Authenticate an agent using a bearer token and explicit agent ID header."""
    agent_id = request.headers.get("X-FALLEN-Agent-ID", "").strip()
    token = credentials.credentials if credentials else ""
    if not agent_id or not token or not store.authenticate(agent_id, token):
        raise HTTPException(
            status_code=401,
            detail="Invalid agent credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    store.heartbeat(agent_id)
    return agent_id


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "online", "role": "cloud_brain"}


@app.post("/auth/session")
async def create_session(payload: SessionRequest, request: Request) -> dict[str, str | bool]:
    client = request.client.host if request.client else "unknown"
    await login_limiter.enforce(f"auth:{client}", limit=10, window=60)
    if not token_matches(payload.token):
        raise HTTPException(status_code=401, detail="Authentication failed.")

    csrf_token = secrets.token_urlsafe(32)
    request.session.clear()
    request.session["authenticated"] = True
    request.session["csrf_token"] = csrf_token
    return {"authenticated": True, "csrf_token": csrf_token}


@app.post("/auth/logout", dependencies=[Depends(require_csrf)])
async def logout(
    request: Request,
    _subject: Annotated[str, Depends(require_auth)],
) -> dict[str, bool]:
    request.session.clear()
    return {"authenticated": False}


@app.post("/chat", dependencies=[Depends(require_csrf)])
async def chat(
    payload: ChatRequest,
    _subject: Annotated[str, Depends(require_auth)],
) -> dict[str, str]:
    online = any(
        agent["agent_id"] == payload.agent_id and agent["online"]
        for agent in store.list_agents()
    )
    if not online:
        raise HTTPException(status_code=409, detail="Selected Windows agent is offline.")

    try:
        reply = await orchestrator.run(payload.message, payload.agent_id)
    except Exception:
        raise HTTPException(status_code=502, detail="AI orchestration failed.") from None
    return {"reply": reply}


@app.post("/agents/register")
async def register_agent(payload: AgentRegistration, request: Request) -> dict[str, str]:
    client = request.client.host if request.client else "unknown"
    await enrollment_limiter.enforce(f"enroll:{client}", limit=5, window=300)
    if not secrets.compare_digest(payload.enrollment_token, AGENT_ENROLLMENT_TOKEN):
        raise HTTPException(status_code=401, detail="Invalid enrollment token.")
    agent_id, token = store.register_agent(payload.name.strip())
    return {"agent_id": agent_id, "token": token}


@app.get("/agents")
async def agents(_subject: Annotated[str, Depends(require_auth)]) -> list[dict]:
    return store.list_agents()


@app.get("/permissions")
async def permissions(_subject: Annotated[str, Depends(require_auth)]) -> list[dict]:
    policies = []
    for tool_name in (
        "windows_open_app",
        "windows_read_text",
        "windows_speak",
    ):
        policy = get_tool_policy(tool_name)
        if policy is None:
            continue
        policies.append(
            {
                "name": policy.name,
                "risk": policy.risk,
                "description": policy.description,
                "requires_confirmation": policy.requires_confirmation,
            }
        )
    return policies


@app.post("/agents/poll")
async def poll_agent(agent_id: Annotated[str, Depends(require_agent)]) -> dict:
    task = store.claim_next(agent_id)
    if task is None:
        return {"task": None}
    return {
        "task": {
            "task_id": task.task_id,
            "tool": task.tool,
            "arguments": task.arguments,
        }
    }


@app.post("/agents/result")
async def agent_result(
    payload: AgentResult,
    agent_id: Annotated[str, Depends(require_agent)],
) -> dict[str, bool]:
    encoded_result = json.dumps(payload.result, default=str, separators=(",", ":"))
    if len(encoded_result.encode("utf-8")) > 64_000:
        raise HTTPException(status_code=413, detail="Agent result is too large.")

    if not store.complete_task(
        payload.task_id,
        agent_id=agent_id,
        success=payload.success,
        result=payload.result,
    ):
        raise HTTPException(status_code=409, detail="Task is not running.")
    return {"accepted": True}


@app.get("/tasks/pending")
async def pending_tasks(
    _subject: Annotated[str, Depends(require_auth)],
) -> list[dict]:
    tasks = store.list_pending_confirmations()
    return [
        {
            "task_id": task.task_id,
            "agent_id": task.agent_id,
            "tool": task.tool,
            "arguments": task.arguments,
            "status": task.status,
            "requires_confirmation": task.requires_confirmation,
            "created_at": task.created_at,
            "policy": {
                "risk": get_tool_policy(task.tool).risk
                if get_tool_policy(task.tool)
                else "unknown",
                "description": get_tool_policy(task.tool).description
                if get_tool_policy(task.tool)
                else "Unknown operation.",
            },
        }
        for task in tasks
    ]


@app.get("/tasks/{task_id}")
async def get_task(
    task_id: str,
    _subject: Annotated[str, Depends(require_auth)],
) -> dict:
    task = store.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found.")
    return {
        "task_id": task.task_id,
        "agent_id": task.agent_id,
        "tool": task.tool,
        "arguments": task.arguments,
        "status": task.status,
        "requires_confirmation": task.requires_confirmation,
        "result": task.result,
    }


@app.post("/tasks/{task_id}/approve", dependencies=[Depends(require_csrf)])
async def approve_task(
    task_id: str,
    _subject: Annotated[str, Depends(require_auth)],
) -> dict[str, bool]:
    if not store.approve_task(task_id):
        raise HTTPException(status_code=409, detail="Task cannot be approved.")
    return {"approved": True}


@app.post("/tasks/{task_id}/cancel", dependencies=[Depends(require_csrf)])
async def cancel_task(
    task_id: str,
    _subject: Annotated[str, Depends(require_auth)],
) -> dict[str, bool]:
    if not store.cancel_task(task_id):
        raise HTTPException(status_code=409, detail="Task cannot be cancelled.")
    return {"cancelled": True}


@app.get("/telemetry")
async def telemetry(_subject: Annotated[str, Depends(require_auth)]) -> dict:
    return snapshot()


class VoiceRequest(BaseModel):
    text: str = Field(min_length=1, max_length=4000)


@app.post("/voice/speak", dependencies=[Depends(require_csrf)])
async def voice_speak(
    payload: VoiceRequest,
    _subject: Annotated[str, Depends(require_auth)],
) -> dict:
    return speak(payload.text)


if FRONTEND_DIR.is_dir():
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
else:
    @app.get("/")
    async def root() -> FileResponse:
        raise HTTPException(status_code=503, detail="Frontend is unavailable.")
