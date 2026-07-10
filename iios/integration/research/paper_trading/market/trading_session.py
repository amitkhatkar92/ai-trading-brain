"""market/trading_session.py — Trading calendar and session phase logic."""
from __future__ import annotations

import datetime
from dataclasses import dataclass
from typing import Any

from iios.integration.research.paper_trading.paper_trading_constants import MarketPhase


@dataclass
class TradingCalendar:
    """
    Simple trading calendar.

    Defines market hours and basic holiday exclusion.
    All times are in *local market* terms; timestamps are UTC epoch floats.
    """
    market_open_hour:   int   = 9
    market_open_minute: int   = 15
    market_close_hour:  int   = 15
    market_close_minute: int  = 30
    # Days of week that are trading days (0=Mon … 6=Sun)
    trading_days:       tuple = (0, 1, 2, 3, 4)   # Mon–Fri
    # Manually excluded dates (YYYY-MM-DD strings)
    holidays:           tuple = ()

    def is_trading_day(self, date: datetime.date) -> bool:
        if date.weekday() not in self.trading_days:
            return False
        return date.isoformat() not in self.holidays

    def market_open_ts(self, date: datetime.date) -> float:
        dt = datetime.datetime(
            date.year, date.month, date.day,
            self.market_open_hour, self.market_open_minute,
        )
        return dt.timestamp()

    def market_close_ts(self, date: datetime.date) -> float:
        dt = datetime.datetime(
            date.year, date.month, date.day,
            self.market_close_hour, self.market_close_minute,
        )
        return dt.timestamp()


class TradingSessionManager:
    """
    Answers questions about when the market is open / which phase is active.
    """

    # Pre-market window: 1 hour before open
    PRE_MARKET_OFFSET_SEC  = 3_600
    # Post-market window: 1 hour after close
    POST_MARKET_OFFSET_SEC = 3_600
    # Opening / closing auction duration
    AUCTION_DURATION_SEC   = 300   # 5 minutes

    def __init__(self, calendar: TradingCalendar | None = None) -> None:
        self._calendar = calendar or TradingCalendar()

    # ── Primary API ───────────────────────────────────────────────────────────

    def is_market_open(self, timestamp: float) -> bool:
        """True when the continuous trading phase is active."""
        return self.session_phase(timestamp) in (
            MarketPhase.CONTINUOUS,
            MarketPhase.OPENING_AUCTION,
            MarketPhase.CLOSING_AUCTION,
        )

    def session_phase(self, timestamp: float) -> MarketPhase:
        """Determine the market phase at the given Unix timestamp."""
        dt   = datetime.datetime.fromtimestamp(timestamp)
        date = dt.date()

        if not self._calendar.is_trading_day(date):
            return MarketPhase.CLOSED

        open_ts  = self._calendar.market_open_ts(date)
        close_ts = self._calendar.market_close_ts(date)

        pre_start  = open_ts  - self.PRE_MARKET_OFFSET_SEC
        post_end   = close_ts + self.POST_MARKET_OFFSET_SEC
        open_end   = open_ts  + self.AUCTION_DURATION_SEC
        close_start = close_ts - self.AUCTION_DURATION_SEC

        if timestamp < pre_start:
            return MarketPhase.CLOSED
        if timestamp < open_ts:
            return MarketPhase.PRE_MARKET
        if timestamp < open_end:
            return MarketPhase.OPENING_AUCTION
        if timestamp < close_start:
            return MarketPhase.CONTINUOUS
        if timestamp < close_ts:
            return MarketPhase.CLOSING_AUCTION
        if timestamp < post_end:
            return MarketPhase.POST_MARKET
        return MarketPhase.CLOSED

    def next_open(self, timestamp: float) -> float:
        """Return the Unix timestamp of the next market open after *timestamp*."""
        dt   = datetime.datetime.fromtimestamp(timestamp)
        date = dt.date()
        # Step forward up to 14 days to find the next trading day
        for _ in range(14):
            date += datetime.timedelta(days=1)
            if self._calendar.is_trading_day(date):
                return self._calendar.market_open_ts(date)
        raise RuntimeError("Could not find next open within 14 days")

    def next_close(self, timestamp: float) -> float:
        """Return the Unix timestamp of the next market close after *timestamp*."""
        dt   = datetime.datetime.fromtimestamp(timestamp)
        date = dt.date()
        close_ts = self._calendar.market_close_ts(date)
        if self._calendar.is_trading_day(date) and timestamp < close_ts:
            return close_ts
        for _ in range(14):
            date += datetime.timedelta(days=1)
            if self._calendar.is_trading_day(date):
                return self._calendar.market_close_ts(date)
        raise RuntimeError("Could not find next close within 14 days")

    def to_dict(self) -> dict[str, Any]:
        return {
            "market_open_hour":    self._calendar.market_open_hour,
            "market_open_minute":  self._calendar.market_open_minute,
            "market_close_hour":   self._calendar.market_close_hour,
            "market_close_minute": self._calendar.market_close_minute,
            "trading_days":        list(self._calendar.trading_days),
        }
