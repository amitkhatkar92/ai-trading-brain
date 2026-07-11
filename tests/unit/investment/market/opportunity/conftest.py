"""tests/unit/investment/market/opportunity/conftest.py"""
from __future__ import annotations

import time
from typing import List

import pytest

from iios.investment.market.opportunity.models import (
    AssetObservation,
    IntelligenceContext,
    Opportunity,
    OpportunityCategory,
    OpportunityLifecycleStage,
    OpportunityPriority,
)


def _ctx(
    trend: float = 65.0,
    rs: float = 70.0,
    vol_ratio: float = 1.5,
    sector_rs: float = 65.0,
    risk: float = 60.0,
    ret1: float = 0.01,
    ret20: float = 0.06,
    breadth: float = 0.65,
    volatility_pct: float = 0.3,
    sector_stage: str = "leading",
) -> IntelligenceContext:
    return IntelligenceContext(
        market_regime="bull",
        trend_stage="up",
        trend_strength=trend,
        rs_vs_market=rs,
        volume_ratio=vol_ratio,
        liquidity_score=70.0,
        sector_rs_score=sector_rs,
        sector_momentum=65.0,
        risk_score=risk,
        return_1bar=ret1,
        return_20bar=ret20,
        breadth_score=65.0,
        above_ma20_pct=breadth,
        volatility_percentile=volatility_pct,
        sector_stage=sector_stage,
        fundamental_score=60.0,
    )


def _obs(
    symbol: str = "AAPL",
    sector: str = "Information Technology",
    industry: str = "Software",
    bar_index: int = 1,
    **ctx_kwargs,
) -> AssetObservation:
    return AssetObservation(
        symbol=symbol,
        sector=sector,
        industry=industry,
        bar_index=bar_index,
        timestamp=float(bar_index),
        intelligence=_ctx(**ctx_kwargs),
    )


def _weak_obs(symbol: str, bar_index: int = 1) -> AssetObservation:
    return _obs(
        symbol=symbol, bar_index=bar_index,
        trend=25.0, rs=25.0, vol_ratio=0.8,
        sector_rs=30.0, risk=30.0, ret1=-0.02, ret20=-0.10,
    )


def _strong_obs(symbol: str, bar_index: int = 1) -> AssetObservation:
    return _obs(
        symbol=symbol, bar_index=bar_index,
        trend=80.0, rs=85.0, vol_ratio=2.0,
        sector_rs=80.0, risk=75.0, ret1=0.03, ret20=0.12,
    )


@pytest.fixture
def strong_obs():
    return _strong_obs("AAPL")


@pytest.fixture
def weak_obs():
    return _weak_obs("LAGGARD")


@pytest.fixture
def obs_batch() -> List[AssetObservation]:
    return [
        _strong_obs("AAPL", 1),
        _strong_obs("MSFT", 1),
        _obs("GOOG", bar_index=1, trend=60.0, rs=65.0, vol_ratio=1.6),
        _obs("JNJ",  "Health Care", "Pharmaceuticals", bar_index=1,
             trend=55.0, rs=58.0, vol_ratio=0.9, ret1=0.005, ret20=0.02),
        _weak_obs("LAGGARD", 1),
    ]


@pytest.fixture
def make_obs():
    return _obs


@pytest.fixture
def make_strong():
    return _strong_obs


@pytest.fixture
def make_weak():
    return _weak_obs
