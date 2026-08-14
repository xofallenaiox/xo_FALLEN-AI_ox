from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from event_bus import FallenEvent, bus
from permissions import permission_manager


@dataclass(frozen=True, slots=True)
class Tool:
    name: str
    capability: str
    description: str
    handler: Callable[..., Any]
    destructive: bool = False
    privileged: bool = False


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def list(self) -> list[dict[str, Any]]:
        return [
            {
                "name": tool.name,
                "capability": tool.capability,
                "description": tool.description,
                "destructive": tool.destructive,
                "privileged": tool.privileged,
            }
            for tool in self._tools.values()
        ]

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    async def execute(self, name: str, *, target: str | None = None, **kwargs: Any) -> Any:
        tool = self.get(name)
        if tool is None:
            raise KeyError(f"Unknown tool: {name}")

        allowed = permission_manager.check(tool.capability)
        if not allowed:
            await bus.publish(FallenEvent(
                type="tool.permission_denied",
                status="denied",
                message=f"Permission denied for {tool.name}",
                target=target,
                data={"capability": tool.capability},
            ))
            raise PermissionError(f"Permission denied: {tool.capability}")

        if tool.destructive or tool.privileged:
            await bus.publish(FallenEvent(
                type="tool.confirmation_required",
                status="awaiting_confirmation",
                message=f"Confirmation required for {tool.name}",
                target=target,
                data={
                    "capability": tool.capability,
                    "destructive": tool.destructive,
                    "privileged": tool.privileged,
                },
            ))
            raise PermissionError(f"Explicit confirmation required: {tool.name}")

        await bus.publish(FallenEvent(
            type="tool.execution_started",
            status="running",
            message=f"Executing {tool.name}",
            target=target,
            data={"capability": tool.capability},
        ))
        try:
            result = tool.handler(**kwargs)
            if hasattr(result, "__await__"):
                result = await result
            await bus.publish(FallenEvent(
                type="tool.execution_completed",
                status="completed",
                message=f"Completed {tool.name}",
                target=target,
                data={"capability": tool.capability},
            ))
            return result
        except Exception as exc:
            await bus.publish(FallenEvent(
                type="tool.execution_failed",
                status="failed",
                message=str(exc),
                target=target,
                data={"tool": tool.name, "capability": tool.capability},
            ))
            raise


registry = ToolRegistry()
