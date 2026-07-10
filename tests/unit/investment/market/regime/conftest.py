"""tests/unit/investment/market/regime/conftest.py
Shared pytest fixtures for regime tests.
"""
from __future__ import annotations

import time
import pytest

from iios.investment.market.market_constants import (
    MarketRegime,
    MarketStatus,
    MarketStrength,
    TrendDirection,
    VolatilityLevel,
    LiquidityLevel,
    BreadthCondition,
    SentimentLevel,
)
from iios.investment.market.market_state.market_snapshot import MarketSnapshot
from iios.investment.market.structure.models import (
    BreakoutEvent,
    BreakoutStatus,
    BreakoutType,
    ConsolidationState,
    ConsolidationType,
    MarketStructureSnapshot,
    StructurePhase,
    StructureQualityScore,
    SwingSequence,
    TrendPhase,
    TrendState,
    Zone,
    ZoneStrength,
    ZoneType,
)
from iios.investment.market.regime.models import (
    RegimeObservation,
)


# ── Structure snapshot builder ────────────────────────────────────────────────

def make_structure_snapshot(
    trend_dir: TrendDirection = TrendDirection.UP,
    confirmed: bool = True,
    leg_count: int = 2,
    phase: StructurePhase = StructurePhase.MARKUP,
    vol_level: VolatilityLevel | None = None,
    in_consolidation: bool = False,
    consolidation_bars: int = 0,
    has_breakout: bool = False,
    breakout_bullish: bool = True,
    quality: float = 75.0,
) -> MarketStructureSnapshot:
    trend = TrendState(
        direction=trend_dir,
        strength=MarketStrength.STRONG,
        phase=TrendPhase.IMPULSE,
        leg_count=leg_count,
        current_leg_height=10.0,
        total_displacement=20.0,
        correction_depth=0.3,
        start_index=0,
        start_price=100.0,
        last_swing_index=10,
        last_swing_price=110.0,
        confirmed=confirmed,
    )

    quality_score = StructureQualityScore(
        overall=quality,
        swing_confidence=quality,
        trend_confidence=quality,
        zone_confidence=quality,
        breakout_confidence=quality,
        data_quality=quality,
        bar_count=50,
        valid_swing_count=4,
    )

    consolidation = None
    if in_consolidation:
        consolidation = ConsolidationState(
            consolidation_type=ConsolidationType.RANGE,
            start_index=0,
            high_bound=110.0,
            low_bound=100.0,
            bar_count=consolidation_bars,
            avg_range=5.0,
            initial_range=10.0,
            tightest_range=3.0,
            volume_trend="decreasing",
            active=True,
        )

    breakout = None
    if has_breakout:
        zone = Zone(
            zone_id="z1",
            zone_type=ZoneType.RESISTANCE,
            upper=112.0,
            lower=110.0,
            strength=ZoneStrength.MAJOR,
            touch_count=2,
            first_touch_index=5,
            last_touch_index=20,
            first_touch_price=111.0,
            origin_swing_count=2,
        )
        breakout = BreakoutEvent(
            breakout_id="b1",
            breakout_type=BreakoutType.BULLISH if breakout_bullish else BreakoutType.BEARISH,
            status=BreakoutStatus.CONFIRMED,
            zone=zone,
            trigger_index=25,
            trigger_price=113.0,
            trigger_volume=10000.0,
            avg_volume_20=8000.0,
            close_beyond=113.5,
        )

    return MarketStructureSnapshot(
        symbol="TEST",
        timeframe="1d",
        bar_index=50,
        timestamp=time.time(),
        trend=trend,
        structure_phase=phase,
        last_swing_high=None,
        last_swing_low=None,
        swing_sequence=SwingSequence(),
        active_zones=[],
        nearest_resistance=None,
        nearest_support=None,
        active_breakout=breakout,
        consolidation=consolidation,
        last_transition=None,
        quality=quality_score,
    )


# ── Market snapshot builder ───────────────────────────────────────────────────

def make_market_snapshot(
    trend_dir: TrendDirection = TrendDirection.UP,
    volatility: VolatilityLevel = VolatilityLevel.MODERATE,
    advances: int = 60,
    declines: int = 40,
) -> MarketSnapshot:
    return MarketSnapshot(
        market_id="TEST",
        status=MarketStatus.OPEN,
        trend=trend_dir,
        volatility=volatility,
        advances=advances,
        declines=declines,
        strength=MarketStrength.MODERATE,
        liquidity=LiquidityLevel.MODERATE,
        breadth=BreadthCondition.MODERATE,
        sentiment=SentimentLevel.NEUTRAL,
    )


# ── Observation builder ───────────────────────────────────────────────────────

def make_observation(
    trend_dir: TrendDirection = TrendDirection.UP,
    confirmed: bool = True,
    leg_count: int = 2,
    phase: str = "markup",
    vol: VolatilityLevel = VolatilityLevel.MODERATE,
    in_consol: bool = False,
    consol_bars: int = 0,
    has_breakout: bool = False,
    breakout_bullish: bool = True,
    adr: float = 1.5,
    quality: float = 75.0,
    trend_phase: str = "impulse",
) -> RegimeObservation:
    return RegimeObservation(
        trend_direction=trend_dir,
        trend_confirmed=confirmed,
        trend_leg_count=leg_count,
        trend_strength=MarketStrength.STRONG.value,
        trend_phase=trend_phase,
        structure_phase=phase,
        volatility=vol,
        in_consolidation=in_consol,
        consolidation_bars=consol_bars,
        consolidation_compression=1.0,
        has_active_breakout=has_breakout,
        breakout_bullish=breakout_bullish,
        advance_decline_ratio=adr,
        quality_score=quality,
        bar_count=50,
    )


# ── Ready-made observation fixtures ──────────────────────────────────────────

@pytest.fixture
def bull_obs() -> RegimeObservation:
    return make_observation(
        trend_dir=TrendDirection.UP,
        confirmed=True,
        leg_count=3,
        phase="markup",
        vol=VolatilityLevel.MODERATE,
        adr=1.8,
    )


@pytest.fixture
def bear_obs() -> RegimeObservation:
    return make_observation(
        trend_dir=TrendDirection.DOWN,
        confirmed=True,
        leg_count=2,
        phase="markdown",
        vol=VolatilityLevel.MODERATE,
        adr=0.4,
    )


@pytest.fixture
def sideways_obs() -> RegimeObservation:
    return make_observation(
        trend_dir=TrendDirection.SIDEWAYS,
        confirmed=False,
        leg_count=0,
        phase="markup",
        vol=VolatilityLevel.LOW,
        adr=1.0,
    )


@pytest.fixture
def crisis_obs() -> RegimeObservation:
    return make_observation(
        trend_dir=TrendDirection.DOWN,
        confirmed=True,
        leg_count=3,
        phase="markdown",
        vol=VolatilityLevel.EXTREME,
        adr=0.2,
    )


# ── Structure snapshot fixtures ───────────────────────────────────────────────

@pytest.fixture
def bull_structure() -> MarketStructureSnapshot:
    return make_structure_snapshot(
        trend_dir=TrendDirection.UP,
        confirmed=True,
        leg_count=3,
        phase=StructurePhase.MARKUP,
        quality=80.0,
    )


@pytest.fixture
def bear_structure() -> MarketStructureSnapshot:
    return make_structure_snapshot(
        trend_dir=TrendDirection.DOWN,
        confirmed=True,
        leg_count=2,
        phase=StructurePhase.MARKDOWN,
        quality=75.0,
    )
