from __future__ import annotations

import os
import platform
import subprocess
import webbrowser
from pathlib import Path
from typing import Any


def system_info() -> dict[str, Any]:
    return {
        "platform": platform.platform(),
        "system": platform.system(),
        "release": platform.release(),
        "version": platform.version(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "hostname": platform.node(),
    }


def open_url(url: str) -> dict[str, Any]:
    if not url.startswith(("http://", "https://")):
        raise ValueError("Only HTTP(S) URLs are allowed")
    return {"ok": webbrowser.open(url), "url": url}


def open_application(name: str) -> dict[str, Any]:
    if platform.system() != "Windows":
        return {"ok": False, "status": "unsupported_platform"}

    allowed = {
        "notepad": ["notepad.exe"],
        "calculator": ["calc.exe"],
        "explorer": ["explorer.exe"],
    }
    command = allowed.get(name.strip().lower())
    if not command:
        return {"ok": False, "status": "not_allowed", "application": name}

    subprocess.Popen(command, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    return {"ok": True, "status": "opened", "application": name}


def safe_read_text(path: str) -> dict[str, Any]:
    candidate = Path(path).expanduser().resolve()
    home = Path.home().resolve()
    if home not in candidate.parents and candidate != home:
        raise PermissionError("File access is restricted to the user home directory")
    if not candidate.is_file():
        return {"ok": False, "status": "not_found", "path": str(candidate)}
    return {"ok": True, "path": str(candidate), "text": candidate.read_text(encoding="utf-8", errors="replace")}
