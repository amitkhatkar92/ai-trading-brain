"""tests/unit/investment/company/governance/conftest.py
Shared fixtures for Management & Governance Intelligence Engine tests.
"""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock


# ── FinancialSnapshot mock ──────────────────────────────────────────────────────

@pytest.fixture
def mock_financial_snapshot():
    snap = MagicMock()
    snap.revenue      = 1_000_000.0
    snap.total_equity = 500_000.0

    cf = MagicMock()
    cf.free_cash_flow      = 120_000.0
    cf.operating_cash_flow = 180_000.0
    snap.cashflow_metrics  = cf

    im = MagicMock()
    im.net_income = 80_000.0
    snap.income_metrics = im

    bs = MagicMock()
    bs.total_debt = 250_000.0
    snap.balance_sheet_metrics = bs

    snap.ratios = {
        "dividend_per_share":    12.5,
        "dividend_payout_ratio": 0.30,
    }
    return snap


@pytest.fixture
def mock_financial_snapshot_minimal():
    snap = MagicMock()
    snap.revenue      = None
    snap.total_equity = None
    cf = MagicMock()
    cf.free_cash_flow      = None
    cf.operating_cash_flow = None
    snap.cashflow_metrics  = cf
    im = MagicMock()
    im.net_income = None
    snap.income_metrics = im
    bs = MagicMock()
    bs.total_debt = None
    snap.balance_sheet_metrics = bs
    snap.ratios = {}
    return snap


# ── EarningsSnapshot mock ───────────────────────────────────────────────────────

@pytest.fixture
def mock_earnings_snapshot():
    snap = MagicMock()
    snap.history_depth = 8

    trend = MagicMock()
    trend.cagr_eps     = 0.18
    trend.cagr_revenue = 0.14
    snap.trend = trend

    prof = MagicMock()
    prof.avg_roic        = 0.18
    prof.avg_roe         = 0.20
    prof.net_margin      = 0.12
    prof.avg_net_margin  = 0.10
    prof.fcf_margin      = 0.12
    snap.profitability = prof

    qual = MagicMock()
    qual.overall_score       = 78.0
    qual.consistency_score   = 80.0
    qual.avg_ocf_to_ni       = 1.10
    qual.avg_accruals_ratio  = 0.04
    snap.quality = qual

    risk = MagicMock()
    risk.earnings_stability_score = 76.0
    risk.is_cyclical              = False
    snap.risk = risk

    return snap


@pytest.fixture
def mock_earnings_snapshot_minimal():
    snap = MagicMock()
    snap.history_depth = 0

    trend = MagicMock()
    trend.cagr_eps     = None
    trend.cagr_revenue = None
    snap.trend = trend

    prof = MagicMock()
    prof.avg_roic       = None
    prof.avg_roe        = None
    prof.net_margin     = None
    prof.avg_net_margin = None
    prof.fcf_margin     = None
    snap.profitability = prof

    qual = MagicMock()
    qual.overall_score      = None
    qual.consistency_score  = None
    qual.avg_ocf_to_ni      = None
    qual.avg_accruals_ratio = None
    snap.quality = qual

    risk = MagicMock()
    risk.earnings_stability_score = None
    risk.is_cyclical              = None
    snap.risk = risk

    return snap


# ── BusinessQualitySnapshot mock ───────────────────────────────────────────────

@pytest.fixture
def mock_business_quality():
    bq = MagicMock()

    moat = MagicMock()
    moat.moat_score          = 72.0
    moat.avg_roic            = 0.18
    moat.detected_moat_types = ["switching_costs"]
    bq.moat = moat

    ops = MagicMock()
    ops.operational_quality_score = 70.0
    bq.operational = ops

    res = MagicMock()
    res.resilience_score = 68.0
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


# ── GrowthSnapshot mock ─────────────────────────────────────────────────────────

@pytest.fixture
def mock_growth_snapshot():
    gs = MagicMock()
    score = MagicMock()
    score.overall_score = 72.0
    gs.growth_score = score
    sus = MagicMock()
    sus.sustainability_score = 68.0
    gs.sustainability = sus
    return gs


# ── Board/Executive info dicts ──────────────────────────────────────────────────

@pytest.fixture
def good_board_info():
    return {
        "total_directors":           10,
        "independent_directors":      7,
        "promoter_directors":          2,
        "female_directors":            3,
        "avg_director_tenure_years":   6.0,
        "has_audit_committee":        True,
        "has_remuneration_committee": True,
        "has_risk_committee":         True,
        "has_nomination_committee":   True,
        "has_esg_committee":          False,
        "audit_committee_all_independent": True,
        "ceo_tenure_years":           8.0,
        "ceo_is_founder":            False,
        "ceo_chairman_same":         False,
        "is_family_controlled":      False,
        "promoter_holding_pct":       0.30,
        "governance_incidents":      [],
        "regulatory_actions":        [],
        "reporting_restatements":     0,
    }


@pytest.fixture
def weak_board_info():
    return {
        "total_directors":           5,
        "independent_directors":      1,
        "promoter_directors":         4,
        "female_directors":           0,
        "avg_director_tenure_years":  20.0,
        "has_audit_committee":        False,
        "has_remuneration_committee": False,
        "has_risk_committee":         False,
        "has_nomination_committee":   False,
        "has_esg_committee":          False,
        "audit_committee_all_independent": False,
        "ceo_tenure_years":           25.0,
        "ceo_is_founder":            True,
        "ceo_chairman_same":         True,
        "is_family_controlled":      True,
        "promoter_holding_pct":       0.75,
        "governance_incidents":      ["accounting_fraud_2018", "regulatory_penalty_2021"],
        "regulatory_actions":        ["sebi_action_2021"],
        "reporting_restatements":     2,
    }


@pytest.fixture
def good_executive_info():
    return {
        "ceo_tenure_years":        8.0,
        "cfo_tenure_years":        6.0,
        "executive_team_tenure_avg": 5.5,
        "leadership_changes_3y":   0,
        "ceo_is_founder":          False,
        "ceo_chairman_same":       False,
    }
