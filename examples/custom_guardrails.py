from collections.abc import Callable, Mapping
from datetime import datetime, timezone
from typing import Any

from gardbuild import BudgetGuard, Guard


class BusinessHoursRule:
    """Only lets payments through on weekdays during business hours in UTC."""

    def __init__(
        self,
        start_hour: int = 9,
        end_hour: int = 17,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        self.start_hour = start_hour
        self.end_hour = end_hour
        self._now = now or (lambda: datetime.now(timezone.utc))

    def check(self, action: Mapping[str, Any]) -> tuple[bool, str]:
        if action.get("type") != "payment":
            return True, ""
        moment = self._now()
        if moment.weekday() < 5 and self.start_hour <= moment.hour < self.end_hour:
            return True, ""
        return False, (
            f"payments run only on weekdays between {self.start_hour}:00 "
            f"and {self.end_hour}:00 UTC"
        )


class PaymentCountRule:
    """Stops the agent once it has made a fixed number of payments."""

    def __init__(self, limit: int = 2) -> None:
        self.limit = limit
        self.count = 0

    def check(self, action: Mapping[str, Any]) -> tuple[bool, str]:
        if action.get("type") == "payment" and self.count >= self.limit:
            return False, f"payment limit of {self.limit} reached"
        return True, ""

    def commit(self, action: Mapping[str, Any]) -> None:
        if action.get("type") == "payment":
            self.count += 1


def main() -> None:
    guard = Guard(
        budget=BudgetGuard(max_transaction=500.0),
        guardrails=[BusinessHoursRule(), PaymentCountRule(limit=1)],
    )

    for action in (
        {"type": "payment", "amount": 120.0, "invoice": "INV-9"},
        {"type": "payment", "amount": 80.0, "invoice": "INV-10"},
    ):
        decision = guard.validate_and_run(action)
        print(f"{decision['status']:>7}  {decision['reason']}")


if __name__ == "__main__":
    main()
