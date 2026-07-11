"""iios/investment/market/breadth/breadth_confidence.py
Produces a BreadthConfidenceScore from current engine state.
"""
from __future__ import annotations

from iios.investment.market.breadth.models import (
    BreadthConfidenceScore,
    BreadthData,
    BreadthRegimeSnapshot,
    MarketHealthSnapshot,
    ParticipationSnapshot,
    UniverseSnapshot,
)
from iios.investment.market.breadth.breadth_quality import BreadthQualityScorer
from iios.investment.market.breadth import internal_strength as ist


class BreadthConfidenceCalculator:
    def __init__(self) -> None:
        self._quality_scorer = BreadthQualityScorer()

    def calculate(
        self,
        universe: UniverseSnapshot,
        breadth: BreadthData,
        participation: ParticipationSnapshot,
        health: MarketHealthSnapshot,
        regime_snapshot: BreadthRegimeSnapshot,
    ) -> BreadthConfidenceScore:
        quality = self._quality_scorer.score(universe)
        n       = len(universe.observations)

        # ── Breadth confidence ────────────────────────────────────────────
        size_norm      = min(1.0, n / 50)
        breadth_conf   = quality * size_norm * breadth.breadth_stability

        # ── Participation confidence ──────────────────────────────────────
        n_sectors      = len(participation.sector_participation)
        sector_cov     = min(1.0, n_sectors / 5)
        tiers = {
            "large":  participation.large_cap_pct,
            "mid":    participation.mid_cap_pct,
            "small":  participation.small_cap_pct,
        }
        tier_cov       = sum(1 for v in tiers.values() if v > 0) / len(tiers)
        part_conf      = sector_cov * 0.60 + tier_cov * 0.40

        # ── Leadership confidence ─────────────────────────────────────────
        leadership_conf = regime_snapshot.confidence * max(0.2, breadth_conf)

        # ── Internal strength score (0-100) ───────────────────────────────
        strength        = ist.internal_strength_score(breadth, participation)
        strength_score  = strength * 100

        # ── Overall ───────────────────────────────────────────────────────
        overall = (
            breadth_conf    * 0.35
            + part_conf     * 0.35
            + leadership_conf * 0.30
        ) * 100

        return BreadthConfidenceScore(
            breadth_confidence=round(min(1.0, breadth_conf), 4),
            participation_confidence=round(min(1.0, part_conf), 4),
            leadership_confidence=round(min(1.0, leadership_conf), 4),
            internal_strength_score=round(max(0.0, min(100.0, strength_score)), 2),
            overall_score=round(max(0.0, min(100.0, overall)), 2),
        )
