"""S002 — Loser DNA: Which DNA patterns most reliably predict losers?"""
from __future__ import annotations

import statistics
from typing import List

from ..scheme_base import BaseDiscoveryScheme, DiscoveryContext
from ..kde_models import DiscoveryCandidate, EvidenceType


class LoserDNAScheme(BaseDiscoveryScheme):
    SCHEME_ID           = "S002"
    SCHEME_NAME         = "Loser DNA"
    SCIENTIFIC_QUESTION = "Which DNA patterns most reliably identify losers across years?"

    def discover(self, ctx: DiscoveryContext) -> List[DiscoveryCandidate]:
        snaps = ctx.dna_snapshots
        if not snaps:
            return []

        loser_years:   dict = {}
        confidence_by: dict = {}

        for yr, ds in snaps.items():
            for dna_id in ds.loser_dna:
                loser_years.setdefault(dna_id, []).append(yr)
                if dna_id in ds.confidence_by_id:
                    confidence_by.setdefault(dna_id, []).append(ds.confidence_by_id[dna_id])

        n_years    = len(snaps)
        candidates = []

        for dna_id, years_l in loser_years.items():
            freq     = len(years_l) / n_years
            confs    = confidence_by.get(dna_id, [0.5])
            avg_conf = statistics.mean(confs)
            std_conf = statistics.stdev(confs) if len(confs) > 1 else 0.0
            stability = 1.0 - min(1.0, std_conf / max(avg_conf, 0.01))
            raw_score = (freq * avg_conf * stability) ** (1 / 3)
            if raw_score < ctx.config.min_raw_score:
                continue

            ev = self._make_evidence(
                evidence_type       = EvidenceType.STATISTICAL.value,
                description         = f"{dna_id} appears as loser DNA in {len(years_l)}/{n_years} years",
                data_points         = len(years_l),
                years_observed      = sorted(years_l),
                regimes_observed    = ctx.all_regimes[:2],
                statistical_support = {
                    "loser_frequency": round(freq, 4),
                    "avg_confidence":  round(avg_conf, 4),
                    "stability":       round(stability, 4),
                },
                raw_values = {"confidence_per_year": dict(zip(years_l, confs))},
            )
            candidates.append(self._candidate(
                question   = self.SCIENTIFIC_QUESTION,
                answer     = (
                    f"`{dna_id}` is a loser indicator in {freq:.0%} of years "
                    f"(avg confidence {avg_conf:.2f})."
                ),
                evidence          = [ev],
                raw_score         = raw_score,
                years_observed    = sorted(years_l),
                regimes_observed  = ctx.all_regimes[:2],
                suggested_followup = [
                    "Is this loser DNA the inverse of a known winner DNA?",
                    "Does this DNA appear in BEAR_MARKET years only?",
                ],
                novelty_hint  = max(0.3, 1.0 - freq),
                impact_hint   = 0.40,
                feature_names = [dna_id.split("::")[0]],
                dna_ids       = [dna_id],
            ))

        candidates.sort(key=lambda c: c.raw_score, reverse=True)
        return candidates
