"""core/paper_portfolio.py — PaperPortfolio model."""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

from iios.integration.research.paper_trading.core.paper_position import PaperPosition


@dataclass(frozen=True)
class PortfolioSnapshot:
    """Point-in-time snapshot of portfolio state."""
    timestamp:      float
    cash:           float
    market_value:   float
    total_equity:   float
    position_count: int
    unrealized_pnl: float
    realized_pnl:   float


@dataclass
class PaperPortfolio:
    """
    Aggregates all open positions for a paper account.

    Maintains a running equity curve of (timestamp, total_equity) tuples.
    """

    portfolio_id: str
    account_id:   str
    session_id:   str
    positions:    dict[str, PaperPosition]         = field(default_factory=dict)
    equity_curve: list[tuple[float, float]]        = field(default_factory=list)
    created_at:   float                            = field(default_factory=time.time)
    updated_at:   float                            = field(default_factory=time.time)

    # ── Factory ───────────────────────────────────────────────────────────────

    @classmethod
    def create(
        cls,
        account_id:   str,
        session_id:   str,
        *,
        portfolio_id: Optional[str] = None,
    ) -> "PaperPortfolio":
        now = time.time()
        return cls(
            portfolio_id = portfolio_id or f"pf_{uuid.uuid4().hex[:12]}",
            account_id   = account_id,
            session_id   = session_id,
            positions    = {},
            equity_curve = [],
            created_at   = now,
            updated_at   = now,
        )

    # ── Aggregates ────────────────────────────────────────────────────────────

    def total_market_value(self) -> float:
        return sum(p.market_value for p in self.positions.values())

    def total_unrealized_pnl(self) -> float:
        return sum(p.unrealized_pnl for p in self.positions.values())

    def total_realized_pnl(self) -> float:
        return sum(p.realized_pnl for p in self.positions.values())

    def position_count(self) -> int:
        return len(self.positions)

    def open_symbols(self) -> list[str]:
        return list(self.positions.keys())

    # ── Updates ───────────────────────────────────────────────────────────────

    def update_prices(self, prices: dict[str, float], timestamp: float) -> None:
        for symbol, price in prices.items():
            if symbol in self.positions:
                self.positions[symbol].update_price(price, timestamp)
        self.updated_at = timestamp

    def add_position(self, position: PaperPosition) -> None:
        self.positions[position.symbol] = position
        self.updated_at = time.time()

    def remove_position(self, symbol: str) -> Optional[PaperPosition]:
        pos = self.positions.pop(symbol, None)
        self.updated_at = time.time()
        return pos

    # ── Snapshot ──────────────────────────────────────────────────────────────

    def snapshot(self, timestamp: float, cash: float) -> PortfolioSnapshot:
        mv    = self.total_market_value()
        equity = cash + mv
        self.equity_curve.append((timestamp, equity))
        return PortfolioSnapshot(
            timestamp      = timestamp,
            cash           = cash,
            market_value   = mv,
            total_equity   = equity,
            position_count = self.position_count(),
            unrealized_pnl = self.total_unrealized_pnl(),
            realized_pnl   = self.total_realized_pnl(),
        )

    # ── Serialization ─────────────────────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        return {
            "portfolio_id":      self.portfolio_id,
            "account_id":        self.account_id,
            "session_id":        self.session_id,
            "position_count":    self.position_count(),
            "total_market_value": self.total_market_value(),
            "total_unrealized_pnl": self.total_unrealized_pnl(),
            "total_realized_pnl": self.total_realized_pnl(),
            "equity_curve_len":  len(self.equity_curve),
            "positions":         {sym: p.to_dict() for sym, p in self.positions.items()},
            "created_at":        self.created_at,
            "updated_at":        self.updated_at,
        }
