"""iios/investment/market/market_state/market_snapshot.py"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from iios.investment.market.market_constants import (
    BreadthCondition,
    LiquidityLevel,
    MarketRegime,
    MarketStatus,
    MarketStrength,
    SentimentLevel,
    TrendDirection,
    VolatilityLevel,
    DEFAULT_SNAPSHOT_TTL_SEC,
)


@dataclass
class MarketSnapshot:
    """Point-in-time market observation captured from market data."""

    snapshot_id:  str              = field(default_factory=lambda: str(uuid.uuid4()))
    market_id:    str              = ""
    timestamp:    float            = field(default_factory=time.time)
    status:       MarketStatus     = MarketStatus.UNKNOWN
    symbols:      list[str]        = field(default_factory=list)

    # Raw market data
    prices:       dict[str, float] = field(default_factory=dict)
    volumes:      dict[str, float] = field(default_factory=dict)
    changes:      dict[str, float] = field(default_factory=dict)   # % change
    spreads:      dict[str, float] = field(default_factory=dict)   # bid-ask spread

    # Derived regime / structural dimensions (populated by structure engine)
    regime:       MarketRegime    = MarketRegime.UNKNOWN
    trend:        TrendDirection  = TrendDirection.UNDEFINED
    strength:     MarketStrength  = MarketStrength.NEUTRAL
    volatility:   VolatilityLevel  = VolatilityLevel.MODERATE
    liquidity:    LiquidityLevel   = LiquidityLevel.MODERATE
    breadth:      BreadthCondition = BreadthCondition.MODERATE
    sentiment:    SentimentLevel   = SentimentLevel.NEUTRAL

    # Breadth counters
    advances:     int   = 0
    declines:     int   = 0
    unchanged:    int   = 0

    # Aggregates
    total_volume: float = 0.0

    metadata:     dict[str, Any] = field(default_factory=dict)
    created_at:   float          = field(default_factory=time.time)

    # ── computed properties ───────────────────────────────────────────────────

    @property
    def age_sec(self) -> float:
        return time.time() - self.created_at

    @property
    def advance_decline_ratio(self) -> float:
        if self.declines == 0:
            return float(self.advances) if self.advances > 0 else 1.0
        return self.advances / self.declines

    def is_stale(self, ttl_sec: float = DEFAULT_SNAPSHOT_TTL_SEC) -> bool:
        return self.age_sec > ttl_sec

    def avg_price(self) -> float:
        if not self.prices:
            return 0.0
        return sum(self.prices.values()) / len(self.prices)

    def avg_change(self) -> float:
        if not self.changes:
            return 0.0
        return sum(self.changes.values()) / len(self.changes)

    def to_dict(self) -> dict[str, Any]:
        return {
            "snapshot_id":  self.snapshot_id,
            "market_id":    self.market_id,
            "timestamp":    self.timestamp,
            "status":       self.status.value,
            "symbols":      self.symbols,
            "prices":       self.prices,
            "volumes":      self.volumes,
            "changes":      self.changes,
            "regime":       self.regime.value,
            "trend":        self.trend.value,
            "strength":     self.strength.value,
            "volatility":   self.volatility.value,
            "liquidity":    self.liquidity.value,
            "breadth":      self.breadth.value,
            "sentiment":    self.sentiment.value,
            "advances":     self.advances,
            "declines":     self.declines,
            "unchanged":    self.unchanged,
            "total_volume": self.total_volume,
            "metadata":     self.metadata,
            "created_at":   self.created_at,
        }
