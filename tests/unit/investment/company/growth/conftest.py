"""tests/unit/investment/company/growth/conftest.py
Shared fixtures for Growth Intelligence Engine tests.
"""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock


# ── FinancialSnapshot mock ──────────────────────────────────────────────────────

@pytest.fixture
def mock_financial_snapshot():
    snap = MagicMock()
    snap.revenue = 1_000_000.0

    cf = MagicMock()
    cf.free_cash_flow      = 120_000.0
    cf.operating_cash_flow = 180_000.0
    snap.cashflow_metrics  = cf

    im = MagicMock()
    im.net_income     = 80_000.0
    snap.income_metrics = im

    snap.ratios = {"ebitda": 150_000.0}
    return snap


@pytest.fixture
def mock_financial_snapshot_no_fcf():
    snap = MagicMock()
    snap.revenue = 500_000.0
    cf = MagicMock()
    cf.free_cash_flow      = None
    cf.operating_cash_flow = None
    snap.cashflow_metrics  = cf
    im = MagicMock()
    im.net_income = 30_000.0
    snap.income_metrics = im
    snap.ratios = {}
    return snap


# ── EarningsSnapshot mock ───────────────────────────────────────────────────────

@pytest.fixture
def mock_earnings_snapshot():
    snap = MagicMock()
    snap.history_depth = 7

    trend = MagicMock()
    trend.cagr_eps          = 0.18
    trend.eps_direction     = "improving"
    trend.revenue_direction = "improving"
    snap.trend = trend

    prof = MagicMock()
    prof.avg_net_margin   = 0.10
    prof.net_margin       = 0.13
    prof.avg_gross_margin = 0.35
    prof.avg_fcf_margin   = 0.11
    prof.avg_roe          = 0.16
    prof.roe              = 0.18
    prof.avg_roic         = 0.14
    prof.roic             = 0.16
    snap.profitability = prof

    risk = MagicMock()
    risk.eps_volatility           = 0.20
    risk.revenue_volatility       = 0.15
    risk.margin_volatility        = 0.10
    risk.earnings_stability_score = 75.0
    risk.is_cyclical              = False
    risk.loss_rate                = 0.0
    snap.risk = risk

    qual = MagicMock()
    qual.consistency_score = 78.0
    qual.overall_score     = 74.0
    snap.quality = qual

    return snap


@pytest.fixture
def mock_earnings_snapshot_minimal():
    """Minimal EarningsSnapshot — only history_depth and bare trend."""
    snap = MagicMock()
    snap.history_depth = 2

    trend = MagicMock()
    trend.cagr_eps          = None
    trend.eps_direction     = None
    trend.revenue_direction = None
    snap.trend = trend

    prof = MagicMock()
    prof.avg_net_margin   = None
    prof.net_margin       = None
    prof.avg_gross_margin = None
    prof.avg_fcf_margin   = None
    prof.avg_roe          = None
    prof.roe              = None
    prof.avg_roic         = None
    prof.roic             = None
    snap.profitability = prof

    risk = MagicMock()
    risk.eps_volatility           = None
    risk.revenue_volatility       = None
    risk.margin_volatility        = None
    risk.earnings_stability_score = None
    risk.is_cyclical              = None
    risk.loss_rate                = None
    snap.risk = risk

    qual = MagicMock()
    qual.consistency_score = None
    qual.overall_score     = None
    snap.quality = qual

    return snap


# ── BusinessQualitySnapshot mock ───────────────────────────────────────────────

@pytest.fixture
def mock_business_quality():
    bq = MagicMock()

    moat = MagicMock()
    moat.moat_score          = 72.0
    moat.avg_roic            = 0.16
    moat.detected_moat_types = ["switching_costs", "network_effects"]
    bq.moat = moat

    ops = MagicMock()
    ops.operational_quality_score = 70.0
    bq.operational = ops

    res = MagicMock()
    res.resilience_score = 65.0
    bq.resilience = res

    return bq


@pytest.fixture
def mock_business_quality_minimal():
    bq = MagicMock()
    moat = MagicMock()
    moat.moat_score          = None
    moat.avg_roic            = None
    moat.detected_moat_types = []
    bq.moat = moat
    ops = MagicMock()
    ops.operational_quality_score = None
    bq.operational = ops
    res = MagicMock()
    res.resilience_score = None
    bq.resilience = res
    return bq
