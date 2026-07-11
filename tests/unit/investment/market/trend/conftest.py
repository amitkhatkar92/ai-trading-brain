"""tests/unit/investment/market/trend/conftest.py
Shared fixtures for trend intelligence engine tests.
"""
from __future__ import annotations

import time
import pytest
from typing import List, Optional

from iios.investment.market.market_constants import TrendDirection, MarketStrength
from iios.investment.market.regime.models import RegimeSnapshot, RegimeType
from iios.investment.market.structure.models import (
    TrendState as StructureTrendState,
    TrendPhase,
    StructurePhase,
    SwingPoint,
    SwingType,
    SwingStrength,
    SwingRelation,
    SwingSequence,
    StructureQualityScore,
    MarketStructureSnapshot,
)
from iios.investment.market.trend.models import (
    TrendStage,
    TrendLegMetrics,
    TrendMomentumState,
    TrendQualityMetrics,
    ImpulseQuality,
    CorrectionQuality,
    TrendDirection as _TrendDir,  # re-exported alias check
)


# ── Helper factories ───────────────────────────────────────────────────────

def make_trend_state(
    direction: str = "up",
    confirmed: bool = True,
    leg_count: int = 3,
    strength: str = "moderate",
    phase: str = "impulse",
    correction_depth: float = 0.38,
    current_leg_height: float = 5.0,
    total_displacement: float = 15.0,
) -> StructureTrendState:
    return StructureTrendState(
        direction=TrendDirection(direction),
        strength=MarketStrength(strength),
        phase=TrendPhase(phase),
        leg_count=leg_count,
        current_leg_height=current_leg_height,
        total_displacement=total_displacement,
        correction_depth=correction_depth,
        start_index=0,
        start_price=100.0,
        last_swing_index=leg_count * 5,
        last_swing_price=100.0 + total_displacement,
        confirmed=confirmed,
    )


def _make_swing(
    index: int,
    price: float,
    swing_type: SwingType,
    relation: Optional[SwingRelation] = None,
) -> SwingPoint:
    return SwingPoint(
        index=index,
        timestamp=float(index),
        price=price,
        swing_type=swing_type,
        strength=SwingStrength.INTERMEDIATE,
        volume=1000.0,
        bar_range=1.0,
        left_bars=3,
        right_bars=3,
        relation=relation,
    )


def make_structure_snapshot(
    direction: str = "up",
    confirmed: bool = True,
    leg_count: int = 3,
    phase: str = "markup",
    trend_phase: str = "impulse",
    n_swing_highs: int = 3,
    n_swing_lows: int = 3,
    quality_overall: float = 72.0,
    in_consolidation: bool = False,
) -> MarketStructureSnapshot:
    trend = make_trend_state(
        direction=direction,
        confirmed=confirmed,
        leg_count=leg_count,
        phase=trend_phase,
    )

    # Build alternating swings: for uptrend, lows rising, highs rising
    highs: List[SwingPoint] = []
    lows: List[SwingPoint] = []

    base_price = 100.0
    step = 5.0 if direction == "up" else -5.0
    corr = -2.0 if direction == "up" else 2.0

    # Build interleaved sequence: L0, H0, L1, H1, ...
    bar = 0
    for i in range(max(n_swing_highs, n_swing_lows)):
        # Low
        lp = base_price + i * (step + corr)
        low_rel = SwingRelation.HIGHER_LOW if direction == "up" else SwingRelation.LOWER_LOW
        lows.append(_make_swing(bar, lp, SwingType.LOW, low_rel if i > 0 else None))
        bar += 5

        # High
        hp = lp + abs(step) + 1.0
        high_rel = SwingRelation.HIGHER_HIGH if direction == "up" else SwingRelation.LOWER_HIGH
        highs.append(_make_swing(bar, hp, SwingType.HIGH, high_rel if i > 0 else None))
        bar += 5

    # Most recent first
    highs_recent = list(reversed(highs[:n_swing_highs]))
    lows_recent = list(reversed(lows[:n_swing_lows]))

    swing_seq = SwingSequence(highs=highs_recent, lows=lows_recent, timeframe="1d")

    quality = StructureQualityScore(
        overall=quality_overall,
        swing_confidence=0.80,
        trend_confidence=0.75,
        zone_confidence=0.70,
        breakout_confidence=0.65,
        data_quality=0.90,
        bar_count=100,
        valid_swing_count=n_swing_highs + n_swing_lows,
    )

    return MarketStructureSnapshot(
        symbol="TEST",
        timeframe="1d",
        bar_index=bar,
        timestamp=float(time.time()),
        trend=trend,
        structure_phase=StructurePhase(phase),
        last_swing_high=highs_recent[0] if highs_recent else None,
        last_swing_low=lows_recent[0] if lows_recent else None,
        swing_sequence=swing_seq,
        active_zones=[],
        nearest_resistance=None,
        nearest_support=None,
        active_breakout=None,
        consolidation=None,
        last_transition=None,
        quality=quality,
    )


def make_regime_snapshot(
    regime: str = "bull",
    confidence: float = 0.80,
    stability: float = 0.70,
) -> RegimeSnapshot:
    return RegimeSnapshot(
        symbol="TEST",
        primary=RegimeType(regime),
        confidence=confidence,
        stability=stability,
        persistence_score=0.70,
    )


def make_legs(n: int = 4, accelerating: bool = False) -> List[TrendLegMetrics]:
    legs = []
    for i in range(n):
        if accelerating:
            displacement = 5.0 + i * 2.0
        else:
            displacement = 5.0 + (i % 2) * 0.5

        velocity = displacement / 5
        is_impulse = (i % 2 == 0)
        legs.append(TrendLegMetrics(
            leg_number=i + 1,
            is_impulse=is_impulse,
            direction=TrendDirection.UP,
            displacement=displacement,
            bars=5,
            velocity=velocity,
            retracement_pct=0.38 if is_impulse else 0.0,
            impulse_quality=ImpulseQuality.MODERATE,
            correction_quality=CorrectionQuality.NORMAL,
        ))
    return legs


# ── Pytest fixtures ────────────────────────────────────────────────────────

@pytest.fixture
def bull_structure() -> MarketStructureSnapshot:
    return make_structure_snapshot(direction="up", confirmed=True, leg_count=3)


@pytest.fixture
def bear_structure() -> MarketStructureSnapshot:
    return make_structure_snapshot(
        direction="down", confirmed=True, leg_count=3,
        phase="markdown", trend_phase="impulse",
    )


@pytest.fixture
def sideways_structure() -> MarketStructureSnapshot:
    return make_structure_snapshot(
        direction="sideways", confirmed=False, leg_count=1,
        phase="contraction", trend_phase="correction",
    )


@pytest.fixture
def bull_regime() -> RegimeSnapshot:
    return make_regime_snapshot(regime="bull", confidence=0.85, stability=0.75)


@pytest.fixture
def bear_regime() -> RegimeSnapshot:
    return make_regime_snapshot(regime="bear", confidence=0.80, stability=0.65)
