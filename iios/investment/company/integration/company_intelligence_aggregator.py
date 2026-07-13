"""iios/investment/company/integration/company_intelligence_aggregator.py
Extracts normalised scores and key signals from upstream snapshots.

Each extraction function uses getattr safely — a missing or None snapshot
returns None (not a fallback score) so downstream code can distinguish
"engine not available" from "engine reported zero".
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from iios.investment.company.integration.company_statistics import (
    safe_float, safe_float_or_none, score_to_label,
)


# ── Per-engine score extractors ───────────────────────────────────────────────

def _extract_financial_score(snap: Any) -> Optional[float]:
    """FinancialSnapshot.quality_score (0-100)."""
    if snap is None:
        return None
    return safe_float_or_none(getattr(snap, "quality_score", None))


def _extract_earnings_score(snap: Any) -> Optional[float]:
    """EarningsSnapshot.quality.overall_score (0-100)."""
    if snap is None:
        return None
    qual = getattr(snap, "quality", None)
    score = getattr(qual, "overall_score", None)
    if score is None:
        # Try alternative path
        score = getattr(snap, "overall_score", None)
    return safe_float_or_none(score)


def _extract_bq_score(snap: Any) -> Optional[float]:
    """BusinessQualitySnapshot.overall_score (0-100)."""
    if snap is None:
        return None
    return safe_float_or_none(getattr(snap, "overall_score", None))


def _extract_valuation_score(snap: Any) -> Optional[float]:
    """ValuationSnapshot.valuation_score.overall_score (0-100)."""
    if snap is None:
        return None
    vs = getattr(snap, "valuation_score", None)
    score = getattr(vs, "overall_score", None)
    return safe_float_or_none(score)


def _extract_growth_score(snap: Any) -> Optional[float]:
    """GrowthSnapshot.overall_growth_score (0-100)."""
    if snap is None:
        return None
    score = getattr(snap, "overall_growth_score", None)
    if score is None:
        gs = getattr(snap, "growth_score", None)
        score = getattr(gs, "overall_score", None)
    return safe_float_or_none(score)


def _extract_management_score(snap: Any) -> Optional[float]:
    """ManagementSnapshot.overall_management_score (0-100)."""
    if snap is None:
        return None
    score = getattr(snap, "overall_management_score", None)
    if score is None:
        ms = getattr(snap, "management_score", None)
        score = getattr(ms, "overall_score", None)
    return safe_float_or_none(score)


def _extract_ownership_score(snap: Any) -> Optional[float]:
    """OwnershipSnapshot.overall_ownership_score (0-100)."""
    if snap is None:
        return None
    return safe_float_or_none(getattr(snap, "overall_ownership_score", None))


def _extract_opportunity_score(snap: Any) -> Optional[float]:
    """OpportunitySnapshot.overall_score (0-100)."""
    if snap is None:
        return None
    return safe_float_or_none(getattr(snap, "overall_score", None))


# ── Signal extractors ─────────────────────────────────────────────────────────

def _is_profitable(earn_snap: Any) -> Optional[bool]:
    return getattr(earn_snap, "is_profitable", None) if earn_snap else None


def _is_growing(growth_snap: Any) -> Optional[bool]:
    return getattr(growth_snap, "is_growing", None) if growth_snap else None


def _is_undervalued(val_snap: Any) -> Optional[bool]:
    return getattr(val_snap, "is_undervalued", None) if val_snap else None


def _is_overvalued(val_snap: Any) -> Optional[bool]:
    return getattr(val_snap, "is_overvalued", None) if val_snap else None


def _roic(earn_snap: Any) -> Optional[float]:
    if earn_snap is None:
        return None
    prof = getattr(earn_snap, "profitability", None)
    return safe_float_or_none(getattr(prof, "avg_roic", None) or getattr(prof, "roic", None))


def _promoter_pledge(own_snap: Any) -> Optional[float]:
    if own_snap is None:
        return None
    # Try direct attribute first
    pct = getattr(own_snap, "promoter_pledge_pct", None)
    if pct is None:
        risk = getattr(own_snap, "ownership_risk", None)
        pct  = getattr(risk, "promoter_pledge_pct", None)
    return safe_float_or_none(pct)


def _governance_risk(mgmt_snap: Any) -> Optional[float]:
    if mgmt_snap is None:
        return None
    gr = getattr(mgmt_snap, "governance_risk", None)
    return safe_float_or_none(getattr(gr, "overall_risk_score", None))


def _opportunity_category(opp_snap: Any) -> Optional[str]:
    if opp_snap is None:
        return None
    cat = getattr(opp_snap, "primary_category", None)
    if cat is None:
        return None
    # Enum or str
    return cat.value if hasattr(cat, "value") else str(cat)


def _opportunity_lifecycle(opp_snap: Any) -> Optional[str]:
    if opp_snap is None:
        return None
    lc = getattr(opp_snap, "lifecycle", None)
    if lc is None:
        return None
    return lc.value if hasattr(lc, "value") else str(lc)


# ── Dimension label helpers ───────────────────────────────────────────────────

def _label_from_score(score: Optional[float], unavailable: str = "unavailable") -> str:
    if score is None:
        return unavailable
    return score_to_label(score)


def _label_from_snap(snap: Any, attr: str = "label") -> str:
    if snap is None:
        return "unavailable"
    val = getattr(snap, attr, None)
    if val is None:
        return "unavailable"
    return val.value if hasattr(val, "value") else str(val)


# ── AggregatedIntelligence ────────────────────────────────────────────────────

@dataclass
class AggregatedIntelligence:
    """
    Normalised intelligence extracted from all upstream snapshots.
    Consumed by validators, conflict detectors, and the snapshot builder.
    """
    ticker: str

    # ── Dimension scores (None = engine unavailable) ──────────────────────────
    financial_score:       Optional[float] = None
    earnings_score:        Optional[float] = None
    business_quality_score: Optional[float] = None
    valuation_score:       Optional[float] = None
    growth_score:          Optional[float] = None
    management_score:      Optional[float] = None
    ownership_score:       Optional[float] = None
    opportunity_score:     Optional[float] = None

    # ── Dimension labels ──────────────────────────────────────────────────────
    financial_label:       str = "unavailable"
    earnings_label:        str = "unavailable"
    business_quality_label: str = "unavailable"
    valuation_label:       str = "unavailable"
    growth_label:          str = "unavailable"
    management_label:      str = "unavailable"
    ownership_label:       str = "unavailable"
    opportunity_label:     str = "unavailable"

    # ── Derived signals ───────────────────────────────────────────────────────
    is_profitable:       Optional[bool] = None
    is_growing:          Optional[bool] = None
    is_undervalued:      Optional[bool] = None
    is_overvalued:       Optional[bool] = None
    roic:                Optional[float] = None
    promoter_pledge_pct: Optional[float] = None
    governance_risk:     Optional[float] = None
    opportunity_category: Optional[str] = None
    opportunity_lifecycle: Optional[str] = None

    # ── Raw snapshots (for downstream that needs detail) ──────────────────────
    financial_snapshot:        Any = field(default=None, repr=False)
    earnings_snapshot:         Any = field(default=None, repr=False)
    business_quality_snapshot: Any = field(default=None, repr=False)
    valuation_snapshot:        Any = field(default=None, repr=False)
    growth_snapshot:           Any = field(default=None, repr=False)
    management_snapshot:       Any = field(default=None, repr=False)
    ownership_snapshot:        Any = field(default=None, repr=False)
    opportunity_snapshot:      Any = field(default=None, repr=False)
    profile_snapshot:          Any = field(default=None, repr=False)

    # ── Metadata ──────────────────────────────────────────────────────────────
    aggregated_at:    datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    available_engines: List[str] = field(default_factory=list)


# ── Public API ────────────────────────────────────────────────────────────────

def aggregate_intelligence(
    ticker:              str,
    snapshot_map:        Dict[str, Any],
) -> AggregatedIntelligence:
    """
    Build an AggregatedIntelligence from a dict of {engine_name: snapshot}.
    Snapshot values may be None (engine not yet available).
    """
    fin  = snapshot_map.get("financials")
    earn = snapshot_map.get("earnings")
    bq   = snapshot_map.get("business_quality")
    val  = snapshot_map.get("valuation")
    grw  = snapshot_map.get("growth")
    mgmt = snapshot_map.get("management")
    own  = snapshot_map.get("ownership")
    opp  = snapshot_map.get("opportunity")
    prof = snapshot_map.get("profile")

    fin_sc  = _extract_financial_score(fin)
    earn_sc = _extract_earnings_score(earn)
    bq_sc   = _extract_bq_score(bq)
    val_sc  = _extract_valuation_score(val)
    grw_sc  = _extract_growth_score(grw)
    mgmt_sc = _extract_management_score(mgmt)
    own_sc  = _extract_ownership_score(own)
    opp_sc  = _extract_opportunity_score(opp)

    available = [
        name for name, snap in snapshot_map.items()
        if snap is not None
    ]

    return AggregatedIntelligence(
        ticker=ticker,
        # Scores
        financial_score=fin_sc,
        earnings_score=earn_sc,
        business_quality_score=bq_sc,
        valuation_score=val_sc,
        growth_score=grw_sc,
        management_score=mgmt_sc,
        ownership_score=own_sc,
        opportunity_score=opp_sc,
        # Labels
        financial_label=_label_from_score(fin_sc),
        earnings_label=_label_from_score(earn_sc),
        business_quality_label=_label_from_score(bq_sc),
        valuation_label=_label_from_score(val_sc),
        growth_label=_label_from_score(grw_sc),
        management_label=_label_from_score(mgmt_sc),
        ownership_label=_label_from_score(own_sc),
        opportunity_label=_label_from_score(opp_sc),
        # Signals
        is_profitable=_is_profitable(earn),
        is_growing=_is_growing(grw),
        is_undervalued=_is_undervalued(val),
        is_overvalued=_is_overvalued(val),
        roic=_roic(earn),
        promoter_pledge_pct=_promoter_pledge(own),
        governance_risk=_governance_risk(mgmt),
        opportunity_category=_opportunity_category(opp),
        opportunity_lifecycle=_opportunity_lifecycle(opp),
        # Raw
        financial_snapshot=fin,
        earnings_snapshot=earn,
        business_quality_snapshot=bq,
        valuation_snapshot=val,
        growth_snapshot=grw,
        management_snapshot=mgmt,
        ownership_snapshot=own,
        opportunity_snapshot=opp,
        profile_snapshot=prof,
        # Metadata
        available_engines=available,
    )
