"""iios/investment/company/opportunity/reason_generator.py
Human-readable reason/narrative generation from intelligence signals.
"""
from __future__ import annotations

from typing import Any, List, Optional

from iios.investment.company.opportunity.investment_thesis import ThesisEvidence
from iios.investment.company.opportunity.opportunity_profile import (
    OpportunityCategory, OpportunityLifecycle, OpportunityStrength,
)
from iios.investment.company.opportunity.opportunity_statistics import safe_float


def _g(obj: Any, *attrs: str) -> Optional[float]:
    cur = obj
    for attr in attrs:
        if cur is None:
            return None
        cur = getattr(cur, attr, None)
    try:
        return float(cur) if cur is not None else None
    except (TypeError, ValueError):
        return None


def _pct(v: Optional[float], default: str = "n/a") -> str:
    return f"{v:.1%}" if v is not None else default


def generate_strengths(
    evidence: List[ThesisEvidence],
    bq_score: float,
    fin_score: float,
    grw_score: float,
    moat_score: float,
    avg_roic: Optional[float],
    eps_cagr: Optional[float],
) -> List[str]:
    """Generate human-readable strength statements."""
    strengths: List[str] = []

    # From positive evidence
    for ev in evidence:
        if ev.signal == "positive" and ev.importance == "high":
            strengths.append(f"{ev.factor}: {ev.value}")

    # Synthesised statements
    if moat_score >= 65:
        strengths.append(f"Identifiable competitive moat (score {moat_score:.0f}/100)")
    if avg_roic is not None and avg_roic >= 0.15:
        strengths.append(f"Strong reinvestment returns (ROIC {_pct(avg_roic)})")
    if eps_cagr is not None and eps_cagr >= 0.12:
        strengths.append(f"Consistent earnings growth ({_pct(eps_cagr)} EPS CAGR)")
    if fin_score >= 70:
        strengths.append("Robust balance sheet and cash generation")
    if bq_score >= 68:
        strengths.append("High business quality with operational resilience")
    if grw_score >= 65:
        strengths.append("Above-average growth trajectory with quality characteristics")

    # Deduplicate while preserving order
    seen: set = set()
    unique: List[str] = []
    for s in strengths:
        key = s[:30]
        if key not in seen:
            seen.add(key)
            unique.append(s)

    return unique[:5]


def generate_weaknesses(
    evidence: List[ThesisEvidence],
    val_score: float,
    fin_score: float,
    mgmt_score: float,
    own_score: float,
) -> List[str]:
    """Generate human-readable weakness statements."""
    weaknesses: List[str] = []
    for ev in evidence:
        if ev.signal == "negative" and ev.importance in ("high", "medium"):
            weaknesses.append(f"{ev.factor}: {ev.value}")

    if val_score >= 65:
        weaknesses.append("Current price reflects significant optimism; limited discount")
    if fin_score < 45:
        weaknesses.append("Financial health metrics indicate pressure on cash generation")
    if mgmt_score < 45:
        weaknesses.append("Governance or capital allocation quality below peer average")
    if own_score < 40:
        weaknesses.append("Ownership structure raises minority protection concerns")

    seen: set = set()
    unique: List[str] = []
    for w in weaknesses:
        key = w[:30]
        if key not in seen:
            seen.add(key)
            unique.append(w)
    return unique[:4]


def generate_key_risks(
    alerts: List[str],
    is_cyclical: bool,
    fin_score: float,
    val_score: float,
    category: OpportunityCategory,
) -> List[str]:
    """Generate key risk statements from alerts and intelligence signals."""
    risks: List[str] = []

    # Propagate existing alerts as risks
    for alert in alerts[:3]:
        risks.append(alert)

    if is_cyclical:
        risks.append("Cyclical earnings exposure — profitability sensitive to macro conditions")
    if fin_score < 40:
        risks.append("Elevated leverage or weak cash conversion limits financial flexibility")
    if val_score >= 70:
        risks.append("Premium valuation leaves limited margin for earnings disappointment")
    if category == OpportunityCategory.TURNAROUND:
        risks.append("Turnaround execution risk — recovery timeline uncertain")
    if category == OpportunityCategory.HIGH_GROWTH:
        risks.append("Growth-stage multiple compression risk if growth decelerates")
    if category == OpportunityCategory.DEEP_VALUE:
        risks.append("Value trap risk — discount may persist without catalyst")

    seen: set = set()
    unique: List[str] = []
    for r in risks:
        key = r[:30]
        if key not in seen:
            seen.add(key)
            unique.append(r)
    return unique[:5]


