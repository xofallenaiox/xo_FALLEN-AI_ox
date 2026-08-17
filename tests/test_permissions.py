from backend.permissions import get_tool_policy


def test_privacy_sensitive_file_reads_require_confirmation() -> None:
    policy = get_tool_policy("windows_read_text")
    assert policy is not None
    assert policy.risk == "medium"
    assert policy.requires_confirmation is True


def test_allowlisted_low_risk_tools_do_not_require_confirmation() -> None:
    for name in ("windows_open_app", "windows_speak"):
        policy = get_tool_policy(name)
        assert policy is not None
        assert policy.risk == "low"
        assert policy.requires_confirmation is False


def test_unknown_tool_is_not_permitted() -> None:
    assert get_tool_policy("powershell_exec") is None
