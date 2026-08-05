"""S012 — Institutional Activity: Does high institutional activity produce better DNA?"""
from __future__ import annotations

import statistics
from typing import List

from ..scheme_base import BaseDiscoveryScheme, DiscoveryContext
from ..kde_models import DiscoveryCandidate, EvidenceType


class InstitutionalActivityScheme(BaseDiscoveryScheme):
    SCHEME_ID           = "S012"
    SCHEME_NAME         = "Institutional Activity"
    SCIENTIFIC_QUESTION = (
        "Does high institutional activity correlate with higher DNA confidence and discovery rate?"
    )
    _MIN_CORR = 0.30   # minimum Pearson-like correlation to report

    def discover(self, ctx: DiscoveryContext) -> List[DiscoveryCandidate]:
        profiles = ctx.market_profiles
        snaps    = ctx.dna_snapshots
        if len(snaps) < 3 or not profiles:
            return []

        years = sorted(set(snaps.keys()) & set(profiles.keys()))
        if len(years) < 3:
            return []

        activity     = [profiles[yr].institutional_activity for yr in years]
        high_conf    = [snaps[yr].high_confidence_count     for yr in years]
        median_conf  = [snaps[yr].median_confidence         for yr in years]
        total_dna    = [snaps[yr].total_discovered          for yr in years]

        def pearson(x: list, y: list) -> float:
            n = len(x)
            if n < 2:
                return 0.0
            mx, my = statistics.mean(x), statistics.mean(y)
            num   = sum((xi - mx) * (yi - my) for xi, yi in zip(x, y))
            denom = (sum((xi - mx) ** 2 for xi in x) * sum((yi - my) ** 2 for yi in y)) ** 0.5
            return num / denom if denom > 1e-9 else 0.0

        corr_high = pearson(activity, high_conf)
        corr_conf = pearson(activity, median_conf)
        corr_dna  = pearson(activity, total_dna)

        candidates = []

        for corr, label, metric_vals in [
            (corr_high, "high-confidence DNA count", high_conf),
            (corr_conf, "median DNA confidence",     median_conf),
            (corr_dna,  "total DNA discovered",      total_dna),
        ]:
            if abs(corr) < self._MIN_CORR:
                continue
            raw_score = min(1.0, abs(corr) * 1.2)
            direction = "positively" if corr > 0 else "negatively"
            ev = self._make_evidence(
                evidence_type    = EvidenceType.STATISTICAL.value,
                description = (
                    f"Institutional activity correlates {direction} with {label} "
                    f"(r={corr:.2f})"
                ),
                data_points         = len(years),
                years_observed      = years,
                regimes_observed    = ctx.all_regimes,
                statistical_support = {
                    "pearson_r":          round(corr, 4),
                    "mean_activity":      round(statistics.mean(activity), 4),
                    f"mean_{label[:8]}":  round(statistics.mean(metric_vals), 4),
                },
                raw_values = {
                    "activity_by_year": dict(zip(years, activity)),
                    "metric_by_year":   dict(zip(years, metric_vals)),
                },
            )
            candidates.append(self._candidate(
                question = self.SCIENTIFIC_QUESTION,
                answer = (
                    f"Institutional activity correlates {direction} with {label} "
                    f"(Pearson r={corr:.2f} across {len(years)} years)."
                ),
                evidence          = [ev],
                raw_score         = raw_score,
                years_observed    = years,
                regimes_observed  = ctx.all_regimes,
                suggested_followup = [
                    "Use institutional_activity as a meta-signal for DNA threshold.",
                    "Is this correlation stable across BULL vs BEAR regimes?",
                ],
                novelty_hint  = 0.50,
                impact_hint   = 0.55,
                feature_names = ["institutional_activity"],
            ))

        candidates.sort(key=lambda c: c.raw_score, reverse=True)
        return candidates
