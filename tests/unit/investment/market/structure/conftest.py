"""tests/unit/investment/market/structure/conftest.py
Synthetic bar data generators for all structure tests.
All generators use seed=42 for determinism. No external data dependencies.
"""
from __future__ import annotations

import math
import random
from typing import List

import pytest

from iios.investment.market.structure.models import Bar

_RNG = random.Random(42)


def _bar(idx: int, o: float, h: float, l: float, c: float, vol: float) -> Bar:
    return Bar(
        index=idx,
        timestamp=float(1_700_000_000 + idx * 86400),
        open=round(o, 2),
        high=round(h, 2),
        low=round(l, 2),
        close=round(c, 2),
        volume=round(vol, 0),
        timeframe="1d",
    )


def make_uptrend_bars(n: int = 50) -> List[Bar]:
    """Steady uptrend: each bar drifts higher with noise."""
    rng = random.Random(42)
    bars: List[Bar] = []
    price = 100.0
    for i in range(n):
        drift = rng.uniform(0.3, 1.2)
        noise = rng.uniform(-0.3, 0.3)
        o = price
        c = price + drift + noise
        h = max(o, c) + rng.uniform(0.1, 0.5)
        l = min(o, c) - rng.uniform(0.1, 0.5)
        vol = rng.uniform(100_000, 200_000)
        bars.append(_bar(i, o, h, l, c, vol))
        price = c
    return bars


def make_downtrend_bars(n: int = 50) -> List[Bar]:
    """Steady downtrend: each bar drifts lower."""
    rng = random.Random(42)
    bars: List[Bar] = []
    price = 200.0
    for i in range(n):
        drift = rng.uniform(0.3, 1.2)
        noise = rng.uniform(-0.3, 0.3)
        o = price
        c = price - drift + noise
        h = max(o, c) + rng.uniform(0.1, 0.5)
        l = min(o, c) - rng.uniform(0.1, 0.5)
        vol = rng.uniform(100_000, 200_000)
        bars.append(_bar(i, o, h, l, c, vol))
        price = c
    return bars


def make_range_bars(n: int = 30) -> List[Bar]:
    """Price oscillates inside a ±2% band around 150."""
    rng = random.Random(42)
    bars: List[Bar] = []
    center = 150.0
    for i in range(n):
        phase = math.sin(i * 0.4)
        c = center + phase * 2.0 + rng.uniform(-0.3, 0.3)
        o = c + rng.uniform(-0.2, 0.2)
        h = max(o, c) + rng.uniform(0.05, 0.3)
        l = min(o, c) - rng.uniform(0.05, 0.3)
        vol = rng.uniform(80_000, 120_000)
        bars.append(_bar(i, o, h, l, c, vol))
    return bars


def make_breakout_bars(n: int = 40) -> List[Bar]:
    """30 bars ranging, then 10 bars strong bullish breakout."""
    rng = random.Random(42)
    bars: List[Bar] = []
    center = 100.0

    # Range phase
    for i in range(30):
        phase = math.sin(i * 0.5)
        c = center + phase * 1.5 + rng.uniform(-0.2, 0.2)
        o = c + rng.uniform(-0.1, 0.1)
        h = max(o, c) + rng.uniform(0.05, 0.2)
        l = min(o, c) - rng.uniform(0.05, 0.2)
        vol = rng.uniform(80_000, 100_000)
        bars.append(_bar(i, o, h, l, c, vol))

    # Breakout phase
    price = center + 1.5
    for i in range(30, n):
        o = price
        c = price + rng.uniform(0.8, 1.5)
        h = c + rng.uniform(0.1, 0.4)
        l = o - rng.uniform(0.05, 0.2)
        vol = rng.uniform(200_000, 350_000)  # high volume breakout
        bars.append(_bar(i, o, h, l, c, vol))
        price = c

    return bars


def make_compression_bars(n: int = 20) -> List[Bar]:
    """Bar ranges shrink progressively by 50% from first to last."""
    rng = random.Random(42)
    bars: List[Bar] = []
    price = 100.0
    for i in range(n):
        scale = 1.0 - (i / n) * 0.5  # shrinks from 1.0 to 0.5
        half = 0.5 * scale
        c = price + rng.uniform(-half * 0.3, half * 0.3)
        o = c + rng.uniform(-half * 0.2, half * 0.2)
        h = max(o, c) + half
        l = min(o, c) - half
        vol = rng.uniform(80_000, 120_000) * (1.0 - i / (n * 1.5))
        bars.append(_bar(i, o, h, l, c, max(vol, 1.0)))
        price = c
    return bars


# ── pytest fixtures ───────────────────────────────────────────────────────

@pytest.fixture
def uptrend_bars() -> List[Bar]:
    return make_uptrend_bars()


@pytest.fixture
def downtrend_bars() -> List[Bar]:
    return make_downtrend_bars()


@pytest.fixture
def range_bars() -> List[Bar]:
    return make_range_bars()


@pytest.fixture
def breakout_bars() -> List[Bar]:
    return make_breakout_bars()


@pytest.fixture
def compression_bars() -> List[Bar]:
    return make_compression_bars()
