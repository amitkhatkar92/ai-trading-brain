"""iios/investment/strategy/core/timeframe_support.py
Timeframe and trading-style support declarations for institutional strategies.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import FrozenSet, Optional


class SupportedTimeframe(str, Enum):
    """Price bar / data resolution a strategy consumes."""
    TICK = "tick"
    M1   = "1m"
    M5   = "5m"
    M15  = "15m"
    M30  = "30m"
    H1   = "1h"
    H4   = "4h"
    D1   = "1d"
    W1   = "1w"
    MN1  = "1M"


class TradingStyle(str, Enum):
    """Broad holding-period style."""
    INTRADAY  = "intraday"   # same-session
    SWING     = "swing"      # 2–10 days
    POSITION  = "position"   # weeks to months
    LONG_TERM = "long_term"  # months to years


# Minimum hold in hours per style
STYLE_MIN_HOLD_HOURS: dict = {
    TradingStyle.INTRADAY:  0.0,
    TradingStyle.SWING:     24.0,
    TradingStyle.POSITION:  168.0,
    TradingStyle.LONG_TERM: 720.0,
}


@dataclass(frozen=True)
class TimeframeSupport:
    """Declares which timeframes and trading styles an institutional strategy supports."""
    timeframes: FrozenSet[SupportedTimeframe] = field(default_factory=frozenset)
    styles: FrozenSet[TradingStyle] = field(default_factory=frozenset)
    primary_timeframe: Optional[SupportedTimeframe] = None
    min_history_bars: int = 50

    def supports_timeframe(self, tf: SupportedTimeframe) -> bool:
        return tf in self.timeframes

    def supports_style(self, style: TradingStyle) -> bool:
        return style in self.styles

    def to_dict(self) -> dict:
        return {
            "timeframes": sorted(t.value for t in self.timeframes),
            "styles": sorted(s.value for s in self.styles),
            "primary_timeframe": self.primary_timeframe.value if self.primary_timeframe else None,
            "min_history_bars": self.min_history_bars,
        }

    @classmethod
    def intraday(cls) -> "TimeframeSupport":
        return cls(
            timeframes=frozenset({
                SupportedTimeframe.M1,
                SupportedTimeframe.M5,
                SupportedTimeframe.M15,
            }),
            styles=frozenset({TradingStyle.INTRADAY}),
            primary_timeframe=SupportedTimeframe.M15,
        )

    @classmethod
    def swing(cls) -> "TimeframeSupport":
        return cls(
            timeframes=frozenset({SupportedTimeframe.D1, SupportedTimeframe.H4}),
            styles=frozenset({TradingStyle.SWING}),
            primary_timeframe=SupportedTimeframe.D1,
        )

    @classmethod
    def long_term(cls) -> "TimeframeSupport":
        return cls(
            timeframes=frozenset({
                SupportedTimeframe.D1,
                SupportedTimeframe.W1,
                SupportedTimeframe.MN1,
            }),
            styles=frozenset({TradingStyle.LONG_TERM, TradingStyle.POSITION}),
            primary_timeframe=SupportedTimeframe.W1,
        )
