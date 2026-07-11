"""iios/investment/market/breadth/models.py
Core domain models for the Institutional Market Breadth Intelligence Engine.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


# ── Enums ─────────────────────────────────────────────────────────────────

class BreadthRegimeType(str, Enum):
    STRONG_PARTICIPATION    = "strong_participation"
    HEALTHY_PARTICIPATION   = "healthy_participation"
    NEUTRAL                 = "neutral"
    WEAK_PARTICIPATION      = "weak_participation"
    VERY_WEAK_PARTICIPATION = "very_weak_participation"
    BROAD_RALLY             = "broad_rally"
    NARROW_RALLY            = "narrow_rally"
    BROAD_SELLOFF           = "broad_selloff"
    NARROW_SELLOFF          = "narrow_selloff"
    UNKNOWN                 = "unknown"


class BreadthEventType(str, Enum):
    REGIME_CHANGE           = "regime_change"
    BROAD_RALLY             = "broad_rally"
    NARROW_RALLY            = "narrow_rally"
    BROAD_SELLOFF           = "broad_selloff"
    NARROW_SELLOFF          = "narrow_selloff"
    BULLISH_DIVERGENCE      = "bullish_divergence"
    BEARISH_DIVERGENCE      = "bearish_divergence"
    HEALTH_IMPROVEMENT      = "health_improvement"
    HEALTH_DETERIORATION    = "health_deterioration"
    LEADERSHIP_CHANGE       = "leadership_change"
    BREADTH_THRUST          = "breadth_thrust"
    PARTICIPATION_COLLAPSE  = "participation_collapse"


class DivergenceType(str, Enum):
    BULLISH_BREADTH        = "bullish_breadth"
    BEARISH_BREADTH        = "bearish_breadth"
    PARTICIPATION_BULLISH  = "participation_bullish"
    PARTICIPATION_BEARISH  = "participation_bearish"
    LEADERSHIP_BULLISH     = "leadership_bullish"
    LEADERSHIP_BEARISH     = "leadership_bearish"


class MarketCapTier(str, Enum):
    LARGE   = "large"
    MID     = "mid"
    SMALL   = "small"
    MICRO   = "micro"
    UNKNOWN = "unknown"


class BreadthTrend(str, Enum):
    RISING   = "rising"
    FALLING  = "falling"
    STABLE   = "stable"
    SURGING  = "surging"
    COLLAPSING = "collapsing"


class HealthTrend(str, Enum):
    IMPROVING     = "improving"
    DETERIORATING = "deteriorating"
    STABLE        = "stable"


# ── Primary input types ────────────────────────────────────────────────────

@dataclass
class SecurityObservation:
    """Single security's state at one bar update."""
    symbol: str
    price_change_pct: float         # % change from previous bar
    sector: str = "unknown"
    industry: str = "unknown"
    market_cap_tier: str = MarketCapTier.UNKNOWN.value
    is_above_ma20: bool = False     # price > 20-period moving average
    is_above_ma50: bool = False     # price > 50-period moving average
    is_new_52w_high: bool = False
    is_new_52w_low: bool = False
    volume_ratio: float = 1.0       # current volume / average volume
    relative_strength: float = 0.0  # vs market index (+ = outperforming)

    @property
    def is_advancing(self) -> bool:
        return self.price_change_pct > 0.0

    @property
    def is_declining(self) -> bool:
        return self.price_change_pct < 0.0

    @property
    def is_unchanged(self) -> bool:
        return self.price_change_pct == 0.0


@dataclass
class UniverseSnapshot:
    """Collection of security observations for a single bar update."""
    universe_id: str                          # e.g. "NSE500", "SP500"
    bar_index: int
    timestamp: float
    observations: List[SecurityObservation]

    @property
    def total(self) -> int:
        return len(self.observations)

    def advancing(self) -> List[SecurityObservation]:
        return [o for o in self.observations if o.is_advancing]

    def declining(self) -> List[SecurityObservation]:
        return [o for o in self.observations if o.is_declining]

    def unchanged(self) -> List[SecurityObservation]:
        return [o for o in self.observations if o.is_unchanged]

    def by_sector(self) -> Dict[str, List[SecurityObservation]]:
        result: Dict[str, List[SecurityObservation]] = {}
        for obs in self.observations:
            result.setdefault(obs.sector, []).append(obs)
        return result

    def by_cap_tier(self) -> Dict[str, List[SecurityObservation]]:
        result: Dict[str, List[SecurityObservation]] = {}
        for obs in self.observations:
            result.setdefault(obs.market_cap_tier, []).append(obs)
        return result


