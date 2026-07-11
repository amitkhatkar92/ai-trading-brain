"""iios/investment/market/trend/models.py
Data models for the Institutional Trend Intelligence Engine.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from iios.investment.market.market_constants import TrendDirection, MarketStrength
from iios.investment.market.regime.models import RegimeType


# ── Enums ──────────────────────────────────────────────────────────────────

class TrendStage(str, Enum):
    EMERGING    = "emerging"
    DEVELOPING  = "developing"
    ESTABLISHED = "established"
    MATURE      = "mature"
    EXHAUSTING  = "exhausting"
    FAILING     = "failing"
    REVERSING   = "reversing"
    COMPLETED   = "completed"


class TrendEventType(str, Enum):
    TREND_START        = "trend_start"
    TREND_CONTINUATION = "trend_continuation"
    TREND_EXPANSION    = "trend_expansion"
    TREND_SLOWDOWN     = "trend_slowdown"
    TREND_WEAKENING    = "trend_weakening"
    TREND_FAILURE      = "trend_failure"
    TREND_EXHAUSTION   = "trend_exhaustion"
    TREND_RECOVERY     = "trend_recovery"
    TREND_RESTART      = "trend_restart"


class TrendTransitionType(str, Enum):
    STAGE_ADVANCE = "stage_advance"
    STAGE_DECLINE = "stage_decline"
    REVERSAL      = "reversal"
    RESTART       = "restart"


class ImpulseQuality(str, Enum):
    STRONG   = "strong"
    MODERATE = "moderate"
    WEAK     = "weak"


class CorrectionQuality(str, Enum):
    SHALLOW = "shallow"
    NORMAL  = "normal"
    DEEP    = "deep"
    FAILED  = "failed"


# ── Dataclasses ────────────────────────────────────────────────────────────

@dataclass
class TrendLegMetrics:
    """Metrics for a single trend leg (impulse or correction)."""
    leg_number: int
    is_impulse: bool
    direction: TrendDirection
    displacement: float
    bars: int
    velocity: float
    retracement_pct: float
    impulse_quality: ImpulseQuality
    correction_quality: CorrectionQuality


@dataclass
class TrendMomentumState:
    velocity: float
    acceleration: float
    impulse_quality: ImpulseQuality
    correction_quality: CorrectionQuality
    is_accelerating: bool
    is_decelerating: bool
    momentum_score: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "velocity": self.velocity,
            "acceleration": self.acceleration,
            "impulse_quality": self.impulse_quality.value,
            "correction_quality": self.correction_quality.value,
            "is_accelerating": self.is_accelerating,
            "is_decelerating": self.is_decelerating,
            "momentum_score": self.momentum_score,
        }


@dataclass
class TrendQualityMetrics:
    smoothness: float
    reliability: float
    efficiency: float
    consistency: float
    stability: float
    persistence: float
    overall: float

    @property
    def grade(self) -> str:
        if self.overall >= 80:
            return "A"
        if self.overall >= 65:
            return "B"
        if self.overall >= 50:
            return "C"
        if self.overall >= 35:
            return "D"
        return "F"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "smoothness": self.smoothness,
            "reliability": self.reliability,
            "efficiency": self.efficiency,
            "consistency": self.consistency,
            "stability": self.stability,
            "persistence": self.persistence,
            "overall": self.overall,
            "grade": self.grade,
        }


@dataclass
class TrendScore:
    overall: float
    quality_score: float
    momentum_score: float
    lifecycle_score: float
    regime_alignment_score: float

    @property
    def grade(self) -> str:
        if self.overall >= 80:
            return "A"
        if self.overall >= 65:
            return "B"
        if self.overall >= 50:
            return "C"
        if self.overall >= 35:
            return "D"
        return "F"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "overall": self.overall,
            "quality_score": self.quality_score,
            "momentum_score": self.momentum_score,
            "lifecycle_score": self.lifecycle_score,
            "regime_alignment_score": self.regime_alignment_score,
            "grade": self.grade,
        }


@dataclass
class StrategyReadiness:
    momentum_suitability: float
    breakout_suitability: float
    retest_suitability: float
    mean_reversion_suitability: float
    swing_trading_suitability: float
    position_trading_suitability: float
    best_approach: str
    notes: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "momentum_suitability": self.momentum_suitability,
            "breakout_suitability": self.breakout_suitability,
            "retest_suitability": self.retest_suitability,
            "mean_reversion_suitability": self.mean_reversion_suitability,
            "swing_trading_suitability": self.swing_trading_suitability,
            "position_trading_suitability": self.position_trading_suitability,
            "best_approach": self.best_approach,
            "notes": self.notes,
        }


@dataclass
class TrendEventRecord:
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    event_type: TrendEventType = TrendEventType.TREND_START
    symbol: str = ""
    timeframe: str = "1d"
    timestamp: float = field(default_factory=time.time)
    bar_index: int = 0
    stage_before: TrendStage = TrendStage.EMERGING
    stage_after: TrendStage = TrendStage.EMERGING
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "timestamp": self.timestamp,
            "bar_index": self.bar_index,
            "stage_before": self.stage_before.value,
            "stage_after": self.stage_after.value,
            "description": self.description,
            "metadata": self.metadata,
        }


@dataclass
class TrendTransitionRecord:
    transition_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    transition_type: TrendTransitionType = TrendTransitionType.STAGE_ADVANCE
    from_stage: TrendStage = TrendStage.EMERGING
    to_stage: TrendStage = TrendStage.DEVELOPING
    from_direction: TrendDirection = TrendDirection.UNDEFINED
    to_direction: TrendDirection = TrendDirection.UNDEFINED
    confidence: float = 0.0
    timestamp: float = field(default_factory=time.time)
    bar_index: int = 0
    trigger: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "transition_id": self.transition_id,
            "transition_type": self.transition_type.value,
            "from_stage": self.from_stage.value,
            "to_stage": self.to_stage.value,
            "from_direction": self.from_direction.value,
            "to_direction": self.to_direction.value,
            "confidence": self.confidence,
            "timestamp": self.timestamp,
            "bar_index": self.bar_index,
            "trigger": self.trigger,
        }


# ── Default factories ──────────────────────────────────────────────────────

def _default_quality() -> TrendQualityMetrics:
    return TrendQualityMetrics(
        smoothness=0.5, reliability=0.5, efficiency=0.5,
        consistency=0.5, stability=0.5, persistence=0.5,
        overall=50.0,
    )


def _default_momentum() -> TrendMomentumState:
    return TrendMomentumState(
        velocity=0.0,
        acceleration=0.0,
        impulse_quality=ImpulseQuality.MODERATE,
        correction_quality=CorrectionQuality.NORMAL,
        is_accelerating=False,
        is_decelerating=False,
        momentum_score=50.0,
    )


def _default_readiness() -> StrategyReadiness:
    return StrategyReadiness(
        momentum_suitability=0.5,
        breakout_suitability=0.5,
        retest_suitability=0.5,
        mean_reversion_suitability=0.5,
        swing_trading_suitability=0.5,
        position_trading_suitability=0.5,
        best_approach="avoid",
        notes="",
    )


def _default_score() -> TrendScore:
    return TrendScore(
        overall=50.0,
        quality_score=50.0,
        momentum_score=50.0,
        lifecycle_score=60.0,
        regime_alignment_score=50.0,
    )


@dataclass
class TrendIntelligenceSnapshot:
    snapshot_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    symbol: str = ""
    timeframe: str = "1d"
    bar_index: int = 0
    timestamp: float = field(default_factory=time.time)

    # Structure-derived (consumed, not recomputed)
    direction: TrendDirection = TrendDirection.UNDEFINED
    confirmed: bool = False
    leg_count: int = 0
    structure_phase: str = "unknown"
    trend_phase: str = "unknown"

    # Stage
    stage: TrendStage = TrendStage.EMERGING
    stage_confidence: float = 0.0

    # Quality
    quality: TrendQualityMetrics = field(default_factory=_default_quality)

    # Momentum
    momentum: TrendMomentumState = field(default_factory=_default_momentum)

    # Confidence
    confidence: float = 0.0
    continuation_probability: float = 0.0
    failure_probability: float = 0.0
    reversal_probability: float = 0.0
    expected_remaining_legs: float = 0.0

    # Strategy
    strategy_readiness: StrategyReadiness = field(default_factory=_default_readiness)

    # Regime context
    regime: RegimeType = RegimeType.UNKNOWN
    regime_aligned: bool = False

    # Events
    last_event: Optional[TrendEventRecord] = None

    # Score
    score: TrendScore = field(default_factory=_default_score)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "bar_index": self.bar_index,
            "timestamp": self.timestamp,
            "direction": self.direction.value,
            "confirmed": self.confirmed,
            "leg_count": self.leg_count,
            "structure_phase": self.structure_phase,
            "trend_phase": self.trend_phase,
            "stage": self.stage.value,
            "stage_confidence": self.stage_confidence,
            "quality": self.quality.to_dict(),
            "momentum": self.momentum.to_dict(),
            "confidence": self.confidence,
            "continuation_probability": self.continuation_probability,
            "failure_probability": self.failure_probability,
            "reversal_probability": self.reversal_probability,
            "expected_remaining_legs": self.expected_remaining_legs,
            "strategy_readiness": self.strategy_readiness.to_dict(),
            "regime": self.regime.value,
            "regime_aligned": self.regime_aligned,
            "last_event": self.last_event.to_dict() if self.last_event else None,
            "score": self.score.to_dict(),
        }
