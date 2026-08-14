from __future__ import annotations

from fastapi import APIRouter

from device_registry import registry
from network_discovery import discover

router = APIRouter(prefix="/network", tags=["network"])


@router.get("/devices")
def network_devices() -> dict:
    discovered = discover()
    return {
        "discovered": discovered,
        "registered": registry.list(),
        "authorized": registry.list(authorized_only=True),
    }


@router.post("/sync")
def network_sync() -> dict:
    discovered = discover()
    registered = []
    for item in discovered:
        device_id = item.get("ip") or item.get("mac")
        if not device_id:
            continue
        if registry.get(device_id) is None:
            from device_registry import Device
            registry.register(
                Device(
                    device_id=device_id,
                    name=device_id,
                    device_type="network-device",
                    address=item.get("ip"),
                    capabilities=[],
                    authorized=False,
                    online=True,
                    adapter="local-discovery",
                )
            )
        registered.append(registry.get(device_id).to_dict())
    return {"count": len(registered), "devices": registered}
