"""
cross_year_analyzer.py — Compares DNA and edges across all completed years.

Classifies each DNA pattern's lifecycle (STABLE, STRENGTHENING, etc.)
and regime dependency (REGIME_SPECIFIC, REGIME_INDEPENDENT, MULTI_REGIME).

Must only be called after all target years are complete.
Read-only: never modifies any year's data.
"""
from __future__ import annotations

import logging
import math
from typing import Dict, List, Optional, Tuple

from .hkap_models import (
    CrossYearDNARecord,
    CrossYearEdgeRecord,
    DNALifecycleLabel,
    RegimeDependency,
    YearKnowledgePackage,
)

log = logging.getLogger(__name__)


class CrossYearAnalyzer:
    """
    Produces CrossYearDNARecord and CrossYearEdgeRecord for the full
    set of completed year packages.  Thread-safe (read-only analysis).
    """

    def analyze(
        self,
        year_results: Dict[int, YearKnowledgePackage],
    ) -> Tuple[List[CrossYearDNARecord], List[CrossYearEdgeRecord]]:
        """
        Analyse all completed years.

        Returns (dna_records, edge_records).
        """
        sorted_years = sorted(year_results.keys())
        dna_records  = self._analyse_dna(sorted_years, year_results)
        edge_records = self._analyse_edges(sorted_years, year_results)
        log.info("[HKAP][CYA] years=%s dna_records=%d edge_records=%d",
                 sorted_years, len(dna_records), len(edge_records))
        return dna_records, edge_records

    # ── DNA analysis ──────────────────────────────────────────────────────

    def _analyse_dna(
        self,
        years: List[int],
        results: Dict[int, YearKnowledgePackage],
    ) -> List[CrossYearDNARecord]:
        # build {dna_id → {year → confidence}}
        all_ids: set = set()
        for yr in years:
            pkg = results[yr]
            if pkg.dna_snapshot:
                all_ids.update(pkg.dna_snapshot.confidence_by_id.keys())

        records = []
        for dna_id in sorted(all_ids):
            conf_by_year: Dict[int, float] = {}
            for yr in years:
                pkg = results[yr]
                if pkg.dna_snapshot and dna_id in pkg.dna_snapshot.confidence_by_id:
                    conf_by_year[yr] = pkg.dna_snapshot.confidence_by_id[dna_id]

            years_present = sorted(conf_by_year.keys())
            years_absent  = [y for y in years if y not in conf_by_year]
            presences     = [y in conf_by_year for y in years]
            confidences   = [conf_by_year.get(y, 0.0) for y in years]

            label    = self._classify_lifecycle(presences, confidences)
            dep      = self._regime_dependency(dna_id, years, results)
            survival = len(years_present) / max(len(years), 1)
            trend    = self._confidence_trend(
                [conf_by_year[y] for y in years_present]
            )
            regimes  = self._regimes_observed(dna_id, years, results)
            feature_name, direction = self._parse_dna_id(dna_id)

            records.append(CrossYearDNARecord(
                dna_id             = dna_id,
                feature_name       = feature_name,
                direction          = direction,
                years_present      = years_present,
                years_absent       = years_absent,
                confidence_by_year = conf_by_year,
                regimes_observed   = regimes,
                lifecycle_label    = label.value,
                regime_dependency  = dep.value,
                survival_score     = survival,
                confidence_trend   = trend,
            ))
        return records

    def _classify_lifecycle(
        self, presences: List[bool], confidences: List[float]
    ) -> DNALifecycleLabel:
        n         = len(presences)
        n_present = sum(presences)
        if n == 0 or n_present == 0:
            return DNALifecycleLabel.SPORADIC

        survival = n_present / n
        # check recent presence (last 2 years)
        recent        = presences[-2:] if n >= 2 else presences
        recently_seen = any(recent)
        early_seen    = any(presences[:2]) if n >= 2 else True

        if survival >= 0.75:
            # stable — but check trend
            present_confs = [c for p, c in zip(presences, confidences) if p]
            trend = self._confidence_trend(present_confs)
            if trend == "RISING":
                return DNALifecycleLabel.STRENGTHENING
            if trend == "FALLING":
                return DNALifecycleLabel.WEAKENING
            return DNALifecycleLabel.STABLE

        if not recently_seen and early_seen:
            return DNALifecycleLabel.DISAPPEARING

        if recently_seen and not early_seen:
            return DNALifecycleLabel.EMERGING

        present_confs = [c for p, c in zip(presences, confidences) if p]
        trend = self._confidence_trend(present_confs)
        if trend == "RISING":
            return DNALifecycleLabel.STRENGTHENING
        if trend == "FALLING":
            return DNALifecycleLabel.WEAKENING
        return DNALifecycleLabel.SPORADIC

    def _regime_dependency(
        self, dna_id: str, years: List[int], results: Dict[int, YearKnowledgePackage]
    ) -> RegimeDependency:
        regimes_with_dna: set = set()
        all_regimes:      set = set()
        for yr in years:
            pkg = results[yr]
            if not pkg.dna_snapshot or not pkg.market_profile:
                continue
            all_regimes.add(pkg.market_profile.dominant_regime)
            if dna_id in pkg.dna_snapshot.confidence_by_id:
                regimes_with_dna.add(pkg.market_profile.dominant_regime)

        if not all_regimes:
            return RegimeDependency.REGIME_INDEPENDENT

        n_all     = len(all_regimes)
        n_with    = len(regimes_with_dna)
        coverage  = n_with / max(n_all, 1)

        if coverage >= 0.75:
            return RegimeDependency.REGIME_INDEPENDENT
        if coverage <= 0.25 and n_with <= 1:
            return RegimeDependency.REGIME_SPECIFIC
        return RegimeDependency.MULTI_REGIME

    def _regimes_observed(
        self, dna_id: str, years: List[int], results: Dict[int, YearKnowledgePackage]
    ) -> List[str]:
        regimes: set = set()
        for yr in years:
            pkg = results[yr]
            if pkg.dna_snapshot and pkg.market_profile:
                if dna_id in pkg.dna_snapshot.confidence_by_id:
                    regimes.add(pkg.market_profile.dominant_regime)
        return sorted(regimes)

    @staticmethod
    def _confidence_trend(values: List[float]) -> str:
        if len(values) < 2:
            return "STABLE"
        n    = len(values)
        xs   = list(range(n))
        mx   = sum(xs) / n
        my   = sum(values) / n
        num  = sum((x - mx) * (y - my) for x, y in zip(xs, values))
        den  = sum((x - mx) ** 2 for x in xs)
        if den == 0:
            return "STABLE"
        slope = num / den
        # normalise slope by mean confidence
        mean_c = my or 1e-6
        rel_slope = slope / mean_c
        if rel_slope > 0.05:
            return "RISING"
        if rel_slope < -0.05:
            return "FALLING"
        # check volatility
        std = math.sqrt(sum((v - my) ** 2 for v in values) / max(n - 1, 1))
        cv  = std / max(my, 1e-6)
        return "VOLATILE" if cv > 0.4 else "STABLE"

    @staticmethod
    def _parse_dna_id(dna_id: str) -> Tuple[str, str]:
        """Attempt to extract (feature_name, direction) from a DNA id string."""
        if "::" in dna_id:
            parts = dna_id.split("::", 1)
            return parts[0], parts[1]
        if "_WINNERS_" in dna_id.upper():
            return dna_id, "WINNERS_HIGHER"
        return dna_id, "UNKNOWN"

    # ── Edge analysis ─────────────────────────────────────────────────────

    def _analyse_edges(
        self,
        years: List[int],
        results: Dict[int, YearKnowledgePackage],
    ) -> List[CrossYearEdgeRecord]:
        all_edges: set = set()
        for yr in years:
            pkg = results[yr]
            if pkg.edge_snapshot:
                all_edges.update(pkg.edge_snapshot.active_edges)

        records = []
        for edge_id in sorted(all_edges):
            years_active:   List[int] = []
            years_inactive: List[int] = []
            conf_by_year:   Dict[int, float] = {}

            for yr in years:
                pkg = results[yr]
                if pkg.edge_snapshot and edge_id in pkg.edge_snapshot.active_edges:
                    years_active.append(yr)
                    if pkg.dna_snapshot and edge_id in pkg.dna_snapshot.confidence_by_id:
                        conf_by_year[yr] = pkg.dna_snapshot.confidence_by_id[edge_id]
                else:
                    years_inactive.append(yr)

            presences  = [y in years_active for y in years]
            confs      = [conf_by_year.get(y, 0.0) for y in years]
            label      = self._classify_lifecycle(presences, confs)
            trend      = self._confidence_trend(
                [conf_by_year.get(y, 0.0) for y in years_active]
            )
            peak_year  = max(conf_by_year, key=conf_by_year.get) if conf_by_year else (years_active[0] if years_active else years[0])
            peak_conf  = conf_by_year.get(peak_year, 0.0)
            feature_name, _ = self._parse_dna_id(edge_id)

            records.append(CrossYearEdgeRecord(
                edge_id              = edge_id,
                feature_name         = feature_name,
                years_active         = years_active,
                years_inactive       = years_inactive,
                lifecycle_label      = label.value,
                peak_confidence_year = peak_year,
                peak_confidence      = peak_conf,
                trend                = trend,
            ))
        return records
