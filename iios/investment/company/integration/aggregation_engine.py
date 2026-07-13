"""iios/investment/company/integration/aggregation_engine.py
Orchestrates aggregation, scoring, and snapshot assembly for one ticker.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from iios.investment.company.integration.company_intelligence_aggregator import (
    AggregatedIntelligence, aggregate_intelligence,
)
from iios.investment.company.integration.company_state import (
    ENGINE_WEIGHTS, SCORED_ENGINES, score_to_grade,
)
from iios.investment.company.integration.company_statistics import (
    clamp, safe_float, safe_average, weighted_average,
)
from iios.investment.company.integration.company_summary import (
    CompanySummary, DimensionSummary,
)


# ── Overall score computation ─────────────────────────────────────────────────

def compute_overall_score(intel: AggregatedIntelligence) -> float:
    """
    Compute the 0-100 overall intelligence score from dimension scores.
    Unavailable dimensions use neutral (50.0) — their weight is NOT redistributed.
    This prevents artificial inflation when few engines are available.
    """
    _score_map = {
        "financials":       intel.financial_score,
        "earnings":         intel.earnings_score,
        "business_quality": intel.business_quality_score,
        "valuation":        intel.valuation_score,
        "growth":           intel.growth_score,
        "management":       intel.management_score,
        "ownership":        intel.ownership_score,
        "opportunity":      intel.opportunity_score,
    }

    pairs = [
        (_score_map[engine], ENGINE_WEIGHTS[engine])
        for engine in SCORED_ENGINES
    ]

    raw = weighted_average(pairs, neutral=50.0, redistribute=False)
    return round(clamp(raw), 2)


# ── Narrative summary builder ─────────────────────────────────────────────────

def _dim(engine: str, score: Optional[float], label: str) -> DimensionSummary:
    return DimensionSummary(
        engine=engine,
        score=score,
        label=label,
        headline=f"{engine.replace('_', ' ').title()}: {label}" if score is None
                  else f"{engine.replace('_', ' ').title()}: {label} ({score:.0f}/100)",
        available=score is not None,
    )


def build_summary(
    ticker:       str,
    company_name: Optional[str],
    intel:        AggregatedIntelligence,
    conflicts:    Optional[List] = None,
) -> CompanySummary:
    """Assemble a CompanySummary from aggregated intelligence."""
    summary = CompanySummary(
        ticker=ticker,
        company_name=company_name,
        financial=       _dim("financials",       intel.financial_score,       intel.financial_label),
        earnings=        _dim("earnings",          intel.earnings_score,        intel.earnings_label),
        business_quality=_dim("business_quality",  intel.business_quality_score, intel.business_quality_label),
        valuation=       _dim("valuation",         intel.valuation_score,       intel.valuation_label),
        growth=          _dim("growth",            intel.growth_score,          intel.growth_label),
        management=      _dim("management",        intel.management_score,      intel.management_label),
        ownership=       _dim("ownership",         intel.ownership_score,       intel.ownership_label),
        opportunity=     _dim("opportunity",       intel.opportunity_score,     intel.opportunity_label),
    )

    # Key strengths: top-scoring available dimensions
    scored = [
        (engine, score)
        for engine, score in [
            ("Financial Strength", intel.financial_score),
            ("Earnings Quality",   intel.earnings_score),
            ("Business Quality",   intel.business_quality_score),
            ("Valuation",          intel.valuation_score),
            ("Growth",             intel.growth_score),
            ("Management",         intel.management_score),
            ("Ownership",          intel.ownership_score),
        ]
        if score is not None
    ]
    scored.sort(key=lambda x: x[1], reverse=True)
    summary.key_strengths = [
        f"{name} score: {score:.0f}/100"
        for name, score in scored[:3]
        if score >= 65
    ]

    # Key risks: low-scoring dimensions
    summary.key_risks = [
        f"{name} score: {score:.0f}/100 (below threshold)"
        for name, score in scored
        if score < 40
    ]

    # Conflicts
    if conflicts:
        summary.key_conflicts = [
            f"{c.engine_a} vs {c.engine_b}: {c.assertion_a} / {c.assertion_b}"
            for c in conflicts[:3]
        ]

    # Key opportunities from opportunity snapshot
    opp = intel.opportunity_snapshot
    if opp is not None:
        thesis = getattr(opp, "thesis", None)
        if thesis is not None:
            cats = getattr(thesis, "key_catalysts", []) or []
            summary.key_opportunities = cats[:3]

    return summary


# ── Aggregation engine ────────────────────────────────────────────────────────

class AggregationEngine:
    """
    Stateless per-evaluation aggregation orchestrator.

    Responsibilities:
    - Extract normalised intelligence from all upstream snapshots
    - Compute overall intelligence score
    - Build a human-readable CompanySummary
    """

    def aggregate(
        self,
        ticker:       str,
        snapshot_map: Dict[str, Any],
        company_name: Optional[str] = None,
        conflicts:    Optional[List] = None,
    ) -> AggregatedIntelligence:
        """
        Produce an AggregatedIntelligence from the raw snapshot map.
        """
        return aggregate_intelligence(ticker, snapshot_map)

    def overall_score(self, intel: AggregatedIntelligence) -> float:
        return compute_overall_score(intel)

    def build_summary(
        self,
        ticker:       str,
        company_name: Optional[str],
        intel:        AggregatedIntelligence,
        conflicts:    Optional[List] = None,
    ) -> CompanySummary:
        return build_summary(ticker, company_name, intel, conflicts)
