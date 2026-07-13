"""iios/investment/company/opportunity/evidence_collector.py
Evidence extraction from upstream intelligence snapshots.
Converts structured data into human-readable ThesisEvidence objects.
"""
from __future__ import annotations

from typing import Any, List, Optional

from iios.investment.company.opportunity.investment_thesis import ThesisEvidence
from iios.investment.company.opportunity.opportunity_statistics import safe_float


def _g(obj: Any, *attrs: str) -> Optional[float]:
    cur = obj
    for attr in attrs:
        if cur is None:
            return None
        cur = getattr(cur, attr, None)
    if cur is None:
        return None
    try:
        return float(cur)
    except (TypeError, ValueError):
        return None


def _pct(v: Optional[float]) -> str:
    return f"{v:.1%}" if v is not None else "n/a"


def _score_signal(v: float, good: float, bad: float) -> str:
    if v >= good:
        return "positive"
    if v <= bad:
        return "negative"
    return "neutral"


# ── Financial evidence ────────────────────────────────────────────────────────

def collect_financial_evidence(snapshot: Any) -> List[ThesisEvidence]:
    if snapshot is None:
        return []
    evidence: List[ThesisEvidence] = []

    cf = getattr(snapshot, "cashflow_metrics", None)
    bs = getattr(snapshot, "balance_sheet_metrics", None)
    revenue = _g(snapshot, "revenue")
    equity  = _g(snapshot, "total_equity")
    debt    = _g(bs, "total_debt") if bs else None
    fcf     = _g(cf, "free_cash_flow") if cf else None

    if fcf is not None and revenue and revenue > 0:
        fcf_m = fcf / revenue
        evidence.append(ThesisEvidence(
            factor="FCF Margin",
            value=_pct(fcf_m),
            signal=_score_signal(fcf_m, 0.12, 0.0),
            importance="high",
            source="financial",
        ))

    if debt is not None and equity and equity > 0:
        de = debt / equity
        evidence.append(ThesisEvidence(
            factor="Debt/Equity",
            value=f"{de:.2f}x",
            signal="positive" if de < 0.5 else ("negative" if de > 2.0 else "neutral"),
            importance="high",
            source="financial",
        ))

    return evidence


# ── Earnings evidence ─────────────────────────────────────────────────────────

def collect_earnings_evidence(snapshot: Any) -> List[ThesisEvidence]:
    if snapshot is None:
        return []
    evidence: List[ThesisEvidence] = []
    prof  = getattr(snapshot, "profitability", None)
    trend = getattr(snapshot, "trend", None)

    roic = _g(prof, "avg_roic") if prof else None
    roe  = _g(prof, "avg_roe")  if prof else None
    net_margin = _g(prof, "net_margin") if prof else None
    eps_cagr   = _g(trend, "cagr_eps") if trend else None
    rev_cagr   = _g(trend, "cagr_revenue") if trend else None

    if roic is not None:
        evidence.append(ThesisEvidence(
            factor="Avg ROIC",
            value=_pct(roic),
            signal=_score_signal(roic, 0.15, 0.06),
            importance="high",
            source="earnings",
        ))
    if roe is not None:
        evidence.append(ThesisEvidence(
            factor="Avg ROE",
            value=_pct(roe),
            signal=_score_signal(roe, 0.15, 0.06),
            importance="medium",
            source="earnings",
        ))
    if net_margin is not None:
        evidence.append(ThesisEvidence(
            factor="Net Margin",
            value=_pct(net_margin),
            signal=_score_signal(net_margin, 0.10, 0.0),
            importance="medium",
            source="earnings",
        ))
    if eps_cagr is not None:
        evidence.append(ThesisEvidence(
            factor="EPS CAGR",
            value=_pct(eps_cagr),
            signal=_score_signal(eps_cagr, 0.12, 0.0),
            importance="high",
            source="earnings",
        ))
    if rev_cagr is not None:
        evidence.append(ThesisEvidence(
            factor="Revenue CAGR",
            value=_pct(rev_cagr),
            signal=_score_signal(rev_cagr, 0.10, 0.0),
            importance="medium",
            source="earnings",
        ))
    return evidence


# ── Business quality evidence ─────────────────────────────────────────────────

