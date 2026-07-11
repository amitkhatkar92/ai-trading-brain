"""conftest.py — shared fixtures for breadth engine tests."""
from __future__ import annotations

import time
from typing import Dict, List, Optional

import pytest

from iios.investment.market.breadth.models import (
    MarketCapTier,
    SecurityObservation,
    UniverseSnapshot,
)


# ── Helpers ────────────────────────────────────────────────────────────────

def make_observation(
    symbol: str,
    price_change_pct: float,
    sector: str = "Technology",
    market_cap_tier: str = MarketCapTier.LARGE.value,
    is_above_ma20: bool = False,
    is_above_ma50: bool = False,
    is_new_52w_high: bool = False,
    is_new_52w_low: bool = False,
    volume_ratio: float = 1.0,
    relative_strength: float = 0.0,
) -> SecurityObservation:
    return SecurityObservation(
        symbol=symbol,
        price_change_pct=price_change_pct,
        sector=sector,
        market_cap_tier=market_cap_tier,
        is_above_ma20=is_above_ma20,
        is_above_ma50=is_above_ma50,
        is_new_52w_high=is_new_52w_high,
        is_new_52w_low=is_new_52w_low,
        volume_ratio=volume_ratio,
        relative_strength=relative_strength,
    )


def make_universe(
    n_advancing: int,
    n_declining: int,
    n_unchanged: int = 0,
    universe_id: str = "TEST",
    bar_index: int = 0,
    sectors: Optional[List[str]] = None,
    cap_tiers: Optional[List[str]] = None,
) -> UniverseSnapshot:
    total = n_advancing + n_declining + n_unchanged
    default_sectors = ["Technology", "Financials", "Healthcare", "Energy", "Consumer"]
    default_tiers   = [MarketCapTier.LARGE.value, MarketCapTier.MID.value, MarketCapTier.SMALL.value]
    obs: List[SecurityObservation] = []

    for i in range(n_advancing):
        sector   = (sectors or default_sectors)[i % len(sectors or default_sectors)]
        cap_tier = (cap_tiers or default_tiers)[i % len(cap_tiers or default_tiers)]
        obs.append(make_observation(
            f"ADV_{i}", 0.5, sector=sector, market_cap_tier=cap_tier,
            is_above_ma20=True, is_above_ma50=True,
        ))

    for i in range(n_declining):
        sector   = (sectors or default_sectors)[i % len(sectors or default_sectors)]
        cap_tier = (cap_tiers or default_tiers)[i % len(cap_tiers or default_tiers)]
        obs.append(make_observation(
            f"DEC_{i}", -0.5, sector=sector, market_cap_tier=cap_tier,
        ))

    for i in range(n_unchanged):
        obs.append(make_observation(f"UNC_{i}", 0.0))

    return UniverseSnapshot(
        universe_id=universe_id,
        bar_index=bar_index,
        timestamp=time.time(),
        observations=obs,
    )


def make_bull_universe(
    n: int = 100, universe_id: str = "TEST", bar_index: int = 0
) -> UniverseSnapshot:
    """70% advancing."""
    return make_universe(
        int(n * 0.70), int(n * 0.20), int(n * 0.10),
        universe_id=universe_id, bar_index=bar_index,
    )


def make_bear_universe(
    n: int = 100, universe_id: str = "TEST", bar_index: int = 0
) -> UniverseSnapshot:
    """70% declining."""
    return make_universe(
        int(n * 0.20), int(n * 0.70), int(n * 0.10),
        universe_id=universe_id, bar_index=bar_index,
    )


def make_mixed_universe(
    n: int = 100, universe_id: str = "TEST", bar_index: int = 0
) -> UniverseSnapshot:
    """~50/50."""
    half = n // 2
    return make_universe(half, n - half, universe_id=universe_id, bar_index=bar_index)


def make_multi_sector_universe(
    sectors: List[str],
    adv_pcts: List[float],
    n_per_sector: int = 20,
    universe_id: str = "TEST",
    bar_index: int = 0,
) -> UniverseSnapshot:
    obs: List[SecurityObservation] = []
    for sector, pct in zip(sectors, adv_pcts):
        n_adv = int(n_per_sector * pct)
        n_dec = n_per_sector - n_adv
        for i in range(n_adv):
            obs.append(make_observation(f"{sector}_ADV_{i}", 0.5, sector=sector))
        for i in range(n_dec):
            obs.append(make_observation(f"{sector}_DEC_{i}", -0.5, sector=sector))
    return UniverseSnapshot(
        universe_id=universe_id,
        bar_index=bar_index,
        timestamp=time.time(),
        observations=obs,
    )


# ── Fixtures ───────────────────────────────────────────────────────────────

@pytest.fixture
def bull_universe():
    return make_bull_universe()


@pytest.fixture
def bear_universe():
    return make_bear_universe()


@pytest.fixture
def mixed_universe():
    return make_mixed_universe()
