"""tests/unit/investment/company/valuation/conftest.py
Shared fixtures for valuation engine tests.
"""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock


# ── Financial Snapshot ─────────────────────────────────────────────────────────

def make_financial_snapshot(
    total_assets:       float = 500_000.0,
    total_equity:       float = 200_000.0,
    revenue:            float = 300_000.0,
    free_cash_flow:     float = 30_000.0,
    operating_cash_flow: float = 40_000.0,
    net_income:         float = 25_000.0,
    ebitda:             float = 60_000.0,
    total_debt:         float = 80_000.0,
    cash:               float = 20_000.0,
    book_value_per_share: float = 200.0,
    dividend_per_share: float = 0.0,
    payout_ratio:       float = 0.0,
) -> MagicMock:
    fs = MagicMock()
    fs.total_assets  = total_assets
    fs.total_equity  = total_equity
    fs.revenue       = revenue

    cf = MagicMock()
    cf.free_cash_flow      = free_cash_flow
    cf.operating_cash_flow = operating_cash_flow
    cf.capex               = operating_cash_flow - free_cash_flow
    fs.cashflow_metrics = cf

    im = MagicMock()
    im.net_income = net_income
    fs.income_metrics = im

    bsm = MagicMock()
    bsm.total_debt            = total_debt
    bsm.cash_and_equivalents  = cash
    fs.balance_sheet_metrics = bsm

    fs.ratios = {
        "ebitda":                 ebitda,
        "dividend_per_share":     dividend_per_share,
        "dividend_payout_ratio":  payout_ratio,
    }

    return fs


def make_earnings_snapshot(
    roe:           float = 0.18,
    roic:          float = 0.15,
    net_margin:    float = 0.12,
    history_depth: int   = 6,
    eps_growth:    float = 0.12,
    margin_volatility: float = 0.10,
    quality_score: float = 65.0,
) -> MagicMock:
    es = MagicMock()
    es.history_depth = history_depth

    prof = MagicMock()
    prof.roe        = roe
    prof.roic       = roic
    prof.net_margin = net_margin
    # Suppress optional attrs that might cause MagicMock comparison issues
    prof.trough_gross_margin = None
    prof.trough_fcf_margin   = None
    prof.gross_margin_cv     = None
    es.profitability = prof

    trend = MagicMock()
    trend.cagr_eps = eps_growth
    es.trend = trend

    risk = MagicMock()
    risk.margin_volatility = margin_volatility
    es.risk = risk

    quality = MagicMock()
    quality.overall_score = quality_score
    es.quality = quality

    return es


def make_business_quality_snapshot() -> MagicMock:
    bqs = MagicMock()
    moat = MagicMock()
    moat.moat_score = 65.0
    moat.avg_roic   = 0.15
    bqs.moat = moat
    return bqs


def make_assumptions():
    """Default ValuationAssumptions suitable for tests."""
    from iios.investment.company.valuation.valuation_assumptions import ValuationAssumptions
    return ValuationAssumptions()
