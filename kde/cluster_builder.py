"""
cluster_builder.py — Groups discoveries into thematic DiscoveryCluster objects.
"""
from __future__ import annotations

import statistics
from typing import Dict, List

from .kde_models import Discovery, DiscoveryCluster


# Scheme-to-theme mapping
_SCHEME_THEME: Dict[str, str] = {
    "S001": "DNA",   "S002": "DNA",
    "S003": "INTERACTION",
    "S004": "STABILITY",
    "S005": "SECTOR",
    "S006": "REGIME", "S007": "REGIME",
    "S008": "BEHAVIOUR",
    "S009": "EVOLUTION", "S010": "EVOLUTION", "S011": "FAILURE",
    "S012": "INSTITUTIONAL",
    "S013": "FEATURE",
    "S014": "PERSISTENCE",
    "S015": "CONTEXT",
}

_THEME_DESCRIPTIONS: Dict[str, str] = {
    "DNA":           "Winner and loser DNA pattern discoveries",
    "INTERACTION":   "Hidden feature interaction and co-occurrence patterns",
    "STABILITY":     "Feature stability and consistency across years",
    "SECTOR":        "Sector rotation and leadership discoveries",
    "REGIME":        "Market regime and personality behaviour",
    "BEHAVIOUR":     "Year behaviour clustering",
    "EVOLUTION":     "DNA and edge evolution over time",
    "FAILURE":       "Pattern failure and disappearance analysis",
    "INSTITUTIONAL": "Institutional activity correlations",
    "FEATURE":       "Feature importance rankings",
    "PERSISTENCE":   "Cross-year persistence of institutional knowledge",
    "CONTEXT":       "Context-specific pattern dependencies",
}


class ClusterBuilder:
    """Groups discoveries into thematic clusters using scheme-derived themes."""

    def build(self, discoveries: List[Discovery]) -> List[DiscoveryCluster]:
        # Group by theme
        theme_map: Dict[str, List[Discovery]] = {}
        for d in discoveries:
            theme = _SCHEME_THEME.get(d.scheme_id, "OTHER")
            theme_map.setdefault(theme, []).append(d)

        clusters: List[DiscoveryCluster] = []
        for idx, (theme, group) in enumerate(sorted(theme_map.items()), start=1):
            if not group:
                continue

            avg_score = statistics.mean(d.score.overall for d in group)
            # Cohesion = fraction sharing at least one feature or DNA id
            if len(group) < 2:
                cohesion = 1.0
            else:
                shared_count = 0
                total_pairs  = 0
                for i, da in enumerate(group):
                    for db in group[i + 1:]:
                        total_pairs += 1
                        if (set(da.feature_names) & set(db.feature_names) or
                                set(da.dna_ids) & set(db.dna_ids)):
                            shared_count += 1
                cohesion = shared_count / max(total_pairs, 1)

            clusters.append(DiscoveryCluster(
                cluster_id     = f"KDE-CL-{idx:03d}",
                name           = f"{theme} Discoveries",
                theme          = theme,
                discoveries    = [d.discovery_id for d in group],
                cohesion_score = round(cohesion, 4),
                description    = _THEME_DESCRIPTIONS.get(
                    theme, f"Discoveries in theme {theme}"
                ) + f" ({len(group)} discoveries, avg score {avg_score:.2f})",
            ))

        clusters.sort(key=lambda c: len(c.discoveries), reverse=True)
        return clusters
