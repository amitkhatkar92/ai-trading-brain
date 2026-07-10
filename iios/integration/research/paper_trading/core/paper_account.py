"""core/paper_account.py — PaperAccount model."""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

from iios.integration.research.paper_trading.paper_trading_constants import (
    AccountStatus,
    DEFAULT_BUYING_POWER_MULTIPLIER,
    DEFAULT_INITIAL_CAPITAL,
)


@dataclass
class PaperAccount:
    """
    Virtual trading account.

    ``cash`` is the actual cash balance after fills.
    ``buying_power`` reflects leveraged capacity; equals ``cash * leverage``
    for fresh accounts and shrinks as positions are entered.
    """

    account_id:      str
    name:            str
    initial_capital: float
    cash:            float
    buying_power:    float
    margin_used:     float           = 0.0
    leverage:        float           = DEFAULT_BUYING_POWER_MULTIPLIER
    status:          AccountStatus   = AccountStatus.ACTIVE
    created_at:      float           = field(default_factory=time.time)
    updated_at:      float           = field(default_factory=time.time)
    metadata:        dict[str, Any]  = field(default_factory=dict)

    # ── Factory ───────────────────────────────────────────────────────────────

    @classmethod
    def create(
        cls,
        name:            str,
        initial_capital: float = DEFAULT_INITIAL_CAPITAL,
        *,
        account_id:      Optional[str]  = None,
        leverage:        float           = DEFAULT_BUYING_POWER_MULTIPLIER,
        metadata:        Optional[dict]  = None,
    ) -> "PaperAccount":
        now = time.time()
        aid = account_id or f"acct_{uuid.uuid4().hex[:12]}"
        return cls(
            account_id      = aid,
            name            = name,
            initial_capital = initial_capital,
            cash            = initial_capital,
            buying_power    = initial_capital * leverage,
            margin_used     = 0.0,
            leverage        = leverage,
            status          = AccountStatus.ACTIVE,
            created_at      = now,
            updated_at      = now,
            metadata        = metadata or {},
        )

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def touch(self) -> None:
        self.updated_at = time.time()

    def is_active(self) -> bool:
        return self.status == AccountStatus.ACTIVE

    # ── Financials ────────────────────────────────────────────────────────────

    def available_cash(self) -> float:
        """Cash available for new orders."""
        return max(0.0, self.buying_power - self.margin_used)

    def equity(self, portfolio_market_value: float) -> float:
        """Total equity = cash + market value of open positions."""
        return self.cash + portfolio_market_value

    def net_liquidation_value(self, portfolio_market_value: float) -> float:
        """Net liquidation = equity - margin used."""
        return self.equity(portfolio_market_value) - self.margin_used

    def total_return_pct(self, portfolio_market_value: float) -> float:
        """Return since inception as a fraction."""
        if self.initial_capital <= 0.0:
            return 0.0
        return (self.equity(portfolio_market_value) - self.initial_capital) / self.initial_capital

    # ── Serialization ─────────────────────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        return {
            "account_id":      self.account_id,
            "name":            self.name,
            "initial_capital": self.initial_capital,
            "cash":            self.cash,
            "buying_power":    self.buying_power,
            "margin_used":     self.margin_used,
            "leverage":        self.leverage,
            "status":          self.status.value,
            "created_at":      self.created_at,
            "updated_at":      self.updated_at,
            "metadata":        self.metadata,
        }
