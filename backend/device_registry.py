from __future__ import annotations

from collections.abc import Iterable
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any


@dataclass(slots=True)
class Device:
    device_id: str
    name: str
    device_type: str
    address: str | None = None
    capabilities: list[str] | None = None
    authorized: bool = False
    online: bool = True
    last_seen: str = ""
    adapter: str | None = None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        if not data["last_seen"]:
            data["last_seen"] = datetime.now(timezone.utc).isoformat()
        return data


class DeviceRegistry:
    def __init__(self) -> None:
        self._devices: dict[str, Device] = {}

    def register(self, device: Device) -> Device:
        if not device.capabilities:
            device.capabilities = []
        if not device.last_seen:
            device.last_seen = datetime.now(timezone.utc).isoformat()
        self._devices[device.device_id] = device
        return device

    def authorize(self, device_id: str, authorized: bool = True) -> Device:
        device = self._devices[device_id]
        device.authorized = authorized
        return device

    def mark_online(self, device_id: str, online: bool = True) -> Device:
        device = self._devices[device_id]
        device.online = online
        device.last_seen = datetime.now(timezone.utc).isoformat()
        return device

    def get(self, device_id: str) -> Device | None:
        return self._devices.get(device_id)

    def list(self, authorized_only: bool = False) -> list[dict[str, Any]]:
        devices: Iterable[Device] = self._devices.values()
        if authorized_only:
            devices = (device for device in devices if device.authorized)
        return [device.to_dict() for device in devices]

    def remove(self, device_id: str) -> None:
        self._devices.pop(device_id, None)


registry = DeviceRegistry()