# ── Metric value ────────────────────────────────────────────────────────────

@dataclass
class BreadthMetricValue:
    """Output from one pluggable breadth metric."""
    metric_name: str
    value: float
    normalized_value: float  # 0-1
    confidence: float        # 0-1
    signal: str              # "bullish", "bearish", "neutral"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "metric_name": self.metric_name,
            "value": round(self.value, 4),
            "normalized_value": round(self.normalized_value, 4),
            "confidence": round(self.confidence, 4),
            "signal": self.signal,
        }


# ── Sub-snapshots ──────────────────────────────────────────────────────────

@dataclass
class BreadthData:
    """Core advance/decline statistics."""
    advancing: int
    declining: int
    unchanged: int
    total: int
    breadth_pct: float        # advancing / total (0-1)
    ad_ratio: float           # advancing / max(declining, 1)
    ad_line: float            # cumulative (advancing - declining)
    ad_momentum: float        # recent breadth_pct change (-1 to 1)
    breadth_trend: BreadthTrend
    breadth_stability: float  # 0-1 (inverse of vol-of-breadth)
    metric_values: Dict[str, BreadthMetricValue] = field(default_factory=dict)

    @property
    def net_change(self) -> int:
        return self.advancing - self.declining

    @property
    def is_bullish_breadth(self) -> bool:
        return self.ad_ratio > 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "advancing": self.advancing,
            "declining": self.declining,
            "unchanged": self.unchanged,
            "total": self.total,
            "breadth_pct": round(self.breadth_pct, 4),
            "ad_ratio": round(self.ad_ratio, 4),
            "ad_line": round(self.ad_line, 2),
            "ad_momentum": round(self.ad_momentum, 4),
            "breadth_trend": self.breadth_trend.value,
            "breadth_stability": round(self.breadth_stability, 4),
            "metric_values": {k: v.to_dict() for k, v in self.metric_values.items()},
        }


@dataclass
class ParticipationSnapshot:
    """Cross-sectional participation analysis."""
    large_cap_pct: float          # fraction of large-caps advancing
    mid_cap_pct: float
    small_cap_pct: float
    sector_participation: Dict[str, float]   # sector -> fraction advancing
    above_ma20_pct: float         # fraction of universe above 20MA
    above_ma50_pct: float         # fraction of universe above 50MA
    new_highs: int
    new_lows: int
    nh_nl_ratio: float            # new_highs / max(new_lows, 1)
    market_participation_score: float    # 0-100
    participation_breadth: float  # fraction of sectors > 50% advancing

    def to_dict(self) -> Dict[str, Any]:
        return {
            "large_cap_pct": round(self.large_cap_pct, 4),
            "mid_cap_pct": round(self.mid_cap_pct, 4),
            "small_cap_pct": round(self.small_cap_pct, 4),
            "sector_participation": {
                k: round(v, 4) for k, v in self.sector_participation.items()
            },
            "above_ma20_pct": round(self.above_ma20_pct, 4),
            "above_ma50_pct": round(self.above_ma50_pct, 4),
            "new_highs": self.new_highs,
            "new_lows": self.new_lows,
            "nh_nl_ratio": round(self.nh_nl_ratio, 4),
            "market_participation_score": round(self.market_participation_score, 2),
            "participation_breadth": round(self.participation_breadth, 4),
        }


@dataclass
class MarketHealthSnapshot:
    """Internal market health and leadership analysis."""
    health_score: float        # 0-100
    internal_strength: float   # 0-1
    leadership_breadth: float  # fraction of sectors outperforming avg
    lagging_breadth: float     # fraction of sectors underperforming
    participation_quality: float   # 0-1
    internal_momentum: float   # -1 to 1 (rate of health change)
    health_trend: HealthTrend
    leading_sectors: List[str]
    lagging_sectors: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "health_score": round(self.health_score, 2),
            "internal_strength": round(self.internal_strength, 4),
            "leadership_breadth": round(self.leadership_breadth, 4),
            "lagging_breadth": round(self.lagging_breadth, 4),
            "participation_quality": round(self.participation_quality, 4),
            "internal_momentum": round(self.internal_momentum, 4),
            "health_trend": self.health_trend.value,
            "leading_sectors": list(self.leading_sectors),
            "lagging_sectors": list(self.lagging_sectors),
        }


