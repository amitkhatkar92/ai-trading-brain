"""S010 — Edge Evolution: Which high-confidence edges are strengthening or fading?"""
from __future__ import annotations

import statistics
from typing import List

from ..scheme_base import BaseDiscoveryScheme, DiscoveryContext
from ..kde_models import DiscoveryCandidate, EvidenceType


class EdgeEvolutionScheme(BaseDiscoveryScheme):
    SCHEME_ID           = "S010"
    SCHEME_NAME         = "Edge Evolution"
    SCIENTIFIC_QUESTION = (
        "Which trading edges are strengthening, stable, or fading across years?"
    )

    def discover(self, ctx: DiscoveryContext) -> List[DiscoveryCandidate]:
        records = ctx.edge_records
        if not records:
            return []

        candidates = []
        by_trend: dict = {}
        for r in records:
            by_trend.setdefault(r.trend, []).append(r)

        # Discovery 1: strongest sustained edges
        rising = sorted(
            by_trend.get("RISING", []),
            key=lambda r: r.peak_confidence, reverse=True,
        )[:5]
        if rising:
            years_obs = sorted({yr for r in rising for yr in r.years_active})
            raw_score = 0.72
            ev = self._make_evidence(
                evidence_type    = EvidenceType.HISTORICAL.value,
                description      = f"{len(rising)} edges with RISING confidence trend",
                data_points      = len(rising),
                years_observed   = years_obs,
                regimes_observed = ctx.all_regimes[:2],
                statistical_support = {
                    "count":            len(rising),
                    "avg_peak_conf":    round(statistics.mean(r.peak_confidence for r in rising), 4),
                    "max_peak_conf":    round(max(r.peak_confidence for r in rising), 4),
                },
                raw_values = {"top_edges": [r.edge_id for r in rising]},
            )
            candidates.append(self._candidate(
                question  = self.SCIENTIFIC_QUESTION,
                answer    = (
                    f"Top rising edges: {[r.edge_id for r in rising[:3]]}. "
                    "Institutional confidence is growing in these patterns."
                ),
                evidence          = [ev],
                raw_score         = raw_score,
                years_observed    = years_obs,
                regimes_observed  = ctx.all_regimes[:2],
                suggested_followup = [
                    "Promote top rising edge to IDR after SD review.",
                    "Study what structural factor drives rising confidence.",
                ],
                novelty_hint  = 0.55,
                impact_hint   = 0.70,
                feature_names = [r.feature_name for r in rising],
                dna_ids       = [r.edge_id for r in rising],
            ))

        # Discovery 2: fading edges
        falling = sorted(
            by_trend.get("FALLING", []),
            key=lambda r: r.peak_confidence, reverse=True,
        )[:5]
        if falling:
            years_obs = sorted({yr for r in falling for yr in r.years_active})
            raw_score = 0.60
            ev = self._make_evidence(
                evidence_type    = EvidenceType.HISTORICAL.value,
                description      = f"{len(falling)} edges with FALLING confidence trend",
                data_points      = len(falling),
                years_observed   = years_obs,
                regimes_observed = ctx.all_regimes[:2],
                statistical_support = {
                    "count":         len(falling),
                    "avg_peak_conf": round(statistics.mean(r.peak_confidence for r in falling), 4),
                },
                raw_values = {"fading_edges": [r.edge_id for r in falling]},
            )
            candidates.append(self._candidate(
                question  = self.SCIENTIFIC_QUESTION,
                answer    = (
                    f"{len(falling)} edges are fading: {[r.edge_id for r in falling[:3]]}. "
                    "These patterns are losing institutional support."
                ),
                evidence          = [ev],
                raw_score         = raw_score,
                years_observed    = years_obs,
                regimes_observed  = ctx.all_regimes[:2],
                suggested_followup = [
                    "Schedule for retirement review in next HKAP run.",
                    "Investigate whether market microstructure change caused fade.",
                ],
                novelty_hint  = 0.50,
                impact_hint   = 0.55,
                feature_names = [r.feature_name for r in falling],
                dna_ids       = [r.edge_id for r in falling],
            ))

        # Discovery 3: longest active edge
        all_edges = sorted(records, key=lambda r: len(r.years_active), reverse=True)
        if all_edges:
            longest = all_edges[0]
            raw_score = min(1.0, len(longest.years_active) / max(len(ctx.years), 1))
            ev = self._make_evidence(
                evidence_type    = EvidenceType.HISTORICAL.value,
                description      = f"Longest active edge: {longest.edge_id} ({len(longest.years_active)} years)",
                data_points      = len(longest.years_active),
                years_observed   = sorted(longest.years_active),
                regimes_observed = ctx.all_regimes,
                statistical_support = {
                    "active_years":   len(longest.years_active),
                    "peak_confidence": longest.peak_confidence,
                    "trend":          longest.trend,
                },
                raw_values = {"edge_id": longest.edge_id, "years": sorted(longest.years_active)},
            )
            candidates.append(self._candidate(
                question  = self.SCIENTIFIC_QUESTION,
                answer    = (
                    f"`{longest.edge_id}` is the most persistent edge: "
                    f"active in {len(longest.years_active)} consecutive years, "
                    f"peak confidence {longest.peak_confidence:.2f}."
                ),
                evidence          = [ev],
                raw_score         = raw_score,
                years_observed    = sorted(longest.years_active),
                regimes_observed  = ctx.all_regimes,
                suggested_followup = [
                    "Is this edge approaching STABLE status?",
                    "Verify robustness to volatility regime changes.",
                ],
                novelty_hint  = 0.40,
                impact_hint   = 0.75,
                feature_names = [longest.feature_name],
                dna_ids       = [longest.edge_id],
            ))

        candidates.sort(key=lambda c: c.raw_score, reverse=True)
        return candidates
