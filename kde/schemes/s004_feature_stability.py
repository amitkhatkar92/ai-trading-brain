"""S004 — Feature Stability: Which features maintain consistent predictive power?"""
from __future__ import annotations

import statistics
from typing import List

from ..scheme_base import BaseDiscoveryScheme, DiscoveryContext
from ..kde_models import DiscoveryCandidate, EvidenceType


class FeatureStabilityScheme(BaseDiscoveryScheme):
    SCHEME_ID           = "S004"
    SCHEME_NAME         = "Feature Stability"
    SCIENTIFIC_QUESTION = (
        "Which features maintain consistent confidence across all market years?"
    )
    _STABLE_CV = 0.15   # coefficient of variation threshold (lower = more stable)

    def discover(self, ctx: DiscoveryContext) -> List[DiscoveryCandidate]:
        snaps = ctx.dna_snapshots
        if len(snaps) < 2:
            return []

        # Gather confidence of each feature across years
        feature_confs: dict = {}   # feature_name -> [confidence per year]
        for yr, ds in snaps.items():
            for dna_id, conf in ds.confidence_by_id.items():
                feat = dna_id.split("::")[0]
                feature_confs.setdefault(feat, []).append((yr, conf))

        candidates = []
        for feat, entries in feature_confs.items():
            if len(entries) < 2:
                continue
            years_list = [e[0] for e in entries]
            confs_list = [e[1] for e in entries]
            mean_c = statistics.mean(confs_list)
            std_c  = statistics.stdev(confs_list)
            cv     = std_c / max(mean_c, 0.01)

            is_stable = cv <= self._STABLE_CV and mean_c >= 0.5
            if not is_stable:
                continue

            raw_score = max(0.0, (1.0 - cv) * mean_c)
            ev = self._make_evidence(
                evidence_type       = EvidenceType.STATISTICAL.value,
                description = (
                    f"`{feat}` has mean confidence {mean_c:.2f} with "
                    f"CV={cv:.3f} (stable threshold: {self._STABLE_CV})"
                ),
                data_points         = len(entries),
                years_observed      = sorted(years_list),
                regimes_observed    = ctx.all_regimes,
                statistical_support = {
                    "mean_confidence": round(mean_c, 4),
                    "std_confidence":  round(std_c, 4),
                    "cv":              round(cv, 4),
                },
                raw_values = {"confidence_by_year": dict(entries)},
            )
            candidates.append(self._candidate(
                question  = self.SCIENTIFIC_QUESTION,
                answer    = (
                    f"`{feat}` is a stable predictor: mean confidence {mean_c:.2f}, "
                    f"CV={cv:.3f} across {len(entries)} years."
                ),
                evidence          = [ev],
                raw_score         = raw_score,
                years_observed    = sorted(years_list),
                regimes_observed  = ctx.all_regimes,
                suggested_followup = [
                    f"Verify {feat} stability in different volatility regimes.",
                    "Compare stability against model-selected features.",
                ],
                novelty_hint  = 0.40,
                impact_hint   = min(1.0, mean_c * 1.1),
                feature_names = [feat],
            ))

        candidates.sort(key=lambda c: c.raw_score, reverse=True)
        return candidates
