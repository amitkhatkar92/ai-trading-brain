"""tests/unit/investment/company/earnings/conftest.py"""
import pytest

from iios.investment.company.earnings.earnings_report import EarningsReport


def make_report(
    fiscal_year:   int,
    quarter:       int | None = None,
    eps:           float = 10.0,
    revenue:       float = 1000.0,
    net_margin:    float = 10.0,
    gross_margin:  float = 35.0,
    ebit_margin:   float = 15.0,
    ebitda_margin: float = 20.0,
    roe:           float = 15.0,
    roa:           float = 5.0,
    roic:          float = 12.0,
    ocf:           float = 120.0,
    ocf_to_ni:     float = 1.2,
    accruals:      float = 0.03,
    is_restated:   bool  = False,
    period_type:   str   = "annual",
) -> EarningsReport:
    label = f"FY{fiscal_year % 100:02d}" if quarter is None else f"Q{quarter}FY{fiscal_year % 100:02d}"
    return EarningsReport(
        period_label=label,
        end_date=f"{fiscal_year}-03-31",
        period_type=period_type,
        fiscal_year=fiscal_year,
        quarter=quarter,
        revenue=revenue,
        gross_profit=revenue * gross_margin / 100,
        ebitda=revenue * ebitda_margin / 100,
        ebit=revenue * ebit_margin / 100,
        net_income=revenue * net_margin / 100,
        net_income_to_common=revenue * net_margin / 100,
        basic_eps=eps,
        diluted_eps=eps,
        gross_margin=gross_margin,
        ebitda_margin=ebitda_margin,
        ebit_margin=ebit_margin,
        net_margin=net_margin,
        roe=roe,
        roa=roa,
        roic=roic,
        operating_cash_flow=ocf,
        free_cash_flow=ocf - 40.0,
        ocf_to_net_income=ocf_to_ni,
        fcf_margin=(ocf - 40.0) / revenue * 100,
        accruals_ratio=accruals,
        cost_of_revenue_pct=100.0 - gross_margin,
        is_restated=is_restated,
        is_cash_backed=(ocf_to_ni >= 0.8),
        has_high_accruals=(accruals > 0.10),
    )


@pytest.fixture
def single_report():
    return make_report(2024)


@pytest.fixture
def growing_history():
    """5 years of consistently growing earnings."""
    return [
        make_report(2020, eps=8.0,  revenue=800.0,  net_margin=10.0, roe=12.0, roic=10.0),
        make_report(2021, eps=9.0,  revenue=900.0,  net_margin=10.5, roe=13.0, roic=11.0),
        make_report(2022, eps=10.5, revenue=1000.0, net_margin=11.0, roe=14.0, roic=12.0),
        make_report(2023, eps=12.0, revenue=1100.0, net_margin=11.5, roe=15.0, roic=13.0),
        make_report(2024, eps=14.0, revenue=1200.0, net_margin=12.0, roe=16.0, roic=14.0),
    ]


@pytest.fixture
def declining_history():
    """5 years of declining earnings."""
    return [
        make_report(2020, eps=15.0, net_margin=15.0),
        make_report(2021, eps=13.0, net_margin=13.0),
        make_report(2022, eps=11.0, net_margin=11.0),
        make_report(2023, eps=9.0,  net_margin=9.0),
        make_report(2024, eps=7.0,  net_margin=7.0),
    ]


@pytest.fixture
def volatile_history():
    """History with high volatility and losses."""
    return [
        make_report(2020, eps=5.0,  net_margin=5.0,  accruals=0.15),
        make_report(2021, eps=-2.0, net_margin=-2.0, ocf=-20.0, ocf_to_ni=0.3),
        make_report(2022, eps=8.0,  net_margin=8.0,  accruals=0.05),
        make_report(2023, eps=-1.0, net_margin=-1.0, ocf=-10.0, ocf_to_ni=0.4),
        make_report(2024, eps=10.0, net_margin=10.0, accruals=0.02),
    ]


@pytest.fixture
def high_quality_history():
    """History with high quality: strong cash conversion, low accruals."""
    reports = []
    for fy in range(2019, 2025):
        reports.append(make_report(
            fy,
            eps=float(fy - 2015),
            net_margin=15.0 + (fy - 2019),
            ocf=float((fy - 2015) * 120),
            ocf_to_ni=1.4,
            accruals=0.02,
            roic=18.0,
        ))
    return reports
