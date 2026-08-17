from pathlib import Path

from backend.agent_service import AgentStore


def test_agent_registration_and_authentication(tmp_path: Path) -> None:
    store = AgentStore(tmp_path / "fallen.db")
    agent_id, token = store.register_agent("test-windows")

    assert store.authenticate(agent_id, token)
    assert not store.authenticate(agent_id, "wrong-token")


def test_confirmation_blocks_task_until_approval(tmp_path: Path) -> None:
    store = AgentStore(tmp_path / "fallen.db")
    agent_id, _ = store.register_agent("test-windows")

    task_id = store.create_task(
        agent_id,
        "windows_speak",
        {"text": "hello"},
        requires_confirmation=True,
    )

    assert store.get_task(task_id).status == "pending_confirmation"
    assert store.claim_next(agent_id) is None

    assert store.approve_task(task_id)
    claimed = store.claim_next(agent_id)

    assert claimed is not None
    assert claimed.task_id == task_id
    assert claimed.status == "running"


def test_completed_task_is_recorded(tmp_path: Path) -> None:
    store = AgentStore(tmp_path / "fallen.db")
    agent_id, _ = store.register_agent("test-windows")
    task_id = store.create_task(
        agent_id,
        "windows_speak",
        {"text": "hello"},
        requires_confirmation=False,
    )

    assert store.claim_next(agent_id) is not None
    assert store.complete_task(
        task_id,
        agent_id=agent_id,
        success=True,
        result={"ok": True},
    )

    task = store.get_task(task_id)
    assert task is not None
    assert task.status == "completed"
    assert task.result == {"ok": True}
