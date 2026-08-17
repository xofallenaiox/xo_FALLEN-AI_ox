"""Server-authoritative tool risk policies."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ToolPolicy:
    name: str
    risk: str
    description: str
    requires_confirmation: bool


TOOL_POLICIES = {
    "windows_open_app": ToolPolicy(
        "windows_open_app",
        "low",
        "Open an allowlisted Windows application.",
        False,
    ),
    "windows_read_text": ToolPolicy(
        "windows_read_text",
        "medium",
        "Read a UTF-8 text file from the Windows user's home directory.",
        True,
    ),
    "windows_speak": ToolPolicy(
        "windows_speak",
        "low",
        "Speak text through the Windows computer.",
        False,
    ),
}


def get_tool_policy(tool_name: str) -> ToolPolicy | None:
    return TOOL_POLICIES.get(tool_name)
