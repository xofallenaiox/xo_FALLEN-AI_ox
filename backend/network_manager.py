from __future__ import annotations

import ipaddress
import platform
import socket
import subprocess
from typing import Any


def _run_windows(args: list[str], timeout: float = 4.0) -> str:
    result = subprocess.run(
        args,
        capture_output=True,
        text=True,
        timeout=timeout,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "command failed")
    return result.stdout


def local_network() -> dict[str, Any]:
    hostname = socket.gethostname()
    addresses: list[str] = []
    try:
        for info in socket.getaddrinfo(hostname, None, socket.AF_INET):
            ip = info[4][0]
            if ip not in addresses and not ip.startswith("127."):
                addresses.append(ip)
    except OSError:
        pass

    gateway = None
    if platform.system() == "Windows":
        try:
            output = _run_windows(["ipconfig"])
            for line in output.splitlines():
                if "Default Gateway" in line and ":" in line:
                    candidate = line.split(":", 1)[1].strip()
                    if candidate:
                        gateway = candidate
                        break
        except Exception:
            pass

    return {
        "hostname": hostname,
        "addresses": addresses,
        "gateway": gateway,
    }


def arp_table() -> list[dict[str, str]]:
    if platform.system() != "Windows":
        return []
    try:
        output = _run_windows(["arp", "-a"])
    except Exception:
        return []

    rows: list[dict[str, str]] = []
    for line in output.splitlines():
        parts = line.split()
        if len(parts) >= 3:
            try:
                ipaddress.ip_address(parts[0])
            except ValueError:
                continue
            rows.append({"ip": parts[0], "mac": parts[1], "type": parts[2]})
    return rows
