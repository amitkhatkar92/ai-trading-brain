"""iios/investment/decision/confidence/coverage_analysis.py
CoverageAnalyzer — measures how completely the evidence snapshot covers required sources.
"""
from __future__ import annotations

import statistics
from dataclasses import dataclass
from typing import Any, Dict, List, Set, Tuple

from iios.investment.decision.confidence.confidence_constants import (
    IDEAL_SOURCE_TYPES_FOR_COVERAGE,
    MIN_SOURCE_TYPES_FOR_COVERAGE,
)
from iios.investment.decision.evidence.evidence_constants import EvidenceSourceType
from iios.investment.decision.evidence.evidence_item import EvidenceItem


# Sources considered required for high confidence
_REQUIRED_SOURCES: Set[str] = {"market", "risk"}
_IDEAL_SOURCES:    Set[str] = {"market", "company", "strategy", "risk", "knowledge"}


@dataclass(frozen=True)
class CoverageResult:
    total_items:          int
    source_types_present: int
    required_met:         bool
    coverage_fraction:    float   # 0–1
    required_fraction:    float   # 0–1 (required sources covered)
    cross_source_agreement: float  # 0–100 (avg confidence across sources)
    missing_required:     Tuple[str, ...]
    coverage_conf:        float   # 0–100

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_items":            self.total_items,
            "source_types_present":   self.source_types_present,
            "required_met":           self.required_met,
            "coverage_fraction":      round(self.coverage_fraction, 4),
            "required_fraction":      round(self.required_fraction, 4),
            "cross_source_agreement": round(self.cross_source_agreement, 2),
            "missing_required":       list(self.missing_required),
            "coverage_conf":          round(self.coverage_conf, 2),
        }


class CoverageAnalyzer:
    """Measures how well the evidence snapshot covers the expected source types."""

    def analyze(self, items: List[EvidenceItem]) -> CoverageResult:
        if not items:
            return CoverageResult(
                total_items=0,
                source_types_present=0,
                required_met=False,
                coverage_fraction=0.0,
                required_fraction=0.0,
                cross_source_agreement=0.0,
                missing_required=tuple(_REQUIRED_SOURCES),
                coverage_conf=0.0,
            )

        present = {i.source_type.value for i in items}
        n_sources = len(present)

        required_met_set = _REQUIRED_SOURCES & present
        required_fraction = len(required_met_set) / len(_REQUIRED_SOURCES)
        required_met = required_fraction == 1.0
        missing_required = tuple(_REQUIRED_SOURCES - present)

        ideal_fraction = len(_IDEAL_SOURCES & present) / len(_IDEAL_SOURCES)
        coverage_fraction = min(1.0, n_sources / max(1, IDEAL_SOURCE_TYPES_FOR_COVERAGE))

        # Cross-source agreement: average confidence per source, then std-dev penalty
        by_source: Dict[str, List[float]] = {}
        for item in items:
            k = item.source_type.value
            by_source.setdefault(k, []).append(item.confidence)
        source_avgs = [statistics.mean(vs) for vs in by_source.values()]
        if len(source_avgs) > 1:
            agreement_std = statistics.stdev(source_avgs)
            cross_agreement = max(0.0, 100.0 - agreement_std)
        else:
            cross_agreement = source_avgs[0] if source_avgs else 0.0

        # Coverage confidence
        coverage_conf = (
            coverage_fraction * 40.0
            + required_fraction * 40.0
            + (cross_agreement / 100.0) * 20.0
        ) * 100.0 / 100.0   # normalise to 0-100

        # Penalty for missing required sources
        if not required_met:
            coverage_conf *= 0.7

        return CoverageResult(
            total_items=len(items),
            source_types_present=n_sources,
            required_met=required_met,
            coverage_fraction=round(coverage_fraction, 4),
            required_fraction=round(required_fraction, 4),
            cross_source_agreement=round(cross_agreement, 4),
            missing_required=missing_required,
            coverage_conf=round(min(100.0, coverage_conf), 4),
        )
