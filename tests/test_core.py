import pytest

from gardbuild import (
    APPROVED,
    BLOCKED,
    BudgetGuard,
    Guard,
    Guardrail,
    PiiGuard,
    RateLimitGuard,
    ToolGuard,
)


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


class PaymentsOnly:
    """A custom rule that refuses every action carrying an amount."""

    def check(self, action):
        if action.get("amount") is not None:
            return False, "payments are disabled for this agent"
        return True, ""


def test_builtin_guardrails_satisfy_the_protocol():
    assert isinstance(BudgetGuard(max_transaction=1.0), Guardrail)
    assert isinstance(RateLimitGuard(max_calls=1, clock=FakeClock()), Guardrail)
    assert isinstance(ToolGuard(), Guardrail)


def test_approves_an_action_within_limits():
    guard = Guard(budget=BudgetGuard(max_transaction=50.0))
    decision = guard.validate({"type": "payment", "amount": 25.0})
    assert decision["status"] == APPROVED
    assert decision["reason"] == "approved"
    assert decision["action"] == {"type": "payment", "amount": 25.0}


def test_blocks_an_action_over_budget():
    guard = Guard(budget=BudgetGuard(max_transaction=50.0))
    decision = guard.validate({"type": "payment", "amount": 75.0})
    assert decision["status"] == BLOCKED
    assert "$75.00" in decision["reason"]


def test_validate_does_not_consume_the_rate_limit():
    guard = Guard(rate_limit=RateLimitGuard(max_calls=1, clock=FakeClock()))
    assert guard.validate({})["status"] == APPROVED
    assert guard.validate({})["status"] == APPROVED
    assert guard.rate_limit.remaining() == 1


def test_validate_and_run_consumes_the_rate_limit():
    guard = Guard(rate_limit=RateLimitGuard(max_calls=1, clock=FakeClock()))
    assert guard.validate_and_run({})["status"] == APPROVED
    assert guard.validate_and_run({})["status"] == BLOCKED


def test_validate_and_run_charges_the_budget():
    guard = Guard(budget=BudgetGuard(max_total=50.0))
    assert guard.validate_and_run({"amount": 30.0})["status"] == APPROVED
    assert guard.budget.spent == pytest.approx(30.0)
    assert guard.validate_and_run({"amount": 30.0})["status"] == BLOCKED


def test_handler_receives_sanitized_actions_and_is_sanitized_in_turn():
    guard = Guard(pii=PiiGuard())
    seen = {}

    def handler(action):
        seen.update(action)
        return {"echo": action["note"]}

    decision = guard.validate_and_run({"note": "ping ops@example.com"}, handler)
    assert seen == {"note": "ping [REDACTED]"}
    assert decision["result"] == {"echo": "ping [REDACTED]"}


def test_blocked_actions_never_reach_the_handler():
    calls = []
    guard = Guard(budget=BudgetGuard(max_transaction=10.0))
    decision = guard.validate_and_run({"amount": 99.0}, calls.append)
    assert decision["status"] == BLOCKED
    assert calls == []
    assert "result" not in decision


def test_pii_is_redacted_even_when_the_action_is_blocked():
    guard = Guard(budget=BudgetGuard(max_transaction=10.0), pii=PiiGuard())
    decision = guard.validate({"amount": 99.0, "note": "card 4242424242424242"})
    assert decision["status"] == BLOCKED
    assert "4242" not in decision["action"]["note"]


def test_the_first_blocking_rule_wins():
    guard = Guard(budget=BudgetGuard(max_transaction=10.0), tools=ToolGuard())
    decision = guard.validate({"tool": "drop_table", "amount": 99.0})
    assert decision["status"] == BLOCKED
    assert "drop_table" in decision["reason"]


def test_accepts_custom_guardrails():
    guard = Guard(guardrails=[PaymentsOnly()])
    assert guard.validate({"tool": "search_web"})["status"] == APPROVED
    assert guard.validate({"amount": 1.0})["status"] == BLOCKED


def test_commits_every_stateful_rule():
    spent = []

    class Recorder:
        def check(self, action):
            return True, ""

        def commit(self, action):
            spent.append(action["amount"])

    guard = Guard(guardrails=[Recorder()])
    guard.validate_and_run({"amount": 12.0})
    assert spent == [12.0]


def test_rejects_rules_without_check():
    with pytest.raises(TypeError):
        Guard(guardrails=[object()])


def test_rejects_non_mapping_actions():
    with pytest.raises(TypeError):
        Guard().validate(["not", "an", "action"])


def test_the_guard_snapshots_the_custom_rule_list():
    rules = [PaymentsOnly()]
    guard = Guard(guardrails=rules)
    rules.clear()
    decision = guard.validate({"amount": 1.0})
    assert decision["status"] == BLOCKED
    assert "disabled" in decision["reason"]


def test_a_guard_without_rules_approves_everything():
    decision = Guard().validate({"type": "payment", "amount": 10_000.0})
    assert decision["status"] == APPROVED
