"""S011 — Failure Analysis: Which DNA patterns failed and when?"""
from __future__ import annotations

import statistics
from typing import List

from ..scheme_base import BaseDiscoveryScheme, DiscoveryContext
from ..kde_models import DiscoveryCandidate, EvidenceType


class FailureAnalysisScheme(BaseDiscoveryScheme):
    SCHEME_ID           = "S011"
    SCHEME_NAME         = "Failure Analysis"
    SCIENTIFIC_QUESTION = (
        "Which DNA patterns were once strong but then disappeared — "
        "and what caused the failure?"
    )

    def discover(self, ctx: DiscoveryContext) -> List[DiscoveryCandidate]:
        records = ctx.dna_records
        if not records:
            return []

        candidates = []

        # DISAPPEARING: was strong, now absent
        disappearing = [
            r for r in records
            if r.lifecycle_label == "DISAPPEARING" and r.survival_score > 0
        ]

        for r in disappearing:
            if not r.years_present:
                continue
            last_present = max(r.years_present)
            years_absent = [y for y in ctx.years if y > last_present]

            # Peak confidence before disappearance
            peak_conf = max(r.confidence_by_year.values()) if r.confidence_by_year else 0.0
            if peak_conf < 0.50:
                continue   # wasn't strong enough to be notable

            raw_score = min(1.0, peak_conf * (len(r.years_present) / max(len(ctx.years), 1)) * 1.5)

            # What was the regime when it was last present?
            last_regime = None
            profiles = ctx.market_profiles
            if last_present in profiles:
                last_regime = profiles[last_present].dominant_regime

            ev = self._make_evidence(
                evidence_type    = EvidenceType.HISTORICAL.value,
                description = (
                    f"{r.dna_id}: peak confidence {peak_conf:.2f} until {last_present}, "
                    f"absent for {len(years_absent)} year(s)"
                ),
                data_points         = len(r.years_present),
                years_observed      = sorted(r.years_present),
                regimes_observed    = r.regimes_observed or ctx.all_regimes[:1],
                statistical_support = {
                    "peak_confidence":  round(peak_conf, 4),
                    "last_seen":        last_present,
                    "years_absent":     len(years_absent),
                },
                raw_values = {
                    "years_present":       sorted(r.years_present),
                    "confidence_by_year":  {str(k): v for k, v in r.confidence_by_year.items()},
                    "last_regime":         last_regime,
                },
            )
            candidates.append(self._candidate(
                question = self.SCIENTIFIC_QUESTION,
                answer = (
                    f"`{r.dna_id}` peaked at {peak_conf:.2f} confidence in {last_present} "
                    f"then disappeared (absent {len(years_absent)} year(s)). "
                    f"Last seen in {last_regime or 'unknown'} regime."
                ),
                evidence          = [ev],
                raw_score         = raw_score,
                years_observed    = sorted(r.years_present),
                regimes_observed  = r.regimes_observed or ctx.all_regimes[:1],
                suggested_followup = [
                    f"Study regime change after {last_present} to explain failure.",
                    "Was this DNA crowded out by structural market change?",
                    "Monitor for re-emergence in future years.",
                ],
                novelty_hint  = 0.60,
                impact_hint   = 0.45,
                feature_names = [r.feature_name],
                dna_ids       = [r.dna_id],
            ))

        candidates.sort(key=lambda c: c.raw_score, reverse=True)
        return candidates
