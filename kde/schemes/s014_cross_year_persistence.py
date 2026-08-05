"""S014 — Cross-Year Persistence: Which DNA patterns appear in the most consecutive years?"""
from __future__ import annotations

from typing import List

from ..scheme_base import BaseDiscoveryScheme, DiscoveryContext
from ..kde_models import DiscoveryCandidate, EvidenceType


def _max_streak(years: List[int]) -> int:
    """Return the length of the longest run of consecutive years."""
    if not years:
        return 0
    s = sorted(set(years))
    best = cur = 1
    for i in range(1, len(s)):
        if s[i] == s[i - 1] + 1:
            cur += 1
            best = max(best, cur)
        else:
            cur = 1
    return best


class CrossYearPersistenceScheme(BaseDiscoveryScheme):
    SCHEME_ID           = "S014"
    SCHEME_NAME         = "Cross-Year Persistence"
    SCIENTIFIC_QUESTION = (
        "Which DNA patterns appear in the most consecutive years — "
        "the institutional bedrock?"
    )
    _MIN_STREAK = 3

    def discover(self, ctx: DiscoveryContext) -> List[DiscoveryCandidate]:
        records = ctx.dna_records
        if not records:
            return []

        n_years    = len(ctx.years)
        candidates = []

        for r in records:
            streak = _max_streak(r.years_present)
            if streak < self._MIN_STREAK:
                continue

            frac      = len(r.years_present) / max(n_years, 1)
            raw_score = min(1.0, streak / max(n_years, 1) * 1.2 + frac * 0.3)

            ev = self._make_evidence(
                evidence_type    = EvidenceType.HISTORICAL.value,
                description = (
                    f"{r.dna_id}: {streak} consecutive years, "
                    f"{len(r.years_present)}/{n_years} total years present"
                ),
                data_points         = len(r.years_present),
                years_observed      = sorted(r.years_present),
                regimes_observed    = r.regimes_observed or ctx.all_regimes[:1],
                statistical_support = {
                    "max_streak":    streak,
                    "total_years":   len(r.years_present),
                    "fraction":      round(frac, 4),
                    "survival":      round(r.survival_score, 4),
                },
                raw_values = {
                    "years_present":  sorted(r.years_present),
                    "lifecycle":      r.lifecycle_label,
                    "trend":          r.confidence_trend,
                },
            )
            candidates.append(self._candidate(
                question = self.SCIENTIFIC_QUESTION,
                answer = (
                    f"`{r.dna_id}` appears in {streak} consecutive years "
                    f"({len(r.years_present)}/{n_years} total). "
                    f"Lifecycle: {r.lifecycle_label}, trend: {r.confidence_trend}."
                ),
                evidence          = [ev],
                raw_score         = raw_score,
                years_observed    = sorted(r.years_present),
                regimes_observed  = r.regimes_observed or ctx.all_regimes[:1],
                suggested_followup = [
                    f"Recommend `{r.dna_id}` for SD institutional knowledge review.",
                    "Verify robustness to BEAR_MARKET and VOLATILE_MARKET conditions.",
                ],
                novelty_hint  = max(0.2, 1.0 - frac),
                impact_hint   = min(1.0, streak / max(n_years, 1) * 1.5),
                feature_names = [r.feature_name],
                dna_ids       = [r.dna_id],
            ))

        candidates.sort(key=lambda c: c.raw_score, reverse=True)
        return candidates
