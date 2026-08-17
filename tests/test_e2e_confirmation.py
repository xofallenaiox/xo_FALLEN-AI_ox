import os
import sys
import types
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


class _FakeAsyncOpenAI:
    def __init__(self, *args, **kwargs):
        pass


sys.modules.setdefault(
    "openai",
    types.SimpleNamespace(AsyncOpenAI=_FakeAsyncOpenAI),
)

os.environ["FALLEN_API_TOKEN"] = "A" * 48
os.environ["FALLEN_SESSION_SECRET"] = "C" * 48
os.environ["FALLEN_AGENT_ENROLLMENT_TOKEN"] = "B" * 48
os.environ["FALLEN_DATA_DIR"] = str(Path.cwd() / ".test-data")
os.environ["FALLEN_ALLOWED_HOSTS"] = "testserver,127.0.0.1,localhost"
os.environ["OPENAI_API_KEY"] = "test-key"

from backend import main  # noqa: E402


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    store = main.AgentStore(tmp_path / "fallen.db")
    main.store = store
    main.orchestrator = None

    with TestClient(main.app) as test_client:
        yield test_client


def authenticate(client: TestClient) -> None:
    response = client.post(
        "/auth/session",
        json={"token": os.environ["FALLEN_API_TOKEN"]},
    )
    assert response.status_code == 200
    client.headers["X-FALLEN-CSRF"] = response.json()["csrf_token"]


def test_complete_confirmation_flow(client: TestClient) -> None:
    authenticate(client)

    registration = client.post(
        "/agents/register",
        json={
            "enrollment_token": os.environ["FALLEN_AGENT_ENROLLMENT_TOKEN"],
            "name": "E2E-WINDOWS",
        },
    )
    assert registration.status_code == 200
    credentials = registration.json()

    agent_id = credentials["agent_id"]
    agent_token = credentials["token"]

    task_id = main.store.create_task(
        agent_id,
        "windows_read_text",
        {"path": "example.txt"},
        requires_confirmation=True,
    )

    pending = client.get("/tasks/pending")
    assert pending.status_code == 200
    assert pending.json()[0]["task_id"] == task_id
    assert pending.json()[0]["policy"]["risk"] == "medium"

    agent_headers = {
        "Authorization": f"Bearer {agent_token}",
        "X-FALLEN-Agent-ID": agent_id,
    }

    poll_before_approval = client.post(
        "/agents/poll",
        headers=agent_headers,
    )
    assert poll_before_approval.status_code == 200
    assert poll_before_approval.json()["task"] is None

    approved = client.post(f"/tasks/{task_id}/approve")
    assert approved.status_code == 200
    assert approved.json() == {"approved": True}

    poll_after_approval = client.post(
        "/agents/poll",
        headers=agent_headers,
    )
    assert poll_after_approval.status_code == 200
    task = poll_after_approval.json()["task"]
    assert task["task_id"] == task_id
    assert task["tool"] == "windows_read_text"

    result = client.post(
        "/agents/result",
        headers=agent_headers,
        json={
            "task_id": task_id,
            "success": True,
            "result": {"ok": True, "text": "hello"},
        },
    )
    assert result.status_code == 200

    final = client.get(f"/tasks/{task_id}")
    assert final.status_code == 200
    assert final.json()["status"] == "completed"
    assert final.json()["result"] == {"ok": True, "text": "hello"}


def test_agent_cannot_complete_another_agents_task(client: TestClient) -> None:
    authenticate(client)

    first = main.store.register_agent("FIRST")
    second = main.store.register_agent("SECOND")
    first_id, first_token = first
    second_id, second_token = second

    task_id = main.store.create_task(
        first_id,
        "windows_read_text",
        {"path": "example.txt"},
        requires_confirmation=True,
    )
    assert main.store.approve_task(task_id)

    first_headers = {
        "Authorization": f"Bearer {first_token}",
        "X-FALLEN-Agent-ID": first_id,
    }
    second_headers = {
        "Authorization": f"Bearer {second_token}",
        "X-FALLEN-Agent-ID": second_id,
    }

    claimed = client.post(
        "/agents/poll",
        headers=first_headers,
    )
    assert claimed.status_code == 200
    assert claimed.json()["task"]["task_id"] == task_id

    rejected = client.post(
        "/agents/result",
        headers=second_headers,
        json={
            "task_id": task_id,
            "success": True,
            "result": {"ok": True},
        },
    )
    assert rejected.status_code == 409

    final = client.get(f"/tasks/{task_id}")
    assert final.json()["status"] == "running"


def test_unauthenticated_user_cannot_approve(client: TestClient) -> None:
    registration = client.post(
        "/agents/register",
        json={
            "enrollment_token": os.environ["FALLEN_AGENT_ENROLLMENT_TOKEN"],
            "name": "SECURITY-E2E",
        },
    )
    assert registration.status_code == 200
    agent_id = registration.json()["agent_id"]

    task_id = main.store.create_task(
        agent_id,
        "windows_read_text",
        {"path": "example.txt"},
        requires_confirmation=True,
    )

    response = client.post(f"/tasks/{task_id}/approve")
    assert response.status_code == 401
    assert main.store.get_task(task_id).status == "pending_confirmation"


def test_session_authenticated_state_change_requires_csrf(
    client: TestClient,
) -> None:
    response = client.post(
        "/auth/session",
        json={"token": os.environ["FALLEN_API_TOKEN"]},
    )
    assert response.status_code == 200

    client.headers.pop("X-FALLEN-CSRF", None)
    response = client.post("/tasks/missing/cancel")
    assert response.status_code == 403
