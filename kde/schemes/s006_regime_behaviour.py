"""S006 — Regime Behaviour: Which DNA patterns behave differently across regimes?"""
from __future__ import annotations

import statistics
from typing import Dict, List

from ..scheme_base import BaseDiscoveryScheme, DiscoveryContext
from ..kde_models import DiscoveryCandidate, EvidenceType


class RegimeBehaviourScheme(BaseDiscoveryScheme):
    SCHEME_ID           = "S006"
    SCHEME_NAME         = "Regime Behaviour"
    SCIENTIFIC_QUESTION = (
        "Which DNA patterns have significantly different confidence across market regimes?"
    )
    _MIN_DIFF = 0.15   # minimum confidence difference across regimes to be noteworthy

    def discover(self, ctx: DiscoveryContext) -> List[DiscoveryCandidate]:
        profiles = ctx.market_profiles
        snaps    = ctx.dna_snapshots
        if len(snaps) < 3 or not profiles:
            return []

        # Group confidence by regime for each DNA id
        dna_by_regime: Dict[str, Dict[str, list]] = {}   # dna_id -> regime -> [conf]
        for yr in sorted(snaps.keys()):
            ds  = snaps.get(yr)
            mp  = profiles.get(yr)
            if not ds or not mp:
                continue
            dom = mp.dominant_regime
            for dna_id, conf in ds.confidence_by_id.items():
                dna_by_regime.setdefault(dna_id, {}).setdefault(dom, []).append(conf)

        candidates = []
        for dna_id, regime_confs in dna_by_regime.items():
            if len(regime_confs) < 2:
                continue
            means = {r: statistics.mean(v) for r, v in regime_confs.items()}
            max_mean = max(means.values())
            min_mean = min(means.values())
            diff = max_mean - min_mean
            if diff < self._MIN_DIFF:
                continue

            best_regime  = max(means, key=means.get)
            worst_regime = min(means, key=means.get)
            raw_score    = min(1.0, diff * 2.5 * statistics.mean(means.values()))

            years_obs = sorted({
                yr for yr in sorted(snaps.keys())
                if dna_id in snaps[yr].confidence_by_id
            })
            ev = self._make_evidence(
                evidence_type    = EvidenceType.COMPARATIVE.value,
                description = (
                    f"{dna_id}: confidence {max_mean:.2f} in {best_regime} "
                    f"vs {min_mean:.2f} in {worst_regime} (diff={diff:.2f})"
                ),
                data_points         = len(years_obs),
                years_observed      = years_obs,
                regimes_observed    = sorted(means.keys()),
                statistical_support = {
                    "max_regime_confidence": round(max_mean, 4),
                    "min_regime_confidence": round(min_mean, 4),
                    "confidence_diff":       round(diff, 4),
                },
                raw_values = {"confidence_by_regime": {r: round(m, 4) for r, m in means.items()}},
            )
            candidates.append(self._candidate(
                question = self.SCIENTIFIC_QUESTION,
                answer = (
                    f"`{dna_id}` performs best in {best_regime} ({max_mean:.2f}) "
                    f"and worst in {worst_regime} ({min_mean:.2f}). "
                    f"Regime sensitivity: {diff:.2f}."
                ),
                evidence          = [ev],
                raw_score         = raw_score,
                years_observed    = years_obs,
                regimes_observed  = sorted(means.keys()),
                suggested_followup = [
                    f"Build regime-gated signal: use `{dna_id}` only in {best_regime}.",
                    "Study whether this pattern is regime-specific or multi-regime.",
                ],
                novelty_hint  = min(1.0, diff * 2.0),
                impact_hint   = 0.60,
                feature_names = [dna_id.split("::")[0]],
                dna_ids       = [dna_id],
            ))

        candidates.sort(key=lambda c: c.raw_score, reverse=True)
        return candidates
