"""
discovery_scorer.py — Scores DiscoveryCandidates and promotes to Discovery objects.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List

from .kde_models import (
    Discovery, DiscoveryCandidate, DiscoveryScore, DiscoveryStatus,
    PotentialValue,
)
from .kde_config import KDEConfig

# Name map for scheme IDs
_SCHEME_NAMES: Dict[str, str] = {
    "S001": "Winner DNA",
    "S002": "Loser DNA",
    "S003": "Hidden Feature Interaction",
    "S004": "Feature Stability",
    "S005": "Sector Rotation",
    "S006": "Regime Behaviour",
    "S007": "Market Personality",
    "S008": "Behaviour Clustering",
    "S009": "DNA Evolution",
    "S010": "Edge Evolution",
    "S011": "Failure Analysis",
    "S012": "Institutional Activity",
    "S013": "Feature Importance",
    "S014": "Cross-Year Persistence",
    "S015": "Context Dependency",
}


class DiscoveryScorer:
    """Scores DiscoveryCandidates and promotes qualifying ones to Discovery."""

    def score_and_promote(
        self,
        candidates: List[DiscoveryCandidate],
        config:     KDEConfig,
    ) -> List[Discovery]:
        discoveries: List[Discovery] = []
        counters:    Dict[str, int]  = {}

        for candidate in candidates:
            score = self._compute_score(candidate, config)
            if score.overall < config.min_overall_score:
                continue
            if len(candidate.years_observed) < config.min_years_observed:
                continue

            sid      = candidate.scheme_id
            counters[sid] = counters.get(sid, 0) + 1
            date_tag = datetime.now(timezone.utc).strftime("%Y%m%d")
            disc_id  = f"KDE-{sid}-{date_tag}-{counters[sid]:04d}"

            discoveries.append(Discovery(
                discovery_id      = disc_id,
                scheme_id         = sid,
                scheme_name       = _SCHEME_NAMES.get(sid, sid),
                question          = candidate.question,
                answer            = candidate.answer,
                evidence          = candidate.evidence,
                score             = score,
                years_observed    = candidate.years_observed,
                regimes_observed  = candidate.regimes_observed,
                potential_value   = self._potential_value(score.overall),
                suggested_followup = candidate.suggested_followup,
                status            = DiscoveryStatus.ACTIVE.value,
                sd_recommendation = None,
                feature_names     = candidate.feature_names,
                dna_ids           = candidate.dna_ids,
                generated_at      = datetime.now(timezone.utc).isoformat(),
            ))

            if len(discoveries) >= config.max_discoveries:
                break

        discoveries.sort(key=lambda d: d.score.overall, reverse=True)
        return discoveries

    def _compute_score(
        self, candidate: DiscoveryCandidate, config: KDEConfig
    ) -> DiscoveryScore:
        n_years = max(len(candidate.years_observed), 1)

        # scientific_confidence: scheme raw_score (primary evidence strength)
        sc = candidate.raw_score

        # novelty: scheme hint, but capped by how common the discovery is
        nv = candidate.novelty_hint

        # reproducibility: more years = more reproducible (caps at ~8 years)
        rep = min(1.0, n_years / 8.0)

        # generality: fraction of known regimes covered
        n_all_regimes = 4  # BULL / BEAR / VOLATILE / RANGE
        gen = min(1.0, len(set(candidate.regimes_observed)) / n_all_regimes)

        # business_impact: scheme hint
        bi = candidate.impact_hint

        return DiscoveryScore.from_components(sc, nv, rep, gen, bi)

    @staticmethod
    def _potential_value(overall: float) -> str:
        if overall >= 0.75:
            return PotentialValue.VERY_HIGH.value
        if overall >= 0.60:
            return PotentialValue.HIGH.value
        if overall >= 0.45:
            return PotentialValue.MEDIUM.value
        return PotentialValue.LOW.value
