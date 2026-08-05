"""S005 — Sector Rotation: Which sectors cycle in/out of institutional leadership?"""
from __future__ import annotations

from typing import List

from ..scheme_base import BaseDiscoveryScheme, DiscoveryContext
from ..kde_models import DiscoveryCandidate, EvidenceType


class SectorRotationScheme(BaseDiscoveryScheme):
    SCHEME_ID           = "S005"
    SCHEME_NAME         = "Sector Rotation"
    SCIENTIFIC_QUESTION = (
        "Which sectors cycle in and out of institutional leadership across years?"
    )

    def discover(self, ctx: DiscoveryContext) -> List[DiscoveryCandidate]:
        profiles = ctx.market_profiles
        if len(profiles) < 2:
            return []

        # Count leadership frequency per sector
        sector_lead_years: dict = {}    # sector -> [years led]
        regime_sector:     dict = {}    # regime -> {sector -> count}

        for yr, mp in sorted(profiles.items()):
            for rank, sector in enumerate(mp.sector_leaders[:3]):
                sector_lead_years.setdefault(sector, []).append(yr)
                # track regime co-occurrence
                dom = mp.dominant_regime
                regime_sector.setdefault(dom, {})
                regime_sector[dom][sector] = regime_sector[dom].get(sector, 0) + 1

        n_years    = len(profiles)
        candidates = []

        # Discovery 1: persistent sector leaders
        for sector, years_led in sector_lead_years.items():
            freq = len(years_led) / n_years
            if freq < 0.3:
                continue
            raw_score = freq * 0.7 + 0.3

            # which regimes this sector leads in
            sector_regimes = [
                regime for regime, smap in regime_sector.items()
                if sector in smap and smap[sector] >= 1
            ]
            ev = self._make_evidence(
                evidence_type       = EvidenceType.HISTORICAL.value,
                description         = f"{sector} is a sector leader in {freq:.0%} of years",
                data_points         = len(years_led),
                years_observed      = sorted(years_led),
                regimes_observed    = sector_regimes or ctx.all_regimes[:1],
                statistical_support = {"leadership_frequency": round(freq, 4)},
                raw_values          = {"years_led": sorted(years_led)},
            )
            candidates.append(self._candidate(
                question  = self.SCIENTIFIC_QUESTION,
                answer    = (
                    f"{sector} leads in {freq:.0%} of years studied. "
                    f"Dominant in regimes: {sector_regimes}."
                ),
                evidence          = [ev],
                raw_score         = raw_score,
                years_observed    = sorted(years_led),
                regimes_observed  = sector_regimes or ctx.all_regimes[:1],
                suggested_followup = [
                    f"Map {sector} leadership to specific regime conditions.",
                    "Identify entry signal when sector begins to lead.",
                ],
                novelty_hint  = max(0.2, 1.0 - freq),
                impact_hint   = 0.50,
                feature_names = ["sector_mom_5d", "sector_relative"],
            ))

        # Discovery 2: rotation events — sector present then absent
        sectors = list(sector_lead_years.keys())
        for sector in sectors:
            years_led = sorted(sector_lead_years[sector])
            if len(years_led) < 2:
                continue
            gaps = [years_led[i+1] - years_led[i] for i in range(len(years_led)-1)]
            if any(g >= 2 for g in gaps):  # at least one rotation out
                raw_score = 0.55
                ev = self._make_evidence(
                    evidence_type       = EvidenceType.PATTERN.value,
                    description         = f"{sector} shows intermittent leadership (rotation pattern)",
                    data_points         = len(years_led),
                    years_observed      = years_led,
                    regimes_observed    = ctx.all_regimes[:2],
                    statistical_support = {"max_gap_years": max(gaps)},
                    raw_values          = {"years_led": years_led, "gaps": gaps},
                )
                candidates.append(self._candidate(
                    question  = self.SCIENTIFIC_QUESTION,
                    answer    = (
                        f"{sector} exhibits rotation: led in years {years_led} "
                        f"with gaps up to {max(gaps)} year(s)."
                    ),
                    evidence          = [ev],
                    raw_score         = raw_score,
                    years_observed    = years_led,
                    regimes_observed  = ctx.all_regimes[:2],
                    suggested_followup = [
                        f"Study what regime change triggers {sector} rotation out.",
                    ],
                    novelty_hint  = 0.55,
                    impact_hint   = 0.45,
                    feature_names = ["sector_mom_5d"],
                ))

        candidates.sort(key=lambda c: c.raw_score, reverse=True)
        return candidates
