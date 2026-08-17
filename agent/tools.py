"""Allowlisted Windows execution boundary."""

from __future__ import annotations

import base64
import os
import platform
import shutil
import subprocess
from pathlib import Path
from typing import Any


MAX_READ_BYTES = 256_000
MAX_SPEECH_LENGTH = 4_000

ALLOWED_APPS = {
    "notepad": "notepad.exe",
    "calculator": "calc.exe",
    "explorer": "explorer.exe",
}


class AgentToolError(RuntimeError):
    """Raised when a local operation is rejected or fails."""


def _require_windows() -> None:
    if platform.system() != "Windows":
        raise AgentToolError("Windows agent requires Windows.")


def open_app(application: str) -> dict[str, Any]:
    _require_windows()
    executable = ALLOWED_APPS.get(application)
    if executable is None:
        raise AgentToolError("Application is not allowlisted.")

    subprocess.Popen(
        [executable],
        shell=False,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    return {"ok": True, "application": application}


def read_text(path: str) -> dict[str, Any]:
    _require_windows()
    candidate = Path(path).expanduser().resolve(strict=True)
    home = Path.home().resolve()

    if candidate != home and home not in candidate.parents:
        raise AgentToolError("Path is outside the Windows home directory.")
    if not candidate.is_file():
        raise AgentToolError("Path is not a regular file.")
    if candidate.stat().st_size > MAX_READ_BYTES:
        raise AgentToolError("File is too large.")

    try:
        content = candidate.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise AgentToolError("Only UTF-8 text files are supported.") from exc

    return {"ok": True, "path": str(candidate), "content": content}


def speak(text: str) -> dict[str, Any]:
    _require_windows()
    normalized = text.strip()
    if not normalized or len(normalized) > MAX_SPEECH_LENGTH:
        raise AgentToolError("Invalid speech text.")

    powershell = shutil.which("powershell.exe") or shutil.which("powershell")
    if not powershell:
        raise AgentToolError("PowerShell is unavailable.")

    encoded = base64.b64encode(normalized.encode("utf-8")).decode("ascii")
    script = (
        "Add-Type -AssemblyName System.Speech; "
        "$s=New-Object System.Speech.Synthesis.SpeechSynthesizer; "
        "$s.Speak([Text.Encoding]::UTF8.GetString("
        "[Convert]::FromBase64String($env:FALLEN_TTS_TEXT))); "
        "$s.Dispose()"
    )

    child_env = {
        key: value
        for key, value in os.environ.items()
        if key not in {
            "OPENAI_API_KEY",
            "FALLEN_API_TOKEN",
            "FALLEN_AGENT_ENROLLMENT_TOKEN",
            "FALLEN_AGENT_TOKEN",
        }
    }
    child_env["FALLEN_TTS_TEXT"] = encoded

    subprocess.Popen(
        [
            powershell,
            "-NoProfile",
            "-NonInteractive",
            "-Command",
            script,
        ],
        shell=False,
        env=child_env,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    return {"ok": True, "status": "speaking"}


TOOL_HANDLERS = {
    "windows_open_app": open_app,
    "windows_read_text": read_text,
    "windows_speak": speak,
}


def execute(tool: str, arguments: dict[str, Any]) -> dict[str, Any]:
    handler = TOOL_HANDLERS.get(tool)
    if handler is None:
        raise AgentToolError("Tool is not allowlisted.")
    return handler(**arguments)
