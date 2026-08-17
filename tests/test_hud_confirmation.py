from pathlib import Path
import re


def test_hud_contains_permission_gate() -> None:
    frontend = Path(__file__).resolve().parents[1] / "frontend"
    index = (frontend / "index.html").read_text(encoding="utf-8")
    confirmation = (frontend / "confirmation.js").read_text(encoding="utf-8")

    assert 'href="/confirmation.css"' in index
    assert 'src="/confirmation.js"' in index
    assert '"/tasks/pending"' in confirmation
    assert "resolveConfirmation" in confirmation
    assert "Approve" in confirmation or "APPROVE" in confirmation


def test_hud_uses_same_origin_api_by_default() -> None:
    frontend = Path(__file__).resolve().parents[1] / "frontend"
    app_js = (frontend / "app.js").read_text(encoding="utf-8-sig")
    assert "window.FALLEN_API_URL ||" in app_js and "window.location.origin" in app_js
    assert 'credentials: "include"' in app_js
    assert "X-FALLEN-CSRF" in app_js


def test_hud_does_not_clear_csrf_when_agent_is_offline() -> None:
    frontend = Path(__file__).resolve().parents[1] / "frontend"
    app_js = (frontend / "app.js").read_text(encoding="utf-8-sig")
    offline_block = re.search(
        r"if \(!online\) \{(?P<body>.*?)\n    \}",
        app_js,
        flags=re.DOTALL,
    )
    assert offline_block is not None
    assert "window.fallenCsrfToken = null" not in offline_block.group("body")
