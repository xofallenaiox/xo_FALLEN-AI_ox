from __future__ import annotations

from typing import Any

from device_registry import Device, registry
from network_discovery import discover


def sync_discovered_devices() -> list[dict[str, Any]]:
    discovered = discover()
    current = {item.get("ip"): item for item in discovered if item.get("ip")}

    for ip, item in current.items():
        device_id = f"lan:{ip}"
        existing = registry.get(device_id)
        if existing is None:
            registry.register(
                Device(
                    device_id=device_id,
                    name=item.get("hostname") or ip,
                    device_type="network_device",
                    address=ip,
                    capabilities=[],
                    authorized=False,
                    online=True,
                    adapter="local_lan",
                )
            )
        else:
            existing.address = ip
            existing.online = True
            existing.last_seen = ""

    return registry.list(authorized_only=False)