def collect_bq_evidence(snapshot: Any) -> List[ThesisEvidence]:
    if snapshot is None:
        return []
    evidence: List[ThesisEvidence] = []
    moat = getattr(snapshot, "moat", None)

    if moat is not None:
        ms = _g(moat, "moat_score")
        if ms is not None:
            evidence.append(ThesisEvidence(
                factor="Moat Score",
                value=f"{ms:.0f}/100",
                signal=_score_signal(ms, 65.0, 35.0),
                importance="high",
                source="business_quality",
            ))
        moat_types = getattr(moat, "detected_moat_types", None)
        if moat_types:
            evidence.append(ThesisEvidence(
                factor="Moat Sources",
                value=", ".join(str(m) for m in moat_types[:3]),
                signal="positive",
                importance="high",
                source="business_quality",
            ))
    return evidence


# ── Valuation evidence ────────────────────────────────────────────────────────

def collect_valuation_evidence(snapshot: Any) -> List[ThesisEvidence]:
    if snapshot is None:
        return []
    evidence: List[ThesisEvidence] = []

    mos = getattr(snapshot, "mos", None)
    if mos is not None:
        mos_pct = _g(mos, "margin_of_safety_pct")
        if mos_pct is not None:
            evidence.append(ThesisEvidence(
                factor="Margin of Safety",
                value=_pct(mos_pct),
                signal="positive" if mos_pct > 15 else ("negative" if mos_pct < -10 else "neutral"),
                importance="high",
                source="valuation",
            ))
    return evidence


# ── Growth evidence ───────────────────────────────────────────────────────────

def collect_growth_evidence(snapshot: Any) -> List[ThesisEvidence]:
    if snapshot is None:
        return []
    evidence: List[ThesisEvidence] = []
    gs = getattr(snapshot, "growth_score", None)
    if gs is not None:
        overall = _g(gs, "overall_score")
        if overall is not None:
            evidence.append(ThesisEvidence(
                factor="Growth Score",
                value=f"{overall:.0f}/100",
                signal=_score_signal(overall, 65.0, 35.0),
                importance="medium",
                source="growth",
            ))
    return evidence


# ── Management evidence ───────────────────────────────────────────────────────

def collect_management_evidence(snapshot: Any) -> List[ThesisEvidence]:
    if snapshot is None:
        return []
    evidence: List[ThesisEvidence] = []
    score = _g(snapshot, "overall_management_score")
    if score is not None:
        evidence.append(ThesisEvidence(
            factor="Governance Score",
            value=f"{score:.0f}/100",
            signal=_score_signal(score, 65.0, 40.0),
            importance="medium",
            source="management",
        ))
    return evidence


# ── Ownership evidence ────────────────────────────────────────────────────────

def collect_ownership_evidence(snapshot: Any) -> List[ThesisEvidence]:
    if snapshot is None:
        return []
    evidence: List[ThesisEvidence] = []
    score = _g(snapshot, "overall_ownership_score")
    if score is not None:
        evidence.append(ThesisEvidence(
            factor="Ownership Quality",
            value=f"{score:.0f}/100",
            signal=_score_signal(score, 60.0, 35.0),
            importance="low",
            source="ownership",
        ))
    # Promoter pledge
    pledge = _g(snapshot, "promoter_pledge_pct")
    if pledge is not None and pledge > 30:
        evidence.append(ThesisEvidence(
            factor="Promoter Pledge",
            value=_pct(pledge / 100),
            signal="negative",
            importance="high",
            source="ownership",
        ))
    return evidence


def collect_all_evidence(
    financial_snapshot:  Any,
    earnings_snapshot:   Any,
    business_quality:    Any,
    valuation_snapshot:  Any,
    growth_snapshot:     Any,
    management_snapshot: Any,
    ownership_snapshot:  Any,
) -> List[ThesisEvidence]:
    """Collect all supporting evidence from available snapshots."""
    all_ev: List[ThesisEvidence] = []
    all_ev.extend(collect_financial_evidence(financial_snapshot))
    all_ev.extend(collect_earnings_evidence(earnings_snapshot))
    all_ev.extend(collect_bq_evidence(business_quality))
    all_ev.extend(collect_valuation_evidence(valuation_snapshot))
    all_ev.extend(collect_growth_evidence(growth_snapshot))
    all_ev.extend(collect_management_evidence(management_snapshot))
    all_ev.extend(collect_ownership_evidence(ownership_snapshot))
    return all_ev
