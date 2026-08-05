"""S015 — Context Dependency: Which DNA only works in specific market conditions?"""
from __future__ import annotations

import statistics
from typing import Dict, List, Tuple

from ..scheme_base import BaseDiscoveryScheme, DiscoveryContext
from ..kde_models import DiscoveryCandidate, EvidenceType


class ContextDependencyScheme(BaseDiscoveryScheme):
    SCHEME_ID           = "S015"
    SCHEME_NAME         = "Context Dependency"
    SCIENTIFIC_QUESTION = (
        "Which DNA patterns are highly context-specific — "
        "only appearing under particular (regime, volatility) conditions?"
    )
    _SPECIFICITY_THRESHOLD = 0.70   # pattern occupies <= 30% of possible contexts

    def discover(self, ctx: DiscoveryContext) -> List[DiscoveryCandidate]:
        profiles = ctx.market_profiles
        snaps    = ctx.dna_snapshots
        if len(snaps) < 3 or not profiles:
            return []

        # Build all unique (regime, vol) contexts observed
        all_contexts: set = set()
        year_context: Dict[int, Tuple[str, str]] = {}
        for yr in sorted(profiles.keys()):
            mp = profiles[yr]
            ctx_key = (mp.dominant_regime, mp.volatility_level)
            all_contexts.add(ctx_key)
            year_context[yr] = ctx_key

        n_contexts = max(len(all_contexts), 1)

        # For each DNA id, find which contexts it appears in
        dna_contexts: Dict[str, set] = {}
        dna_years:    Dict[str, list] = {}
        for yr in sorted(snaps.keys()):
            ds = snaps.get(yr)
            if not ds:
                continue
            ctx_key = year_context.get(yr)
            if not ctx_key:
                continue
            for dna_id in ds.winner_dna + ds.loser_dna:
                dna_contexts.setdefault(dna_id, set()).add(ctx_key)
                dna_years.setdefault(dna_id, []).append(yr)

        candidates = []
        for dna_id, dna_ctx_set in dna_contexts.items():
            n_dna_ctx  = len(dna_ctx_set)
            specificity = 1.0 - n_dna_ctx / n_contexts

            if specificity < self._SPECIFICITY_THRESHOLD:
                continue   # not specific enough

            years_obs = sorted(set(dna_years.get(dna_id, [])))
            raw_score = min(1.0, specificity * 0.8 + (
                statistics.mean(
                    snaps[yr].confidence_by_id.get(dna_id, 0.5)
                    for yr in years_obs if yr in snaps
                ) if years_obs else 0.5
            ) * 0.3)

            contexts_str = ", ".join(f"{r}/{v}" for r, v in sorted(dna_ctx_set))
            ev = self._make_evidence(
                evidence_type    = EvidenceType.PATTERN.value,
                description = (
                    f"{dna_id}: appears only in contexts [{contexts_str}] "
                    f"({n_dna_ctx}/{n_contexts} possible contexts)"
                ),
                data_points         = len(years_obs),
                years_observed      = years_obs,
                regimes_observed    = sorted({r for r, v in dna_ctx_set}),
                statistical_support = {
                    "specificity":   round(specificity, 4),
                    "n_contexts":    n_dna_ctx,
                    "total_contexts": n_contexts,
                },
                raw_values = {
                    "active_contexts":    [f"{r}/{v}" for r, v in sorted(dna_ctx_set)],
                    "all_contexts_count": n_contexts,
                },
            )
            candidates.append(self._candidate(
                question = self.SCIENTIFIC_QUESTION,
                answer = (
                    f"`{dna_id}` is highly context-specific (specificity={specificity:.0%}): "
                    f"only appears in [{contexts_str}]."
                ),
                evidence          = [ev],
                raw_score         = raw_score,
                years_observed    = years_obs,
                regimes_observed  = sorted({r for r, v in dna_ctx_set}),
                suggested_followup = [
                    f"Build conditional signal: apply `{dna_id}` only in {contexts_str}.",
                    "Is this specificity due to sample size or genuine dependency?",
                ],
                novelty_hint  = min(1.0, specificity),
                impact_hint   = 0.60,
                feature_names = [dna_id.split("::")[0]],
                dna_ids       = [dna_id],
            ))

        candidates.sort(key=lambda c: c.raw_score, reverse=True)
        return candidates
