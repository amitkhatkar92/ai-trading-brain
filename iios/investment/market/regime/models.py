"""iios/investment/market/regime/models.py
Core data models for the Institutional Market Regime Engine.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, ClassVar, Dict, List, Optional, TYPE_CHECKING

from iios.investment.market.market_constants import (
    MarketRegime,
    TrendDirection,
    VolatilityLevel,
)

if TYPE_CHECKING:
    pass


# ── Enums ──────────────────────────────────────────────────────────────────

class RegimeType(str, Enum):
    BULL         = "bull"
    BEAR         = "bear"
    SIDEWAYS     = "sideways"
    TRENDING     = "trending"
    RANGING      = "ranging"
    EXPANSION    = "expansion"
    CONTRACTION  = "contraction"
    RECOVERY     = "recovery"
    DISTRIBUTION = "distribution"
    ACCUMULATION = "accumulation"
    VOLATILE     = "volatile"
    CALM         = "calm"
    TRANSITION   = "transition"
    CRISIS       = "crisis"
    UNKNOWN      = "unknown"


class TransitionType(str, Enum):
    EMERGING_TREND          = "emerging_trend"
    TREND_FAILURE           = "trend_failure"
    REVERSAL                = "reversal"
    VOLATILITY_EXPANSION    = "volatility_expansion"
    VOLATILITY_COMPRESSION  = "volatility_compression"
    REGIME_SHIFT            = "regime_shift"
    REGIME_PERSISTENCE      = "regime_persistence"


# ── Mapping: RegimeType → MarketRegime ────────────────────────────────────

_REGIME_TYPE_TO_MARKET_REGIME: Dict[RegimeType, MarketRegime] = {
    RegimeType.BULL:         MarketRegime.BULL,
    RegimeType.BEAR:         MarketRegime.BEAR,
    RegimeType.SIDEWAYS:     MarketRegime.SIDEWAYS,
    RegimeType.TRENDING:     MarketRegime.BULL,           # closest match
    RegimeType.RANGING:      MarketRegime.SIDEWAYS,
    RegimeType.EXPANSION:    MarketRegime.EXPANSION,
    RegimeType.CONTRACTION:  MarketRegime.CONTRACTION,
    RegimeType.RECOVERY:     MarketRegime.RECOVERY,
    RegimeType.DISTRIBUTION: MarketRegime.HIGH_VOLATILITY,
    RegimeType.ACCUMULATION: MarketRegime.SIDEWAYS,
    RegimeType.VOLATILE:     MarketRegime.HIGH_VOLATILITY,
    RegimeType.CALM:         MarketRegime.LOW_VOLATILITY,
    RegimeType.TRANSITION:   MarketRegime.SIDEWAYS,
    RegimeType.CRISIS:       MarketRegime.CRISIS,
    RegimeType.UNKNOWN:      MarketRegime.UNKNOWN,
}


def regime_type_to_market_regime(rt: RegimeType) -> MarketRegime:
    """Map RegimeType to the legacy MarketRegime enum."""
    return _REGIME_TYPE_TO_MARKET_REGIME.get(rt, MarketRegime.UNKNOWN)


# ── RegimeObservation ─────────────────────────────────────────────────────

@dataclass(frozen=True)
class RegimeObservation:
    """Flattened, immutable view of market structure relevant to regime classification."""

    # Trend
    trend_direction: TrendDirection
    trend_confirmed: bool
    trend_leg_count: int
    trend_strength: str                # MarketStrength.value
    trend_phase: str                   # TrendPhase.value

    # Structure
    structure_phase: str               # StructurePhase.value

    # Volatility
    volatility: VolatilityLevel

    # Consolidation
    in_consolidation: bool
    consolidation_bars: int
    consolidation_compression: float   # <1 means tighter

    # Breakout
    has_active_breakout: bool
    breakout_bullish: bool

    # Market breadth
    advance_decline_ratio: float

    # Quality
    quality_score: float               # 0-100
    bar_count: int


# ── RegimeSnapshot ────────────────────────────────────────────────────────

@dataclass
class RegimeSnapshot:
    """Point-in-time snapshot of the classified market regime."""

    regime_id:            str                  = field(default_factory=lambda: str(uuid.uuid4()))
    market_id:            str                  = ""
    symbol:               str                  = ""
    primary:              RegimeType           = RegimeType.UNKNOWN
    secondary:            List[RegimeType]     = field(default_factory=list)
    confidence:           float                = 0.0
    stability:            float                = 0.5
    persistence_score:    float                = 0.0
    duration_bars:        int                  = 0
    transition_probability: float              = 0.5
    market_regime:        MarketRegime         = MarketRegime.UNKNOWN
    timestamp:            float                = field(default_factory=time.time)
    observation:          Optional[RegimeObservation] = None
    metadata:             Dict[str, Any]       = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "regime_id":             self.regime_id,
            "market_id":             self.market_id,
            "symbol":                self.symbol,
            "primary":               self.primary.value,
            "secondary":             [r.value for r in self.secondary],
            "confidence":            self.confidence,
            "stability":             self.stability,
            "persistence_score":     self.persistence_score,
            "duration_bars":         self.duration_bars,
            "transition_probability": self.transition_probability,
            "market_regime":         self.market_regime.value,
            "timestamp":             self.timestamp,
            "metadata":              self.metadata,
        }


# ── TransitionEvent ───────────────────────────────────────────────────────

@dataclass
class TransitionEvent:
    """Detected regime transition signal."""

    event_id:          str            = field(default_factory=lambda: str(uuid.uuid4()))
    market_id:         str            = ""
    from_regime:       RegimeType     = RegimeType.UNKNOWN
    to_regime:         RegimeType     = RegimeType.UNKNOWN
    transition_type:   TransitionType = TransitionType.REGIME_SHIFT
    probability:       float          = 0.5
    confidence:        float          = 0.5
    trigger:           str            = ""
    bars_since_signal: int            = 0
    confirmed:         bool           = False
    timestamp:         float          = field(default_factory=time.time)
    metadata:          Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id":          self.event_id,
            "market_id":         self.market_id,
            "from_regime":       self.from_regime.value,
            "to_regime":         self.to_regime.value,
            "transition_type":   self.transition_type.value,
            "probability":       self.probability,
            "confidence":        self.confidence,
            "trigger":           self.trigger,
            "bars_since_signal": self.bars_since_signal,
            "confirmed":         self.confirmed,
            "timestamp":         self.timestamp,
            "metadata":          self.metadata,
        }


# ── StrategyCompatibility ─────────────────────────────────────────────────

@dataclass
class StrategyCompatibility:
    """Defines which strategies are allowed/discouraged/blocked in a given regime."""

    regime:                  RegimeType      = RegimeType.UNKNOWN
    allowed:                 List[str]       = field(default_factory=list)
    discouraged:             List[str]       = field(default_factory=list)
    blocked:                 List[str]       = field(default_factory=list)
    preferred_timeframes:    List[str]       = field(default_factory=list)
    preferred_risk_profile:  str             = "moderate"
    max_position_size_pct:   float           = 1.0
    notes:                   str             = ""

    def is_allowed(self, strategy_type: str) -> bool:
        """True if strategy is in the allowed list (and not blocked)."""
        return strategy_type in self.allowed and strategy_type not in self.blocked

    def is_blocked(self, strategy_type: str) -> bool:
        """True if strategy is in the blocked list."""
        return strategy_type in self.blocked

    def is_discouraged(self, strategy_type: str) -> bool:
        """True if strategy is in the discouraged list (but not blocked)."""
        return strategy_type in self.discouraged and strategy_type not in self.blocked

    def to_dict(self) -> Dict[str, Any]:
        return {
            "regime":                 self.regime.value,
            "allowed":                self.allowed,
            "discouraged":            self.discouraged,
            "blocked":                self.blocked,
            "preferred_timeframes":   self.preferred_timeframes,
            "preferred_risk_profile": self.preferred_risk_profile,
            "max_position_size_pct":  self.max_position_size_pct,
            "notes":                  self.notes,
        }
