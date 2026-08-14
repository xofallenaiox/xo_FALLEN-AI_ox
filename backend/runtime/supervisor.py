from __future__ import annotations

import asyncio
import inspect
from dataclasses import dataclass, field
from typing import Awaitable, Callable

from ..event_bus import FallenEvent, bus


StartFn = Callable[[], Awaitable[None] | None]
StopFn = Callable[[], Awaitable[None] | None]
HealthFn = Callable[[], bool]


@dataclass(slots=True)
class ServiceSpec:
    name: str
    start: StartFn
    stop: StopFn
    health: HealthFn | None = None
    dependencies: tuple[str, ...] = field(default_factory=tuple)
    critical: bool = False


class ServiceSupervisor:
    """Small, deterministic lifecycle supervisor for FALLEN components."""

    def __init__(self) -> None:
        self._services: dict[str, ServiceSpec] = {}
        self._started: list[str] = []
        self._lock = asyncio.Lock()

    def register(self, service: ServiceSpec) -> None:
        if service.name in self._services:
            raise ValueError(f"Service already registered: {service.name}")
        self._services[service.name] = service

    def status(self) -> list[dict[str, object]]:
        return [
            {
                "name": name,
                "started": name in self._started,
                "healthy": bool(spec.health()) if spec.health and name in self._started else False,
                "critical": spec.critical,
                "dependencies": list(spec.dependencies),
            }
            for name, spec in self._services.items()
        ]

    async def _call(self, fn: Callable[[], object]) -> None:
        result = fn()
        if inspect.isawaitable(result):
            await result

    async def start_all(self) -> None:
        async with self._lock:
            pending = set(self._services)
            while pending:
                progress = False
                for name in tuple(pending):
                    spec = self._services[name]
                    if any(dep not in self._started for dep in spec.dependencies):
                        continue
                    await self._call(spec.start)
                    self._started.append(name)
                    pending.remove(name)
                    progress = True
                    await bus.publish(FallenEvent(
                        type="service.started",
                        status="ready",
                        message=f"Service started: {name}",
                        target=name,
                    ))
                if not progress:
                    raise RuntimeError(f"Unresolved service dependencies: {sorted(pending)}")

    async def stop_all(self) -> None:
        async with self._lock:
            for name in reversed(self._started):
                spec = self._services[name]
                await self._call(spec.stop)
                await bus.publish(FallenEvent(
                    type="service.stopped",
                    status="stopped",
                    message=f"Service stopped: {name}",
                    target=name,
                ))
            self._started.clear()


supervisor = ServiceSupervisor()
