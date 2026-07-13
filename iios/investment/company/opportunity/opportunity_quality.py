"""iios/investment/company/opportunity/opportunity_quality.py
Score extraction functions — pull scalar quality scores from upstream snapshots.
All functions accept Any (upstream snapshot objects) and use safe getattr access.
"""
from __future__ import annotations

from typing import Any, Optional

from iios.investment.company.opportunity.opportunity_statistics import clamp, safe_float


# ── Financial Strength ────────────────────────────────────────────────────────

def extract_financial_strength(snapshot: Any, default: float = 50.0) -> float:
    """
    Derive a financial strength score (0-100) from a FinancialSnapshot.
    Uses cash flow quality, leverage, and profitability signals.
    """
    if snapshot is None:
        return default

    scores = []

    cf = getattr(snapshot, "cashflow_metrics", None)
    bs = getattr(snapshot, "balance_sheet_metrics", None)
    revenue = safe_float(getattr(snapshot, "revenue", None), 0.0)
    equity  = safe_float(getattr(snapshot, "total_equity", None), 0.0)

    # FCF margin: fcf / revenue
    fcf = safe_float(getattr(cf, "free_cash_flow", None) if cf else None, None)
    if fcf is not None and revenue > 0:
        fcf_margin = fcf / revenue
        # 0% → 50, 15% → 95, negative → low
        fcf_score = clamp(50.0 + fcf_margin * 300.0)
        scores.append(fcf_score)

    # Debt/Equity: lower is better
    debt = safe_float(getattr(bs, "total_debt", None) if bs else None, None)
    if debt is not None and equity > 0:
        de = debt / equity
        # 0 → 100, 0.5 → 85, 1 → 70, 2 → 40, 3+ → 20
        de_score = clamp(100.0 - de * 27.0)
        scores.append(de_score)

    # OCF quality: OCF / Net Income (>1 = high quality)
    ocf = safe_float(getattr(cf, "operating_cash_flow", None) if cf else None, None)
    ni  = safe_float(getattr(getattr(snapshot, "income_metrics", None), "net_income", None), None)
    if ocf is not None and ni is not None and ni > 0:
        ratio = ocf / ni
        ocf_score = clamp(30.0 + ratio * 35.0)
        scores.append(ocf_score)

    # Cash buffer: cash / revenue
    cash = safe_float(getattr(bs, "cash_and_equivalents", None) if bs else None, None)
    if cash is not None and revenue > 0:
        cash_ratio = cash / revenue
        cash_score = clamp(40.0 + cash_ratio * 200.0)
        scores.append(cash_score)

    if not scores:
        return default
    return clamp(sum(scores) / len(scores))


# ── Earnings Quality ──────────────────────────────────────────────────────────

def extract_earnings_quality(snapshot: Any, default: float = 50.0) -> float:
    """Pull the composite earnings quality score from an EarningsSnapshot."""
    if snapshot is None:
        return default
    # Primary: overall_score
    overall = getattr(snapshot, "overall_score", None)
    if overall is not None:
        return clamp(safe_float(overall, default))
    # Fallback: quality sub-object
    quality = getattr(snapshot, "quality", None)
    if quality is not None:
        q_score = getattr(quality, "overall_score", None)
        if q_score is not None:
            return clamp(safe_float(q_score, default))
    return default


# ── Business Quality ──────────────────────────────────────────────────────────

def extract_business_quality(snapshot: Any, default: float = 50.0) -> float:
    """Pull the composite business quality score from a BusinessQualitySnapshot."""
    if snapshot is None:
        return default
    # Primary: overall_score property
    overall = getattr(snapshot, "overall_score", None)
    if overall is not None:
        return clamp(safe_float(overall, default))
    # Fallback: average moat + operational + resilience
    scores = []
    moat = getattr(snapshot, "moat", None)
    if moat:
        ms = getattr(moat, "moat_score", None)
        if ms is not None:
            scores.append(safe_float(ms))
    ops = getattr(snapshot, "operational", None)
    if ops:
        oqs = getattr(ops, "operational_quality_score", None)
        if oqs is not None:
            scores.append(safe_float(oqs))
    res = getattr(snapshot, "resilience", None)
    if res:
        rs = getattr(res, "resilience_score", None)
        if rs is not None:
            scores.append(safe_float(rs))
    return clamp(sum(scores) / len(scores)) if scores else default


