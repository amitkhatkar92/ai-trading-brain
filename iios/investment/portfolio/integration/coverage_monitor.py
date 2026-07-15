"""iios/investment/portfolio/integration/coverage_monitor.py

Monitors which upstream engines have contributed for a given portfolio.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple

from iios.investment.portfolio.integration.integration_types import (
    EngineId, REQUIRED_ENGINES, now_utc,
)


@dataclass(frozen=True)
class CoverageReport:
    report_id:        str              = field(default_factory=lambda: str(uuid.uuid4()))
    portfolio_id:     str              = ""
    generated_at:     str              = field(default_factory=now_utc)
    present_engines:  Tuple[str, ...]  = field(default_factory=tuple)
    missing_engines:  Tuple[str, ...]  = field(default_factory=tuple)
    n_present:        int              = 0
    n_required:       int              = 0
    n_missing:        int              = 0
    coverage_score:   float            = 0.0
    is_full_coverage: bool             = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "coverage_score":   round(self.coverage_score, 4),
            "is_full_coverage": self.is_full_coverage,
            "n_present":        self.n_present,
            "n_missing":        self.n_missing,
            "missing":          list(self.missing_engines),
        }


class CoverageMonitor:
    """Analyzes which required engines have contributed for a portfolio."""

    def analyze(
        self,
        present_engine_ids: List[EngineId],
        portfolio_id:       str = "",
    ) -> CoverageReport:
        present_set  = set(present_engine_ids)
        required_set = set(REQUIRED_ENGINES)
        missing      = required_set - present_set
        n_required   = len(required_set)
        n_present    = len(present_set & required_set)
        coverage     = n_present / n_required if n_required > 0 else 0.0

        return CoverageReport(
            portfolio_id    = portfolio_id,
            present_engines = tuple(e.value for e in sorted(present_set, key=lambda x: x.value)),
            missing_engines = tuple(e.value for e in sorted(missing, key=lambda x: x.value)),
            n_present       = n_present,
            n_required      = n_required,
            n_missing       = len(missing),
            coverage_score  = round(coverage, 4),
            is_full_coverage = len(missing) == 0,
        )
