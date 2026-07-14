"""iios/investment/decision/evidence/coverage_validator.py
CoverageValidator — checks required source types are represented.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Set, Tuple

from iios.investment.decision.evidence.evidence_constants import (
    EvidenceSourceType,
    MIN_COVERAGE_FRACTION,
    EvidenceValidationStatus,
)
from iios.investment.decision.evidence.evidence_item import EvidenceItem


@dataclass(frozen=True)
class CoverageReport:
    total_source_types:    int
    sources_present:       int
    required_types:        Tuple[str, ...]
    missing_required:      Tuple[str, ...]
    coverage_fraction:     float
    validation_status:     EvidenceValidationStatus

    @property
    def has_required(self) -> bool:
        return len(self.missing_required) == 0


class CoverageValidator:
    """Validates that required evidence sources are present."""

    def __init__(self, min_coverage: float = MIN_COVERAGE_FRACTION) -> None:
        self._min_coverage = min_coverage

    def validate(self, items: List[EvidenceItem]) -> CoverageReport:
        present: Set[EvidenceSourceType] = {i.source_type for i in items}

        all_types  = list(EvidenceSourceType)
        required   = [st for st in all_types if st.is_required]
        missing    = [st for st in required if st not in present]

        coverage   = len(present) / len(all_types) if all_types else 0.0

        if missing:
            status = EvidenceValidationStatus.INSUFFICIENT
        elif coverage < self._min_coverage:
            status = EvidenceValidationStatus.PASSED_WITH_GAPS
        else:
            status = EvidenceValidationStatus.PASSED

        return CoverageReport(
            total_source_types=len(all_types),
            sources_present=len(present),
            required_types=tuple(st.value for st in required),
            missing_required=tuple(st.value for st in missing),
            coverage_fraction=round(coverage, 4),
            validation_status=status,
        )