def generate_catalysts(
    category:     OpportunityCategory,
    grw_score:    float,
    val_score:    float,
    moat_score:   float,
    eps_cagr:     Optional[float],
) -> List[str]:
    """Generate potential catalyst statements."""
    catalysts: List[str] = []

    if category == OpportunityCategory.TURNAROUND:
        catalysts.append("Successful operational restructuring or product rationalisation")
        catalysts.append("Return to positive free cash flow generation")
    elif category == OpportunityCategory.CYCLICAL_RECOVERY:
        catalysts.append("Cyclical demand recovery supporting volume and pricing improvement")
    elif category == OpportunityCategory.UNDERVALUED_QUALITY:
        catalysts.append("Market recognition of intrinsic value as earnings compound")
    elif category == OpportunityCategory.HIGH_GROWTH:
        catalysts.append("Sustained revenue growth above consensus expectations")
        if eps_cagr is not None and eps_cagr >= 0.20:
            catalysts.append("Operating leverage driving accelerating EPS growth")
    elif category == OpportunityCategory.COMPOUNDER:
        catalysts.append("Continued reinvestment at high returns on incremental capital")
        catalysts.append("New market entry or product expansion amplifying growth runway")
    elif category in (OpportunityCategory.INCOME, OpportunityCategory.DIVIDEND_GROWTH):
        catalysts.append("Dividend increase supported by growing free cash flow")
    elif category == OpportunityCategory.WIDE_MOAT:
        catalysts.append("Pricing power allowing above-inflation revenue growth")

    if val_score <= 45:
        catalysts.append("Narrowing valuation gap as earnings track higher")
    if moat_score >= 70:
        catalysts.append("Moat expansion protecting and widening return on capital")

    return catalysts[:4]


def generate_monitoring_points(
    category:      OpportunityCategory,
    lifecycle:     OpportunityLifecycle,
    is_cyclical:   bool,
    fin_score:     float,
) -> List[str]:
    """Generate monitoring points tailored to category and lifecycle."""
    points = [
        "Quarterly earnings quality and margin trajectory",
        "Free cash flow versus net income divergence",
    ]

    if category in (OpportunityCategory.TURNAROUND, OpportunityCategory.RECOVERY):
        points.append("Return to consistent operating profitability")
        points.append("Debt reduction progress and balance sheet repair")
    if is_cyclical:
        points.append("Industry capacity utilisation and pricing indicators")
    if category in (OpportunityCategory.HIGH_GROWTH, OpportunityCategory.INNOVATION_LEADER):
        points.append("Revenue growth rate versus consensus and prior-year periods")
        points.append("Customer acquisition cost and unit economics")
    if lifecycle == OpportunityLifecycle.WEAKENING:
        points.append("Stabilisation of score decline — watch for reversal signal")
        points.append("Management guidance and forward earnings revisions")
    if fin_score < 50:
        points.append("Leverage ratio trend and covenant headroom")

    return points[:5]


def build_headline(
    ticker:   str,
    category: OpportunityCategory,
    strength: OpportunityStrength,
    bq_score: float,
    val_score: float,
) -> str:
    """Generate a concise one-line opportunity headline."""
    cat_label = category.value.replace("_", " ").title()
    str_label = strength.value.title()
    if bq_score >= 65 and val_score <= 55:
        return f"{ticker} — {str_label} {cat_label} with valuation support"
    if bq_score >= 65:
        return f"{ticker} — {str_label} {cat_label} opportunity"
    return f"{ticker} — {cat_label} profile under evaluation"


def build_narrative(
    ticker:    str,
    category:  OpportunityCategory,
    strengths: List[str],
    risks:     List[str],
    lifecycle: OpportunityLifecycle,
    overall_score: float,
) -> str:
    """Build a 2-3 sentence explanatory narrative."""
    cat_desc = category.value.replace("_", " ")
    str_bullet = "; ".join(strengths[:2]) if strengths else "fundamentals under assessment"
    risk_bullet = risks[0] if risks else "standard market risks"

    para1 = (
        f"{ticker} presents a {cat_desc} opportunity profile "
        f"with an overall intelligence score of {overall_score:.0f}/100. "
        f"Key strengths include {str_bullet}."
    )
    para2 = (
        f"The principal risk consideration is: {risk_bullet}. "
        f"Current lifecycle state is {lifecycle.value.replace('_', ' ')}, "
        f"reflecting the signal maturity of this evaluation."
    )
    return f"{para1} {para2}"
