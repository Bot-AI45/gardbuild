from __future__ import annotations

from collections.abc import Mapping
from typing import Any


class BudgetGuard:
    """Caps the size of a single payment and the total spend of an agent.

    A limit left as ``None`` is not enforced. ``check`` is side-effect free;
    approved amounts are charged by ``commit``.
    """

    def __init__(
        self,
        max_transaction: float | None = None,
        max_total: float | None = None,
    ) -> None:
        if max_transaction is None and max_total is None:
            raise ValueError("at least one of max_transaction or max_total is required")
        for name, limit in (("max_transaction", max_transaction), ("max_total", max_total)):
            if limit is not None and limit < 0:
                raise ValueError(f"{name} must be non-negative")
        self.max_transaction = max_transaction
        self.max_total = max_total
        self.spent = 0.0

    def check(self, action: Mapping[str, Any]) -> tuple[bool, str]:
        """Approve the action's amount against both limits."""
        amount = action.get("amount")
        if amount is None:
            return True, ""
        if isinstance(amount, bool) or not isinstance(amount, (int, float)):
            return False, f"invalid payment amount: {amount!r}"
        amount = float(amount)
        if amount < 0:
            return False, f"invalid payment amount: {amount:.2f}"
        if self.max_transaction is not None and amount > self.max_transaction:
            return False, (
                f"amount ${amount:.2f} exceeds the per-transaction limit "
                f"${self.max_transaction:.2f}"
            )
        if self.max_total is not None:
            remaining = self.max_total - self.spent
            if amount > remaining:
                return False, (
                    f"amount ${amount:.2f} exceeds the remaining budget "
                    f"${max(remaining, 0.0):.2f}"
                )
        return True, ""

    def commit(self, action: Mapping[str, Any]) -> None:
        """Charge an approved amount to the running total."""
        amount = action.get("amount")
        if amount is None or isinstance(amount, bool) or not isinstance(amount, (int, float)):
            return
        self.spent += float(amount)

    def reset(self) -> None:
        """Forget all recorded spend."""
        self.spent = 0.0

    @property
    def remaining(self) -> float | None:
        """Budget left under ``max_total``, or ``None`` when uncapped."""
        if self.max_total is None:
            return None
        return max(self.max_total - self.spent, 0.0)
