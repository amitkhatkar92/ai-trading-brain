"""iios/investment/company/opportunity/company_classifier.py
Pure classification logic — no classes, just functions.
Classifies companies into OpportunityCategory based on intelligence signals.
"""
from __future__ import annotations

from typing import Any, List, Optional, Tuple

from iios.investment.company.opportunity.opportunity_profile import OpportunityCategory
from iios.investment.company.opportunity.opportunity_statistics import safe_float


def _g(obj: Any, *attrs: str, default: Optional[float] = None) -> Optional[float]:
    """Safe nested getattr on an object chain, converting to float or None."""
    cur = obj
    for attr in attrs:
        if cur is None:
            return default
        cur = getattr(cur, attr, None)
    if cur is None:
        return default
    try:
        return float(cur)
    except (TypeError, ValueError):
        return default


def _b(obj: Any, *attrs: str) -> bool:
    """Safe nested getattr returning a bool."""
    cur = obj
    for attr in attrs:
        if cur is None:
            return False
        cur = getattr(cur, attr, None)
    return bool(cur)


def _classify_primary(
    bq_score:        float,
    val_score:       float,
    grw_score:       float,
    mgmt_score:      float,
    fin_score:       float,
    ear_score:       float,
    own_score:       float,
    moat_score:      float,
    eps_cagr:        Optional[float],
    rev_cagr:        Optional[float],
    avg_roic:        Optional[float],
    is_undervalued:  Optional[bool],
    is_overvalued:   Optional[bool],
    is_cyclical:     bool,
    dividend_yield:  Optional[float],
    payout_ratio:    Optional[float],
    fcf_margin:      Optional[float],
    has_alerts:      bool,
    overall_score:   float,
) -> Tuple[OpportunityCategory, List[str]]:
    """
    Rule-based primary category selection.
    Returns (category, rationale_list).
    """
    rationale: List[str] = []

    # ── Observation Only / Watchlist (low signal) ─────────────────────────────
    if overall_score < 35:
        rationale.append("Overall opportunity score below observation threshold")
        return OpportunityCategory.OBSERVATION_ONLY, rationale

    if overall_score < 50:
        rationale.append("Insufficient conviction for active tracking")
        return OpportunityCategory.WATCHLIST, rationale

    # ── Wide Moat (highest quality, narrow band) ──────────────────────────────
    if moat_score >= 75 and bq_score >= 70 and fin_score >= 60:
        rationale.append(f"Moat score {moat_score:.0f} with strong financials")
        return OpportunityCategory.WIDE_MOAT, rationale

    # ── Compounder ────────────────────────────────────────────────────────────
    roic_ok  = avg_roic is not None and avg_roic >= 0.15
    grw_ok   = (eps_cagr is not None and eps_cagr >= 0.10) or grw_score >= 60
    if roic_ok and bq_score >= 65 and grw_ok and fin_score >= 60:
        rationale.append(
            f"High ROIC ({avg_roic:.1%}) with consistent growth and quality fundamentals"
        )
        return OpportunityCategory.COMPOUNDER, rationale

    # ── Capital Allocator ─────────────────────────────────────────────────────
    if mgmt_score >= 72 and roic_ok and own_score >= 60 and fin_score >= 60:
        rationale.append("Exceptional capital allocation track with high ROIC")
        return OpportunityCategory.CAPITAL_ALLOCATOR, rationale

    # ── Innovation Leader ─────────────────────────────────────────────────────
    rev_strong = rev_cagr is not None and rev_cagr >= 0.18
    margin_expand = fcf_margin is not None and fcf_margin >= 0.12
    if rev_strong and margin_expand and bq_score >= 60:
        rationale.append("High revenue growth with expanding free cash flow margin")
        return OpportunityCategory.INNOVATION_LEADER, rationale

    # ── High Growth ───────────────────────────────────────────────────────────
    high_eps  = eps_cagr is not None and eps_cagr >= 0.18
    high_rev  = rev_cagr is not None and rev_cagr >= 0.15
    if (high_eps or high_rev) and grw_score >= 65:
        rationale.append(
            f"Strong EPS/revenue growth trajectory (EPS CAGR: "
            f"{eps_cagr:.1%}" if eps_cagr else "Revenue CAGR: "
            f"{rev_cagr:.1%})" if rev_cagr else ")"
        )
        return OpportunityCategory.HIGH_GROWTH, rationale

    # ── Undervalued Quality ───────────────────────────────────────────────────
    if is_undervalued and bq_score >= 60 and ear_score >= 55:
        rationale.append("Quality business trading at a discount to intrinsic value")
        return OpportunityCategory.UNDERVALUED_QUALITY, rationale

    # ── Deep Value ────────────────────────────────────────────────────────────
    if val_score <= 40 and is_undervalued:
        rationale.append("Significant discount to estimated intrinsic value")
        return OpportunityCategory.DEEP_VALUE, rationale

    # ── Dividend Growth ───────────────────────────────────────────────────────
    div_growing  = dividend_yield is not None and dividend_yield >= 0.02
    payout_ok    = payout_ratio is not None and payout_ratio <= 0.60
    grw_positive = rev_cagr is not None and rev_cagr >= 0.06
    if div_growing and payout_ok and grw_positive and fin_score >= 55:
        rationale.append("Growing dividend backed by expanding earnings and healthy payout")
        return OpportunityCategory.DIVIDEND_GROWTH, rationale

    # ── Income ────────────────────────────────────────────────────────────────
    high_yield = dividend_yield is not None and dividend_yield >= 0.035
    sust_payout = payout_ratio is not None and payout_ratio <= 0.75
    if high_yield and sust_payout and fin_score >= 50:
        rationale.append(f"High dividend yield ({dividend_yield:.1%}) with sustainable payout")
        return OpportunityCategory.INCOME, rationale

    # ── Cyclical Recovery ─────────────────────────────────────────────────────
    if is_cyclical and grw_score >= 55 and ear_score >= 50:
        rationale.append("Cyclical company with improving earnings at sector trough")
        return OpportunityCategory.CYCLICAL_RECOVERY, rationale

    # ── Turnaround / Recovery ─────────────────────────────────────────────────
    grw_improving = grw_score >= 55 and ear_score >= 45
    if grw_improving and val_score <= 55:
        if ear_score < 52:
            rationale.append("Profitability recovering from prior trough; turnaround underway")
            return OpportunityCategory.TURNAROUND, rationale
        rationale.append("Earnings recovery with improving growth trajectory")
        return OpportunityCategory.RECOVERY, rationale

    # ── Special Situation ─────────────────────────────────────────────────────
    if has_alerts and overall_score >= 55:
        rationale.append("Elevated monitoring flags alongside solid fundamentals")
        return OpportunityCategory.SPECIAL_SITUATION, rationale

    # ── Default: Watchlist ────────────────────────────────────────────────────
    rationale.append("Adequate fundamentals; insufficient differentiation for specific category")
    return OpportunityCategory.WATCHLIST, rationale


