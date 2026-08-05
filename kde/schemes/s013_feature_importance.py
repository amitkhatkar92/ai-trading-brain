"""S013 — Feature Importance: Which features discriminate winners from losers most?"""
from __future__ import annotations

import statistics
from typing import Dict, List

from ..scheme_base import BaseDiscoveryScheme, DiscoveryContext
from ..kde_models import DiscoveryCandidate, EvidenceType


class FeatureImportanceScheme(BaseDiscoveryScheme):
    SCHEME_ID           = "S013"
    SCHEME_NAME         = "Feature Importance"
    SCIENTIFIC_QUESTION = (
        "Which individual features discriminate winners from losers most consistently?"
    )

    def discover(self, ctx: DiscoveryContext) -> List[DiscoveryCandidate]:
        snaps = ctx.dna_snapshots
        if not snaps:
            return []

        winner_counts: Dict[str, int] = {}
        loser_counts:  Dict[str, int] = {}
        total_years = len(snaps)

        for ds in snaps.values():
            for dna_id in ds.winner_dna:
                feat = dna_id.split("::")[0]
                winner_counts[feat] = winner_counts.get(feat, 0) + 1
            for dna_id in ds.loser_dna:
                feat = dna_id.split("::")[0]
                loser_counts[feat] = loser_counts.get(feat, 0) + 1

        all_features = sorted(set(winner_counts) | set(loser_counts))
        if not all_features:
            return []

        candidates = []
        for feat in all_features:
            w = winner_counts.get(feat, 0)
            l = loser_counts.get(feat, 0)
            total = w + l
            if total < 1:
                continue

            # Discriminative score: +1 = always winner, -1 = always loser, 0 = neutral
            disc_score = (w - l) / (total + 1e-9)
            # Prevalence score: how often does this feature appear at all
            prevalence = total / (total_years * 2)  # max is 2 (winner + loser each year)

            importance = abs(disc_score) * min(1.0, prevalence * 3)
            if importance < ctx.config.min_raw_score * 0.5:
                continue

            years_obs = sorted({
                yr for yr, ds in snaps.items()
                if any(feat in dna.split("::")[0] for dna in ds.winner_dna + ds.loser_dna)
            })
            direction = "WINNER_PREDICTOR" if disc_score > 0 else "LOSER_PREDICTOR"
            ev = self._make_evidence(
                evidence_type    = EvidenceType.STATISTICAL.value,
                description = (
                    f"`{feat}`: winner appearances={w}, loser appearances={l}, "
                    f"discriminative score={disc_score:.2f}"
                ),
                data_points         = total,
                years_observed      = years_obs,
                regimes_observed    = ctx.all_regimes,
                statistical_support = {
                    "discriminative_score": round(disc_score, 4),
                    "winner_appearances":   w,
                    "loser_appearances":    l,
                    "prevalence":           round(prevalence, 4),
                },
                raw_values = {
                    "feature":   feat,
                    "direction": direction,
                    "importance": round(importance, 4),
                },
            )
            candidates.append(self._candidate(
                question = self.SCIENTIFIC_QUESTION,
                answer = (
                    f"`{feat}` is a {direction} (score={disc_score:+.2f}): "
                    f"appears {w}x in winner DNA vs {l}x in loser DNA across {len(years_obs)} years."
                ),
                evidence          = [ev],
                raw_score         = min(1.0, importance * 1.5),
                years_observed    = years_obs,
                regimes_observed  = ctx.all_regimes,
                suggested_followup = [
                    f"Test {feat} as a primary filter in strategy selection.",
                    "Study whether importance varies by volatility regime.",
                ],
                novelty_hint  = 0.40,
                impact_hint   = min(1.0, abs(disc_score) * 1.2),
                feature_names = [feat],
            ))

        candidates.sort(key=lambda c: c.raw_score, reverse=True)
        return candidates
