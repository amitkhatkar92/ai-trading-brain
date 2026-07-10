"""portfolio/cash_manager.py — Cash balance management for a paper account."""
from __future__ import annotations

import time
from typing import Any, Optional

from iios.integration.research.paper_trading.paper_trading_exceptions import InsufficientCapitalError


class CashManager:
    """
    Manages the cash balance of a single paper account.

    Maintains a ledger of debits, credits, and reservations.
    Reservations lock cash for pending orders without debiting it immediately;
    the debit happens when the order fills.
    """

    def __init__(self, initial_capital: float) -> None:
        if initial_capital < 0.0:
            raise InsufficientCapitalError("Initial capital cannot be negative")
        self._balance:     float             = initial_capital
        self._reservations: dict[str, float] = {}
        self._ledger:       list[dict]       = []

    # ── Balance operations ────────────────────────────────────────────────────

    def debit(self, amount: float, reason: str) -> None:
        """Remove *amount* from the cash balance."""
        if amount < 0.0:
            raise InsufficientCapitalError("Debit amount must be non-negative")
        if amount > self._balance:
            raise InsufficientCapitalError(
                f"Insufficient cash: need {amount:.2f}, have {self._balance:.2f}"
            )
        self._balance -= amount
        self._ledger.append({"type": "debit", "amount": amount, "reason": reason, "ts": time.time()})

    def credit(self, amount: float, reason: str) -> None:
        """Add *amount* to the cash balance."""
        if amount < 0.0:
            raise InsufficientCapitalError("Credit amount must be non-negative")
        self._balance += amount
        self._ledger.append({"type": "credit", "amount": amount, "reason": reason, "ts": time.time()})

    # ── Reservations ──────────────────────────────────────────────────────────

    def reserve(self, amount: float, reservation_id: str) -> None:
        """
        Reserve *amount* from available cash for a pending order.

        Available cash = balance − total_reserved.
        Raises InsufficientCapitalError if available cash < amount.
        """
        if amount < 0.0:
            raise InsufficientCapitalError("Reservation amount must be non-negative")
        if amount > self.available():
            raise InsufficientCapitalError(
                f"Insufficient available cash: need {amount:.2f}, have {self.available():.2f}"
            )
        self._reservations[reservation_id] = amount

    def release(self, reservation_id: str) -> float:
        """Release a reservation and return the reserved amount."""
        amount = self._reservations.pop(reservation_id, 0.0)
        return amount

    # ── Queries ───────────────────────────────────────────────────────────────

    def balance(self) -> float:
        return self._balance

    def reserved(self) -> float:
        return sum(self._reservations.values())

    def available(self) -> float:
        """Cash available for new orders = balance − reserved."""
        return max(0.0, self._balance - self.reserved())

    def history(self) -> list[dict]:
        return list(self._ledger)

    # ── State sync ────────────────────────────────────────────────────────────

    def set_balance(self, amount: float) -> None:
        """Directly set the balance (used for reconciliation)."""
        self._balance = amount