# ── Valuation Attractiveness ──────────────────────────────────────────────────

def extract_valuation_attractiveness(snapshot: Any, default: float = 50.0) -> float:
    """
    Pull valuation attractiveness from a ValuationSnapshot.
    Higher score → more attractive (undervalued).
    """
    if snapshot is None:
        return default
    # Primary: valuation_score.overall_score
    val_score = getattr(snapshot, "valuation_score", None)
    if val_score is not None:
        overall = getattr(val_score, "overall_score", None)
        if overall is not None:
            return clamp(safe_float(overall, default))
    # Fallback: margin of safety
    mos = getattr(snapshot, "mos", None)
    if mos is not None:
        mos_pct = getattr(mos, "margin_of_safety_pct", None)
        if mos_pct is not None:
            # +30% MOS → ~90 score; -30% MOS → ~20 score
            return clamp(55.0 + safe_float(mos_pct) * 1.2)
    return default


# ── Growth Quality ────────────────────────────────────────────────────────────

def extract_growth_quality(snapshot: Any, default: float = 50.0) -> float:
    """Pull the growth intelligence score from a GrowthSnapshot."""
    if snapshot is None:
        return default
    # Primary: overall_growth_score property
    overall = getattr(snapshot, "overall_growth_score", None)
    if overall is not None:
        return clamp(safe_float(overall, default))
    # Fallback: growth_score sub-object
    gs = getattr(snapshot, "growth_score", None)
    if gs is not None:
        s = getattr(gs, "overall_score", None)
        if s is not None:
            return clamp(safe_float(s, default))
    return default


# ── Management Quality ────────────────────────────────────────────────────────

def extract_management_quality(snapshot: Any, default: float = 50.0) -> float:
    """Pull the management score from a ManagementSnapshot."""
    if snapshot is None:
        return default
    # Primary: overall_management_score property
    overall = getattr(snapshot, "overall_management_score", None)
    if overall is not None:
        return clamp(safe_float(overall, default))
    # Fallback: management_score sub-object
    ms = getattr(snapshot, "management_score", None)
    if ms is not None:
        s = getattr(ms, "overall_score", None)
        if s is not None:
            return clamp(safe_float(s, default))
    return default


# ── Ownership Quality ─────────────────────────────────────────────────────────

def extract_ownership_quality(snapshot: Any, default: float = 50.0) -> float:
    """Pull the ownership intelligence score from an OwnershipSnapshot."""
    if snapshot is None:
        return default
    # Primary: overall_ownership_score property
    overall = getattr(snapshot, "overall_ownership_score", None)
    if overall is not None:
        return clamp(safe_float(overall, default))
    return default


# ── Risk Penalty ──────────────────────────────────────────────────────────────

def extract_risk_penalty(
    risk_snapshot: Any,
    market_intelligence: Any,
    max_penalty: float = 20.0,
) -> float:
    """
    Compute a risk penalty (0-max_penalty) to deduct from the composite score.
    Sources: risk snapshot overall risk score + market intelligence signals.
    """
    components = []

    # Risk snapshot
    if risk_snapshot is not None:
        # Prefer overall_risk_score (0-100, higher = riskier)
        overall_risk = getattr(risk_snapshot, "overall_risk_score", None)
        if overall_risk is not None:
            # map 0-100 risk → 0-15 penalty
            components.append(safe_float(overall_risk) / 100.0 * 15.0)

    # Market intelligence
    if market_intelligence is not None:
        market_stress = getattr(market_intelligence, "market_stress_score", None)
        if market_stress is not None:
            # map 0-100 stress → 0-5 penalty
            components.append(safe_float(market_stress) / 100.0 * 5.0)

    if not components:
        return 0.0
    return clamp(sum(components) / len(components), 0.0, max_penalty)
