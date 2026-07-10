"""iios/execution/monitoring/reconciliation/reconciliation_engine.py"""
from __future__ import annotations

import logging
import threading
import time
import uuid
from typing import Any

from iios.execution.monitoring.monitoring_constants import (
    EntityType,
    ReconciliationStatus,
)
from iios.execution.monitoring.reconciliation.discrepancy_detector import DiscrepancyDetector
from iios.execution.monitoring.reconciliation.reconciliation_report import ReconciliationReport
from iios.execution.monitoring.reconciliation.reconciliation_result import (
    Discrepancy,
    DiscrepancyType,
    AlertSeverity,
    ReconciliationResult,
)

logger = logging.getLogger(__name__)


class ReconciliationEngine:
    """
    Compares internal execution records against external broker/exchange records.

    Broker-agnostic: both record sets must be supplied as normalised dicts
    keyed by a common id_field (e.g. order_id).

    Thread-safe.
    """

    def __init__(
        self,
        detector:   DiscrepancyDetector | None = None,
        id_field:   str                        = "order_id",
    ) -> None:
        self._detector       = detector or DiscrepancyDetector()
        self._default_id_field = id_field
        self._reports:        dict[str, ReconciliationReport] = {}
        self._lock            = threading.RLock()
        self._run_count       = 0

    # ── Core reconciliation ───────────────────────────────────────────────────

    def reconcile(
        self,
        internal_records:   list[dict[str, Any]],
        external_records:   list[dict[str, Any]],
        entity_type:        EntityType = EntityType.ORDER,
        fields_to_compare:  list[str] | None = None,
        id_field:           str | None = None,
    ) -> ReconciliationReport:
        """
        Compare *internal_records* vs *external_records*.

        Returns a ReconciliationReport with full per-entity results.
        """
        key   = id_field or self._default_id_field
        recon_id = str(uuid.uuid4())
        report   = ReconciliationReport(
            entity_type=entity_type,
            reconciliation_id=recon_id,
            started_at=time.time(),
        )

        # Build lookup maps
        internal_map: dict[str, dict[str, Any]] = {r.get(key, ""): r for r in internal_records}
        external_map: dict[str, dict[str, Any]] = {r.get(key, ""): r for r in external_records}

        all_ids = set(internal_map) | set(external_map)
        results: list[ReconciliationResult] = []

        for entity_id in all_ids:
            iv = internal_map.get(entity_id)
            ev = external_map.get(entity_id)
            result = self._compare_pair(entity_id, iv, ev, entity_type, fields_to_compare)
            results.append(result)

        # Aggregate
        report.total_compared    = len(all_ids)
        report.matched           = sum(1 for r in results if r.status == ReconciliationStatus.MATCHED)
        report.discrepant        = sum(1 for r in results if r.status == ReconciliationStatus.DISCREPANT)
        report.missing_internal  = sum(1 for r in results if any(
            d.discrepancy_type == DiscrepancyType.MISSING_INTERNAL for d in r.discrepancies
        ))
        report.missing_external  = sum(1 for r in results if any(
            d.discrepancy_type == DiscrepancyType.MISSING_EXTERNAL for d in r.discrepancies
        ))
        report.results           = results
        report.status            = (
            ReconciliationStatus.MATCHED
            if report.discrepant == 0 and report.missing_internal == 0 and report.missing_external == 0
            else ReconciliationStatus.DISCREPANT
        )
        report.completed_at = time.time()

        with self._lock:
            self._reports[recon_id] = report
            self._run_count += 1

        logger.info(
            "Reconciliation %s: %d/%d matched, %d discrepant",
            recon_id[:8], report.matched, report.total_compared, report.discrepant,
        )
        return report

    # ── Stored reports ────────────────────────────────────────────────────────

    def get_report(self, reconciliation_id: str) -> ReconciliationReport | None:
        with self._lock:
            return self._reports.get(reconciliation_id)

    def all_reports(self) -> list[ReconciliationReport]:
        with self._lock:
            return list(self._reports.values())

    def run_count(self) -> int:
        with self._lock:
            return self._run_count

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _compare_pair(
        self,
        entity_id:         str,
        internal:          dict[str, Any] | None,
        external:          dict[str, Any] | None,
        entity_type:       EntityType,
        fields_to_compare: list[str] | None,
    ) -> ReconciliationResult:
        if internal is None:
            return ReconciliationResult(
                entity_type=entity_type,
                internal_id="",
                external_id=entity_id,
                status=ReconciliationStatus.DISCREPANT,
                discrepancies=[
                    Discrepancy(
                        discrepancy_type=DiscrepancyType.MISSING_INTERNAL,
                        field_name=self._default_id_field,
                        external_value=entity_id,
                        severity=AlertSeverity.HIGH,
                        description=f"Entity '{entity_id}' exists externally but not internally",
                    )
                ],
                external_record=external or {},
            )
        if external is None:
            return ReconciliationResult(
                entity_type=entity_type,
                internal_id=entity_id,
                external_id="",
                status=ReconciliationStatus.DISCREPANT,
                discrepancies=[
                    Discrepancy(
                        discrepancy_type=DiscrepancyType.MISSING_EXTERNAL,
                        field_name=self._default_id_field,
                        internal_value=entity_id,
                        severity=AlertSeverity.MEDIUM,
                        description=f"Entity '{entity_id}' exists internally but not externally",
                    )
                ],
                internal_record=internal,
            )

        discs = self._detector.detect(internal, external, fields_to_compare)
        return ReconciliationResult(
            entity_type=entity_type,
            internal_id=entity_id,
            external_id=entity_id,
            status=ReconciliationStatus.DISCREPANT if discs else ReconciliationStatus.MATCHED,
            discrepancies=discs,
            internal_record=internal,
            external_record=external,
        )
