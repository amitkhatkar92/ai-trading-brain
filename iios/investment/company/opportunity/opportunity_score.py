"""iios/investment/company/opportunity/opportunity_score.py
Composite opportunity score assembly from component scores.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from iios.investment.company.opportunity.opportunity_profile import (
    ComponentScore, OpportunityScoreBreakdown,
)
from iios.investment.company.opportunity.opportunity_quality import (
    extract_business_quality,
    extract_earnings_quality,
    extract_financial_strength,
    extract_growth_quality,
    extract_management_quality,
    extract_ownership_quality,
    extract_risk_penalty,
    extract_valuation_attractiveness,
)
from iios.investment.company.opportunity.opportunity_statistics import clamp


# ── Weight configuration ──────────────────────────────────────────────────────

_BASE_WEIGHTS: Dict[str, float] = {
    "business_quality":         0.25,
    "financial_strength":       0.20,
    "growth_quality":           0.15,
    "valuation_attractiveness": 0.15,
    "earnings_quality":         0.10,
    "management_quality":       0.08,
    "ownership_quality":        0.07,
}
_RISK_PENALTY_MAX = 20.0


def compute_opportunity_score(
    financial_snapshot:   Any,
    earnings_snapshot:    Any,
    business_quality:     Any,
    valuation_snapshot:   Any = None,
    growth_snapshot:      Any = None,
    management_snapshot:  Any = None,
    ownership_snapshot:   Any = None,
    risk_snapshot:        Any = None,
    market_intelligence:  Any = None,
) -> OpportunityScoreBreakdown:
    """
    Assemble the composite opportunity score from all upstream intelligence sources.

    Components with unavailable snapshots receive a neutral score (50.0)
    and their weight is redistributed to available components proportionally.
    """

    # ── Extract raw component scores ─────────────────────────────────────────
    fin_score  = extract_financial_strength(financial_snapshot)
    ear_score  = extract_earnings_quality(earnings_snapshot)
    bq_score   = extract_business_quality(business_quality)
    val_score  = extract_valuation_attractiveness(valuation_snapshot)
    grw_score  = extract_growth_quality(growth_snapshot)
    mgmt_score = extract_management_quality(management_snapshot)
    own_score  = extract_ownership_quality(ownership_snapshot)
    risk_pen   = extract_risk_penalty(risk_snapshot, market_intelligence, _RISK_PENALTY_MAX)

    # ── Determine availability (True if snapshot provided) ───────────────────
    availability = {
        "financial_strength":        financial_snapshot is not None,
        "earnings_quality":          earnings_snapshot is not None,
        "business_quality":          business_quality is not None,
        "valuation_attractiveness":  valuation_snapshot is not None,
        "growth_quality":            growth_snapshot is not None,
        "management_quality":        management_snapshot is not None,
        "ownership_quality":         ownership_snapshot is not None,
    }

    raw_scores = {
        "financial_strength":        fin_score,
        "earnings_quality":          ear_score,
        "business_quality":          bq_score,
        "valuation_attractiveness":  val_score,
        "growth_quality":            grw_score,
        "management_quality":        mgmt_score,
        "ownership_quality":         own_score,
    }

    # ── Normalise weights (unavailable components still contribute at 50) ────
    # We do NOT redistribute weights — unavailable components use neutral default.
    # This keeps weights stable and prevents score inflation from missing data.

    components = {}
    for key, base_w in _BASE_WEIGHTS.items():
        score   = raw_scores[key]
        avail   = availability[key]
        w_score = score * base_w
        components[key] = ComponentScore(
            name=key,
            score=score,
            weight=base_w,
            weighted_score=w_score,
            available=avail,
        )

    raw = clamp(sum(c.weighted_score for c in components.values()))
    final = clamp(raw - risk_pen)

    return OpportunityScoreBreakdown(
        financial_strength=components["financial_strength"],
        earnings_quality=components["earnings_quality"],
        business_quality=components["business_quality"],
        valuation_attractiveness=components["valuation_attractiveness"],
        growth_quality=components["growth_quality"],
        management_quality=components["management_quality"],
        ownership_quality=components["ownership_quality"],
        risk_penalty=round(risk_pen, 2),
        raw_score=round(raw, 2),
        final_score=round(final, 2),
    )
