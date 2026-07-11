"""iios/investment/market/sector_rotation/sector_confidence.py
Computes SectorConfidenceScore from all engine outputs.
"""
from __future__ import annotations

from typing import Dict, List, Optional

from iios.investment.market.sector_rotation.models import (
    CapitalFlowProfile,
    RotationSignal,
    SectorConfidenceScore,
    SectorLifecycleProfile,
    SectorPerformance,
    SectorRankEntry,
)


def compute_confidence(
    sector_rankings:  List[SectorRankEntry],
    sector_perfs:     Dict[str, SectorPerformance],
    lifecycle_profiles: Dict[str, SectorLifecycleProfile],
    capital_flows:    Dict[str, CapitalFlowProfile],
    rotation_signals: List[RotationSignal],
    n_bars_warm:      int,
    min_bars:         int = 10,
) -> SectorConfidenceScore:
    """Aggregate confidence across all sub-engines."""

    # ── leadership confidence ─────────────────────────────────────────────────
    if sector_rankings:
        top_score   = sector_rankings[0].composite_score
        # High confidence when top sector clearly leads
        lead_spread = top_score - (sector_rankings[1].composite_score if len(sector_rankings) > 1 else 0.0)
        leadership_conf = min(1.0, max(0.0, lead_spread / 15.0))
    else:
        leadership_conf = 0.0

    # ── rotation confidence ────────────────────────────────────────────────────
    confirmed = [s for s in rotation_signals if s.confirmed]
    rotation_conf = (
        sum(s.confidence for s in confirmed) / len(confirmed)
        if confirmed else 0.0
    )

    # ── strength score (mean composite across sectors) ────────────────────────
    if sector_rankings:
        strength = sum(e.composite_score for e in sector_rankings) / len(sector_rankings)
    else:
        strength = 50.0

    # ── flow confidence ────────────────────────────────────────────────────────
    if capital_flows:
        flow_intensities = [f.flow_intensity for f in capital_flows.values()]
        flow_conf = sum(flow_intensities) / len(flow_intensities)
    else:
        flow_conf = 0.0

    # ── warm-up damping ────────────────────────────────────────────────────────
    warmup_factor = min(1.0, n_bars_warm / max(min_bars, 1))

    overall = (
        leadership_conf * 0.25
        + rotation_conf * 0.25
        + (strength / 100.0) * 0.30
        + flow_conf * 0.20
    ) * warmup_factor * 100.0

    return SectorConfidenceScore(
        leadership_confidence=leadership_conf * warmup_factor,
        rotation_confidence=rotation_conf   * warmup_factor,
        strength_score=strength             * warmup_factor,
        flow_confidence=flow_conf           * warmup_factor,
        overall_score=max(0.0, min(100.0, overall)),
    )
