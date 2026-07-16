"""iios/execution/oms/persistence/recovery_index.py
==================================================
RecoveryIndex — thread-safe in-process index of RecoveryRecord objects.

C6 Execution Intelligence — Phase 2, Module 5
"""
from __future__ import annotations

import threading
from typing import Iterator

from iios.execution.oms.persistence.constants import RecoveryState
from iios.execution.oms.persistence.recovery_record import RecoveryRecord


class RecoveryIndex:
    """
    Thread-safe, in-memory index of RecoveryRecord objects.

    Indexed by:
    - recovery_id  (primary key — unique)
    - order_id     (secondary key — one order may have many recovery attempts)
    - record_id    (secondary key — one record may have many recovery attempts)

    Only holds the *latest* record for a given recovery_id; to update a
    recovery's state use ``replace()`` with the new RecoveryRecord.
    """

    def __init__(self) -> None:
        self._by_recovery_id: dict[str, RecoveryRecord] = {}
        self._by_order_id:    dict[str, list[RecoveryRecord]] = {}
        self._by_record_id:   dict[str, list[RecoveryRecord]] = {}
        self._lock = threading.RLock()

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def register(self, record: RecoveryRecord) -> None:
        """Add a new RecoveryRecord.  Raises ValueError on duplicate recovery_id."""
        with self._lock:
            if record.recovery_id in self._by_recovery_id:
                raise ValueError(
                    f"RecoveryRecord '{record.recovery_id}' already registered"
                )
            self._by_recovery_id[record.recovery_id] = record
            self._by_order_id.setdefault(record.order_id, []).append(record)
            self._by_record_id.setdefault(record.record_id, []).append(record)

    def replace(self, record: RecoveryRecord) -> None:
        """Update an existing RecoveryRecord in-place (e.g., after state transition)."""
        with self._lock:
            if record.recovery_id not in self._by_recovery_id:
                raise KeyError(
                    f"RecoveryRecord '{record.recovery_id}' not found"
                )
            old = self._by_recovery_id[record.recovery_id]
            self._by_recovery_id[record.recovery_id] = record

            # Update secondary indices
            for lst in (
                self._by_order_id.get(old.order_id, []),
                self._by_record_id.get(old.record_id, []),
            ):
                for i, r in enumerate(lst):
                    if r.recovery_id == record.recovery_id:
                        lst[i] = record
                        break

    def remove(self, recovery_id: str) -> bool:
        """Remove a recovery record.  Returns True if removed, False if not found."""
        with self._lock:
            record = self._by_recovery_id.pop(recovery_id, None)
            if record is None:
                return False
            _remove_from_list(self._by_order_id.get(record.order_id, []), recovery_id)
            _remove_from_list(self._by_record_id.get(record.record_id, []), recovery_id)
            return True

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def get(self, recovery_id: str) -> RecoveryRecord | None:
        with self._lock:
            return self._by_recovery_id.get(recovery_id)

    def by_order_id(self, order_id: str) -> list[RecoveryRecord]:
        with self._lock:
            return list(self._by_order_id.get(order_id, []))

    def by_record_id(self, record_id: str) -> list[RecoveryRecord]:
        with self._lock:
            return list(self._by_record_id.get(record_id, []))

    def pending(self) -> list[RecoveryRecord]:
        with self._lock:
            return [
                r for r in self._by_recovery_id.values()
                if r.recovery_state == RecoveryState.PENDING
            ]

    def in_progress(self) -> list[RecoveryRecord]:
        with self._lock:
            return [
                r for r in self._by_recovery_id.values()
                if r.recovery_state == RecoveryState.IN_PROGRESS
            ]

    def completed(self) -> list[RecoveryRecord]:
        with self._lock:
            return [
                r for r in self._by_recovery_id.values()
                if r.recovery_state in (
                    RecoveryState.COMPLETED,
                    RecoveryState.FAILED,
                    RecoveryState.PARTIAL,
                )
            ]

    def all(self) -> list[RecoveryRecord]:
        with self._lock:
            return list(self._by_recovery_id.values())

    @property
    def count(self) -> int:
        with self._lock:
            return len(self._by_recovery_id)

    @property
    def pending_count(self) -> int:
        with self._lock:
            return sum(
                1 for r in self._by_recovery_id.values()
                if r.recovery_state == RecoveryState.PENDING
            )

    def __iter__(self) -> Iterator[RecoveryRecord]:
        with self._lock:
            snapshot = list(self._by_recovery_id.values())
        return iter(snapshot)

    def __len__(self) -> int:
        return self.count


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _remove_from_list(lst: list[RecoveryRecord], recovery_id: str) -> None:
    """Remove the first entry with the given recovery_id from lst in-place."""
    for i, r in enumerate(lst):
        if r.recovery_id == recovery_id:
            lst.pop(i)
            return
