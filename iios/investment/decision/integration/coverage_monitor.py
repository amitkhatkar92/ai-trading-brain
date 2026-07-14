"""iios/investment/decision/integration/coverage_monitor.py
CoverageMonitor — tracks component coverage across integration cycles.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Any, Dict, FrozenSet, List

from iios.investment.decision.integration.integration_constants import ComponentId


@dataclass(frozen=True)
class CoverageReport:
    required_count:   int
    present_count:    int
    coverage_fraction: float
    missing_required: FrozenSet[str]
    optional_present: FrozenSet[str]

    @property
    def is_full_coverage(self) -> bool:
        return len(self.missing_required) == 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "required_count":    self.required_count,
            "present_count":     self.present_count,
            "coverage_fraction": round(self.coverage_fraction, 3),
            "missing_required":  sorted(self.missing_required),
            "optional_present":  sorted(self.optional_present),
            "is_full_coverage":  self.is_full_coverage,
        }


class CoverageMonitor:
    """
    Monitors component coverage for in-progress decisions.
    Tracks running coverage statistics across multiple integration cycles.
    """

    def __init__(self) -> None:
        self._lock          = threading.RLock()
        self._total_cycles  = 0
        self._full_coverage = 0

    def evaluate(self, present: FrozenSet) -> CoverageReport:
        required        = ComponentId.required()
        req_values      = frozenset(c.value if hasattr(c, "value") else c for c in required)
        present_values  = frozenset(
            c.value if hasattr(c, "value") else str(c) for c in present
        )
        optional_all    = frozenset(c.value for c in ComponentId.all_components())
        optional_only   = optional_all - req_values

        present_req     = req_values & present_values
        present_opt     = optional_only & present_values
        missing_req     = req_values - present_values

        fraction = len(present_req) / len(req_values) if req_values else 0.0

        with self._lock:
            self._total_cycles += 1
            if not missing_req:
                self._full_coverage += 1

        return CoverageReport(
            required_count    = len(req_values),
            present_count     = len(present_req),
            coverage_fraction = fraction,
            missing_required  = frozenset(missing_req),
            optional_present  = frozenset(present_opt),
        )

    def full_coverage_rate(self) -> float:
        with self._lock:
            if self._total_cycles == 0:
                return 0.0
            return self._full_coverage / self._total_cycles

    def reset(self) -> None:
        with self._lock:
            self._total_cycles  = 0
            self._full_coverage = 0
