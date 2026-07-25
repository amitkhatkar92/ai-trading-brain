"""
workflow_history.py — iios.workflow.engine
-------------------------------------------
Bounded, append-only history of workflow engine requests and responses.

C16 Enterprise Workflow & Process Orchestration — Phase 1, Module 2
"""
from __future__ import annotations

import threading
from collections import deque
from typing import Deque, Dict, List, Optional

from .constants import DEFAULT_MAX_HISTORY
from .workflow_request import WorkflowEngineRequest
from .workflow_response import WorkflowEngineResponse


class WorkflowEngineHistory:
    """
    Thread-safe, bounded, append-only history of workflow engine activity.

    Maintains separate bounded queues for requests and responses.
    Per-session and per-request indexes allow efficient lookup.
    """

    def __init__(self, max_history: int = DEFAULT_MAX_HISTORY) -> None:
        self._max        = max_history
        self._requests:  Deque[WorkflowEngineRequest]  = deque(maxlen=max_history)
        self._responses: Deque[WorkflowEngineResponse] = deque(maxlen=max_history)
        self._req_idx:   Dict[str, WorkflowEngineRequest]  = {}
        self._resp_idx:  Dict[str, WorkflowEngineResponse] = {}
        self._by_session: Dict[str, List[str]]             = {}   # session_id → [response_id]
        self._lock       = threading.Lock()

    # ----------------------------------------------------------------
    # Record
    # ----------------------------------------------------------------

    def record_request(self, request: WorkflowEngineRequest) -> None:
        with self._lock:
            if len(self._requests) == self._max:
                oldest = self._requests[0]
                self._req_idx.pop(oldest.request_id, None)
            self._requests.append(request)
            self._req_idx[request.request_id] = request

    def record_response(self, response: WorkflowEngineResponse) -> None:
        with self._lock:
            if len(self._responses) == self._max:
                oldest = self._responses[0]
                self._resp_idx.pop(oldest.response_id, None)
                sl = self._by_session.get(oldest.session_id, [])
                if oldest.response_id in sl:
                    sl.remove(oldest.response_id)
            self._responses.append(response)
            self._resp_idx[response.response_id] = response
            self._by_session.setdefault(response.session_id, []).append(
                response.response_id
            )

    # ----------------------------------------------------------------
    # Read
    # ----------------------------------------------------------------

    def get_request(self, request_id: str) -> Optional[WorkflowEngineRequest]:
        with self._lock:
            return self._req_idx.get(request_id)

    def get_response(self, response_id: str) -> Optional[WorkflowEngineResponse]:
        with self._lock:
            return self._resp_idx.get(response_id)

    def recent_requests(self, n: int = 20) -> List[WorkflowEngineRequest]:
        with self._lock:
            return list(self._requests)[-n:]

    def recent_responses(self, n: int = 20) -> List[WorkflowEngineResponse]:
        with self._lock:
            return list(self._responses)[-n:]

    def by_session(self, session_id: str) -> List[WorkflowEngineResponse]:
        with self._lock:
            ids = list(self._by_session.get(session_id, []))
        return [r for rid in ids if (r := self._resp_idx.get(rid))]

    def response_for_request(
        self, request_id: str
    ) -> Optional[WorkflowEngineResponse]:
        with self._lock:
            for resp in reversed(self._responses):
                if resp.request_id == request_id:
                    return resp
        return None

    # ----------------------------------------------------------------
    # Introspection
    # ----------------------------------------------------------------

    def request_count(self) -> int:
        with self._lock:
            return len(self._requests)

    def response_count(self) -> int:
        with self._lock:
            return len(self._responses)

    def clear(self) -> None:
        with self._lock:
            self._requests.clear()
            self._responses.clear()
            self._req_idx.clear()
            self._resp_idx.clear()
            self._by_session.clear()
