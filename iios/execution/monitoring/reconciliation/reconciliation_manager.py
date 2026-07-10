"""iios/execution/monitoring/reconciliation/reconciliation_manager.py"""
from __future__ import annotations

import threading
import time
from typing import Any

from iios.execution.monitoring.monitoring_constants import EntityType
from iios.execution.monitoring.reconciliation.reconciliation_engine import ReconciliationEngine
from iios.execution.monitoring.reconciliation.reconciliation_report import ReconciliationReport


class ReconciliationManager:
    """
    Orchestrates scheduled and on-demand reconciliation runs across
    multiple entity types.

    Thread-safe.
    """

    def __init__(self, engine: ReconciliationEngine | None = None) -> None:
        self._engine   = engine or ReconciliationEngine()
        self._history: list[ReconciliationReport] = []
        self._lock     = threading.RLock()

    # ── Run management ────────────────────────────────────────────────────────

    def run(
        self,
        internal_records:  list[dict[str, Any]],
        external_records:  list[dict[str, Any]],
        entity_type:       EntityType        = EntityType.ORDER,
        fields_to_compare: list[str] | None  = None,
        id_field:          str               = "order_id",
    ) -> ReconciliationReport:
        report = self._engine.reconcile(
            internal_records,
            external_records,
            entity_type=entity_type,
            fields_to_compare=fields_to_compare,
            id_field=id_field,
        )
        with self._lock:
            self._history.append(report)
        return report

    def last_report(self) -> ReconciliationReport | None:
        with self._lock:
            return self._history[-1] if self._history else None

    def all_reports(self) -> list[ReconciliationReport]:
        with self._lock:
            return list(self._history)

    def clean_runs(self) -> int:
        with self._lock:
            return sum(1 for r in self._history if r.is_clean())

    def discrepant_runs(self) -> int:
        with self._lock:
            return sum(1 for r in self._history if not r.is_clean())

    def statistics(self) -> dict[str, Any]:
        with self._lock:
            return {
                "total_runs":    len(self._history),
                "clean_runs":    sum(1 for r in self._history if r.is_clean()),
                "discrepant_runs": sum(1 for r in self._history if not r.is_clean()),
                "engine_run_count": self._engine.run_count(),
            }
