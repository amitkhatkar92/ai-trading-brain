"""S009 — DNA Evolution: How has the DNA landscape changed over the years?"""
from __future__ import annotations

import statistics
from typing import List

from ..scheme_base import BaseDiscoveryScheme, DiscoveryContext
from ..kde_models import DiscoveryCandidate, EvidenceType


class DNAEvolutionScheme(BaseDiscoveryScheme):
    SCHEME_ID           = "S009"
    SCHEME_NAME         = "DNA Evolution"
    SCIENTIFIC_QUESTION = (
        "How has the institutional DNA landscape evolved — "
        "what emerged, strengthened, weakened, or disappeared?"
    )

    def discover(self, ctx: DiscoveryContext) -> List[DiscoveryCandidate]:
        records = ctx.dna_records
        if not records:
            return []

        candidates = []

        # Group by lifecycle label
        by_label: dict = {}
        for r in records:
            by_label.setdefault(r.lifecycle_label, []).append(r)

        n_total = len(records)

        for label, group in by_label.items():
            if not group:
                continue
            frac = len(group) / n_total
            avg_survival = statistics.mean(r.survival_score for r in group)
            all_years = sorted({yr for r in group for yr in r.years_present})
            all_regimes = sorted({reg for r in group for reg in r.regimes_observed})

            raw_score = min(1.0, frac * 1.5 + avg_survival * 0.3)

            feature_names = [r.feature_name for r in group[:10]]

            ev = self._make_evidence(
                evidence_type       = EvidenceType.HISTORICAL.value,
                description         = f"{len(group)} DNA patterns classified as {label}",
                data_points         = len(group),
                years_observed      = all_years,
                regimes_observed    = all_regimes,
                statistical_support = {
                    "count":        len(group),
                    "fraction":     round(frac, 4),
                    "avg_survival": round(avg_survival, 4),
                },
                raw_values = {"sample_dna": [r.dna_id for r in group[:5]]},
            )
            candidates.append(self._candidate(
                question = self.SCIENTIFIC_QUESTION,
                answer = (
                    f"{len(group)} DNA patterns ({frac:.0%} of total) "
                    f"have lifecycle label {label}. "
                    f"Avg survival score: {avg_survival:.2f}."
                ),
                evidence          = [ev],
                raw_score         = raw_score,
                years_observed    = all_years,
                regimes_observed  = all_regimes,
                suggested_followup = [
                    f"Study what market conditions cause {label} patterns.",
                    f"For EMERGING: is the pattern new or previously ignored?",
                ],
                novelty_hint  = 0.55 if label in ("EMERGING", "DISAPPEARING") else 0.35,
                impact_hint   = 0.50 if label in ("STABLE", "STRENGTHENING") else 0.30,
                feature_names = feature_names[:5],
            ))

        # Strengthening trend discovery
        strengthening = by_label.get("STRENGTHENING", [])
        if strengthening:
            top = sorted(strengthening, key=lambda r: r.survival_score, reverse=True)[:5]
            years_obs = sorted({yr for r in top for yr in r.years_present})
            raw_score = 0.70
            ev = self._make_evidence(
                evidence_type       = EvidenceType.PATTERN.value,
                description         = f"Top {len(top)} strengthening DNA patterns",
                data_points         = len(top),
                years_observed      = years_obs,
                regimes_observed    = ctx.all_regimes[:2],
                statistical_support = {"count": len(top), "avg_survival": round(
                    statistics.mean(r.survival_score for r in top), 4
                )},
                raw_values = {"top_dna": [r.dna_id for r in top]},
            )
            candidates.append(self._candidate(
                question  = self.SCIENTIFIC_QUESTION,
                answer    = (
                    f"Top strengthening DNA: {[r.dna_id for r in top]}. "
                    "These patterns are gaining institutional confidence over time."
                ),
                evidence          = [ev],
                raw_score         = raw_score,
                years_observed    = years_obs,
                regimes_observed  = ctx.all_regimes[:2],
                suggested_followup = [
                    "Are these patterns related to a structural market shift?",
                    "Extend study to confirm strengthening through next year.",
                ],
                novelty_hint  = 0.60,
                impact_hint   = 0.65,
                feature_names = [r.feature_name for r in top],
                dna_ids       = [r.dna_id for r in top],
            ))

        candidates.sort(key=lambda c: c.raw_score, reverse=True)
        return candidates
