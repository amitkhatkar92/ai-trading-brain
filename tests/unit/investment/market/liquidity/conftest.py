"""tests/unit/investment/market/liquidity/conftest.py
Fixtures for liquidity engine tests.
"""
from __future__ import annotations

import math
from typing import List

import pytest

from iios.investment.market.structure.models import Bar
from iios.investment.market.liquidity.models import (
    VolumeBar, VolumeLevel,
)
from iios.investment.market.liquidity.volume_statistics import VolumeStatistics
from iios.investment.market.liquidity.volume_engine import VolumeEngine


# ── Bar factories ──────────────────────────────────────────────────────────

def make_bar(
    index: int = 0,
    open: float = 100.0,
    high: float = 102.0,
    low: float = 99.0,
    close: float = 101.5,
    volume: float = 100_000.0,
    timeframe: str = "1d",
) -> Bar:
    return Bar(
        index=index,
        timestamp=float(1_700_000_000 + index * 86400),
        open=open,
        high=high,
        low=low,
        close=close,
        volume=volume,
        timeframe=timeframe,
    )


def make_up_bar(
    index: int = 0,
    base: float = 100.0,
    volume: float = 150_000.0,
) -> Bar:
    """Up bar: close > open, closes near high."""
    return Bar(
        index=index,
        timestamp=float(1_700_000_000 + index * 86400),
        open=base,
        high=base + 3.0,
        low=base - 0.5,
        close=base + 2.8,
        volume=volume,
        timeframe="1d",
    )


def make_down_bar(
    index: int = 0,
    base: float = 100.0,
    volume: float = 150_000.0,
) -> Bar:
    return Bar(
        index=index,
        timestamp=float(1_700_000_000 + index * 86400),
        open=base,
        high=base + 0.5,
        low=base - 3.0,
        close=base - 2.8,
        volume=volume,
        timeframe="1d",
    )


def make_doji_bar(
    index: int = 0,
    base: float = 100.0,
    volume: float = 100_000.0,
) -> Bar:
    """Doji: open ~= close."""
    return Bar(
        index=index,
        timestamp=float(1_700_000_000 + index * 86400),
        open=base,
        high=base + 2.0,
        low=base - 2.0,
        close=base + 0.02,
        volume=volume,
        timeframe="1d",
    )


def make_high_volume_bar(
    index: int = 0,
    volume_multiplier: float = 3.0,
) -> Bar:
    base_vol = 100_000.0
    return make_bar(index=index, volume=base_vol * volume_multiplier)


def make_low_volume_bar(
    index: int = 0,
    volume_multiplier: float = 0.2,
) -> Bar:
    base_vol = 100_000.0
    return make_bar(index=index, volume=base_vol * volume_multiplier)


def make_bars(
    n: int = 30,
    trend: str = "up",
    base_volume: float = 100_000.0,
) -> List[Bar]:
    """Synthetic bar series with volume and price movement."""
    bars = []
    price = 100.0
    for i in range(n):
        vol = base_volume * (1.0 + 0.05 * math.sin(i / 5.0))
        if trend == "up":
            price += 0.5
            o, c = price - 0.3, price + 0.3
            h, l = price + 0.8, price - 0.5
        elif trend == "down":
            price -= 0.5
            o, c = price + 0.3, price - 0.3
            h, l = price + 0.5, price - 0.8
        else:
            o, c = price - 0.2, price + 0.1
            h, l = price + 0.8, price - 0.8
        bars.append(Bar(
            index=i,
            timestamp=float(1_700_000_000 + i * 86400),
            open=o,
            high=h,
            low=l,
            close=c,
            volume=vol,
            timeframe="1d",
        ))
    return bars


def make_volume_bar(
    index: int = 0,
    volume: float = 100_000.0,
    relative_volume: float = 1.0,
    normalized_volume: float = 0.5,
    is_up: bool = True,
    close_position: float = 0.7,
    body_pct: float = 0.6,
    bar_range: float = 3.0,
    price_change: float = 1.8,
    price_change_pct: float = 1.8,
    volume_level: VolumeLevel = VolumeLevel.AVERAGE,
) -> VolumeBar:
    return VolumeBar(
        index=index,
        timestamp=float(1_700_000_000 + index * 86400),
        volume=volume,
        relative_volume=relative_volume,
        normalized_volume=normalized_volume,
        price_change=price_change,
        price_change_pct=price_change_pct,
        bar_range=bar_range,
        is_up=is_up,
        body_pct=body_pct,
        close_position=close_position,
        volume_level=volume_level,
    )


# ── Fixtures ───────────────────────────────────────────────────────────────

@pytest.fixture
def volume_stats_populated() -> VolumeStatistics:
    stats = VolumeStatistics(window=20)
    for i in range(20):
        stats.update(100_000.0 * (1.0 + 0.1 * i))
    return stats


@pytest.fixture
def volume_engine_with_history() -> VolumeEngine:
    engine = VolumeEngine(window=20)
    bars = make_bars(25)
    for b in bars:
        engine.update(b)
    return engine
