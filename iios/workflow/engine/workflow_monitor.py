"""
workflow_monitor.py — iios.workflow.engine
-------------------------------------------
WorkflowMonitor — active monitoring of running workflows.

Tracks active executions, detects stalled workflows, and emits
monitoring events.  Does NOT execute business logic.

C16 Enterprise Workflow & Process Orchestration — Phase 1, Module 2
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from iios.common.logging.logging_manager import get_logger

_log = get_logger(__name__)

_OnStall = Callable[[str, str, float], None]   # (request_id, session_id, elapsed_ms)


@dataclass(frozen=True)
class ActiveWorkflowRecord:
    """Snapshot of a currently-running workflow."""
    request_id:  str
    session_id:  str
    workflow_id: str
    started_at:  float   # monotonic
    registered_at: str

    def elapsed_ms(self) -> float:
        return (time.monotonic() - self.started_at) * 1000

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id":  self.request_id,
            "session_id":  self.session_id,
            "workflow_id": self.workflow_id,
            "elapsed_ms":  round(self.elapsed_ms(), 3),
            "registered_at": self.registered_at,
        }


class WorkflowMonitor:
    """
    Thread-safe tracker for active workflow executions.

    Provides:
      - Registration of started workflows
      - Deregistration of completed / failed workflows
      - Stall detection (optional callback)
      - Snapshot of active workflows
    """

    def __init__(
        self,
        stall_threshold_ms: float               = 30_000.0,
        on_stall:           Optional[_OnStall]  = None,
    ) -> None:
        self._stall_ms = stall_threshold_ms
        self._on_stall = on_stall
        self._active:  Dict[str, ActiveWorkflowRecord] = {}
        self._lock     = threading.Lock()

    # ----------------------------------------------------------------
    # Registration
    # ----------------------------------------------------------------

    def register(
        self,
        request_id:  str,
        session_id:  str,
        workflow_id: str,
    ) -> ActiveWorkflowRecord:
        record = ActiveWorkflowRecord(
            request_id    = request_id,
            session_id    = session_id,
            workflow_id   = workflow_id,
            started_at    = time.monotonic(),
            registered_at = datetime.now(tz=timezone.utc).isoformat(),
        )
        with self._lock:
            self._active[request_id] = record
        _log.debug(
            f"Monitor: registered request={request_id!r} "
            f"session={session_id!r}"
        )
        return record

    def deregister(self, request_id: str) -> Optional[ActiveWorkflowRecord]:
        with self._lock:
            record = self._active.pop(request_id, None)
        if record:
            _log.debug(
                f"Monitor: deregistered request={request_id!r} "
                f"elapsed={record.elapsed_ms():.1f}ms"
            )
        return record

    # ----------------------------------------------------------------
    # Stall detection
    # ----------------------------------------------------------------

    def check_stalls(self) -> List[ActiveWorkflowRecord]:
        """
        Identify and return all stalled workflow records.

        A workflow is stalled if elapsed_ms() >= stall_threshold_ms.
        Fires on_stall callback for each stalled workflow.
        """
        stalled = []
        with self._lock:
            records = list(self._active.values())
        for record in records:
            if record.elapsed_ms() >= self._stall_ms:
                stalled.append(record)
                if self._on_stall:
                    try:
                        self._on_stall(
                            record.request_id,
                            record.session_id,
                            record.elapsed_ms(),
                        )
                    except Exception as exc:
                        _log.warning(
                            f"Monitor on_stall callback error: {exc!r}"
                        )
        return stalled

    # ----------------------------------------------------------------
    # Introspection
    # ----------------------------------------------------------------

    def get(self, request_id: str) -> Optional[ActiveWorkflowRecord]:
        with self._lock:
            return self._active.get(request_id)

    def all_active(self) -> List[ActiveWorkflowRecord]:
        with self._lock:
            return list(self._active.values())

    def active_count(self) -> int:
        with self._lock:
            return len(self._active)

    def clear(self) -> None:
        with self._lock:
            self._active.clear()

    @property
    def stall_threshold_ms(self) -> float:
        return self._stall_ms
