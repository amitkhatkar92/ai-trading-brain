"""S003 — Hidden Feature Interaction: Which feature pairs are more powerful combined?"""
from __future__ import annotations

import math
from itertools import combinations
from typing import List

from ..scheme_base import BaseDiscoveryScheme, DiscoveryContext
from ..kde_models import DiscoveryCandidate, EvidenceType


class HiddenFeatureInteractionScheme(BaseDiscoveryScheme):
    SCHEME_ID           = "S003"
    SCHEME_NAME         = "Hidden Feature Interaction"
    SCIENTIFIC_QUESTION = (
        "Which pairs of features co-appear in winner DNA significantly more than chance?"
    )
    _MIN_LIFT = 1.25   # discovery threshold: co-occurrence lift >= 1.25

    def discover(self, ctx: DiscoveryContext) -> List[DiscoveryCandidate]:
        snaps   = ctx.dna_snapshots
        n_years = len(snaps)
        if n_years < 2:
            return []

        # Build per-year winner feature sets
        winner_features_by_year: list = []
        for yr in sorted(snaps.keys()):
            ds = snaps[yr]
            feats = {dna.split("::")[0] for dna in ds.winner_dna}
            winner_features_by_year.append(feats)

        all_features = sorted({f for fs in winner_features_by_year for f in fs})
        if len(all_features) < 2:
            return []

        # P(A) per feature
        p_a: dict = {}
        for feat in all_features:
            p_a[feat] = sum(1 for fs in winner_features_by_year if feat in fs) / n_years

        candidates = []
        for feat_a, feat_b in combinations(all_features, 2):
            co_years = [yr for yr, fs in zip(sorted(snaps.keys()), winner_features_by_year)
                        if feat_a in fs and feat_b in fs]
            p_ab = len(co_years) / n_years
            pa   = p_a[feat_a]
            pb   = p_a[feat_b]
            expected = pa * pb
            if expected < 1e-9:
                continue
            lift = p_ab / expected

            if lift < self._MIN_LIFT or p_ab < 0.2:
                continue

            raw_score = min(1.0, (lift - 1.0) / 2.0 * 0.6 + p_ab * 0.4)
            ev = self._make_evidence(
                evidence_type       = EvidenceType.STATISTICAL.value,
                description = (
                    f"{feat_a} and {feat_b} co-appear in winner DNA with lift={lift:.2f} "
                    f"(co-occurrence {p_ab:.0%} vs expected {expected:.0%})"
                ),
                data_points         = len(co_years),
                years_observed      = co_years,
                regimes_observed    = ctx.all_regimes[:2],
                statistical_support = {
                    "lift":          round(lift, 4),
                    "p_ab":          round(p_ab, 4),
                    "p_a":           round(pa, 4),
                    "p_b":           round(pb, 4),
                    "expected_p_ab": round(expected, 4),
                },
                raw_values = {"co_years": co_years, "lift": lift},
            )
            candidates.append(self._candidate(
                question = self.SCIENTIFIC_QUESTION,
                answer = (
                    f"`{feat_a}` + `{feat_b}` co-appear in winner DNA {p_ab:.0%} of years "
                    f"(lift={lift:.2f} vs independence baseline)."
                ),
                evidence          = [ev],
                raw_score         = raw_score,
                years_observed    = co_years,
                regimes_observed  = ctx.all_regimes[:2],
                suggested_followup = [
                    f"Build composite signal: {feat_a} AND {feat_b} simultaneously.",
                    "Verify interaction persists in out-of-sample years.",
                ],
                novelty_hint  = min(1.0, (lift - 1.0) / 3.0),
                impact_hint   = 0.55,
                feature_names = [feat_a, feat_b],
            ))

        candidates.sort(key=lambda c: c.raw_score, reverse=True)
        return candidates
