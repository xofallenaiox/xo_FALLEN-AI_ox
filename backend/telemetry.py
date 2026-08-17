"""Authenticated system telemetry."""

from __future__ import annotations

import psutil


def snapshot() -> dict:
    memory = psutil.virtual_memory()
    network = psutil.net_io_counters()
    return {
        "cpu": psutil.cpu_percent(interval=None),
        "memory": memory.percent,
        "gpu": 0,
        "network": {
            "bytes_sent": network.bytes_sent,
            "bytes_recv": network.bytes_recv,
        },
    }
