"""tests/unit/investment/portfolio/allocation/conftest.py

Shared fixtures for the Portfolio Allocation Engine test suite.
"""
from __future__ import annotations

import pytest
from dataclasses import dataclass, field
from typing import Any, Dict, Tuple
from iios.investment.portfolio.allocation.allocation_plan import AllocationRequest
from iios.investment.portfolio.allocation.allocation_types import AllocationMethod


# ---------------------------------------------------------------------------
# Minimal blueprint slot stub
# ---------------------------------------------------------------------------

@dataclass
class _Slot:
    symbol:            str   = "RELIA.NS"
    name:              str   = "Reliance"
    target_weight:     float = 0.10
    sector:            str   = "energy"
    industry:          str   = "oil_gas"
    asset_class:       Any   = "equity"
    conviction:        float = 0.7
    confidence:        float = 0.8
    risk_score:        float = 0.3
    recommendation_id: str   = "rec-1"
    source_decision_id:str   = "dec-1"
    slot_id:           str   = "slot-1"


@dataclass
class _Blueprint:
    blueprint_id: str                = "bp-test"
    portfolio_id: str                = "pf-test"
    version:      int                = 1
    slots:        Tuple[_Slot, ...]  = field(default_factory=tuple)


@pytest.fixture
def single_slot_blueprint():
    return _Blueprint(slots=(
        _Slot(symbol="RELIA.NS", target_weight=0.30),
    ))


@pytest.fixture
def multi_slot_blueprint():
    return _Blueprint(slots=(
        _Slot(symbol="RELIA.NS", target_weight=0.30, sector="energy",       conviction=0.8, confidence=0.85, risk_score=0.2),
        _Slot(symbol="TCS.NS",   target_weight=0.20, sector="it",           conviction=0.7, confidence=0.75, risk_score=0.3),
        _Slot(symbol="HDFCB.NS", target_weight=0.15, sector="financials",   conviction=0.6, confidence=0.70, risk_score=0.4),
        _Slot(symbol="INFY.NS",  target_weight=0.10, sector="it",           conviction=0.5, confidence=0.60, risk_score=0.5),
        _Slot(symbol="WIPRO.NS", target_weight=0.05, sector="it",           conviction=0.4, confidence=0.55, risk_score=0.6),
    ))


@pytest.fixture
def standard_request():
    return AllocationRequest(
        portfolio_id      = "pf-test",
        blueprint_id      = "bp-test",
        total_capital     = 1_000_000.0,
        currency          = "INR",
        cash_reserve_pct  = 0.05,
        method            = AllocationMethod.BLUEPRINT_WEIGHT,
        max_position_weight = 0.35,
        min_position_weight = 0.005,
        min_trade_size      = 100.0,
        allow_short         = False,
    )
