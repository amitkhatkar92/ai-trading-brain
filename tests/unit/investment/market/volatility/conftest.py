"""tests/unit/investment/market/volatility/conftest.py
Shared fixtures and helpers for volatility engine tests.
"""
from __future__ import annotations

import math
from typing import List

import pytest

from iios.investment.market.structure.models import Bar
from iios.investment.market.volatility.models import (
    VolatilityState,
    BehaviourSnapshot,
    VolatilityBehaviour,
    VolatilityRegimeType,
    VolatilityRegimeSnapshot,
    VolatilityTransitionType,
)
from iios.investment.market.volatility.volatility_statistics import VolatilityStatistics


# ── Bar helpers ───────────────────────────────────────────────────────────

def make_bar(
    index: int = 0,
    open: float = 100.0,
    high: float = 103.0,
    low: float = 97.0,
    close: float = 101.0,
    volume: float = 100_000.0,
) -> Bar:
    return Bar(
        index=index,
        timestamp=float(1_700_000_000 + index * 86400),
        open=open,
        high=high,
        low=low,
        close=close,
        volume=volume,
    )


def make_up_bar(index: int = 0, base: float = 100.0, volume: float = 150_000.0) -> Bar:
    return Bar(
        index=index,
        timestamp=float(1_700_000_000 + index * 86400),
        open=base,
        high=base + 3.0,
        low=base - 0.5,
        close=base + 2.5,
        volume=volume,
    )


def make_down_bar(index: int = 0, base: float = 100.0, volume: float = 150_000.0) -> Bar:
    return Bar(
        index=index,
        timestamp=float(1_700_000_000 + index * 86400),
        open=base,
        high=base + 0.5,
        low=base - 3.0,
        close=base - 2.5,
        volume=volume,
    )


def make_bars(
    n: int = 30,
    trend: str = "up",
    base_price: float = 100.0,
    base_vol: float = 100_000.0,
    volatility: float = 0.01,   # daily std dev fraction
) -> List[Bar]:
    """Synthetic bar series with realistic OHLCV."""
    bars: List[Bar] = []
    price = base_price
    for i in range(n):
        # Random-walk-like price
        noise = math.sin(i * 0.7) * volatility * price
        if trend == "up":
            price_change = price * 0.003 + noise
        elif trend == "down":
            price_change = -price * 0.003 + noise
        else:
            price_change = noise

        open_p = price
        close_p = price + price_change
        high_p = max(open_p, close_p) + abs(noise) * 0.5
        low_p  = min(open_p, close_p) - abs(noise) * 0.5
        # Ensure OHLC consistency
        high_p = max(high_p, open_p, close_p)
        low_p  = min(low_p, open_p, close_p)
        if high_p == low_p:
            high_p += 0.01

        bars.append(Bar(
            index=i,
            timestamp=float(1_700_000_000 + i * 86400),
            open=round(open_p, 4),
            high=round(high_p, 4),
            low=round(low_p, 4),
            close=round(close_p, 4),
            volume=base_vol,
        ))
        price = close_p

    return bars


def make_volatile_bars(n: int = 30, base_price: float = 100.0) -> List[Bar]:
    """High-volatility bars with large swings."""
    return make_bars(n=n, trend="flat", base_price=base_price, volatility=0.05)


def make_quiet_bars(n: int = 30, base_price: float = 100.0) -> List[Bar]:
    """Low-volatility bars with tiny swings."""
    return make_bars(n=n, trend="flat", base_price=base_price, volatility=0.001)


# ── State helpers ─────────────────────────────────────────────────────────

def make_vol_state(
    realized_volatility: float = 20.0,
    normalized_volatility: float = 0.50,
    relative_volatility: float = 1.0,
    volatility_persistence: float = 0.60,
    volatility_stability: float = 0.70,
    vol_of_vol: float = 3.0,
    bar_range_ratio: float = 1.0,
    is_initialized: bool = True,
) -> VolatilityState:
    return VolatilityState(
        realized_volatility=realized_volatility,
        short_term_vol=realized_volatility,
        medium_term_vol=realized_volatility,
        long_term_vol=realized_volatility,
        relative_volatility=relative_volatility,
        normalized_volatility=normalized_volatility,
        volatility_persistence=volatility_persistence,
        volatility_stability=volatility_stability,
        vol_of_vol=vol_of_vol,
        bar_range_ratio=bar_range_ratio,
        bars_processed=25,
        is_initialized=is_initialized,
    )


def make_behaviour(
    behaviour: VolatilityBehaviour = VolatilityBehaviour.STABLE,
    expansion_score: float = 0.0,
    compression_score: float = 0.0,
    persistence_score: float = 0.5,
    acceleration: float = 0.0,
    cycle_phase: str = "contraction",
    bars_in_phase: int = 5,
) -> BehaviourSnapshot:
    return BehaviourSnapshot(
        behaviour=behaviour,
        expansion_score=expansion_score,
        compression_score=compression_score,
        persistence_score=persistence_score,
        acceleration=acceleration,
        cycle_phase=cycle_phase,
        bars_in_phase=bars_in_phase,
    )


def make_regime_snap(
    regime: VolatilityRegimeType = VolatilityRegimeType.NORMAL,
    confidence: float = 0.75,
    duration_bars: int = 10,
    transition_probability: float = 0.10,
    regime_score: float = 50.0,
) -> VolatilityRegimeSnapshot:
    return VolatilityRegimeSnapshot(
        regime=regime,
        confidence=confidence,
        duration_bars=duration_bars,
        previous_regime=None,
        transition_type=VolatilityTransitionType.STABLE,
        transition_probability=transition_probability,
        regime_score=regime_score,
    )


# ── Statistics fixture ────────────────────────────────────────────────────

@pytest.fixture
def populated_stats() -> VolatilityStatistics:
    """VolatilityStatistics with 30 realistic observations."""
    stats = VolatilityStatistics(window=50)
    base = 20.0
    for i in range(30):
        stats.update(base + math.sin(i * 0.5) * 5.0)
    return stats
