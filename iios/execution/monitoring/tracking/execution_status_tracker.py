"""iios/execution/monitoring/tracking/execution_status_tracker.py

Lightweight append-only status-transition log for each execution.
"""
from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from iios.execution.monitoring.monitoring_constants import ExecutionRecordStatus


@dataclass
class StatusTransition:
    """One recorded status change for an execution."""
    execution_id: str                  = ""
    old_status:   ExecutionRecordStatus | None = None
    new_status:   ExecutionRecordStatus = ExecutionRecordStatus.PENDING
    reason:       str                   = ""
    source:       str                   = ""
    transition_id: str                  = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp:    float                 = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "transition_id": self.transition_id,
            "execution_id":  self.execution_id,
            "old_status":    self.old_status.value if self.old_status else None,
            "new_status":    self.new_status.value,
            "reason":        self.reason,
            "source":        self.source,
            "timestamp":     self.timestamp,
        }


class ExecutionStatusTracker:
    """
    Maintains an append-only log of status transitions per execution.
    Enables full execution lifecycle reconstruction.
    Thread-safe.
    """

    def __init__(self) -> None:
        self._transitions: dict[str, list[StatusTransition]] = {}
        self._lock = threading.RLock()

    def record_transition(
        self,
        execution_id: str,
        new_status:   ExecutionRecordStatus,
        old_status:   ExecutionRecordStatus | None = None,
        reason:       str = "",
        source:       str = "",
    ) -> StatusTransition:
        t = StatusTransition(
            execution_id=execution_id,
            old_status=old_status,
            new_status=new_status,
            reason=reason,
            source=source,
        )
        with self._lock:
            self._transitions.setdefault(execution_id, []).append(t)
        return t

    def history(self, execution_id: str) -> list[StatusTransition]:
        with self._lock:
            return list(self._transitions.get(execution_id, []))

    def all_execution_ids(self) -> list[str]:
        with self._lock:
            return list(self._transitions.keys())

    def statistics(self) -> dict[str, Any]:
        with self._lock:
            total = sum(len(v) for v in self._transitions.values())
            return {
                "tracked_executions": len(self._transitions),
                "total_transitions":  total,
            }
