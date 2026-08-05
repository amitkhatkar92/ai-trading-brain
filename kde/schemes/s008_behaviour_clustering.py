"""S008 — Behaviour Clustering: Which years cluster together by market behaviour?"""
from __future__ import annotations

import math
import statistics
from typing import Dict, List, Tuple

from ..scheme_base import BaseDiscoveryScheme, DiscoveryContext
from ..kde_models import DiscoveryCandidate, EvidenceType

_REGIME_ENC = {
    "BULL_TREND": 1.0, "BEAR_MARKET": -1.0,
    "VOLATILE_MARKET": 0.5, "RANGE_MARKET": 0.0,
}
_VOL_ENC = {
    "LOW": 0.25, "MEDIUM": 0.50, "HIGH": 0.75, "EXTREME": 1.0,
}


def _profile_vector(mp) -> Tuple[float, ...]:
    """Convert YearMarketProfile to a numeric vector for clustering."""
    return (
        _REGIME_ENC.get(mp.dominant_regime, 0.0),
        _VOL_ENC.get(mp.volatility_level, 0.5),
        mp.momentum_strength,
        mp.breadth_score,
        max(-1.0, min(1.0, mp.index_return_ytd)),
    )


def _distance(a: Tuple, b: Tuple) -> float:
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


class BehaviourClusteringScheme(BaseDiscoveryScheme):
    SCHEME_ID           = "S008"
    SCHEME_NAME         = "Behaviour Clustering"
    SCIENTIFIC_QUESTION = (
        "Which years cluster together by market behaviour, and what do they share?"
    )
    _N_CLUSTERS = 3

    def discover(self, ctx: DiscoveryContext) -> List[DiscoveryCandidate]:
        profiles = ctx.market_profiles
        if len(profiles) < 4:
            return []

        years   = sorted(profiles.keys())
        vectors = {yr: _profile_vector(profiles[yr]) for yr in years}

        # Agglomerative single-linkage clustering
        clusters: List[List[int]] = [[yr] for yr in years]

        while len(clusters) > self._N_CLUSTERS:
            min_dist = float("inf")
            merge_i = merge_j = -1
            for i in range(len(clusters)):
                for j in range(i + 1, len(clusters)):
                    # single-linkage: min pairwise distance
                    d = min(
                        _distance(vectors[a], vectors[b])
                        for a in clusters[i]
                        for b in clusters[j]
                    )
                    if d < min_dist:
                        min_dist, merge_i, merge_j = d, i, j
            merged = clusters[merge_i] + clusters[merge_j]
            clusters = [c for k, c in enumerate(clusters) if k not in (merge_i, merge_j)]
            clusters.append(merged)

        candidates = []
        for idx, cluster_years in enumerate(sorted(clusters, key=lambda c: min(c))):
            if len(cluster_years) < 2:
                continue
            vecs = [vectors[yr] for yr in cluster_years]
            centroid = tuple(statistics.mean(v[i] for v in vecs) for i in range(len(vecs[0])))

            # Compute intra-cluster cohesion (avg distance to centroid)
            avg_dist = statistics.mean(_distance(v, centroid) for v in vecs)
            cohesion = max(0.0, 1.0 - avg_dist / 2.0)

            # Characterise cluster
            pers_list  = [profiles[yr].market_personality for yr in cluster_years]
            common_pers = max(set(pers_list), key=pers_list.count)
            raw_score  = cohesion * 0.6 + min(1.0, len(cluster_years) / len(years)) * 0.4

            ev = self._make_evidence(
                evidence_type       = EvidenceType.PATTERN.value,
                description         = f"Cluster {idx+1}: years {sorted(cluster_years)} share behaviour",
                data_points         = len(cluster_years),
                years_observed      = sorted(cluster_years),
                regimes_observed    = list({profiles[yr].dominant_regime for yr in cluster_years}),
                statistical_support = {
                    "cohesion":       round(cohesion, 4),
                    "avg_dist":       round(avg_dist, 4),
                    "cluster_size":   len(cluster_years),
                },
                raw_values = {
                    "years":          sorted(cluster_years),
                    "centroid_regime": round(centroid[0], 2),
                },
            )
            candidates.append(self._candidate(
                question  = self.SCIENTIFIC_QUESTION,
                answer    = (
                    f"Cluster {idx+1}: years {sorted(cluster_years)} behave similarly "
                    f"(cohesion={cohesion:.2f}, personality={common_pers})."
                ),
                evidence          = [ev],
                raw_score         = raw_score,
                years_observed    = sorted(cluster_years),
                regimes_observed  = list({profiles[yr].dominant_regime for yr in cluster_years}),
                suggested_followup = [
                    "Do these years share the same winner DNA?",
                    "Can cluster membership be predicted before year-end?",
                ],
                novelty_hint  = 0.50,
                impact_hint   = 0.40,
            ))

        candidates.sort(key=lambda c: c.raw_score, reverse=True)
        return candidates
