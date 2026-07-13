"""tests/unit/investment/company/opportunity/conftest.py
Shared fixtures for the Opportunity Engine test suite.
"""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock


# ── Financial Snapshot ────────────────────────────────────────────────────────

@pytest.fixture
def mock_financial():
    snap = MagicMock()
    snap.revenue = 1_000_000
    snap.total_equity = 500_000
    snap.total_assets = 900_000
    cf = MagicMock()
    cf.free_cash_flow = 120_000
    cf.operating_cash_flow = 180_000
    cf.capex = -60_000
    snap.cashflow_metrics = cf
    im = MagicMock()
    im.net_income = 80_000
    snap.income_metrics = im
    bs = MagicMock()
    bs.total_debt = 150_000
    bs.cash_and_equivalents = 80_000
    snap.balance_sheet_metrics = bs
    snap.ratios = {
        "dividend_per_share": 10.0,
        "dividend_payout_ratio": 0.30,
        "dividend_yield": 0.025,
    }
    return snap


@pytest.fixture
def weak_financial():
    snap = MagicMock()
    snap.revenue = 1_000_000
    snap.total_equity = 100_000
    snap.total_assets = 900_000
    cf = MagicMock()
    cf.free_cash_flow = -50_000
    cf.operating_cash_flow = -30_000
    cf.capex = -20_000
    snap.cashflow_metrics = cf
    im = MagicMock()
    im.net_income = -40_000
    snap.income_metrics = im
    bs = MagicMock()
    bs.total_debt = 800_000
    bs.cash_and_equivalents = 20_000
    snap.balance_sheet_metrics = bs
    snap.ratios = {}
    return snap


# ── Earnings Snapshot ─────────────────────────────────────────────────────────

@pytest.fixture
def mock_earnings():
    snap = MagicMock()
    snap.overall_score = 78.0
    snap.history_depth = 8
    snap.is_profitable = True
    prof = MagicMock()
    prof.avg_roic = 0.18
    prof.avg_roe = 0.20
    prof.net_margin = 0.12
    prof.avg_net_margin = 0.10
    prof.fcf_margin = 0.12
    snap.profitability = prof
    qual = MagicMock()
    qual.overall_score = 78.0
    qual.consistency_score = 80.0
    qual.avg_ocf_to_ni = 1.10
    snap.quality = qual
    trend = MagicMock()
    trend.cagr_eps = 0.15
    trend.cagr_revenue = 0.12
    snap.trend = trend
    risk_e = MagicMock()
    risk_e.earnings_stability_score = 76.0
    risk_e.is_cyclical = False
    snap.risk = risk_e
    return snap


@pytest.fixture
def weak_earnings():
    snap = MagicMock()
    snap.overall_score = 28.0
    snap.history_depth = 3
    snap.is_profitable = False
    prof = MagicMock()
    prof.avg_roic = 0.03
    prof.avg_roe = 0.02
    prof.net_margin = -0.04
    prof.avg_net_margin = -0.02
    prof.fcf_margin = -0.05
    snap.profitability = prof
    qual = MagicMock()
    qual.overall_score = 28.0
    qual.consistency_score = 30.0
    snap.quality = qual
    trend = MagicMock()
    trend.cagr_eps = -0.10
    trend.cagr_revenue = -0.05
    snap.trend = trend
    risk_e = MagicMock()
    risk_e.earnings_stability_score = 25.0
    risk_e.is_cyclical = True
    snap.risk = risk_e
    return snap


# ── Business Quality ──────────────────────────────────────────────────────────

@pytest.fixture
def mock_bq():
    bq = MagicMock()
    bq.overall_score = 72.0
    moat = MagicMock()
    moat.moat_score = 72.0
    moat.avg_roic = 0.18
    moat.detected_moat_types = ["switching_costs", "network_effects"]
    bq.moat = moat
    ops = MagicMock()
    ops.operational_quality_score = 70.0
    bq.operational = ops
    res = MagicMock()
    res.resilience_score = 68.0
    bq.resilience = res
    return bq


@pytest.fixture
def weak_bq():
    bq = MagicMock()
    bq.overall_score = 28.0
    moat = MagicMock()
    moat.moat_score = 22.0
    moat.avg_roic = 0.04
    moat.detected_moat_types = []
    bq.moat = moat
    ops = MagicMock()
    ops.operational_quality_score = 30.0
    bq.operational = ops
    res = MagicMock()
    res.resilience_score = 28.0
    bq.resilience = res
    return bq


# ── Valuation Snapshot ────────────────────────────────────────────────────────

@pytest.fixture
def mock_valuation():
    snap = MagicMock()
    vs = MagicMock()
    vs.overall_score = 65.0
    snap.valuation_score = vs
    mos = MagicMock()
    mos.margin_of_safety_pct = 20.0
    mos.band = "undervalued"
    snap.mos = mos
    snap.is_undervalued = True
    snap.is_overvalued = False
    snap.market_price = 100.0
    snap.market_cap = 10_000_000
    return snap


@pytest.fixture
def overvalued_valuation():
    snap = MagicMock()
    vs = MagicMock()
    vs.overall_score = 25.0
    snap.valuation_score = vs
    mos = MagicMock()
    mos.margin_of_safety_pct = -30.0
    mos.band = "overvalued"
    snap.mos = mos
    snap.is_undervalued = False
    snap.is_overvalued = True
    snap.market_price = 200.0
    snap.market_cap = 20_000_000
    return snap


# ── Growth Snapshot ───────────────────────────────────────────────────────────

@pytest.fixture
def mock_growth():
    snap = MagicMock()
    snap.overall_growth_score = 72.0
    gs = MagicMock()
    gs.overall_score = 72.0
    gs.label = "strong"
    snap.growth_score = gs
    snap.is_growing = True
    snap.is_accelerating = False
    snap.growth_label = "strong"
    return snap


@pytest.fixture
def weak_growth():
    snap = MagicMock()
    snap.overall_growth_score = 22.0
    gs = MagicMock()
    gs.overall_score = 22.0
    gs.label = "poor"
    snap.growth_score = gs
    snap.is_growing = False
    snap.is_accelerating = False
    return snap


# ── Management Snapshot ───────────────────────────────────────────────────────

@pytest.fixture
def mock_management():
    snap = MagicMock()
    snap.overall_management_score = 70.0
    ms = MagicMock()
    ms.overall_score = 70.0
    snap.management_score = ms
    gr = MagicMock()
    gr.overall_risk_score = 25.0
    snap.governance_risk = gr
    snap.flags = []
    return snap


# ── Ownership Snapshot ────────────────────────────────────────────────────────

@pytest.fixture
def mock_ownership():
    snap = MagicMock()
    snap.overall_ownership_score = 68.0
    snap.promoter_pledge_pct = 5.0
    risk = MagicMock()
    risk.overall_risk_score = 20.0
    risk.alerts = []
    snap.ownership_risk = risk
    return snap


@pytest.fixture
def risky_ownership():
    snap = MagicMock()
    snap.overall_ownership_score = 28.0
    snap.promoter_pledge_pct = 65.0
    risk = MagicMock()
    risk.overall_risk_score = 75.0
    risk.alerts = ["High promoter pledge ratio"]
    snap.ownership_risk = risk
    return snap
