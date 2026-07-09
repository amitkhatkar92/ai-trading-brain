"""iios/investment/market/market_state/market_state.py"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from iios.investment.market.market_constants import MarketStatus


@dataclass
class MarketState:
    """Authoritative state of a single market."""

    state_id:      str         = field(default_factory=lambda: str(uuid.uuid4()))
    market_id:     str         = ""
    name:          str         = ""
    status:        MarketStatus = MarketStatus.UNKNOWN
    session_start: float | None = None
    session_end:   float | None = None
    trading_date:  str         = ""
    timezone:      str         = "UTC"
    is_trading:    bool        = False
    metadata:      dict[str, Any] = field(default_factory=dict)
    created_at:    float       = field(default_factory=time.time)
    updated_at:    float       = field(default_factory=time.time)

    # ── lifecycle ─────────────────────────────────────────────────────────────

    def open(self, trading_date: str = "") -> None:
        self.status        = MarketStatus.OPEN
        self.is_trading    = True
        self.session_start = time.time()
        if trading_date:
            self.trading_date = trading_date
        self.updated_at = time.time()

    def close(self) -> None:
        self.status      = MarketStatus.CLOSED
        self.is_trading  = False
        self.session_end = time.time()
        self.updated_at  = time.time()

    def halt(self) -> None:
        self.status     = MarketStatus.HALTED
        self.is_trading = False
        self.updated_at = time.time()

    def set_status(self, status: MarketStatus) -> None:
        self.status     = status
        self.is_trading = (status == MarketStatus.OPEN)
        self.updated_at = time.time()

    def session_duration_sec(self) -> float:
        if self.session_start is None:
            return 0.0
        end = self.session_end if self.session_end is not None else time.time()
        return max(0.0, end - self.session_start)

    def to_dict(self) -> dict[str, Any]:
        return {
            "state_id":      self.state_id,
            "market_id":     self.market_id,
            "name":          self.name,
            "status":        self.status.value,
            "session_start": self.session_start,
            "session_end":   self.session_end,
            "trading_date":  self.trading_date,
            "timezone":      self.timezone,
            "is_trading":    self.is_trading,
            "metadata":      self.metadata,
            "created_at":    self.created_at,
            "updated_at":    self.updated_at,
        }