@dataclass
class DivergenceSignal:
    divergence_type: DivergenceType
    strength: float       # 0-1
    bars_active: int
    description: str
    confirmed: bool       # True if persisted >= min_bars

    def to_dict(self) -> Dict[str, Any]:
        return {
            "divergence_type": self.divergence_type.value,
            "strength": round(self.strength, 4),
            "bars_active": self.bars_active,
            "description": self.description,
            "confirmed": self.confirmed,
        }


@dataclass
class BreadthRegimeSnapshot:
    regime: BreadthRegimeType
    confidence: float
    duration_bars: int
    previous_regime: Optional[BreadthRegimeType]
    transition_probability: float
    regime_score: float     # 0-100

    def to_dict(self) -> Dict[str, Any]:
        return {
            "regime": self.regime.value,
            "confidence": round(self.confidence, 4),
            "duration_bars": self.duration_bars,
            "previous_regime": (
                self.previous_regime.value if self.previous_regime else None
            ),
            "transition_probability": round(self.transition_probability, 4),
            "regime_score": round(self.regime_score, 2),
        }


@dataclass
class BreadthConfidenceScore:
    breadth_confidence: float         # quality of A/D data (0-1)
    participation_confidence: float   # quality of participation data (0-1)
    leadership_confidence: float      # confidence in leadership signal (0-1)
    internal_strength_score: float    # 0-100
    overall_score: float              # 0-100

    def to_dict(self) -> Dict[str, Any]:
        return {
            "breadth_confidence": round(self.breadth_confidence, 4),
            "participation_confidence": round(self.participation_confidence, 4),
            "leadership_confidence": round(self.leadership_confidence, 4),
            "internal_strength_score": round(self.internal_strength_score, 2),
            "overall_score": round(self.overall_score, 2),
        }


@dataclass
class BreadthEvent:
    event_type: BreadthEventType
    universe_id: str
    bar_index: int
    severity: float                          # 0-1
    from_regime: Optional[BreadthRegimeType] = None
    to_regime: Optional[BreadthRegimeType]   = None
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.event_type.value,
            "universe_id": self.universe_id,
            "bar_index": self.bar_index,
            "severity": round(self.severity, 4),
            "from_regime": self.from_regime.value if self.from_regime else None,
            "to_regime": self.to_regime.value if self.to_regime else None,
            "description": self.description,
        }


# ── Primary output ─────────────────────────────────────────────────────────

@dataclass
class BreadthIntelligenceSnapshot:
    """Primary output of InstitutionalMarketBreadthEngine."""

    snapshot_id: str
    universe_id: str
    bar_index: int
    timestamp: float

    breadth_data: BreadthData
    participation: ParticipationSnapshot
    market_health: MarketHealthSnapshot
    regime_snapshot: BreadthRegimeSnapshot
    active_divergences: List[DivergenceSignal]
    confidence: BreadthConfidenceScore

    active_events: List[BreadthEvent]
    last_event: Optional[BreadthEvent]

    # Cross-engine context
    market_regime: Optional[str]      = None
    trend_stage: Optional[str]        = None
    volatility_regime: Optional[str]  = None
    liquidity_score: Optional[float]  = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "universe_id": self.universe_id,
            "bar_index": self.bar_index,
            "timestamp": self.timestamp,
            "breadth_data": self.breadth_data.to_dict(),
            "participation": self.participation.to_dict(),
            "market_health": self.market_health.to_dict(),
            "regime": self.regime_snapshot.to_dict(),
            "active_divergences": [d.to_dict() for d in self.active_divergences],
            "confidence": self.confidence.to_dict(),
            "active_events": [e.to_dict() for e in self.active_events],
            "last_event": self.last_event.to_dict() if self.last_event else None,
            "market_regime": self.market_regime,
            "trend_stage": self.trend_stage,
            "volatility_regime": self.volatility_regime,
            "liquidity_score": self.liquidity_score,
        }
