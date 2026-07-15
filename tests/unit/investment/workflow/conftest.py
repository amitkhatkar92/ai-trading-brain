"""tests/unit/investment/workflow/conftest.py
Shared fixtures for the Institutional Investment Workflow test suite.
"""
from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

import pytest

from iios.investment.models.investment_request import InvestmentRequest
from iios.investment.investment_constants import (
    AssetClass, InvestmentObjective, RiskProfile, TimeHorizon,
)
from iios.investment.workflow.workflow_context import WorkflowEngines, WorkflowParameters
from iios.investment.workflow.workflow_events import WorkflowEvent, WorkflowEventPublisher
from iios.investment.workflow.workflow_history import WorkflowHistory
from iios.investment.workflow.workflow_state import WorkflowState
from iios.investment.workflow.workflow_statistics import WorkflowStatistics
from iios.investment.workflow.workflow_types import WorkflowStage


# ── Minimal snapshot stubs ────────────────────────────────────────────────────

class _MarketSnap:
    snapshot_id   = "mkt-snap-001"
    quality_score = 0.82
    overall_score = 82.0

    def to_dict(self): return {"snapshot_id": self.snapshot_id}


class _CompanySnap:
    snapshot_id   = "cmp-snap-001"
    overall_score = 78.0
    quality_score = 0.78

    def to_dict(self): return {"snapshot_id": self.snapshot_id}


class _StrategySnap:
    snapshot_id    = "str-snap-001"
    strategy_id    = "STRAT-TEST"
    quality_score  = 0.75
    intelligence_score = 75.0

    def to_dict(self): return {"snapshot_id": self.snapshot_id}


class _DecisionSnap:
    snapshot_id   = "dec-snap-001"
    decision_id   = "dec-snap-001"
    quality_score = 0.80

    def to_dict(self): return {"snapshot_id": self.snapshot_id}


class _PortfolioSnap:
    snapshot_id   = "prt-snap-001"
    quality_score = 0.85
    is_ready      = True

    def to_dict(self): return {"snapshot_id": self.snapshot_id}


# ── Engine mocks ─────────────────────────────────────────────────────────────

def _make_market_engine() -> MagicMock:
    eng = MagicMock()
    bundle_mock = MagicMock()
    eng.make_bundle.return_value = bundle_mock
    eng.update.return_value = _MarketSnap()
    return eng


def _make_company_engine() -> MagicMock:
    eng = MagicMock()
    eng.integrate.return_value  = _CompanySnap()
    eng.update.return_value     = _CompanySnap()
    return eng


def _make_strategy_engine() -> MagicMock:
    eng = MagicMock()
    eng.submit_update_sync.return_value = None
    eng.get_snapshot_sync.return_value  = _StrategySnap()
    return eng


def _make_decision_engine() -> MagicMock:
    eng = MagicMock()
    eng.start.return_value          = None
    eng.stop.return_value           = None
    eng.integrate_sync.return_value = _DecisionSnap()
    return eng


def _make_portfolio_engine() -> MagicMock:
    eng = MagicMock()
    eng.start.return_value    = None
    eng.stop.return_value     = None
    eng.receive.return_value  = MagicMock()
    eng.integrate.return_value = _PortfolioSnap()
    return eng


def make_engines(
    *,
    market_snap:   Any = None,
    company_snap:  Any = None,
    strategy_snap: Any = None,
    decision_snap: Any = None,
    portfolio_snap: Any = None,
) -> WorkflowEngines:
    me = _make_market_engine()
    if market_snap is not None:
        me.update.return_value = market_snap

    ce = _make_company_engine()
    if company_snap is not None:
        ce.integrate.return_value = company_snap

    se = _make_strategy_engine()
    if strategy_snap is not None:
        se.get_snapshot_sync.return_value = strategy_snap
    elif strategy_snap is False:
        se.get_snapshot_sync.return_value = None

    de = _make_decision_engine()
    if decision_snap is not None:
        de.integrate_sync.return_value = decision_snap

    pe = _make_portfolio_engine()
    if portfolio_snap is not None:
        pe.integrate.return_value = portfolio_snap

    return WorkflowEngines(
        market_engine   = me,
        company_engine  = ce,
        strategy_engine = se,
        decision_engine = de,
        portfolio_engine = pe,
    )


# ── Pytest fixtures ────────────────────────────────────────────────────────────

@pytest.fixture
def engines() -> WorkflowEngines:
    return make_engines()


@pytest.fixture
def params() -> WorkflowParameters:
    return WorkflowParameters(max_retries=0, retry_delay_sec=0.0)


@pytest.fixture
def request_obj() -> InvestmentRequest:
    return InvestmentRequest(
        request_id    = str(uuid.uuid4()),
        asset_class   = AssetClass.EQUITY,
        symbols       = ["RELIANCE"],
        objective     = InvestmentObjective.GROWTH,
        time_horizon  = TimeHorizon.MEDIUM_TERM,
        risk_profile  = RiskProfile.MODERATE,
        market        = "NSE",
        country       = "IN",
        metadata      = {},
    )


@pytest.fixture
def events() -> List[WorkflowEvent]:
    captured: List[WorkflowEvent] = []
    return captured


@pytest.fixture
def event_publisher(events) -> WorkflowEventPublisher:
    pub = WorkflowEventPublisher()
    pub.register(lambda e: events.append(e))
    return pub
