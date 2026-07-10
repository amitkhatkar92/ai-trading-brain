"""iios/execution/monitoring/reconciliation/reconciliation_report.py"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from iios.execution.monitoring.monitoring_constants import (
    EntityType,
    ReconciliationStatus,
)
from iios.execution.monitoring.reconciliation.reconciliation_result import ReconciliationResult


@dataclass
class ReconciliationReport:
    """
    Summary report produced by one full reconciliation run.

    Contains aggregate counts and the list of per-entity results.
    """

    entity_type:         EntityType           = EntityType.ORDER
    status:              ReconciliationStatus  = ReconciliationStatus.MATCHED
    total_compared:      int                   = 0
    matched:             int                   = 0
    discrepant:          int                   = 0
    missing_internal:    int                   = 0
    missing_external:    int                   = 0
    results:             list[ReconciliationResult] = field(default_factory=list)
    started_at:          float                 = field(default_factory=time.time)
    completed_at:        float | None          = None
    report_id:           str                   = field(default_factory=lambda: str(uuid.uuid4()))
    reconciliation_id:   str                   = ""   # set by engine at run time
    metadata:            dict[str, Any]        = field(default_factory=dict)

    # ── Computed ──────────────────────────────────────────────────────────────

    def match_rate(self) -> float:
        if self.total_compared == 0:
            return 1.0
        return self.matched / self.total_compared

    def discrepancy_rate(self) -> float:
        return 1.0 - self.match_rate()

    def duration_sec(self) -> float | None:
        if self.completed_at is None:
            return None
        return max(0.0, self.completed_at - self.started_at)

    def is_clean(self) -> bool:
        return self.discrepant == 0 and self.missing_internal == 0 and self.missing_external == 0

    def discrepant_results(self) -> list[ReconciliationResult]:
        return [r for r in self.results if r.has_discrepancies()]

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_id":          self.report_id,
            "reconciliation_id":  self.reconciliation_id,
            "entity_type":        self.entity_type.value,
            "status":             self.status.value,
            "total_compared":     self.total_compared,
            "matched":            self.matched,
            "discrepant":         self.discrepant,
            "missing_internal":   self.missing_internal,
            "missing_external":   self.missing_external,
            "match_rate":         round(self.match_rate(), 4),
            "is_clean":           self.is_clean(),
            "started_at":         self.started_at,
            "completed_at":       self.completed_at,
            "duration_sec":       self.duration_sec(),
            "metadata":           self.metadata,
        }
