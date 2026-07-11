"""tests/unit/investment/market/integration/conftest.py"""
from __future__ import annotations

from typing import Any, Dict, Optional

import pytest

from iios.investment.market.integration.models import (
    EnginePayload,
    EngineSource,
    IntelligenceBundle,
)


def _payload(
    name: str,
    source: EngineSource,
    data: Dict[str, Any],
    bar_index: int = 1,
) -> EnginePayload:
    return EnginePayload(
        engine_name=name,
        source=source,
        payload=data,
        bar_index=bar_index,
        timestamp=float(bar_index),
    )


def _full_bundle(
    bar_index: int = 1,
    regime: str = "bull",
    trend: str = "up",
    trend_strength: float = 70.0,
    volatility: str = "normal",
    breadth: str = "positive",
    correlation: str = "normal",
    liquidity: str = "normal",
    sector_phase: str = "expansion",
    opportunities: int = 5,
) -> IntelligenceBundle:
    bundle = IntelligenceBundle(bar_index=bar_index, timestamp=float(bar_index))
    bundle.add(_payload("market_regime",   EngineSource.MARKET_REGIME,
                         {"regime": regime}, bar_index))
    bundle.add(_payload("trend",           EngineSource.TREND,
                         {"trend_direction": trend, "trend_strength": trend_strength,
                          "trend_stage": "mature"}, bar_index))
    bundle.add(_payload("volatility",      EngineSource.VOLATILITY,
                         {"volatility_regime": volatility, "volatility_percentile": 40.0,
                          "vix_equivalent": 18.0}, bar_index))
    bundle.add(_payload("breadth",         EngineSource.BREADTH,
                         {"breadth_regime": breadth, "breadth_score": 65.0,
                          "advance_decline_ratio": 1.4}, bar_index))
    bundle.add(_payload("correlation",     EngineSource.CORRELATION,
                         {"correlation_regime": correlation,
                          "avg_correlation": 0.3}, bar_index))
    bundle.add(_payload("volume_liquidity", EngineSource.VOLUME_LIQUIDITY,
                         {"liquidity_regime": liquidity,
                          "liquidity_score": 65.0}, bar_index))
    bundle.add(_payload("sector_rotation", EngineSource.SECTOR_ROTATION,
                         {"sector_rotation_phase": sector_phase,
                          "leading_sectors": ["IT", "Consumer"],
                          "lagging_sectors":  ["Energy"]}, bar_index))
    bundle.add(_payload("opportunity",     EngineSource.OPPORTUNITY,
                         {"total_active": opportunities,
                          "top_opportunity_symbols": ["AAPL", "MSFT"],
                          "high_priority_count": 2}, bar_index))
    return bundle


def _crisis_bundle(bar_index: int = 1) -> IntelligenceBundle:
    return _full_bundle(
        bar_index=bar_index,
        regime="crisis",
        trend="down",
        trend_strength=75.0,
        volatility="extreme",
        breadth="negative",
        correlation="crisis",
        liquidity="crisis",
        opportunities=8,
    )


def _empty_bundle(bar_index: int = 1) -> IntelligenceBundle:
    return IntelligenceBundle(bar_index=bar_index, timestamp=float(bar_index))


@pytest.fixture
def full_bundle():
    return _full_bundle()


@pytest.fixture
def crisis_bundle():
    return _crisis_bundle()


@pytest.fixture
def empty_bundle():
    return _empty_bundle()


@pytest.fixture
def make_bundle():
    return _full_bundle


@pytest.fixture
def make_crisis():
    return _crisis_bundle
