"""tests/unit/investment/company/integration/conftest.py
Shared fixtures for Company Intelligence Integration Engine tests.
"""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock


# ── Financial snapshot ────────────────────────────────────────────────────────

@pytest.fixture
def mock_financial():
    snap = MagicMock()
    snap.quality_score = 72.0
    snap.ratios = {"dividend_yield": 0.025, "dividend_payout_ratio": 0.30}
    cf = MagicMock(); cf.free_cash_flow = 120_000; cf.operating_cash_flow = 180_000
    snap.cashflow_metrics = cf
    bs = MagicMock(); bs.total_debt = 150_000; bs.cash_and_equivalents = 80_000
    snap.balance_sheet_metrics = bs
    im = MagicMock(); im.net_income = 80_000
    snap.income_metrics = im
    return snap


@pytest.fixture
def weak_financial():
    snap = MagicMock()
    snap.quality_score = 22.0
    snap.ratios = {}
    cf = MagicMock(); cf.free_cash_flow = -50_000; cf.operating_cash_flow = -20_000
    snap.cashflow_metrics = cf
    bs = MagicMock(); bs.total_debt = 800_000; bs.cash_and_equivalents = 10_000
    snap.balance_sheet_metrics = bs
    im = MagicMock(); im.net_income = -30_000
    snap.income_metrics = im
    return snap


# ── Earnings snapshot ─────────────────────────────────────────────────────────

@pytest.fixture
def mock_earnings():
    snap = MagicMock()
    qual = MagicMock(); qual.overall_score = 75.0
    snap.quality = qual
    snap.overall_score = 75.0
    snap.is_profitable = True
    prof = MagicMock(); prof.avg_roic = 0.18; prof.roic = 0.18
    snap.profitability = prof
    trend = MagicMock(); trend.cagr_eps = 0.15; trend.cagr_revenue = 0.12
    snap.trend = trend
    risk = MagicMock(); risk.is_cyclical = False
    snap.risk = risk
    return snap


@pytest.fixture
def weak_earnings():
    snap = MagicMock()
    qual = MagicMock(); qual.overall_score = 22.0
    snap.quality = qual
    snap.overall_score = 22.0
    snap.is_profitable = False
    prof = MagicMock(); prof.avg_roic = 0.02; prof.roic = 0.02
    snap.profitability = prof
    trend = MagicMock(); trend.cagr_eps = -0.10; trend.cagr_revenue = -0.05
    snap.trend = trend
    risk = MagicMock(); risk.is_cyclical = True
    snap.risk = risk
    return snap


# ── Business quality snapshot ─────────────────────────────────────────────────

@pytest.fixture
def mock_bq():
    snap = MagicMock()
    snap.overall_score = 72.0
    moat = MagicMock(); moat.moat_score = 72.0; moat.avg_roic = 0.18
    moat.detected_moat_types = ["switching_costs"]
    snap.moat = moat
    ops = MagicMock(); ops.operational_quality_score = 70.0
    snap.operational = ops
    res = MagicMock(); res.resilience_score = 68.0
    snap.resilience = res
    return snap


@pytest.fixture
def weak_bq():
    snap = MagicMock()
    snap.overall_score = 22.0
    moat = MagicMock(); moat.moat_score = 18.0; moat.avg_roic = 0.04
    moat.detected_moat_types = []
    snap.moat = moat
    ops = MagicMock(); ops.operational_quality_score = 25.0
    snap.operational = ops
    res = MagicMock(); res.resilience_score = 22.0
    snap.resilience = res
    return snap


# ── Valuation snapshot ────────────────────────────────────────────────────────

@pytest.fixture
def mock_valuation():
    snap = MagicMock()
    vs = MagicMock(); vs.overall_score = 65.0
    snap.valuation_score = vs
    snap.is_undervalued = True; snap.is_overvalued = False
    mos = MagicMock(); mos.margin_of_safety_pct = 20.0
    snap.mos = mos
    return snap


@pytest.fixture
def overvalued_valuation():
    snap = MagicMock()
    vs = MagicMock(); vs.overall_score = 22.0
    snap.valuation_score = vs
    snap.is_undervalued = False; snap.is_overvalued = True
    mos = MagicMock(); mos.margin_of_safety_pct = -35.0
    snap.mos = mos
    return snap


# ── Growth snapshot ───────────────────────────────────────────────────────────

@pytest.fixture
def mock_growth():
    snap = MagicMock()
    gs = MagicMock(); gs.overall_score = 70.0; gs.label = "good"
    snap.growth_score = gs
    snap.overall_growth_score = 70.0
    snap.is_growing = True
    return snap


@pytest.fixture
def weak_growth():
    snap = MagicMock()
    gs = MagicMock(); gs.overall_score = 22.0; gs.label = "poor"
    snap.growth_score = gs
    snap.overall_growth_score = 22.0
    snap.is_growing = False
    return snap


# ── Management snapshot ───────────────────────────────────────────────────────

@pytest.fixture
def mock_management():
    snap = MagicMock()
    ms = MagicMock(); ms.overall_score = 70.0; ms.label = "good"
    snap.management_score = ms
    snap.overall_management_score = 70.0
    gr = MagicMock(); gr.overall_risk_score = 25.0
    snap.governance_risk = gr
    snap.flags = []
    return snap


@pytest.fixture
def high_risk_management():
    snap = MagicMock()
    ms = MagicMock(); ms.overall_score = 72.0; ms.label = "good"
    snap.management_score = ms
    snap.overall_management_score = 72.0
    gr = MagicMock(); gr.overall_risk_score = 80.0
    snap.governance_risk = gr
    snap.flags = ["RELATED_PARTY_TRANSACTIONS"]
    return snap


# ── Ownership snapshot ────────────────────────────────────────────────────────

@pytest.fixture
def mock_ownership():
    snap = MagicMock()
    snap.overall_ownership_score = 68.0
    snap.promoter_pledge_pct = 5.0
    risk = MagicMock(); risk.overall_risk_score = 22.0; risk.alerts = []
    snap.ownership_risk = risk
    return snap


@pytest.fixture
def risky_ownership():
    snap = MagicMock()
    snap.overall_ownership_score = 22.0
    snap.promoter_pledge_pct = 68.0
    risk = MagicMock(); risk.overall_risk_score = 80.0
    risk.alerts = ["HIGH_PROMOTER_PLEDGE"]
    snap.ownership_risk = risk
    return snap


# ── Opportunity snapshot ──────────────────────────────────────────────────────

@pytest.fixture
def mock_opportunity():
    snap = MagicMock()
    snap.overall_score = 70.0
    cat = MagicMock(); cat.value = "compounder"
    snap.primary_category = cat
    lc = MagicMock(); lc.value = "high_conviction"
    snap.lifecycle = lc
    snap.confidence = 0.72
    thesis = MagicMock()
    thesis.key_catalysts = ["Market expansion", "Margin improvement"]
    snap.thesis = thesis
    return snap
