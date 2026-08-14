from __future__ import annotations

from typing import Any

from device_registry import Device, registry
from network import discover_local_network


def sync_discovered_devices() -> list[dict[str, Any]]:
    """Register local discovery results without authorizing control."""
    discovered = discover_local_network()
    synced: list[dict[str, Any]] = []

    for item in discovered.get("arp", []):
        address = item.get("ip")
        mac = item.get("mac")
        if not address:
            continue

        device_id = f"lan:{mac or address}".lower()
        device = registry.get(device_id)
        if device is None:
            device = registry.register(
                Device(
                    device_id=device_id,
                    name=address,
                    device_type="unknown",
                    address=address,
                    capabilities=[],
                    authorized=False,
                    online=True,
                    adapter="local_arp",
                )
            )
        else:
            device.address = address
            device.online = True

        synced.append(device.to_dict())

    return synced
