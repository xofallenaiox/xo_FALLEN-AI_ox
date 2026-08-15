import platform
import time
from typing import Any

try:
    import psutil
except ImportError:  # pragma: no cover
    psutil = None


def _gpu_percent() -> float | None:
    """Best-effort NVIDIA GPU utilization without requiring NVML bindings."""
    if platform.system() != "Windows":
        return None
    try:
        import subprocess
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=utilization.gpu",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=2,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        if result.returncode != 0:
            return None
        values = [float(line.strip()) for line in result.stdout.splitlines() if line.strip()]
        return max(values) if values else None
    except Exception:
        return None


def snapshot() -> dict[str, Any]:
    now = time.time()
    if psutil is None:
        return {
            "timestamp": now,
            "platform": platform.platform(),
            "cpu": None,
            "memory": None,
            "gpu": _gpu_percent(),
            "network": None,
        }

    net = psutil.net_io_counters()
    return {
        "timestamp": now,
        "platform": platform.platform(),
        "cpu": psutil.cpu_percent(interval=None),
        "memory": psutil.virtual_memory().percent,
        "gpu": _gpu_percent(),
        "network": {
            "bytes_sent": net.bytes_sent,
            "bytes_recv": net.bytes_recv,
        },
    }
