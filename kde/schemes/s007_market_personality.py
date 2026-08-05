"""S007 — Market Personality: How does market personality affect DNA discovery?"""
from __future__ import annotations

import statistics
from typing import Dict, List

from ..scheme_base import BaseDiscoveryScheme, DiscoveryContext
from ..kde_models import DiscoveryCandidate, EvidenceType


class MarketPersonalityScheme(BaseDiscoveryScheme):
    SCHEME_ID           = "S007"
    SCHEME_NAME         = "Market Personality"
    SCIENTIFIC_QUESTION = (
        "How does market personality affect the quantity and confidence of DNA discoveries?"
    )

    def discover(self, ctx: DiscoveryContext) -> List[DiscoveryCandidate]:
        profiles = ctx.market_profiles
        snaps    = ctx.dna_snapshots
        if len(snaps) < 3 or not profiles:
            return []

        # Group key metrics by personality
        personality_stats: Dict[str, dict] = {}
        for yr in sorted(snaps.keys()):
            ds = snaps.get(yr)
            mp = profiles.get(yr)
            if not ds or not mp:
                continue
            pers = mp.market_personality
            personality_stats.setdefault(pers, {
                "years": [], "total_dna": [], "high_conf": [], "median_conf": [],
            })
            personality_stats[pers]["years"].append(yr)
            personality_stats[pers]["total_dna"].append(ds.total_discovered)
            personality_stats[pers]["high_conf"].append(ds.high_confidence_count)
            personality_stats[pers]["median_conf"].append(ds.median_confidence)

        if len(personality_stats) < 2:
            return []

        personalities = sorted(personality_stats.keys())
        global_avg_dna  = statistics.mean(
            v for p in personality_stats.values() for v in p["total_dna"]
        )
        global_avg_conf = statistics.mean(
            v for p in personality_stats.values() for v in p["median_conf"]
        )

        candidates = []
        for pers, st in personality_stats.items():
            if len(st["years"]) < 1:
                continue
            avg_dna  = statistics.mean(st["total_dna"])
            avg_conf = statistics.mean(st["median_conf"])
            dna_lift = avg_dna / max(global_avg_dna, 1)
            conf_diff = avg_conf - global_avg_conf

            if abs(dna_lift - 1.0) < 0.1 and abs(conf_diff) < 0.03:
                continue  # not noteworthy

            raw_score = min(1.0, (abs(dna_lift - 1.0) + abs(conf_diff) * 5) * 0.5)
            ev = self._make_evidence(
                evidence_type       = EvidenceType.COMPARATIVE.value,
                description = (
                    f"{pers}: avg {avg_dna:.1f} DNA (lift={dna_lift:.2f}x), "
                    f"median confidence {avg_conf:.2f} (vs global {global_avg_conf:.2f})"
                ),
                data_points         = len(st["years"]),
                years_observed      = sorted(st["years"]),
                regimes_observed    = ctx.all_regimes[:2],
                statistical_support = {
                    "avg_dna_count":    round(avg_dna, 2),
                    "dna_lift":         round(dna_lift, 4),
                    "avg_conf":         round(avg_conf, 4),
                    "conf_vs_global":   round(conf_diff, 4),
                },
                raw_values = {"years": sorted(st["years"])},
            )
            direction = "higher" if dna_lift > 1 else "lower"
            candidates.append(self._candidate(
                question = self.SCIENTIFIC_QUESTION,
                answer = (
                    f"{pers} years produce {dna_lift:.1f}x {direction} DNA discovery rate "
                    f"and {conf_diff:+.2f} median confidence vs all years."
                ),
                evidence          = [ev],
                raw_score         = raw_score,
                years_observed    = sorted(st["years"]),
                regimes_observed  = ctx.all_regimes[:2],
                suggested_followup = [
                    f"Adjust DNA threshold in {pers} years.",
                    "Is this caused by institutional activity correlation?",
                ],
                novelty_hint  = 0.45,
                impact_hint   = 0.35,
            ))

        candidates.sort(key=lambda c: c.raw_score, reverse=True)
        return candidates