def _select_secondary(
    primary:    OpportunityCategory,
    bq_score:   float,
    val_score:  float,
    grw_score:  float,
    moat_score: float,
    avg_roic:   Optional[float],
    dividend_yield: Optional[float],
) -> List[OpportunityCategory]:
    """Select up to 2 complementary secondary categories."""
    secondary: List[OpportunityCategory] = []
    excluded = {primary}

    # Always flag Wide Moat as secondary if moat_score is high and not already primary
    if moat_score >= 70 and OpportunityCategory.WIDE_MOAT not in excluded:
        secondary.append(OpportunityCategory.WIDE_MOAT)
        excluded.add(OpportunityCategory.WIDE_MOAT)

    # Flag Compounder secondary if ROIC is strong
    roic_good = avg_roic is not None and avg_roic >= 0.15
    if roic_good and bq_score >= 60 and OpportunityCategory.COMPOUNDER not in excluded:
        secondary.append(OpportunityCategory.COMPOUNDER)
        excluded.add(OpportunityCategory.COMPOUNDER)

    # Flag Income secondary if dividend yield is meaningful
    if (
        dividend_yield is not None
        and dividend_yield >= 0.025
        and OpportunityCategory.INCOME not in excluded
        and len(secondary) < 2
    ):
        secondary.append(OpportunityCategory.INCOME)

    return secondary[:2]


