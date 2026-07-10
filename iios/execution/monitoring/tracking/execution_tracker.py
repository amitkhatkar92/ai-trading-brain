"""iios/execution/monitoring/tracking/execution_tracker.py"""
from __future__ import annotations

import logging
import threading
import time
from typing import Any

from iios.execution.monitoring.monitoring_constants import (
    DEFAULT_MAX_EXECUTION_RECORDS,
    ExecutionRecordStatus,
    TERMINAL_EXECUTION_STATUSES,
)
from iios.execution.monitoring.monitoring_exceptions import (
    ExecutionRecordAlreadyExistsError,
    ExecutionRecordNotFoundError,
    ExecutionTrackerOverflowError,
)
from iios.execution.monitoring.core.execution_record import ExecutionRecord

logger = logging.getLogger(__name__)


class ExecutionTracker:
    """
    Central store for all active and recently completed ExecutionRecord objects.

    Thread-safe.  Supports creation, status updates, and bulk queries.
    """

    def __init__(self, max_records: int = DEFAULT_MAX_EXECUTION_RECORDS) -> None:
        self._records:     dict[str, ExecutionRecord] = {}
        self._by_order:    dict[str, str]             = {}   # order_id → execution_id
        self._by_broker:   dict[str, list[str]]       = {}   # broker_id → [execution_ids]
        self._max_records  = max_records
        self._lock         = threading.RLock()

    # ── CRUD ──────────────────────────────────────────────────────────────────

    def create(self, record: ExecutionRecord) -> ExecutionRecord:
        with self._lock:
            if record.execution_id in self._records:
                raise ExecutionRecordAlreadyExistsError(
                    f"Execution '{record.execution_id}' already tracked",
                    "EM-012",
                )
            if len(self._records) >= self._max_records:
                raise ExecutionTrackerOverflowError(
                    f"ExecutionTracker capacity reached ({self._max_records})",
                    "EM-013",
                )
            self._records[record.execution_id] = record
            if record.order_id:
                self._by_order[record.order_id] = record.execution_id
            if record.broker_id:
                self._by_broker.setdefault(record.broker_id, []).append(record.execution_id)
            logger.debug("Tracking execution %s", record.execution_id)
            return record

    def get(self, execution_id: str) -> ExecutionRecord:
        with self._lock:
            record = self._records.get(execution_id)
        if record is None:
            raise ExecutionRecordNotFoundError(
                f"No execution record found for '{execution_id}'",
                "EM-011",
            )
        return record

    def get_by_order(self, order_id: str) -> ExecutionRecord | None:
        with self._lock:
            eid = self._by_order.get(order_id)
            if eid is None:
                return None
            return self._records.get(eid)

    def has(self, execution_id: str) -> bool:
        with self._lock:
            return execution_id in self._records

    def update_status(
        self,
        execution_id: str,
        new_status:   ExecutionRecordStatus,
        reason:       str = "",
    ) -> ExecutionRecord:
        record = self.get(execution_id)
        record.transition_to(new_status, reason)
        logger.debug("Execution %s → %s", execution_id, new_status.value)
        return record

    def apply_fill(
        self,
        execution_id: str,
        quantity:     float,
        price:        float,
    ) -> ExecutionRecord:
        record = self.get(execution_id)
        record.apply_fill(quantity, price)
        return record

    # ── Bulk queries ──────────────────────────────────────────────────────────

    def active_executions(self) -> list[ExecutionRecord]:
        with self._lock:
            return [
                r for r in self._records.values()
                if r.status not in TERMINAL_EXECUTION_STATUSES
            ]

    def terminal_executions(self) -> list[ExecutionRecord]:
        with self._lock:
            return [
                r for r in self._records.values()
                if r.status in TERMINAL_EXECUTION_STATUSES
            ]

    def executions_for_broker(self, broker_id: str) -> list[ExecutionRecord]:
        with self._lock:
            ids = self._by_broker.get(broker_id, [])
            return [self._records[eid] for eid in ids if eid in self._records]

    def all_records(self) -> list[ExecutionRecord]:
        with self._lock:
            return list(self._records.values())

    def size(self) -> int:
        with self._lock:
            return len(self._records)

    def statistics(self) -> dict[str, Any]:
        with self._lock:
            statuses: dict[str, int] = {}
            for r in self._records.values():
                statuses[r.status.value] = statuses.get(r.status.value, 0) + 1
            return {
                "total":    len(self._records),
                "active":   len([r for r in self._records.values()
                                  if r.status not in TERMINAL_EXECUTION_STATUSES]),
                "by_status": statuses,
            }
