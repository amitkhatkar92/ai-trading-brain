"""S001 — Winner DNA: Which DNA patterns most reliably predict winners?"""
from __future__ import annotations

import statistics
from typing import List

from ..scheme_base import BaseDiscoveryScheme, DiscoveryContext
from ..kde_models import DiscoveryCandidate, EvidenceType


class WinnerDNAScheme(BaseDiscoveryScheme):
    SCHEME_ID           = "S001"
    SCHEME_NAME         = "Winner DNA"
    SCIENTIFIC_QUESTION = "Which DNA patterns most reliably identify winners across years?"

    def discover(self, ctx: DiscoveryContext) -> List[DiscoveryCandidate]:
        snaps = ctx.dna_snapshots
        if not snaps:
            return []

        # Aggregate winner DNA frequency and confidence across years
        winner_years:  dict = {}   # dna_id -> [years present as winner]
        confidence_by: dict = {}   # dna_id -> [confidence per year]

        for yr, ds in snaps.items():
            for dna_id in ds.winner_dna:
                winner_years.setdefault(dna_id, []).append(yr)
                if dna_id in ds.confidence_by_id:
                    confidence_by.setdefault(dna_id, []).append(ds.confidence_by_id[dna_id])

        n_years    = len(snaps)
        candidates = []

        for dna_id, years_w in winner_years.items():
            freq     = len(years_w) / n_years
            confs    = confidence_by.get(dna_id, [0.5])
            avg_conf = statistics.mean(confs)
            std_conf = statistics.stdev(confs) if len(confs) > 1 else 0.0
            stability = 1.0 - min(1.0, std_conf / max(avg_conf, 0.01))

            # raw_score = geometric mean of frequency, confidence, stability
            raw_score = (freq * avg_conf * stability) ** (1 / 3)
            if raw_score < ctx.config.min_raw_score:
                continue

            regimes = list({
                r
                for yr in years_w
                for ds in [snaps.get(yr)]
                if ds
                for regime, ids in ds.regime_specific_dna.items()
                if dna_id in ids
                for r in [regime]
            }) or ctx.all_regimes[:1]

            ev = self._make_evidence(
                evidence_type       = EvidenceType.STATISTICAL.value,
                description         = f"{dna_id} appears as winner DNA in {len(years_w)}/{n_years} years",
                data_points         = len(years_w),
                years_observed      = sorted(years_w),
                regimes_observed    = regimes,
                statistical_support = {
                    "winner_frequency": round(freq, 4),
                    "avg_confidence":   round(avg_conf, 4),
                    "stability":        round(stability, 4),
                },
                raw_values = {"confidence_per_year": dict(zip(years_w, confs))},
            )
            candidates.append(self._candidate(
                question  = self.SCIENTIFIC_QUESTION,
                answer    = (
                    f"`{dna_id}` is a winner indicator in {freq:.0%} of years "
                    f"(avg confidence {avg_conf:.2f}, stability {stability:.2f})."
                ),
                evidence         = [ev],
                raw_score        = raw_score,
                years_observed   = sorted(years_w),
                regimes_observed = regimes,
                suggested_followup = [
                    "Test whether this DNA persists in BEAR_MARKET years.",
                    "Examine if confidence is rising (STRENGTHENING lifecycle).",
                ],
                novelty_hint  = max(0.3, 1.0 - freq),
                impact_hint   = min(1.0, avg_conf * 1.2),
                feature_names = [dna_id.split("::")[0]],
                dna_ids       = [dna_id],
            ))

        candidates.sort(key=lambda c: c.raw_score, reverse=True)
        return candidates
