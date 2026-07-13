"""iios/investment/company/ownership/dilution_analysis.py
Share dilution risk analysis.
"""
from __future__ import annotations

from typing import Optional

from iios.investment.company.ownership.ownership_statistics import clamp, score_dilution_risk, pct_to_100


def score_esop_dilution(esop_outstanding_pct: Optional[float]) -> float:
    """
    Risk score for ESOP dilution (0-100; higher = more dilution risk).
    """
    return score_dilution_risk(esop_outstanding_pct)


def score_share_count_growth(
    shares_now:   Optional[int],
    shares_prior: Optional[int],
) -> float:
    """
    Risk score from share count growth (dilution of existing holders).
    0-100; higher = more dilutive.
    """
    if shares_now is None or shares_prior is None or shares_prior <= 0:
        return 15.0   # no data → mild risk assumption

    growth = (shares_now - shares_prior) / shares_prior
    if growth <= -0.02:
        return 0.0    # buybacks → anti-dilutive
    if growth <= 0.01:
        return 5.0
    if growth <= 0.03:
        return 20.0
    if growth <= 0.05:
        return 40.0
    if growth <= 0.10:
        return 60.0
    return clamp(60.0 + (growth - 0.10) / 0.10 * 40)


def score_total_dilution_risk(
    esop_outstanding_pct: Optional[float],
    promoter_pct_change:  Optional[float],
    free_float_pct:       Optional[float],
) -> float:
    """
    Composite dilution risk score (0-100; higher = more dilutive pressure).
    """
    components: list[float] = []

    # ESOP dilution risk (weight 50%)
    esop_risk = score_esop_dilution(esop_outstanding_pct)
    components.append(esop_risk * 0.50)

    # Promoter selling as dilution proxy (weight 30%)
    if promoter_pct_change is not None:
        # Promoter selling increases free float which can be dilutive to price
        if promoter_pct_change <= -5.0:
            components.append(70.0 * 0.30)
        elif promoter_pct_change <= -2.0:
            components.append(50.0 * 0.30)
        elif promoter_pct_change >= 0:
            components.append(10.0 * 0.30)
        else:
            components.append(25.0 * 0.30)
    else:
        components.append(20.0 * 0.30)

    # Low free float + ESOP = future dilution pressure (weight 20%)
    if free_float_pct is not None:
        ff = pct_to_100(free_float_pct) or 0.0
        if ff < 15 and (esop_outstanding_pct or 0) > 3:
            components.append(60.0 * 0.20)
        else:
            components.append(20.0 * 0.20)
    else:
        components.append(20.0 * 0.20)

    return clamp(sum(components))
