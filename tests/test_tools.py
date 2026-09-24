from buildguard import ToolGuard


def test_allows_tools_in_the_allowlist():
    guard = ToolGuard(allowed={"search_web", "read_file"})
    assert guard.check({"tool": "search_web"})[0]


def test_blocks_tools_outside_the_allowlist():
    guard = ToolGuard(allowed={"search_web"})
    allowed, reason = guard.check({"tool": "write_file"})
    assert not allowed
    assert "write_file" in reason


def test_allows_every_tool_without_an_allowlist():
    guard = ToolGuard(block_dangerous=False)
    assert guard.check({"tool": "generate_report"})[0]


def test_blocks_dangerous_tools_by_default():
    guard = ToolGuard()
    for tool in ("execute_command", "drop_table"):
        allowed, reason = guard.check({"tool": tool})
        assert not allowed
        assert "blocked" in reason


def test_blocks_explicitly_blocked_tools():
    guard = ToolGuard(blocked={"send_email"})
    assert not guard.check({"tool": "send_email"})[0]


def test_dangerous_tools_can_be_enabled_explicitly():
    guard = ToolGuard(block_dangerous=False)
    assert guard.check({"tool": "execute_command"})[0]


def test_wildcard_allowlist_permits_everything():
    guard = ToolGuard(allowed={"*"})
    assert guard.check({"tool": "generate_report"})[0]


def test_ignores_actions_without_a_tool():
    guard = ToolGuard()
    assert guard.check({"amount": 5})[0]


def test_rejects_non_string_tool_names():
    guard = ToolGuard()
    allowed, reason = guard.check({"tool": 7})
    assert not allowed
    assert "invalid tool name" in reason


def test_role_grants_only_its_own_tools():
    guard = ToolGuard(roles={"analyst": {"search_web"}, "admin": {"*"}})
    assert guard.check({"tool": "search_web", "role": "analyst"})[0]

    allowed, reason = guard.check({"tool": "send_email", "role": "analyst"})
    assert not allowed
    assert "analyst" in reason
    assert guard.check({"tool": "send_email", "role": "admin"})[0]


def test_unknown_role_falls_back_to_the_allowlist():
    guard = ToolGuard(allowed={"search_web"}, roles={"admin": {"*"}})
    assert guard.check({"tool": "search_web", "role": "intern"})[0]
    assert not guard.check({"tool": "deploy", "role": "intern"})[0]


def test_blocklist_beats_role_permissions():
    guard = ToolGuard(roles={"admin": {"*"}}, blocked={"drop_table"})
    assert not guard.check({"tool": "drop_table", "role": "admin"})[0]
