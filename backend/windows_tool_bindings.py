from __future__ import annotations

from tool_registry import Tool, registry
from windows_tools import open_application, open_url, safe_read_text, system_info


# Safe, non-destructive Windows tools. These bindings are intentionally narrow;
# the registry applies permission checks before execution and publishes events.
registry.register(
    Tool(
        name="system_info",
        capability="windows.system.read",
        description="Read basic host and operating-system information.",
        handler=system_info,
    )
)
registry.register(
    Tool(
        name="open_application",
        capability="windows.app.launch",
        description="Open an application from FALLEN's approved application allowlist.",
        handler=open_application,
    )
)
registry.register(
    Tool(
        name="open_url",
        capability="browser.navigate",
        description="Open an HTTP(S) URL in the default browser.",
        handler=open_url,
    )
)
registry.register(
    Tool(
        name="read_text_file",
        capability="files.read",
        description="Read a UTF-8 text file inside the user's home directory.",
        handler=safe_read_text,
    )
)
