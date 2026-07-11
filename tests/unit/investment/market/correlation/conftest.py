"""conftest.py — shared fixtures for correlation engine tests."""
from __future__ import annotations

import time
from typing import Dict, List, Optional

import numpy as np
import pytest

from iios.investment.market.correlation.models import (
    AssetClass,
    MultiAssetSnapshot,
    PriceObservation,
)


# ── Helpers ───────────────────────────────────────────────────────────────

def make_observation(
    symbol: str,
    return_pct: float,
    asset_class: str = AssetClass.EQUITY.value,
    sector: str = "Technology",
    price: float = 100.0,
) -> PriceObservation:
    return PriceObservation(
        symbol=symbol,
        return_pct=return_pct,
        asset_class=asset_class,
        sector=sector,
        price=price,
        timestamp=time.time(),
    )


def make_snapshot(
    returns: Dict[str, float],
    bar_index: int = 0,
    asset_classes: Optional[Dict[str, str]] = None,
) -> MultiAssetSnapshot:
    ac = asset_classes or {}
    obs = [
        make_observation(
            sym, ret,
            asset_class=ac.get(sym, AssetClass.EQUITY.value),
        )
        for sym, ret in returns.items()
    ]
    return MultiAssetSnapshot(
        bar_index=bar_index,
        timestamp=float(bar_index),
        observations=obs,
    )


def make_correlated_snapshots(
    n_bars: int,
    symbols: List[str],
    target_corr: float = 0.80,
    rng_seed: int = 42,
    base_return: float = 0.001,
) -> List[MultiAssetSnapshot]:
    """
    Generate n_bars snapshots with pairwise correlation ≈ target_corr.
    Uses a one-factor model: r_i = sqrt(rho)*F + sqrt(1-rho)*eps_i.
    """
    rng = np.random.default_rng(rng_seed)
    n   = len(symbols)
    rho = max(0.0, min(0.999, target_corr))

    # Common factor + idiosyncratic noise
    F   = rng.normal(base_return, 0.01, n_bars)
    eps = rng.normal(0, 0.01, (n, n_bars))
    returns = (rho ** 0.5) * F + ((1 - rho) ** 0.5) * eps  # (n, n_bars)

    snapshots = []
    for i in range(n_bars):
        r = {sym: float(returns[j, i]) for j, sym in enumerate(symbols)}
        snapshots.append(make_snapshot(r, bar_index=i))
    return snapshots


def make_anti_correlated_snapshots(
    n_bars: int,
    symbol_a: str = "A",
    symbol_b: str = "B",
    rng_seed: int = 42,
) -> List[MultiAssetSnapshot]:
    """
    Generate snapshots where A and B have strong negative correlation.
    """
    rng = np.random.default_rng(rng_seed)
    F   = rng.normal(0, 0.01, n_bars)
    eps = rng.normal(0, 0.003, (2, n_bars))
    ra  =  F + eps[0]
    rb  = -F + eps[1]
    snapshots = []
    for i in range(n_bars):
        r = {symbol_a: float(ra[i]), symbol_b: float(rb[i])}
        snapshots.append(make_snapshot(r, bar_index=i))
    return snapshots


def make_independent_snapshots(
    n_bars: int,
    symbols: List[str],
    rng_seed: int = 42,
) -> List[MultiAssetSnapshot]:
    """Generate completely independent (zero correlation) return series."""
    rng = np.random.default_rng(rng_seed)
    n   = len(symbols)
    returns = rng.normal(0, 0.01, (n, n_bars))
    snapshots = []
    for i in range(n_bars):
        r = {sym: float(returns[j, i]) for j, sym in enumerate(symbols)}
        snapshots.append(make_snapshot(r, bar_index=i))
    return snapshots


def make_multi_asset_snapshots(
    n_bars: int,
    rng_seed: int = 42,
) -> List[MultiAssetSnapshot]:
    """Generate snapshots for a mixed-asset universe for integration tests."""
    rng = np.random.default_rng(rng_seed)
    symbols = ["SPY", "QQQ", "IWM", "TLT", "GLD", "VIX_SYN", "DX", "USO"]
    asset_classes = {
        "SPY": AssetClass.INDEX.value,
        "QQQ": AssetClass.INDEX.value,
        "IWM": AssetClass.INDEX.value,
        "TLT": AssetClass.BOND.value,
        "GLD": AssetClass.PRECIOUS_METAL.value,
        "VIX_SYN": AssetClass.VOLATILITY.value,
        "DX":  AssetClass.CURRENCY.value,
        "USO": AssetClass.COMMODITY.value,
    }
    # Factor model: equity factor, safe-haven factor
    eq_factor   = rng.normal(0.001, 0.01, n_bars)
    safe_factor = -eq_factor + rng.normal(0, 0.005, n_bars)

    returns = {
        "SPY":     eq_factor   + rng.normal(0, 0.003, n_bars),
        "QQQ":     eq_factor   + rng.normal(0, 0.004, n_bars),
        "IWM":     eq_factor   + rng.normal(0, 0.006, n_bars),
        "TLT":     safe_factor + rng.normal(0, 0.005, n_bars),
        "GLD":     safe_factor * 0.7 + rng.normal(0, 0.005, n_bars),
        "VIX_SYN": safe_factor * 0.8 + rng.normal(0, 0.008, n_bars),
        "DX":      rng.normal(0, 0.003, n_bars),  # independent
        "USO":     eq_factor * 0.3 + rng.normal(0, 0.015, n_bars),
    }

    snapshots = []
    for i in range(n_bars):
        r = {sym: float(returns[sym][i]) for sym in symbols}
        snapshots.append(make_snapshot(r, bar_index=i, asset_classes=asset_classes))
    return snapshots


# ── Fixtures ──────────────────────────────────────────────────────────────

@pytest.fixture
def correlated_snapshots():
    return make_correlated_snapshots(80, ["A", "B", "C", "D"])


@pytest.fixture
def anti_correlated_snapshots():
    return make_anti_correlated_snapshots(80)


@pytest.fixture
def independent_snapshots():
    return make_independent_snapshots(80, ["X", "Y", "Z"])


@pytest.fixture
def multi_asset_snapshots():
    return make_multi_asset_snapshots(100)
