"""tests/unit/investment/market/sector_rotation/conftest.py
Shared fixtures for all sector rotation tests.
"""
from __future__ import annotations

import time
from typing import List

import pytest

from iios.investment.market.sector_rotation.models import (
    MarketSnapshot,
    SecurityData,
)
from iios.investment.market.sector_rotation.sector_taxonomy import SectorTaxonomy


def _make_security(
    symbol: str,
    sector: str,
    industry: str,
    return_pct: float = 0.01,
    market_cap: float = 10.0,
    volume: float = 1_000_000,
    avg_volume_20d: float = 800_000,
    price: float = 100.0,
) -> SecurityData:
    return SecurityData(
        symbol=symbol,
        return_pct=return_pct,
        sector=sector,
        industry=industry,
        market_cap=market_cap,
        volume=volume,
        avg_volume_20d=avg_volume_20d,
        price=price,
        timestamp=time.time(),
    )


def _make_gics_snapshot(
    bar_index: int = 1,
    benchmark_return: float = 0.005,
    it_return: float = 0.02,
    fin_return: float = -0.01,
    hc_return: float = 0.005,
    bench_ts: float = 0.0,
) -> MarketSnapshot:
    ts = bench_ts or time.time()
    securities: List[SecurityData] = [
        # IT
        _make_security("AAPL",  "Information Technology", "Software",       it_return,  50.0),
        _make_security("MSFT",  "Information Technology", "Software",       it_return,  45.0),
        _make_security("NVDA",  "Information Technology", "Semiconductors", it_return,  30.0),
        # Financials
        _make_security("JPM",   "Financials", "Banks",               fin_return, 40.0),
        _make_security("BAC",   "Financials", "Banks",               fin_return, 30.0),
        _make_security("GS",    "Financials", "Capital Markets",     fin_return, 25.0),
        # Health Care
        _make_security("JNJ",   "Health Care", "Pharmaceuticals",    hc_return,  20.0),
        _make_security("PFE",   "Health Care", "Pharmaceuticals",    hc_return,  18.0),
        _make_security("UNH",   "Health Care", "Health Care Services", hc_return, 22.0),
    ]
    return MarketSnapshot(
        bar_index=bar_index,
        timestamp=ts,
        securities=securities,
        benchmark_return=benchmark_return,
        taxonomy="GICS",
    )


@pytest.fixture
def taxonomy() -> SectorTaxonomy:
    return SectorTaxonomy(taxonomy_type="GICS")


@pytest.fixture
def single_snapshot() -> MarketSnapshot:
    return _make_gics_snapshot()


@pytest.fixture
def multi_snapshot_series() -> List[MarketSnapshot]:
    """20-bar series; IT outperforms in first half, Financials in second half."""
    snaps = []
    for i in range(1, 21):
        it_ret  = 0.03  if i <= 10 else -0.01
        fin_ret = -0.01 if i <= 10 else  0.03
        snaps.append(
            _make_gics_snapshot(
                bar_index=i,
                it_return=it_ret,
                fin_return=fin_ret,
                bench_ts=float(i),
            )
        )
    return snaps


@pytest.fixture
def make_security():
    return _make_security


@pytest.fixture
def make_snapshot():
    return _make_gics_snapshot
