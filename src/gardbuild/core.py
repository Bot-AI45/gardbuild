from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from typing import Any, Protocol, runtime_checkable

from .guardrails.budget import BudgetGuard
from .guardrails.pii import PiiGuard
from .guardrails.rate_limit import RateLimitGuard
from .guardrails.tools import ToolGuard

APPROVED = "APPROVED"
BLOCKED = "BLOCKED"


@runtime_checkable
class Guardrail(Protocol):
    """A rule that approves or blocks an action before the agent runs it.

    ``check`` receives the action and returns ``(allowed, reason)`` without
    touching shared state. A rule that accounts for approved actions may also
    define ``commit(action)``, which the guard calls once every rule has
    passed.
    """

    def check(self, action: Mapping[str, Any]) -> tuple[bool, str]:
        """Return whether the action may proceed."""
        ...


class Guard:
    """Runs actions through the configured guardrails and reports the verdict.

    Built-in guardrails run in the order tools, budget, rate limit, followed by
    any extra ``guardrails`` in the order given. The first rule to block
    decides the outcome.
    """

    def __init__(
        self,
        budget: BudgetGuard | None = None,
        rate_limit: RateLimitGuard | None = None,
        tools: ToolGuard | None = None,
        pii: PiiGuard | None = None,
        guardrails: Iterable[Guardrail] = (),
    ) -> None:
        ordered = [rule for rule in (tools, budget, rate_limit) if rule is not None]
        ordered.extend(guardrails)
        for rule in ordered:
            if not callable(getattr(rule, "check", None)):
                raise TypeError(f"{type(rule).__name__} does not implement check(action)")

        self.tools = tools
        self.budget = budget
        self.rate_limit = rate_limit
        self.pii = pii
        self.guardrails: list[Guardrail] = ordered

    def validate(self, action: Mapping[str, Any]) -> dict[str, Any]:
        """Return an APPROVED or BLOCKED decision without committing state."""
        if not isinstance(action, Mapping):
            raise TypeError("action must be a mapping")

        prepared = dict(self.sanitize(action))
        for rule in self.guardrails:
            allowed, reason = rule.check(prepared)
            if not allowed:
                return {"status": BLOCKED, "reason": reason, "action": prepared}
        return {"status": APPROVED, "reason": "approved", "action": prepared}

    def validate_and_run(
        self,
        action: Mapping[str, Any],
        handler: Callable[[dict[str, Any]], Any] | None = None,
    ) -> dict[str, Any]:
        """Validate and commit an action, then hand it to ``handler``.

        Blocked actions never reach the handler. The handler's return value is
        sanitized before it is exposed as ``result``.
        """
        decision = self.validate(action)
        if decision["status"] == BLOCKED:
            return decision

        for rule in self.guardrails:
            commit = getattr(rule, "commit", None)
            if callable(commit):
                commit(decision["action"])
        if handler is not None:
            decision["result"] = self.sanitize(handler(decision["action"]))
        return decision

    def sanitize(self, value: Any) -> Any:
        """Strip PII from a value with the configured sanitizer, if any."""
        if self.pii is None:
            return value
        return self.pii.scrub(value)
