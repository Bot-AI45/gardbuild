import pytest

from buildguard import BudgetGuard


def test_approves_an_amount_at_the_limit():
    guard = BudgetGuard(max_transaction=50.0)
    allowed, reason = guard.check({"amount": 50.0})
    assert allowed
    assert reason == ""


def test_blocks_an_amount_above_the_limit():
    guard = BudgetGuard(max_transaction=50.0)
    allowed, reason = guard.check({"amount": 50.01})
    assert not allowed
    assert "$50.00" in reason


def test_ignores_actions_without_an_amount():
    guard = BudgetGuard(max_transaction=50.0)
    allowed, _ = guard.check({"type": "tool_call", "tool": "search_web"})
    assert allowed


def test_check_alone_does_not_spend():
    guard = BudgetGuard(max_total=100.0)
    assert guard.check({"amount": 100.0})[0]
    assert guard.spent == 0.0


def test_commit_accumulates_spend():
    guard = BudgetGuard(max_total=100.0)
    action = {"amount": 60.0}
    assert guard.check(action)[0]
    guard.commit(action)
    assert guard.spent == 60.0
    assert guard.remaining == pytest.approx(40.0)


def test_blocks_once_the_cumulative_cap_is_reached():
    guard = BudgetGuard(max_total=100.0)
    guard.commit({"amount": 60.0})
    allowed, reason = guard.check({"amount": 60.0})
    assert not allowed
    assert "$40.00" in reason


def test_blocked_amounts_are_never_charged():
    guard = BudgetGuard(max_transaction=10.0)
    guard.check({"amount": 25.0})
    assert guard.spent == 0.0


def test_remaining_is_none_without_a_total():
    guard = BudgetGuard(max_transaction=10.0)
    assert guard.remaining is None


def test_reset_clears_spend():
    guard = BudgetGuard(max_total=10.0)
    guard.commit({"amount": 5.0})
    guard.reset()
    assert guard.spent == 0.0
    assert guard.remaining == pytest.approx(10.0)


def test_rejects_invalid_amounts():
    guard = BudgetGuard(max_transaction=10.0)
    assert not guard.check({"amount": -1})[0]
    assert not guard.check({"amount": "25"})[0]
    assert not guard.check({"amount": True})[0]


def test_requires_at_least_one_limit():
    with pytest.raises(ValueError):
        BudgetGuard()


def test_rejects_negative_limits():
    with pytest.raises(ValueError):
        BudgetGuard(max_total=-1)
