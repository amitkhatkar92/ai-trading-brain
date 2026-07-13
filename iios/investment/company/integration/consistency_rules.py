"""iios/investment/company/integration/consistency_rules.py
Consistency rule definitions for cross-engine validation.

Each rule is a named check function that receives an AggregatedIntelligence object
and returns a ValidationCheck (or None if the rule cannot be evaluated).
"""
from __future__ import annotations

from typing import Callable, List, Optional

from iios.investment.company.integration.company_state import (
    ConflictSeverity, DIVERGENCE_CRIT_THRESHOLD, DIVERGENCE_WARN_THRESHOLD,
    ValidationStatus,
)
from iios.investment.company.integration.company_statistics import safe_float
from iios.investment.company.integration.validation_report import ValidationCheck


# ── Type alias for rule callables ─────────────────────────────────────────────

AggIntel = object   # typing placeholder; actual type is AggregatedIntelligence


def _check(
    name: str, description: str,
    engine_a: str, engine_b: str,
    value_a: Optional[float], value_b: Optional[float],
    status: ValidationStatus,
    message: str,
    severity: ConflictSeverity = ConflictSeverity.INFO,
) -> ValidationCheck:
    return ValidationCheck(
        name=name, description=description,
        status=status, engine_a=engine_a, engine_b=engine_b,
        value_a=value_a, value_b=value_b,
        message=message, severity=severity,
    )


# ── Individual rules ──────────────────────────────────────────────────────────

def rule_growth_vs_earnings(intel: AggIntel) -> Optional[ValidationCheck]:
    """
    Growth score must not be dramatically higher than earnings quality.
    High revenue growth with very poor earnings quality signals unsustainable growth.
    """
    g = getattr(intel, "growth_score", None)
    e = getattr(intel, "earnings_score", None)
    if g is None or e is None:
        return None

    g, e = safe_float(g), safe_float(e)
    gap = g - e

    if gap > DIVERGENCE_CRIT_THRESHOLD and e < 30:
        return _check(
            "growth_vs_earnings",
            "Growth score vs Earnings quality consistency",
            "growth", "earnings", g, e,
            ValidationStatus.FAILED,
            f"Growth score ({g:.0f}) is dramatically higher than earnings quality ({e:.0f}). "
            "High growth with poor earnings quality may be unsustainable.",
            ConflictSeverity.HIGH,
        )
    if gap > DIVERGENCE_WARN_THRESHOLD and e < 45:
        return _check(
            "growth_vs_earnings",
            "Growth score vs Earnings quality consistency",
            "growth", "earnings", g, e,
            ValidationStatus.WARNING,
            f"Growth score ({g:.0f}) significantly exceeds earnings quality ({e:.0f}). "
            "Monitor earnings sustainability.",
            ConflictSeverity.MEDIUM,
        )
    return _check(
        "growth_vs_earnings", "Growth score vs Earnings quality consistency",
        "growth", "earnings", g, e,
        ValidationStatus.PASSED, "Growth and earnings quality are consistent.",
    )


def rule_growth_vs_valuation(intel: AggIntel) -> Optional[ValidationCheck]:
    """
    Very low growth with a very poor valuation score indicates a value trap risk.
    (Not a contradiction per se, but a material risk flag.)
    """
    g = getattr(intel, "growth_score", None)
    v = getattr(intel, "valuation_score", None)
    if g is None or v is None:
        return None

    g, v = safe_float(g), safe_float(v)

    if g < 30 and v < 25:
        return _check(
            "growth_vs_valuation",
            "Growth profile vs Valuation attractiveness",
            "growth", "valuation", g, v,
            ValidationStatus.WARNING,
            f"Low growth ({g:.0f}) combined with poor valuation score ({v:.0f}) "
            "suggests potential value trap.",
            ConflictSeverity.MEDIUM,
        )
    return _check(
        "growth_vs_valuation", "Growth profile vs Valuation attractiveness",
        "growth", "valuation", g, v,
        ValidationStatus.PASSED, "Growth and valuation are consistent.",
    )


def rule_bq_vs_financial(intel: AggIntel) -> Optional[ValidationCheck]:
    """
    Very high business quality with very poor financial health is a tension.
    A company with durable competitive advantages should not have severe financial distress.
    """
    bq = getattr(intel, "business_quality_score", None)
    f  = getattr(intel, "financial_score", None)
    if bq is None or f is None:
        return None

    bq, f = safe_float(bq), safe_float(f)

    if bq >= 75 and f < 25:
        return _check(
            "bq_vs_financial",
            "Business quality vs Financial health",
            "business_quality", "financials", bq, f,
            ValidationStatus.FAILED,
            f"High business quality ({bq:.0f}) conflicts with poor financial health ({f:.0f}). "
            "Durable moats should be reflected in financial strength.",
            ConflictSeverity.HIGH,
        )
    if bq >= 65 and f < 35:
        return _check(
            "bq_vs_financial",
            "Business quality vs Financial health",
            "business_quality", "financials", bq, f,
            ValidationStatus.WARNING,
            f"Strong business quality ({bq:.0f}) not yet reflected in financial health ({f:.0f}).",
            ConflictSeverity.MEDIUM,
        )
    return _check(
        "bq_vs_financial", "Business quality vs Financial health",
        "business_quality", "financials", bq, f,
        ValidationStatus.PASSED, "Business quality and financial health are consistent.",
    )


