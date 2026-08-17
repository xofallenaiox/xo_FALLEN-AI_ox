"""Cloud voice boundary.

Actual Windows speech remains on the authenticated Windows Agent.
"""


def speak(text: str) -> dict[str, str | bool]:
    return {
        "ok": False,
        "status": "windows_agent_voice",
        "message": "Voice playback is handled by the Windows Agent.",
    }
