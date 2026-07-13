"""iios/investment/strategy/opportunity/market_opportunity.py
MarketOpportunity — input type consumed from Market Intelligence Engine.
Never produced by the Opportunity Engine.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional


class OpportunityType(str, Enum):
    TREND_FOLLOWING        = "trend_following"
    MEAN_REVERSION         = "mean_reversion"
    BREAKOUT               = "breakout"
    BREAKDOWN              = "breakdown"
    MOMENTUM               = "momentum"
    VOLATILITY_EXPANSION   = "volatility_expansion"
    VOLATILITY_CONTRACTION = "volatility_contraction"
    SECTOR_ROTATION        = "sector_rotation"
    EVENT_DRIVEN           = "event_driven"
    ARBITRAGE              = "arbitrage"
    UNKNOWN                = "unknown"


class MarketRegime(str, Enum):
    BULL            = "bull"
    BEAR            = "bear"
    SIDEWAYS        = "sideways"
    HIGH_VOLATILITY = "high_volatility"
    LOW_VOLATILITY  = "low_volatility"
    CRISIS          = "crisis"
    RECOVERY        = "recovery"
    UNKNOWN         = "unknown"


class VolatilityRegime(str, Enum):
    LOW      = "low"       # VIX-equivalent < 15
    MODERATE = "moderate"  # 15 – 24
    HIGH     = "high"      # 25 – 34
    EXTREME  = "extreme"   # 35+


class Timeframe(str, Enum):
    INTRADAY   = "intraday"    # < 1 day
    SWING      = "swing"       # 2 – 10 days
    POSITIONAL = "positional"  # 10 – 90 days
    LONG_TERM  = "long_term"   # 90+ days


@dataclass(frozen=True)
class MarketOpportunity:
    """
    An investment opportunity detected by the Market Intelligence Engine.
    All fields set at construction; immutable thereafter.
    """
    opportunity_id:     str
    opportunity_type:   OpportunityType
    symbol:             str
    sector:             str
    regime:             MarketRegime
    direction:          str           # "long" | "short" | "neutral"
    confidence:         float         # 0 – 1
    strength:           float         # 0 – 1
    timeframe:          Timeframe
    volatility_regime:  VolatilityRegime
    liquidity_score:    float         # 0 – 1
    momentum_score:     float         # −1 to 1
    trend_score:        float         # −1 to 1
    detected_at:        datetime
    expires_at:         Optional[datetime] = None
    source:             str = "market_intelligence"
    metadata:           Dict[str, Any] = field(default_factory=dict)

    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return datetime.now(timezone.utc) >= self.expires_at

    def is_valid(self) -> bool:
        return not self.is_expired()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "opportunity_id":    self.opportunity_id,
            "opportunity_type":  self.opportunity_type.value,
            "symbol":            self.symbol,
            "sector":            self.sector,
            "regime":            self.regime.value,
            "direction":         self.direction,
            "confidence":        self.confidence,
            "strength":          self.strength,
            "timeframe":         self.timeframe.value,
            "volatility_regime": self.volatility_regime.value,
            "liquidity_score":   self.liquidity_score,
            "momentum_score":    self.momentum_score,
            "trend_score":       self.trend_score,
            "detected_at":       self.detected_at.isoformat(),
            "expires_at":        self.expires_at.isoformat() if self.expires_at else None,
            "source":            self.source,
        }
