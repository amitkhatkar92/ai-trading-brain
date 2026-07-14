"""tests/unit/investment/strategy/integration/conftest.py
Shared fixtures for Integration Engine tests.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest

from iios.investment.strategy.integration.aggregation_state import (
    IntelligenceUpdate,
    StrategyAggregationState,
    make_update,
)
from iios.investment.strategy.integration.aggregation_engine import AggregationEngine
from iios.investment.strategy.integration.integration_constants import (
    IntelligenceSource,
    UpdateType,
)


# ---------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------

def _sid() -> str:
    return f"STRAT-{uuid.uuid4().hex[:6].upper()}"


def make_eval_update(
    strategy_id: str = None,
    score: float = 75.0,
    status: str = "active",
    confidence: float = 80.0,
) -> IntelligenceUpdate:
    return make_update(
        source=IntelligenceSource.EVALUATION,
        strategy_id=strategy_id or _sid(),
        payload={"score": score, "status": status, "headline": "Eval update"},
        confidence=confidence,
    )


def make_risk_update(
    strategy_id: str = None,
    risk_level: str = "medium",
    confidence: float = 75.0,
) -> IntelligenceUpdate:
    return make_update(
        source=IntelligenceSource.RISK,
        strategy_id=strategy_id or _sid(),
        payload={
            "risk_level": risk_level,
            "score": 60.0,
            "risk_flags": ["VaR elevated"],
        },
        confidence=confidence,
    )


def make_lifecycle_update(
    strategy_id: str = None,
    phase: str = "production",
    confidence: float = 90.0,
) -> IntelligenceUpdate:
    return make_update(
        source=IntelligenceSource.LIFECYCLE,
        strategy_id=strategy_id or _sid(),
        payload={"phase": phase, "status": "active"},
        confidence=confidence,
    )


def make_framework_update(
    strategy_id: str = None,
    confidence: float = 85.0,
) -> IntelligenceUpdate:
    return make_update(
        source=IntelligenceSource.STRATEGY_FRAMEWORK,
        strategy_id=strategy_id or _sid(),
        payload={"version": "2.0", "status": "active"},
        confidence=confidence,
    )


def make_full_state(sid: str = None) -> tuple:
    """Returns (sid, StrategyAggregationState) with all 4 required sources."""
    sid = sid or _sid()
    engine = AggregationEngine()
    for upd in [
        make_eval_update(sid),
        make_risk_update(sid),
        make_lifecycle_update(sid),
        make_framework_update(sid),
    ]:
        engine.apply(upd)
    return sid, engine.get_state(sid), engine


# ---------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------

@pytest.fixture
def strategy_id() -> str:
    return _sid()


@pytest.fixture
def agg_engine() -> AggregationEngine:
    return AggregationEngine()


@pytest.fixture
def full_state(strategy_id):
    """Populated StrategyAggregationState with 4 required sources."""
    sid, state, engine = make_full_state(strategy_id)
    return state, engine
