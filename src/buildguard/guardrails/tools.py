from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

WILDCARD = "*"

DANGEROUS_TOOLS = frozenset(
    {
        "execute_command",
        "run_shell",
        "shell",
        "subprocess",
        "eval",
        "exec",
        "drop_table",
        "drop_database",
        "delete_database",
        "rm_rf",
        "format_disk",
        "shutdown",
    }
)


class ToolGuard:
    """Restricts agent tool calls with an allowlist, a denylist and roles.

    ``allowed=None`` permits every tool that is not blocked. Tools listed in
    ``DANGEROUS_TOOLS`` stay blocked unless ``block_dangerous`` is turned off.
    ``roles`` maps a role name to the tools it may call, where ``"*"`` grants
    all of them.
    """

    def __init__(
        self,
        allowed: Iterable[str] | None = None,
        blocked: Iterable[str] = (),
        roles: Mapping[str, Iterable[str]] | None = None,
        block_dangerous: bool = True,
    ) -> None:
        self.allowed = None if allowed is None else frozenset(allowed)
        self.blocked = frozenset(blocked) | (DANGEROUS_TOOLS if block_dangerous else frozenset())
        self.roles = {role: frozenset(tools) for role, tools in (roles or {}).items()}

    def check(self, action: Mapping[str, Any]) -> tuple[bool, str]:
        """Decide whether the tool named by ``action["tool"]`` may run."""
        tool = action.get("tool")
        if tool is None:
            return True, ""
        if not isinstance(tool, str):
            return False, f"invalid tool name: {tool!r}"
        if tool in self.blocked:
            return False, f"tool '{tool}' is blocked"
        role = action.get("role")
        if isinstance(role, str) and role in self.roles:
            permitted = self.roles[role]
            if WILDCARD in permitted or tool in permitted:
                return True, ""
            return False, f"tool '{tool}' is not permitted for role '{role}'"
        if self.allowed is not None and WILDCARD not in self.allowed and tool not in self.allowed:
            return False, f"tool '{tool}' is not in the allowed set"
        return True, ""
