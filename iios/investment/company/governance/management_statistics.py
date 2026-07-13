"""iios/investment/company/governance/management_statistics.py
Statistical utilities for management and governance calculations.
No numpy — stdlib only.
"""
from __future__ import annotations

import math
from typing import List, Optional


def clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def safe_mean(values: List[Optional[float]]) -> Optional[float]:
    c = [v for v in values if v is not None and math.isfinite(v)]
    return sum(c) / len(c) if c else None


def score_roic(avg_roic: Optional[float]) -> float:
    """Convert ROIC to a 0-100 score. >20% = 100, 0% = 0."""
    if avg_roic is None:
        return 0.0
    if avg_roic >= 0.25:
        return 100.0
    if avg_roic >= 0.20:
        return 80.0 + (avg_roic - 0.20) / 0.05 * 20.0
    if avg_roic >= 0.15:
        return 60.0 + (avg_roic - 0.15) / 0.05 * 20.0
    if avg_roic >= 0.10:
        return 40.0 + (avg_roic - 0.10) / 0.05 * 20.0
    if avg_roic >= 0.0:
        return avg_roic / 0.10 * 40.0
    return 0.0


def score_ceo_tenure(ceo_tenure_years: Optional[float]) -> float:
    """
    Score CEO tenure on a 0-100 basis.
    Optimal range: 3-15 years.
    Too short (<3y) = transition risk. Too long (>20y) = entrenchment risk.
    """
    if ceo_tenure_years is None:
        return 50.0   # neutral prior
    t = ceo_tenure_years
    if t < 0:
        return 30.0
    if t < 1:
        return 30.0   # very new
    if t < 3:
        return clamp(30.0 + (t - 1) / 2.0 * 30.0, 30, 60)
    if t <= 10:
        return 80.0 + clamp((t - 3) / 7.0 * 15.0, 0, 15)
    if t <= 15:
        return 80.0
    if t <= 20:
        return clamp(80.0 - (t - 15) / 5.0 * 20.0, 60, 80)
    return clamp(80.0 - (t - 15) / 10.0 * 40.0, 30, 80)


def score_board_independence(independence_ratio: Optional[float]) -> float:
    """Score board independence (0-1 ratio → 0-100 score)."""
    if independence_ratio is None:
        return 30.0   # unknown → below average assumption
    r = independence_ratio
    if r >= 0.75:
        return 100.0
    if r >= 0.66:
        return 85.0 + (r - 0.66) / 0.09 * 15.0
    if r >= 0.50:
        return 65.0 + (r - 0.50) / 0.16 * 20.0
    if r >= 0.33:
        return 40.0 + (r - 0.33) / 0.17 * 25.0
    return clamp(r / 0.33 * 40.0, 0, 40)


def score_accruals(avg_accruals_ratio: Optional[float]) -> float:
    """
    Score accounting quality from accruals ratio.
    Lower accruals → better earnings quality → higher score.
    """
    if avg_accruals_ratio is None:
        return 50.0
    a = avg_accruals_ratio
    if a <= 0.03:
        return 100.0
    if a <= 0.06:
        return 80.0 + (0.06 - a) / 0.03 * 20.0
    if a <= 0.10:
        return 60.0 + (0.10 - a) / 0.04 * 20.0
    if a <= 0.15:
        return 40.0 + (0.15 - a) / 0.05 * 20.0
    if a <= 0.25:
        return 20.0 + (0.25 - a) / 0.10 * 20.0
    return clamp(20.0 - (a - 0.25) * 50, 0, 20)


def score_ocf_to_ni(avg_ocf_to_ni: Optional[float]) -> float:
    """
    Score OCF / Net Income ratio.
    > 1.0 → cash earnings > accrual earnings → excellent.
    """
    if avg_ocf_to_ni is None:
        return 50.0
    r = avg_ocf_to_ni
    if r >= 1.20:
        return 100.0
    if r >= 1.00:
        return 80.0 + (r - 1.00) / 0.20 * 20.0
    if r >= 0.80:
        return 55.0 + (r - 0.80) / 0.20 * 25.0
    if r >= 0.60:
        return 30.0 + (r - 0.60) / 0.20 * 25.0
    return clamp(r / 0.60 * 30.0, 0, 30)


def score_debt_level(debt_to_equity: Optional[float]) -> float:
    """
    Score debt management from D/E ratio.
    Lower is generally better; highly asset-light businesses may have 0.
    """
    if debt_to_equity is None:
        return 50.0
    de = debt_to_equity
    if de < 0:   # negative equity (extreme distress)
        return 0.0
    if de <= 0.2:
        return 90.0
    if de <= 0.5:
        return 75.0
    if de <= 1.0:
        return 60.0
    if de <= 2.0:
        return 40.0
    if de <= 3.0:
        return 20.0
    return clamp(20.0 - (de - 3.0) * 5.0, 0, 20)


def score_payout_ratio(payout_ratio: Optional[float]) -> float:
    """
    Score dividend payout ratio.
    Optimal: 20-50% (returning cash while reinvesting for growth).
    Very high (>80%) → may be unsustainable or company lacks reinvestment options.
    Very low (<10%) with high FCF → may be hoarding cash.
    """
    if payout_ratio is None:
        return 50.0
    p = payout_ratio
    if 0.25 <= p <= 0.50:
        return 85.0
    if 0.20 <= p < 0.25 or 0.50 < p <= 0.65:
        return 70.0
    if 0.10 <= p < 0.20 or 0.65 < p <= 0.80:
        return 55.0
    if p > 0.80:
        return clamp(55.0 - (p - 0.80) * 100.0, 20, 55)
    return 40.0  # very low payout


def score_leadership_stability(
    ceo_tenure_years:      Optional[float],
    leadership_changes_3y: int = 0,
    ceo_chairman_same:     bool = False,
) -> float:
    """Composite leadership stability score (0-100)."""
    base = score_ceo_tenure(ceo_tenure_years)
    penalty = 0.0
    if leadership_changes_3y >= 3:
        penalty += 25.0
    elif leadership_changes_3y == 2:
        penalty += 15.0
    elif leadership_changes_3y == 1:
        penalty += 5.0
    if ceo_chairman_same:
        penalty += 10.0   # governance concern, not stability per se
    return clamp(base - penalty, 0, 100)


def _label_score(score: float) -> str:
    if score >= 80:
        return "exceptional"
    if score >= 65:
        return "strong"
    if score >= 45:
        return "adequate"
    if score >= 25:
        return "weak"
    return "poor"
