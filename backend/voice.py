"""FALLEN voice helpers for Windows/browser-facing voice features."""

from __future__ import annotations

import platform
import subprocess


def speak(text: str) -> dict:
    """Best-effort local Windows TTS using PowerShell SAPI.

    The API returns a structured result so the frontend can treat voice as a
    tool/action without depending on a third-party package. On non-Windows
    systems this reports that local TTS is unavailable.
    """
    if not text.strip():
        return {"ok": False, "status": "empty"}

    if platform.system() != "Windows":
        return {"ok": False, "status": "unsupported_platform"}

    # Quote safely for PowerShell single-quoted string literals.
    safe = text.replace("'", "''")
    script = (
        "Add-Type -AssemblyName System.Speech; "
        "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
        f"$s.Speak('{safe}')"
    )

    try:
        subprocess.Popen(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        return {"ok": True, "status": "speaking"}
    except Exception as exc:
        return {"ok": False, "status": "error", "message": str(exc)}
