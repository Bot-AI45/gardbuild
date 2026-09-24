import pytest

from gardbuild import RateLimitGuard


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def test_allows_calls_up_to_the_limit():
    clock = FakeClock()
    guard = RateLimitGuard(max_calls=2, period_seconds=60.0, clock=clock)
    assert guard.check()[0]
    guard.commit()
    assert guard.check()[0]
    guard.commit()
    assert not guard.check()[0]


def test_window_slides_after_the_period():
    clock = FakeClock()
    guard = RateLimitGuard(max_calls=1, period_seconds=10.0, clock=clock)
    guard.commit()
    assert not guard.check()[0]
    clock.advance(10.0)
    assert guard.check()[0]


def test_check_does_not_record_a_call():
    guard = RateLimitGuard(max_calls=1, clock=FakeClock())
    assert guard.check()[0]
    assert guard.check()[0]
    assert guard.remaining() == 1


def test_commit_records_a_call():
    guard = RateLimitGuard(max_calls=1, clock=FakeClock())
    guard.check()
    guard.commit()
    assert guard.remaining() == 0


def test_remaining_tracks_usage():
    guard = RateLimitGuard(max_calls=3, clock=FakeClock())
    assert guard.remaining() == 3
    guard.commit()
    assert guard.remaining() == 2


def test_reset_clears_the_window():
    guard = RateLimitGuard(max_calls=1, clock=FakeClock())
    guard.commit()
    guard.reset()
    assert guard.check()[0]


def test_blocked_reason_reports_the_retry_delay():
    clock = FakeClock()
    guard = RateLimitGuard(max_calls=1, period_seconds=30.0, clock=clock)
    guard.commit()
    clock.advance(25.0)
    allowed, reason = guard.check()
    assert not allowed
    assert "5.000s" in reason


def test_rejects_invalid_configuration():
    with pytest.raises(ValueError):
        RateLimitGuard(max_calls=0)
    with pytest.raises(ValueError):
        RateLimitGuard(max_calls=1, period_seconds=0)