def classify_company(
    bq_score:        float,
    val_score:       float,
    grw_score:       float,
    mgmt_score:      float,
    fin_score:       float,
    ear_score:       float,
    own_score:       float,
    moat_score:      float,
    overall_score:   float,
    eps_cagr:        Optional[float] = None,
    rev_cagr:        Optional[float] = None,
    avg_roic:        Optional[float] = None,
    is_undervalued:  Optional[bool] = None,
    is_overvalued:   Optional[bool] = None,
    is_cyclical:     bool = False,
    dividend_yield:  Optional[float] = None,
    payout_ratio:    Optional[float] = None,
    fcf_margin:      Optional[float] = None,
    has_alerts:      bool = False,
) -> Tuple[OpportunityCategory, List[OpportunityCategory], List[str]]:
    """
    Classify a company into primary + secondary opportunity categories.
    Returns (primary, secondary_list, rationale_list).
    """
    primary, rationale = _classify_primary(
        bq_score=bq_score, val_score=val_score, grw_score=grw_score,
        mgmt_score=mgmt_score, fin_score=fin_score, ear_score=ear_score,
        own_score=own_score, moat_score=moat_score,
        eps_cagr=eps_cagr, rev_cagr=rev_cagr, avg_roic=avg_roic,
        is_undervalued=is_undervalued, is_overvalued=is_overvalued,
        is_cyclical=is_cyclical, dividend_yield=dividend_yield,
        payout_ratio=payout_ratio, fcf_margin=fcf_margin,
        has_alerts=has_alerts, overall_score=overall_score,
    )
    secondary = _select_secondary(
        primary=primary, bq_score=bq_score, val_score=val_score,
        grw_score=grw_score, moat_score=moat_score,
        avg_roic=avg_roic, dividend_yield=dividend_yield,
    )
    return primary, secondary, rationale


def extract_classification_inputs(
    earnings_snapshot:  Any,
    business_quality:   Any,
    valuation_snapshot: Any,
    growth_snapshot:    Any,
) -> dict:
    """
    Extract classification-specific inputs from upstream snapshots.
    Returns a dict of keyword args passable to classify_company().
    """
    # Earnings
    prof = getattr(earnings_snapshot, "profitability", None) if earnings_snapshot else None
    trend = getattr(earnings_snapshot, "trend", None) if earnings_snapshot else None
    risk_e = getattr(earnings_snapshot, "risk", None) if earnings_snapshot else None

    eps_cagr  = _g(trend, "cagr_eps")
    rev_cagr  = _g(trend, "cagr_revenue")
    avg_roic  = _g(prof, "avg_roic")
    fcf_margin = _g(prof, "fcf_margin")
    is_cyclical = _b(risk_e, "is_cyclical")

    # Valuation
    is_undervalued = getattr(valuation_snapshot, "is_undervalued", None) if valuation_snapshot else None
    is_overvalued  = getattr(valuation_snapshot, "is_overvalued",  None) if valuation_snapshot else None

    # Business Quality - moat score
    moat = getattr(business_quality, "moat", None) if business_quality else None
    moat_score = safe_float(_g(moat, "moat_score"), 50.0)

    # Dividend (from financial ratios dict)
    return {
        "moat_score":      moat_score,
        "eps_cagr":        eps_cagr,
        "rev_cagr":        rev_cagr,
        "avg_roic":        avg_roic,
        "fcf_margin":      fcf_margin,
        "is_cyclical":     is_cyclical,
        "is_undervalued":  is_undervalued,
        "is_overvalued":   is_overvalued,
    }
