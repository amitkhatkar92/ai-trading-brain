"""iios/investment/company/ownership/capital_return.py
Capital return to shareholders analysis.
"""
from __future__ import annotations

from typing import Optional

from iios.investment.company.ownership.ownership_statistics import (
    clamp, score_dividend_policy, score_buyback_quality, pct_to_100,
)


def score_dividend_sustainability(
    payout_ratio:    Optional[float],
    eps_cagr:        Optional[float],
    avg_ocf_to_ni:   Optional[float],
    div_per_share:   Optional[float],
) -> float:
    """
    Score dividend sustainability — can the company sustain its dividend?
    Sustainable: adequate payout with strong cash conversion.
    """
    if payout_ratio is None and div_per_share is None:
        return 45.0   # no dividend data

    sustainability = 50.0

    if payout_ratio is not None:
        p = pct_to_100(payout_ratio) or 0.0
        if p <= 0:
            sustainability = 45.0   # no dividend
        elif p < 40:
            sustainability = 80.0   # low payout → room to grow
        elif p < 60:
            sustainability = 75.0
        elif p < 80:
            sustainability = 55.0   # stretching payout
        else:
            sustainability = 30.0   # unsustainable payout

    # Cash quality adjustment
    if avg_ocf_to_ni is not None:
        if avg_ocf_to_ni >= 1.20:
            sustainability += 10.0
        elif avg_ocf_to_ni >= 0.90:
            sustainability += 3.0
        elif avg_ocf_to_ni < 0.70:
            sustainability -= 15.0

    # EPS growth adjustment
    if eps_cagr is not None and payout_ratio is not None:
        p = pct_to_100(payout_ratio) or 0.0
        if eps_cagr > 0.15 and p < 70:
            sustainability += 5.0
        elif eps_cagr < 0 and p > 50:
            sustainability -= 10.0

    return clamp(sustainability)


def score_total_shareholder_return_quality(
    payout_ratio:  Optional[float],
    avg_roic:      Optional[float],
    fcf_margin:    Optional[float],
    eps_cagr:      Optional[float],
) -> float:
    """
    Score total shareholder return quality (dividend + buyback + earnings growth).
    """
    components: list[float] = []

    # Dividend component
    div_score = score_dividend_policy(payout_ratio, eps_cagr)
    components.append(div_score * 0.35)

    # Buyback quality (proxy: high ROIC + strong FCF)
    bb_score = score_buyback_quality(avg_roic, fcf_margin)
    components.append(bb_score * 0.30)

    # Earnings growth component
    if eps_cagr is not None:
        if eps_cagr >= 0.20:
            components.append(100.0 * 0.35)
        elif eps_cagr >= 0.12:
            components.append(80.0 * 0.35)
        elif eps_cagr >= 0.05:
            components.append(60.0 * 0.35)
        elif eps_cagr >= 0:
            components.append(40.0 * 0.35)
        else:
            components.append(10.0 * 0.35)
    else:
        components.append(45.0 * 0.35)

    return clamp(sum(components))


def score_cash_return_policy(
    fcf:         Optional[float],
    net_income:  Optional[float],
    payout_ratio: Optional[float],
) -> float:
    """
    Score how well FCF is converted to shareholder returns.
    Comparing dividend payments to actual free cash flow generation.
    """
    if fcf is None or net_income is None or net_income <= 0:
        return 50.0

    # FCF coverage of stated earnings
    fcf_to_ni = fcf / net_income
    if payout_ratio is None:
        # Can't compute; just score FCF quality
        if fcf_to_ni >= 1.2:
            return 80.0
        if fcf_to_ni >= 0.9:
            return 65.0
        if fcf_to_ni >= 0.6:
            return 50.0
        return 30.0

    pct = pct_to_100(payout_ratio) or 0.0
    # Actual cash payout relative to FCF generation
    if fcf > 0:
        cash_coverage = fcf_to_ni / (pct / 100 + 0.001)
        if cash_coverage >= 2.5:
            return 95.0
        if cash_coverage >= 1.5:
            return 80.0
        if cash_coverage >= 1.0:
            return 65.0
        if cash_coverage >= 0.7:
            return 45.0
        return 20.0
    else:
        return 15.0   # negative FCF with dividends = unsustainable
