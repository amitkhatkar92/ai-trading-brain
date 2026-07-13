"""iios/investment/company/ownership/ownership_concentration.py
Ownership concentration metrics.
"""
from __future__ import annotations

from typing import Optional

from iios.investment.company.ownership.ownership_profile import ConcentrationLevel
from iios.investment.company.ownership.ownership_statistics import clamp, pct_to_100


def classify_concentration_level(top10_pct: Optional[float]) -> ConcentrationLevel:
    """Classify overall ownership concentration from top-10 holder percentage."""
    if top10_pct is None:
        return ConcentrationLevel.UNKNOWN
    p = pct_to_100(top10_pct) or 0.0
    if p > 80:
        return ConcentrationLevel.HIGHLY_CONCENTRATED
    if p > 60:
        return ConcentrationLevel.CONCENTRATED
    if p > 40:
        return ConcentrationLevel.MODERATE
    if p > 20:
        return ConcentrationLevel.DIVERSIFIED
    return ConcentrationLevel.WIDELY_HELD


def score_concentration_risk(
    top10_pct:      Optional[float],
    promoter_pct:   Optional[float],
    free_float_pct: Optional[float],
) -> float:
    """
    Risk score from ownership concentration (0-100, higher = more risky).
    Extreme concentration → forced-selling / illiquidity risk.
    Extreme dispersion → low governance quality.
    """
    risk = 20.0   # base moderate risk

    if top10_pct is not None:
        p = pct_to_100(top10_pct) or 0.0
        if p > 90:
            risk += 35.0
        elif p > 80:
            risk += 25.0
        elif p > 70:
            risk += 15.0
        elif p < 20:
            risk += 15.0   # too dispersed also adds governance risk

    if promoter_pct is not None:
        pp = pct_to_100(promoter_pct) or 0.0
        if pp > 75:
            risk += 20.0   # minority shareholder protection concern
        elif pp < 15:
            risk += 10.0   # very low promoter skin-in-game

    if free_float_pct is not None:
        ff = pct_to_100(free_float_pct) or 0.0
        if ff < 10:
            risk += 20.0   # extremely illiquid
        elif ff < 20:
            risk += 10.0

    return clamp(risk)


def score_herfindahl_proxy(
    promoter_pct:      Optional[float],
    institutional_pct: Optional[float],
    retail_pct:        Optional[float],
    government_pct:    Optional[float],
) -> float:
    """
    Pseudo-Herfindahl-Hirschman index for ownership concentration.
    Returns a 0-100 diversity quality score (higher = better diversification).
    """
    portions: list[float] = []
    for v in [promoter_pct, institutional_pct, retail_pct, government_pct]:
        if v is not None:
            p = pct_to_100(v)
            if p is not None and p > 0:
                portions.append(p / 100.0)

    if not portions:
        return 50.0

    # HHI = sum of squared shares
    hhi = sum(s ** 2 for s in portions)
    # hhi is 0-1; 1 = fully concentrated, 1/n = perfectly equal
    n = len(portions)
    min_hhi = 1.0 / n   # perfectly equal split

    # Convert to 0-100 diversity score (lower HHI = higher diversity score)
    if hhi <= min_hhi + 0.01:
        return 85.0   # near-perfect diversification
    if hhi >= 0.9:
        return 5.0    # near-monopoly concentration

    # Scale between min_hhi and 1.0
    normalized = (hhi - min_hhi) / (1.0 - min_hhi)
    return clamp(85.0 - normalized * 80)


def score_control_concentration(
    promoter_pct:      Optional[float],
    institutional_pct: Optional[float],
    is_family_controlled: bool = False,
) -> float:
    """
    Assess quality of control structure from a minority-shareholder perspective.
    Returns a governance-quality score (0-100; higher = more minority-friendly).
    """
    score = 60.0  # neutral base

    if promoter_pct is not None:
        pp = pct_to_100(promoter_pct) or 0.0
        if pp > 75:
            score -= 20.0   # too concentrated; minority at risk
        elif pp > 65:
            score -= 10.0
        elif 40 <= pp <= 65:
            score += 15.0   # optimal alignment zone
        elif pp < 20:
            score -= 10.0   # low promoter accountability

    if institutional_pct is not None:
        ip = pct_to_100(institutional_pct) or 0.0
        if ip >= 25:
            score += 10.0   # institutional watchdogs present
        elif ip < 5:
            score -= 5.0

    if is_family_controlled:
        score -= 10.0   # additional minority risk disclosure

    return clamp(score)
