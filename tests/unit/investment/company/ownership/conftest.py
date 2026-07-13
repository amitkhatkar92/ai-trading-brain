"""tests/unit/investment/company/ownership/conftest.py
Shared fixtures for Ownership Intelligence Engine tests.
"""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock


# ── FinancialSnapshot mock ──────────────────────────────────────────────────────

@pytest.fixture
def mock_financial():
    snap = MagicMock()
    snap.revenue      = 1_000_000.0
    snap.total_equity = 500_000.0
    snap.total_assets = 900_000.0
    cf = MagicMock()
    cf.free_cash_flow      = 120_000.0
    cf.operating_cash_flow = 180_000.0
    cf.capex               = -60_000.0
    snap.cashflow_metrics  = cf
    im = MagicMock(); im.net_income = 80_000.0; snap.income_metrics = im
    bs = MagicMock()
    bs.total_debt            = 150_000.0
    bs.cash_and_equivalents  = 80_000.0
    snap.balance_sheet_metrics = bs
    snap.ratios = {
        "dividend_per_share":    10.0,
        "dividend_payout_ratio": 0.30,
    }
    return snap


@pytest.fixture
def mock_financial_minimal():
    snap = MagicMock()
    snap.revenue = None; snap.total_equity = None; snap.total_assets = None
    cf = MagicMock(); cf.free_cash_flow = None; cf.operating_cash_flow = None; cf.capex = None
    snap.cashflow_metrics = cf
    im = MagicMock(); im.net_income = None; snap.income_metrics = im
    bs = MagicMock(); bs.total_debt = None; bs.cash_and_equivalents = None
    snap.balance_sheet_metrics = bs
    snap.ratios = {}
    return snap


# ── EarningsSnapshot mock ───────────────────────────────────────────────────────

@pytest.fixture
def mock_earnings():
    snap = MagicMock()
    snap.history_depth = 8
    trend = MagicMock(); trend.cagr_eps = 0.18; trend.cagr_revenue = 0.14; snap.trend = trend
    prof = MagicMock()
    prof.avg_roic = 0.18; prof.avg_roe = 0.20
    prof.net_margin = 0.12; prof.avg_net_margin = 0.10; prof.fcf_margin = 0.12
    snap.profitability = prof
    qual = MagicMock()
    qual.overall_score = 78.0; qual.consistency_score = 80.0
    qual.avg_ocf_to_ni = 1.10; qual.avg_accruals_ratio = 0.04
    snap.quality = qual
    risk = MagicMock(); risk.earnings_stability_score = 76.0; risk.is_cyclical = False
    snap.risk = risk
    return snap


# ── BusinessQualitySnapshot mock ───────────────────────────────────────────────

@pytest.fixture
def mock_bq():
    bq = MagicMock()
    moat = MagicMock(); moat.moat_score = 72.0; moat.avg_roic = 0.18
    moat.detected_moat_types = ["switching_costs"]
    bq.moat = moat
    ops = MagicMock(); ops.operational_quality_score = 70.0; bq.operational = ops
    res = MagicMock(); res.resilience_score = 68.0; bq.resilience = res
    return bq


# ── GrowthSnapshot mock ─────────────────────────────────────────────────────────

@pytest.fixture
def mock_growth():
    gs = MagicMock()
    score = MagicMock(); score.overall_score = 72.0; gs.growth_score = score
    sus = MagicMock(); sus.sustainability_score = 68.0; gs.sustainability = sus
    return gs


# ── ManagementSnapshot mock ─────────────────────────────────────────────────────

@pytest.fixture
def mock_management():
    ms = MagicMock()
    mgmt_q = MagicMock(); mgmt_q.long_term_orientation_score = 75.0; ms.management_quality = mgmt_q
    gov = MagicMock(); gov.overall_governance_score = 70.0; ms.governance = gov
    cap = MagicMock(); cap.overall_capital_score = 68.0; ms.capital_allocation = cap
    gov_risk = MagicMock(); gov_risk.overall_risk_score = 30.0; ms.governance_risk = gov_risk
    exec_team = MagicMock()
    exec_team.is_family_controlled = False
    exec_team.ceo_chairman_same = False
    ms.executive_team = exec_team
    board = MagicMock(); board.independence_ratio = 0.70; ms.board = board
    return ms


# ── Ownership data dicts ────────────────────────────────────────────────────────

@pytest.fixture
def good_ownership_data():
    return {
        "promoter_holding_pct":           0.52,
        "institutional_holding_pct":       0.28,
        "retail_holding_pct":              0.12,
        "government_holding_pct":          0.03,
        "fii_holding_pct":                 0.12,
        "dii_holding_pct":                 0.10,
        "mutual_fund_holding_pct":         0.06,
        "free_float_pct":                  0.45,
        "top10_holder_pct":                0.65,
        "promoter_pledge_pct":             0.05,
        "promoter_holding_change_3m":      0.5,
        "promoter_holding_change_1y":      1.2,
        "institutional_holding_change_3m": 0.8,
        "total_shareholders":              250_000,
        "shares_outstanding":              1_000_000_000,
        "ownership_jurisdiction":          "IN",
    }


@pytest.fixture
def risky_ownership_data():
    return {
        "promoter_holding_pct":           0.75,
        "institutional_holding_pct":       0.08,
        "retail_holding_pct":              0.17,
        "free_float_pct":                  0.22,
        "top10_holder_pct":                0.85,
        "promoter_pledge_pct":             0.60,    # high pledge
        "promoter_holding_change_3m":     -3.0,     # selling
        "promoter_holding_change_1y":     -7.0,
        "total_shareholders":              50_000,
        "ownership_jurisdiction":          "IN",
    }


@pytest.fixture
def good_insider_data():
    return {
        "ceo_ownership_pct":         0.025,
        "cfo_ownership_pct":         0.010,
        "board_total_ownership_pct": 0.045,
        "insider_ownership_pct":     0.060,
        "esop_outstanding_pct":      0.020,
        "insider_buy_count_6m":      5,
        "insider_sell_count_6m":     1,
        "net_insider_buying_6m":     50_000,
    }


@pytest.fixture
def liquidating_insider_data():
    return {
        "ceo_ownership_pct":         0.001,
        "insider_buy_count_6m":      0,
        "insider_sell_count_6m":     8,
        "net_insider_buying_6m":     -500_000,
        "esop_outstanding_pct":      0.10,
    }
