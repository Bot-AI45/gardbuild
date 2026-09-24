from __future__ import annotations

import time
from collections import deque
from collections.abc import Callable, Mapping
from typing import Any


class RateLimitGuard:
    """A sliding-window call limit tracked entirely in memory.

    ``clock`` is any zero-argument callable returning seconds, which lets tests
    advance the window without sleeping.
    """

    def __init__(
        self,
        max_calls: int,
        period_seconds: float = 60.0,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if max_calls < 1:
            raise ValueError("max_calls must be at least 1")
        if period_seconds <= 0:
            raise ValueError("period_seconds must be positive")
        self.max_calls = max_calls
        self.period_seconds = period_seconds
        self._clock = clock
        self._calls: deque[float] = deque()

    def check(self, action: Mapping[str, Any] | None = None) -> tuple[bool, str]:
        """Report whether one more call fits inside the current window.

        The action is accepted for interface compatibility and is not read.
        """
        now = self._clock()
        self._expire(now)
        if len(self._calls) >= self.max_calls:
            wait = self.period_seconds - (now - self._calls[0])
            return False, (
                f"rate limit reached: {self.max_calls} calls per "
                f"{self.period_seconds:g}s, retry in {max(wait, 0.0):.3f}s"
            )
        return True, ""

    def commit(self, action: Mapping[str, Any] | None = None) -> None:
        """Record an approved call in the window."""
        self._calls.append(self._clock())

    def remaining(self, action: Mapping[str, Any] | None = None) -> int:
        """Calls still available before the window closes."""
        self._expire(self._clock())
        return max(self.max_calls - len(self._calls), 0)

    def reset(self) -> None:
        """Drop every recorded call."""
        self._calls.clear()

    def _expire(self, now: float) -> None:
        cutoff = now - self.period_seconds
        while self._calls and self._calls[0] <= cutoff:
            self._calls.popleft()
