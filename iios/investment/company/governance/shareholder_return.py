"""iios/investment/company/governance/shareholder_return.py
Shareholder return analysis — dividend policy, buybacks, total shareholder return.
"""
from __future__ import annotations

from typing import Optional

from iios.investment.company.governance.management_statistics import (
    clamp, score_payout_ratio, score_debt_level,
)


def score_dividend_policy(
    dividend_payout_ratio: Optional[float] = None,
    dividend_per_share:    Optional[float] = None,
    fcf_margin:            Optional[float] = None,
) -> float:
    """
    Score dividend policy quality.
    Optimal policy: sustainable payout ratio, covered by FCF.
    """
    base = score_payout_ratio(dividend_payout_ratio)

    # If FCF negative and paying dividends → sustainability concern
    if fcf_margin is not None and fcf_margin < 0 and dividend_per_share is not None and dividend_per_share > 0:
        base -= 20.0

    return clamp(base, 0, 100)


def score_buyback_quality(
    avg_roic:         Optional[float] = None,
    fcf_margin:       Optional[float] = None,
    payout_ratio:     Optional[float] = None,
) -> float:
    """
    Score share buyback quality.
    Buybacks at high ROIC companies with strong FCF are value-enhancing.
    Buybacks at low ROIC companies with debt are often value-destructive.
    """
    if fcf_margin is None and avg_roic is None:
        return 50.0

    score = 55.0

    if avg_roic is not None:
        if avg_roic >= 0.15:
            score += 20.0  # high ROIC company buying back is excellent
        elif avg_roic < 0.08:
            score -= 15.0  # low ROIC buyback may signal capital misallocation

    if fcf_margin is not None:
        if fcf_margin > 0.10:
            score += 10.0
        elif fcf_margin < 0:
            score -= 20.0

    return clamp(score, 0, 100)


def score_debt_management(
    debt_to_equity:    Optional[float] = None,
    avg_roic:          Optional[float] = None,
) -> float:
    """
    Score debt management.
    Acceptable leverage depends on ROIC vs interest cost.
    High ROIC companies can safely carry more debt.
    """
    base = score_debt_level(debt_to_equity)

    # ROIC > 15% → company generates returns well above debt cost; moderate leverage acceptable
    if avg_roic is not None and avg_roic >= 0.15 and debt_to_equity is not None:
        if debt_to_equity <= 1.5:
            base = min(base + 10.0, 100.0)

    return clamp(base, 0, 100)
