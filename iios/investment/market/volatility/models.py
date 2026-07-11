"""iios/investment/market/volatility/models.py
Core domain models for the Institutional Volatility Intelligence Engine.
All enums, dataclasses and composite snapshots live here.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


# ── Enums ─────────────────────────────────────────────────────────────────

class VolatilityRegimeType(str, Enum):
    VERY_LOW    = "very_low"
    LOW         = "low"
    NORMAL      = "normal"
    ELEVATED    = "elevated"
    HIGH        = "high"
    EXTREME     = "extreme"
    SHOCK       = "shock"
    RECOVERY    = "recovery"
    COMPRESSION = "compression"
    EXPANSION   = "expansion"
    UNKNOWN     = "unknown"


class VolatilityBehaviour(str, Enum):
    EXPANDING    = "expanding"
    COMPRESSING  = "compressing"
    CLIMAX       = "climax"
    COOLING      = "cooling"
    PERSISTENT   = "persistent"
    ACCELERATING = "accelerating"
    DECELERATING = "decelerating"
    STABLE       = "stable"


class VolatilityEventType(str, Enum):
    REGIME_CHANGE      = "regime_change"
    EXPANSION_START    = "expansion_start"
    COMPRESSION_START  = "compression_start"
    CLIMAX             = "climax"
    SHOCK              = "shock"
    RECOVERY_START     = "recovery_start"
    SPIKE              = "spike"
    DRY_UP             = "dry_up"
    PERSISTENCE_BREAK  = "persistence_break"


class RiskLevel(str, Enum):
    VERY_LOW  = "very_low"
    LOW       = "low"
    MODERATE  = "moderate"
    HIGH      = "high"
    VERY_HIGH = "very_high"
    EXTREME   = "extreme"


class StrategyType(str, Enum):
    MOMENTUM             = "momentum"
    BREAKOUT             = "breakout"
    RETEST               = "retest"
    MEAN_REVERSION       = "mean_reversion"
    SWING_TRADING        = "swing_trading"
    POSITION_TRADING     = "position_trading"
    OPTIONS              = "options"
    PORTFOLIO_REBALANCING = "portfolio_rebalancing"


class VolatilityTransitionType(str, Enum):
    RISING     = "rising"
    FALLING    = "falling"
    STABLE     = "stable"
    SPIKING    = "spiking"
    COLLAPSING = "collapsing"


# ── Value objects ─────────────────────────────────────────────────────────

@dataclass
class VolatilityEstimate:
    """Output from one pluggable volatility estimator."""
    estimator_name: str
    raw_value: float        # e.g. daily log-return std dev
    annualized_pct: float   # annualized percentage (20.0 = 20 % annual vol)
    window_bars: int
    confidence: float       # 0-1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "estimator_name": self.estimator_name,
            "raw_value": round(self.raw_value, 6),
            "annualized_pct": round(self.annualized_pct, 4),
            "window_bars": self.window_bars,
            "confidence": round(self.confidence, 4),
        }


@dataclass
class VolatilityEvent:
    event_type: VolatilityEventType
    symbol: str
    timeframe: str
    bar_index: int
    severity: float                              # 0-1
    from_regime: Optional[VolatilityRegimeType] = None
    to_regime: Optional[VolatilityRegimeType]   = None
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.event_type.value,
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "bar_index": self.bar_index,
            "severity": round(self.severity, 4),
            "from_regime": self.from_regime.value if self.from_regime else None,
            "to_regime": self.to_regime.value if self.to_regime else None,
            "description": self.description,
        }


# ── State / profile dataclasses ───────────────────────────────────────────

@dataclass
class VolatilityState:
    """Numerical volatility state derived from rolling windows."""
    realized_volatility: float   # primary estimate, annualised %
    short_term_vol: float        # 5-bar window average of annualised vol
    medium_term_vol: float       # 20-bar window average
    long_term_vol: float         # 50-bar window average
    relative_volatility: float   # short_term / medium_term
    normalized_volatility: float # 0-1 percentile rank within own history
    volatility_persistence: float # lag-1 autocorrelation proxy 0-1
    volatility_stability: float  # 1/(1 + vol_of_vol / medium_vol)
    vol_of_vol: float            # std of the rolling vol estimates
    bar_range_ratio: float       # current bar range / avg range
    bars_processed: int
    is_initialized: bool         # True once medium window is full

    def to_dict(self) -> Dict[str, Any]:
        return {
            "realized_volatility": round(self.realized_volatility, 4),
            "short_term_vol": round(self.short_term_vol, 4),
            "medium_term_vol": round(self.medium_term_vol, 4),
            "long_term_vol": round(self.long_term_vol, 4),
            "relative_volatility": round(self.relative_volatility, 4),
            "normalized_volatility": round(self.normalized_volatility, 4),
            "volatility_persistence": round(self.volatility_persistence, 4),
            "volatility_stability": round(self.volatility_stability, 4),
            "vol_of_vol": round(self.vol_of_vol, 4),
            "bar_range_ratio": round(self.bar_range_ratio, 4),
            "bars_processed": self.bars_processed,
            "is_initialized": self.is_initialized,
        }


@dataclass
class VolatilityProfile:
    """Composite volatility profile combining estimator outputs and state."""
    state: VolatilityState
    estimates: Dict[str, VolatilityEstimate]
    primary_estimate: Optional[VolatilityEstimate]
    estimate_agreement: float   # 0-1 agreement among estimators
    estimate_spread: float      # spread in annualised % among estimators

    def to_dict(self) -> Dict[str, Any]:
        return {
            "state": self.state.to_dict(),
            "estimates": {k: v.to_dict() for k, v in self.estimates.items()},
            "primary_estimate": (
                self.primary_estimate.to_dict() if self.primary_estimate else None
            ),
            "estimate_agreement": round(self.estimate_agreement, 4),
            "estimate_spread": round(self.estimate_spread, 4),
        }


@dataclass
class VolatilityRegimeSnapshot:
    regime: VolatilityRegimeType
    confidence: float
    duration_bars: int
    previous_regime: Optional[VolatilityRegimeType]
    transition_type: VolatilityTransitionType
    transition_probability: float  # estimated prob of change next bar
    regime_score: float            # 0-100 position within regime band

    def to_dict(self) -> Dict[str, Any]:
        return {
            "regime": self.regime.value,
            "confidence": round(self.confidence, 4),
            "duration_bars": self.duration_bars,
            "previous_regime": (
                self.previous_regime.value if self.previous_regime else None
            ),
            "transition_type": self.transition_type.value,
            "transition_probability": round(self.transition_probability, 4),
            "regime_score": round(self.regime_score, 2),
        }


@dataclass
class BehaviourSnapshot:
    behaviour: VolatilityBehaviour
    expansion_score: float    # 0-1
    compression_score: float  # 0-1
    persistence_score: float  # 0-1
    acceleration: float       # + = accelerating, − = decelerating
    cycle_phase: str          # "expansion" | "peak" | "contraction" | "trough"
    bars_in_phase: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "behaviour": self.behaviour.value,
            "expansion_score": round(self.expansion_score, 4),
            "compression_score": round(self.compression_score, 4),
            "persistence_score": round(self.persistence_score, 4),
            "acceleration": round(self.acceleration, 4),
            "cycle_phase": self.cycle_phase,
            "bars_in_phase": self.bars_in_phase,
        }


@dataclass
class RiskProfile:
    execution_risk: float  # 0-1
    gap_risk: float        # 0-1
    overnight_risk: float  # 0-1
    portfolio_risk: float  # 0-1
    strategy_risk: float   # 0-1
    market_risk: float     # 0-1
    overall_risk: float    # 0-1
    risk_level: RiskLevel
    risk_score: float      # 0-100

    def to_dict(self) -> Dict[str, Any]:
        return {
            "execution_risk": round(self.execution_risk, 4),
            "gap_risk": round(self.gap_risk, 4),
            "overnight_risk": round(self.overnight_risk, 4),
            "portfolio_risk": round(self.portfolio_risk, 4),
            "strategy_risk": round(self.strategy_risk, 4),
            "market_risk": round(self.market_risk, 4),
            "overall_risk": round(self.overall_risk, 4),
            "risk_level": self.risk_level.value,
            "risk_score": round(self.risk_score, 2),
        }


@dataclass
class StrategyCompatibility:
    permissions: Dict[str, bool]  # StrategyType.value -> allowed
    recommended: List[str]        # recommended strategy type values
    restricted: List[str]         # restricted strategy type values

    def is_permitted(self, strategy: str) -> bool:
        return self.permissions.get(strategy, False)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "permissions": dict(self.permissions),
            "recommended": list(self.recommended),
            "restricted": list(self.restricted),
        }


@dataclass
class ConfidenceScore:
    volatility_confidence: float   # 0-1 quality of vol estimate
    forecast_confidence: float     # 0-1 near-term vol forecast confidence
    regime_stability: float        # 0-1 stability of current regime
    expected_persistence: float    # 0-1 expected continuation of vol level
    transition_probability: float  # 0-1 probability of regime change

    def to_dict(self) -> Dict[str, Any]:
        return {
            "volatility_confidence": round(self.volatility_confidence, 4),
            "forecast_confidence": round(self.forecast_confidence, 4),
            "regime_stability": round(self.regime_stability, 4),
            "expected_persistence": round(self.expected_persistence, 4),
            "transition_probability": round(self.transition_probability, 4),
        }


# ── Primary output ────────────────────────────────────────────────────────

@dataclass
class VolatilityIntelligenceSnapshot:
    """Primary output of InstitutionalVolatilityIntelligenceEngine."""

    # Identity
    snapshot_id: str
    symbol: str
    timeframe: str
    bar_index: int
    timestamp: float

    # Core vol metrics
    volatility_profile: VolatilityProfile

    # Convenience scalar fields
    realized_volatility: float    # annualised %
    relative_volatility: float    # ratio to own history
    normalized_volatility: float  # 0-1
    volatility_score: float       # 0-100

    # Sub-snapshots
    regime_snapshot: VolatilityRegimeSnapshot
    behaviour_snapshot: BehaviourSnapshot
    risk_profile: RiskProfile
    strategy_compatibility: StrategyCompatibility
    confidence: ConfidenceScore

    # Events
    active_events: List[VolatilityEvent]
    last_event: Optional[VolatilityEvent]

    # Cross-engine context (may be None if not connected)
    structure_regime: Optional[str]   = None
    market_regime: Optional[str]      = None
    trend_stage: Optional[str]        = None
    liquidity_score: Optional[float]  = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "bar_index": self.bar_index,
            "timestamp": self.timestamp,
            "realized_volatility": round(self.realized_volatility, 4),
            "relative_volatility": round(self.relative_volatility, 4),
            "normalized_volatility": round(self.normalized_volatility, 4),
            "volatility_score": round(self.volatility_score, 2),
            "volatility_profile": self.volatility_profile.to_dict(),
            "regime": self.regime_snapshot.to_dict(),
            "behaviour": self.behaviour_snapshot.to_dict(),
            "risk_profile": self.risk_profile.to_dict(),
            "strategy_compatibility": self.strategy_compatibility.to_dict(),
            "confidence": self.confidence.to_dict(),
            "active_events": [e.to_dict() for e in self.active_events],
            "last_event": self.last_event.to_dict() if self.last_event else None,
            "structure_regime": self.structure_regime,
            "market_regime": self.market_regime,
            "trend_stage": self.trend_stage,
            "liquidity_score": self.liquidity_score,
        }
