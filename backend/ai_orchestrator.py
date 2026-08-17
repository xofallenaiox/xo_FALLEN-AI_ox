"""OpenAI Responses orchestration with a remote Windows execution boundary."""

from __future__ import annotations

import asyncio
import json
import os
from typing import Any

from openai import AsyncOpenAI

from .agent_service import AgentStore
from .permissions import get_tool_policy


TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "name": "windows_open_app",
        "description": "Open one allowlisted Windows application.",
        "parameters": {
            "type": "object",
            "properties": {
                "application": {
                    "type": "string",
                    "enum": ["notepad", "calculator", "explorer"],
                }
            },
            "required": ["application"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "windows_read_text",
        "description": "Read a UTF-8 text file under the Windows user's home directory.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "maxLength": 500}
            },
            "required": ["path"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "windows_speak",
        "description": "Speak text through the user's Windows computer.",
        "parameters": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "minLength": 1, "maxLength": 4000}
            },
            "required": ["text"],
            "additionalProperties": False,
        },
        "strict": True,
    },
]


class AIOrchestrator:
    """Runs a bounded Responses API function-calling loop."""

    def __init__(self, store: AgentStore) -> None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is not configured.")
        self.client = AsyncOpenAI(api_key=api_key)
        self.store = store
        self.model = os.getenv("OPENAI_MODEL", "gpt-5.6")
        self.max_rounds = 6

    async def run(self, message: str, agent_id: str) -> str:
        instructions = (
            "You are FALLEN AI. Use Windows tools only when necessary. "
            "The Windows agent is a separate execution boundary. "
            "Never claim an action completed unless its result confirms it. "
            "Never request, reveal, or invent credentials or secrets."
        )
        input_items: list[Any] = [
            {"role": "user", "content": message}
        ]

        for _ in range(self.max_rounds):
            response = await self.client.responses.create(
                model=self.model,
                instructions=instructions,
                input=input_items,
                tools=TOOL_DEFINITIONS,
            )

            calls = [
                item
                for item in response.output
                if getattr(item, "type", None) == "function_call"
            ]
            if not calls:
                return response.output_text

            input_items.extend(response.output)
            for call in calls:
                result = await self._dispatch(
                    agent_id,
                    call.name,
                    json.loads(call.arguments),
                )
                input_items.append(
                    {
                        "type": "function_call_output",
                        "call_id": call.call_id,
                        "output": json.dumps(result, default=str),
                    }
                )

        raise RuntimeError("Maximum tool rounds exceeded.")

    async def _dispatch(
        self,
        agent_id: str,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:
        policy = get_tool_policy(tool_name)
        if policy is None:
            self.store.audit(
                "tool.denied",
                "openai",
                tool_name,
                {"reason": "unknown_tool"},
            )
            return {"ok": False, "error": "Tool is not permitted."}

        try:
            task_id = self.store.create_task(
                agent_id,
                tool_name,
                arguments,
                requires_confirmation=policy.requires_confirmation,
            )
        except ValueError:
            return {"ok": False, "error": "Windows agent is not registered."}

        if policy.requires_confirmation:
            return {
                "ok": False,
                "error": "User confirmation is required.",
                "task_id": task_id,
            }

        deadline = asyncio.get_running_loop().time() + 45
        while asyncio.get_running_loop().time() < deadline:
            task = self.store.get_task(task_id)
            if task is None:
                return {"ok": False, "error": "Task disappeared."}

            if task.status in {"completed", "failed", "cancelled"}:
                return task.result or {
                    "ok": False,
                    "error": f"Task ended with status {task.status}.",
                }

            await asyncio.sleep(0.5)

        self.store.cancel_task(task_id)
        return {"ok": False, "error": "Windows agent timed out."}
