from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any


@dataclass(slots=True)
class RouterAdapter:
    name: str
    vendor: str
    base_url: str
    capabilities: list[str]
    authenticated: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class RouterManager:
    """Authenticated, vendor-neutral router integration registry.

    This layer deliberately does not implement credential bypassing, password
    cracking, or exploit techniques. Vendor-specific adapters should provide
    authenticated API calls for devices the user owns or is authorized to manage.
    """

    def __init__(self) -> None:
        self._adapters: dict[str, RouterAdapter] = {}

    def register(self, adapter: RouterAdapter) -> None:
        self._adapters[adapter.name] = adapter

    def list(self) -> list[dict[str, Any]]:
        return [adapter.to_dict() for adapter in self._adapters.values()]

    def get(self, name: str) -> RouterAdapter | None:
        return self._adapters.get(name)

    def capabilities(self, name: str) -> list[str]:
        adapter = self._adapters.get(name)
        if adapter is None:
            raise KeyError(name)
        return list(adapter.capabilities)

    def require_authenticated(self, name: str) -> RouterAdapter:
        adapter = self._adapters.get(name)
        if adapter is None:
            raise KeyError(name)
        if not adapter.authenticated:
            raise PermissionError(f"Router adapter '{name}' is not authenticated")
        return adapter


router_manager = RouterManager()
