"""iios/execution/context/execution_session.py
==================================================
ExecutionSession — immutable session descriptor that identifies
the market session and exchange context for an execution.

C6 Execution Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

from iios.execution.context.constants import MarketSession


# Standard IANA timezone for Indian markets
_DEFAULT_TZ = "Asia/Kolkata"
_DEFAULT_EXCHANGE = "NSE"


@dataclass(frozen=True)
class ExecutionSession:
    """
    Immutable descriptor of the market session in which an execution runs.

    Tracks session identity, timing, exchange, and timezone.
    """

    session_id:     str          = field(default_factory=lambda: str(uuid.uuid4()))
    exchange:       str          = _DEFAULT_EXCHANGE
    timezone:       str          = _DEFAULT_TZ
    market_session: MarketSession = MarketSession.UNKNOWN

    session_start:  Optional[float] = None   # Unix timestamp
    session_end:    Optional[float]  = None   # Unix timestamp
    trading_date:   str              = ""     # "YYYY-MM-DD"

    # Derived state
    is_primary:     bool = True    # True if this is the main exchange session

    created_at:     float = field(default_factory=time.time)
    metadata:       dict[str, Any] = field(default_factory=dict)

    # ── Computed properties ───────────────────────────────────────────────────

    @property
    def is_open(self) -> bool:
        return self.market_session == MarketSession.OPEN

    @property
    def is_closed(self) -> bool:
        return self.market_session in (MarketSession.CLOSED, MarketSession.HOLIDAY)

    @property
    def duration_sec(self) -> Optional[float]:
        if self.session_start is None or self.session_end is None:
            return None
        return self.session_end - self.session_start

    # ── Factory helpers ───────────────────────────────────────────────────────

    @classmethod
    def nse(
        cls,
        market_session: MarketSession = MarketSession.OPEN,
        trading_date:   str = "",
    ) -> "ExecutionSession":
        return cls(
            exchange       = "NSE",
            timezone       = "Asia/Kolkata",
            market_session = market_session,
            trading_date   = trading_date,
        )

    @classmethod
    def bse(
        cls,
        market_session: MarketSession = MarketSession.OPEN,
        trading_date:   str = "",
    ) -> "ExecutionSession":
        return cls(
            exchange       = "BSE",
            timezone       = "Asia/Kolkata",
            market_session = market_session,
            trading_date   = trading_date,
        )

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id":     self.session_id,
            "exchange":       self.exchange,
            "timezone":       self.timezone,
            "market_session": self.market_session.value,
            "session_start":  self.session_start,
            "session_end":    self.session_end,
            "trading_date":   self.trading_date,
            "is_primary":     self.is_primary,
            "is_open":        self.is_open,
            "is_closed":      self.is_closed,
            "duration_sec":   self.duration_sec,
        }

    def __repr__(self) -> str:
        return (
            f"ExecutionSession("
            f"exchange={self.exchange!r}, "
            f"session={self.market_session.value}, "
            f"date={self.trading_date!r})"
        )