def rule_management_vs_ownership(intel: AggIntel) -> Optional[ValidationCheck]:
    """
    High management score with high ownership risk (e.g., high promoter pledge) is a conflict.
    Good management claims should not coexist with governance-level ownership risks.
    """
    m  = getattr(intel, "management_score", None)
    ow = getattr(intel, "ownership_score", None)
    pledge = getattr(intel, "promoter_pledge_pct", None)

    if m is None or ow is None:
        return None

    m, ow = safe_float(m), safe_float(ow)
    p = safe_float(pledge) if pledge is not None else 0.0

    if m >= 70 and ow < 30:
        return _check(
            "management_vs_ownership",
            "Management quality vs Ownership risk",
            "management", "ownership", m, ow,
            ValidationStatus.FAILED,
            f"High management score ({m:.0f}) conflicts with poor ownership quality ({ow:.0f}). "
            "High governance risk undermines management credibility.",
            ConflictSeverity.HIGH,
        )
    if p >= 50 and m >= 65:
        return _check(
            "management_vs_ownership",
            "Management quality vs Promoter pledge risk",
            "management", "ownership", m, p,
            ValidationStatus.WARNING,
            f"High promoter pledge ({p:.0f}%) coexists with high management score ({m:.0f}). "
            "Pledge risk may undermine governance.",
            ConflictSeverity.MEDIUM,
        )
    return _check(
        "management_vs_ownership", "Management quality vs Ownership risk",
        "management", "ownership", m, ow,
        ValidationStatus.PASSED, "Management and ownership scores are consistent.",
    )


def rule_earnings_vs_financial(intel: AggIntel) -> Optional[ValidationCheck]:
    """
    Strong earnings quality should be supported by financial health.
    """
    e = getattr(intel, "earnings_score", None)
    f = getattr(intel, "financial_score", None)
    if e is None or f is None:
        return None

    e, f = safe_float(e), safe_float(f)
    gap = e - f

    if gap > DIVERGENCE_CRIT_THRESHOLD and f < 25:
        return _check(
            "earnings_vs_financial",
            "Earnings quality vs Financial health",
            "earnings", "financials", e, f,
            ValidationStatus.FAILED,
            f"Earnings quality ({e:.0f}) is much higher than financial health ({f:.0f}). "
            "Earnings may not be converting to financial strength.",
            ConflictSeverity.HIGH,
        )
    if gap > DIVERGENCE_WARN_THRESHOLD and f < 40:
        return _check(
            "earnings_vs_financial",
            "Earnings quality vs Financial health",
            "earnings", "financials", e, f,
            ValidationStatus.WARNING,
            f"Earnings quality ({e:.0f}) materially exceeds financial health ({f:.0f}).",
            ConflictSeverity.MEDIUM,
        )
    return _check(
        "earnings_vs_financial", "Earnings quality vs Financial health",
        "earnings", "financials", e, f,
        ValidationStatus.PASSED, "Earnings and financial quality are consistent.",
    )


def rule_opportunity_vs_financial(intel: AggIntel) -> Optional[ValidationCheck]:
    """
    A very high opportunity score despite poor financial health deserves scrutiny.
    """
    opp = getattr(intel, "opportunity_score", None)
    f   = getattr(intel, "financial_score", None)
    if opp is None or f is None:
        return None

    opp, f = safe_float(opp), safe_float(f)

    if opp >= 75 and f < 25:
        return _check(
            "opportunity_vs_financial",
            "Opportunity score vs Financial health",
            "opportunity", "financials", opp, f,
            ValidationStatus.FAILED,
            f"High opportunity score ({opp:.0f}) is inconsistent with very poor financial "
            f"health ({f:.0f}). Opportunity assessment may be overoptimistic.",
            ConflictSeverity.HIGH,
        )
    if opp >= 65 and f < 30:
        return _check(
            "opportunity_vs_financial",
            "Opportunity score vs Financial health",
            "opportunity", "financials", opp, f,
            ValidationStatus.WARNING,
            f"Opportunity score ({opp:.0f}) is high despite weak financials ({f:.0f}).",
            ConflictSeverity.MEDIUM,
        )
    return _check(
        "opportunity_vs_financial", "Opportunity score vs Financial health",
        "opportunity", "financials", opp, f,
        ValidationStatus.PASSED, "Opportunity and financial scores are consistent.",
    )


def rule_bq_vs_earnings(intel: AggIntel) -> Optional[ValidationCheck]:
    """
    Strong business quality (moats) should eventually produce strong earnings.
    A wide divergence may indicate the moat is eroding or earnings are suppressed.
    """
    bq = getattr(intel, "business_quality_score", None)
    e  = getattr(intel, "earnings_score", None)
    if bq is None or e is None:
        return None

    bq, e = safe_float(bq), safe_float(e)
    gap = bq - e

    if gap > DIVERGENCE_CRIT_THRESHOLD and e < 30:
        return _check(
            "bq_vs_earnings",
            "Business quality vs Earnings quality",
            "business_quality", "earnings", bq, e,
            ValidationStatus.WARNING,
            f"Business quality ({bq:.0f}) materially exceeds earnings quality ({e:.0f}). "
            "Moat may be eroding or earnings are temporarily suppressed.",
            ConflictSeverity.MEDIUM,
        )
    return _check(
        "bq_vs_earnings", "Business quality vs Earnings quality",
        "business_quality", "earnings", bq, e,
        ValidationStatus.PASSED, "Business quality and earnings are consistent.",
    )


# ── Rule registry ─────────────────────────────────────────────────────────────

ALL_RULES: List[Callable] = [
    rule_growth_vs_earnings,
    rule_growth_vs_valuation,
    rule_bq_vs_financial,
    rule_management_vs_ownership,
    rule_earnings_vs_financial,
    rule_opportunity_vs_financial,
    rule_bq_vs_earnings,
]
