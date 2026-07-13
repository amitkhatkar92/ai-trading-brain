"""tests/unit/investment/company/business_quality/conftest.py"""
import pytest
from unittest.mock import MagicMock

from iios.investment.company.business_quality.assessment_context import AssessmentContext


def make_financial_snapshot(
    gross_margin:     float = 40.0,
    net_margin:       float = 12.0,
    ebitda_margin:    float = 20.0,
    roic:             float = 15.0,
    roe:              float = 18.0,
    roa:              float = 8.0,
    asset_turnover:   float = 1.2,
    debt_to_equity:   float = 0.5,
    current_ratio:    float = 2.0,
    interest_coverage: float = 10.0,
    fcf_margin:       float = 10.0,
    capex_pct:        float = 4.0,
    sga_pct:          float = 15.0,
    rd_pct:           float = 2.0,
    inventory_turnover: float = 6.0,
    receivables_days: float = 45.0,
    payables_days:    float = 30.0,
    revenue:          float = 1000.0,
    ocf_to_ni:        float = 1.2,
):
    snap = MagicMock()
    snap.ratios = {
        "gross_margin":           gross_margin,
        "net_margin":             net_margin,
        "ebitda_margin":          ebitda_margin,
        "roic":                   roic,
        "roe":                    roe,
        "roa":                    roa,
        "asset_turnover":         asset_turnover,
        "debt_to_equity":         debt_to_equity,
        "current_ratio":          current_ratio,
        "interest_coverage":      interest_coverage,
        "fcf_margin":             fcf_margin,
        "capex_pct":              capex_pct,
        "sga_pct":                sga_pct,
        "rd_pct":                 rd_pct,
        "inventory_turnover":     inventory_turnover,
        "receivable_turnover_days": receivables_days,
        "dso":                    receivables_days,
        "dpo":                    payables_days,
        "payable_turnover_days":  payables_days,
    }
    snap.income_metrics = {
        "gross_margin":  gross_margin,
        "net_margin":    net_margin,
        "ebitda_margin": ebitda_margin,
        "sga_pct":       sga_pct,
        "rd_pct":        rd_pct,
    }
    snap.cashflow_metrics = {
        "fcf_margin":  fcf_margin,
        "capex_pct":   capex_pct,
        "ocf_to_ni":   ocf_to_ni,
    }
    snap.balance_sheet_metrics = {
        "current_ratio":   current_ratio,
        "debt_to_equity":  debt_to_equity,
    }
    snap.revenue      = revenue
    snap.total_assets = revenue / asset_turnover if asset_turnover else revenue
    snap.total_equity = revenue * 0.5
    return snap


def make_earnings_snapshot(
    avg_roic:         float = 15.0,
    avg_roe:          float = 18.0,
    avg_roa:          float = 8.0,
    avg_gross_margin: float = 40.0,
    avg_net_margin:   float = 12.0,
    avg_fcf_margin:   float = 10.0,
    history_depth:    int   = 5,
    eps_volatility:   float = 0.15,
    margin_volatility: float = 1.5,
    revenue_volatility: float = 0.2,
    earnings_stability_score: float = 70.0,
    quality_score:    float = 75.0,
    consistency_score: float = 70.0,
    is_cyclical:      bool  = False,
    loss_rate:        float = 0.0,
):
    snap = MagicMock()
    snap.history_depth = history_depth

    # profitability
    prof = MagicMock()
    prof.avg_roic         = avg_roic
    prof.avg_roe          = avg_roe
    prof.avg_roa          = avg_roa
    prof.avg_gross_margin = avg_gross_margin
    prof.avg_net_margin   = avg_net_margin
    prof.avg_fcf_margin   = avg_fcf_margin
    # Trough / derived attrs — explicitly None to avoid MagicMock comparison
    prof.trough_gross_margin = None
    prof.trough_net_margin   = None
    prof.trough_fcf_margin   = None
    prof.trough_ebit_margin  = None
    prof.gross_margin_cv     = None
    prof.fcf_conversion      = None
    snap.profitability    = prof

    # quality
    qual = MagicMock()
    qual.overall_score       = quality_score
    qual.consistency_score   = consistency_score
    qual.avg_accruals_ratio  = 0.03
    snap.quality = qual

    # risk
    risk = MagicMock()
    risk.eps_volatility              = eps_volatility
    risk.margin_volatility           = margin_volatility
    risk.revenue_volatility          = revenue_volatility
    risk.earnings_stability_score    = earnings_stability_score
    risk.is_cyclical                 = is_cyclical
    risk.loss_rate                   = loss_rate
    snap.risk = risk

    # trend
    from iios.investment.company.earnings.earnings_report import TrendDirection
    trend = MagicMock()
    trend.eps_direction     = TrendDirection.ACCELERATING
    trend.revenue_direction = TrendDirection.STABLE
    trend.margin_direction  = TrendDirection.STABLE
    snap.trend = trend

    return snap


_FS_PARAMS = {
    "net_margin", "ebitda_margin", "roe", "roa", "asset_turnover",
    "debt_to_equity", "current_ratio", "interest_coverage", "fcf_margin",
    "sga_pct", "rd_pct", "inventory_turnover", "receivables_days",
    "payables_days", "revenue", "ocf_to_ni",
}


def make_ctx(
    ticker: str = "TEST",
    gross_margin: float = 40.0,
    roic: float = 15.0,
    capex_pct: float = 4.0,
    avg_fcf_margin: float = 10.0,
    **kwargs,
) -> AssessmentContext:
    fs_kwargs = {k: v for k, v in kwargs.items() if k in _FS_PARAMS}
    fs = make_financial_snapshot(
        gross_margin=gross_margin, roic=roic, capex_pct=capex_pct, **fs_kwargs
    )
    fcf_in_fs = fs_kwargs.get("fcf_margin", 10.0)
    effective_avg_fcf = min(avg_fcf_margin, fcf_in_fs) if "fcf_margin" in fs_kwargs else avg_fcf_margin
    es = make_earnings_snapshot(
        avg_roic=roic, avg_gross_margin=gross_margin,
        avg_fcf_margin=effective_avg_fcf,
    )
    return AssessmentContext(
        ticker=ticker, financial_snapshot=fs, earnings_snapshot=es
    )


@pytest.fixture
def ctx_high_quality():
    """Context for a high-quality business: high margins, ROIC, low debt."""
    return make_ctx(
        ticker="HQ", gross_margin=60.0, roic=22.0,
        capex_pct=3.0, debt_to_equity=0.2, net_margin=18.0,
        sga_pct=20.0,
    )


@pytest.fixture
def ctx_asset_heavy():
    """Context for an asset-heavy business."""
    return make_ctx(
        ticker="AH", gross_margin=25.0, roic=8.0,
        capex_pct=20.0, debt_to_equity=3.0, net_margin=5.0,
    )


@pytest.fixture
def ctx_commodity():
    return make_ctx(
        ticker="CM", gross_margin=10.0, roic=5.0,
        capex_pct=12.0, debt_to_equity=1.5, net_margin=2.0,
    )


@pytest.fixture
def ctx_minimal():
    """Minimal context with no financial or earnings data."""
    return AssessmentContext(ticker="MIN")
