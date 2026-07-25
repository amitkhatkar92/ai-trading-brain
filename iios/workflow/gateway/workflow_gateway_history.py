"""
workflow_gateway_history.py — iios.workflow.gateway
----------------------------------------------------
WorkflowGatewayHistory — bounded, thread-safe history of gateway
request/response pairs.

C16 Enterprise Workflow & Process Orchestration — Phase 1, Module 6
"""
from __future__ import annotations

import threading
import uuid
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .constants import DEFAULT_MAX_HISTORY, PREFIX_RECORD
from .workflow_gateway_request import WorkflowGatewayRequest
from .workflow_gateway_response import WorkflowGatewayResponse


@dataclass(frozen=True)
class WorkflowGatewayHistoryRecord:
    """Immutable record of a completed gateway request/response pair."""
    record_id:     str
    request_id:    str
    workflow_id:   str
    request_type:  str
    status:        str
    snapshot_id:   str
    error_message: str
    latency_ms:    float
    created_at:    str
    metadata:      Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "record_id":    self.record_id,
            "request_id":   self.request_id,
            "workflow_id":  self.workflow_id,
            "request_type": self.request_type,
            "status":       self.status,
            "snapshot_id":  self.snapshot_id,
            "error_message": self.error_message,
            "latency_ms":   self.latency_ms,
            "created_at":   self.created_at,
        }


class WorkflowGatewayHistory:
    """
    Thread-safe bounded history of WorkflowGatewayHistoryRecord objects.
    """

    def __init__(self, max_records: int = DEFAULT_MAX_HISTORY) -> None:
        self._max      = max_records
        self._deque:   deque[WorkflowGatewayHistoryRecord]    = deque(maxlen=max_records)
        self._by_req:  Dict[str, WorkflowGatewayHistoryRecord] = {}
        self._by_wf:   Dict[str, List[str]]                   = {}
        self._lock     = threading.Lock()

    def record(
        self,
        request:  WorkflowGatewayRequest,
        response: WorkflowGatewayResponse,
    ) -> WorkflowGatewayHistoryRecord:
        rec = WorkflowGatewayHistoryRecord(
            record_id     = f"{PREFIX_RECORD}{uuid.uuid4().hex[:10]}",
            request_id    = request.request_id,
            workflow_id   = request.workflow_id,
            request_type  = request.request_type.value,
            status        = response.status.value,
            snapshot_id   = response.snapshot_id,
            error_message = response.error_message,
            latency_ms    = response.gateway_latency_ms,
            created_at    = datetime.now(tz=timezone.utc).isoformat(),
            metadata      = {},
        )
        with self._lock:
            if len(self._deque) == self._max and self._deque:
                oldest = self._deque[0]
                self._by_req.pop(oldest.request_id, None)
            self._deque.append(rec)
            self._by_req[rec.request_id] = rec
            self._by_wf.setdefault(rec.workflow_id, [])
            if rec.request_id not in self._by_wf[rec.workflow_id]:
                self._by_wf[rec.workflow_id].append(rec.request_id)
        return rec

    def get(self, request_id: str) -> Optional[WorkflowGatewayHistoryRecord]:
        with self._lock:
            return self._by_req.get(request_id)

    def for_workflow(self, workflow_id: str) -> List[WorkflowGatewayHistoryRecord]:
        with self._lock:
            ids  = list(self._by_wf.get(workflow_id, []))
            recs = [self._by_req[rid] for rid in ids if rid in self._by_req]
        return recs

    def recent(self, n: int = 20) -> List[WorkflowGatewayHistoryRecord]:
        with self._lock:
            items = list(self._deque)
        return list(reversed(items[-n:]))

    def count(self) -> int:
        with self._lock:
            return len(self._deque)

    def clear(self) -> int:
        with self._lock:
            n = len(self._deque)
            self._deque.clear()
            self._by_req.clear()
            self._by_wf.clear()
        return n
