"""
Market Data Models
Canonical data structures for all market-related information flowing through the system.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional


class RegimeLabel(str, Enum):
    BULL_TREND    = "bull_trend"       # Strong uptrend → momentum strategies
    RANGE_MARKET  = "range_market"     # Sideways → mean reversion strategies
    BEAR_MARKET   = "bear_market"      # Downtrend → hedging / short strategies
    VOLATILE      = "volatile"         # High VIX, uncertain direction


class VolatilityLevel(str, Enum):
    LOW    = "low"
    MEDIUM = "medium"
    HIGH   = "high"
    EXTREME = "extreme"


@dataclass
class IndexData:
    """Snapshot of a single index at a point in time."""
    symbol: str
    ltp: float                          # Last traded price
    open: float
    high: float
    low: float
    close: float
    volume: int
    oi: float = 0.0                     # Open interest (for derivatives)
    change_pct: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class FIIDIIData:
    """Institutional flow data for a trading session."""
    date: datetime
    fii_buy:  float = 0.0              # INR crores
    fii_sell: float = 0.0
    dii_buy:  float = 0.0
    dii_sell: float = 0.0

    @property
    def fii_net(self) -> float:
        return self.fii_buy - self.fii_sell

    @property
    def dii_net(self) -> float:
        return self.dii_buy - self.dii_sell


@dataclass
class SectorFlow:
    """Money-flow summary for a single sector."""
    sector_name: str
    flow_score: float          # Positive = inflow, negative = outflow
    rank: int                  # 1 = strongest inflow
    leaders: List[str] = field(default_factory=list)   # Top stocks in sector


@dataclass
class MarketSnapshot:
    """
    Complete picture of the market at a given instant.
    Produced by MarketDataAI and consumed by all downstream agents.
    """
    timestamp: datetime
    indices: Dict[str, IndexData]             # symbol → IndexData
    regime: RegimeLabel = RegimeLabel.RANGE_MARKET
    volatility: VolatilityLevel = VolatilityLevel.MEDIUM
    vix: float = 15.0
    fii_dii: Optional[FIIDIIData] = None
    sector_flows: List[SectorFlow] = field(default_factory=list)
    sector_leaders: List[str] = field(default_factory=list)
    events_today: List[str] = field(default_factory=list)   # e.g. "RBI Policy"
    market_breadth: float = 0.5             # 0 (all down) → 1 (all up)
    pcr: float = 1.0                        # Put-Call Ratio
    global_bias: Optional[str] = None      # "bullish" | "neutral" | "bearish" from GMIL
    global_sentiment_score: float = 0.0    # −1 → +1 from GlobalSentimentAI

    def summary(self) -> str:
        global_tag = f" | Global={self.global_bias}" if self.global_bias else ""
        return (
            f"[MarketSnapshot] {self.timestamp.strftime('%Y-%m-%d %H:%M')} | "
            f"Regime: {self.regime.value} | VIX: {self.vix:.1f} | "
            f"Vol: {self.volatility.value} | PCR: {self.pcr:.2f} | "
            f"Breadth: {self.market_breadth:.0%}{global_tag}"
        )
