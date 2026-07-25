"""
workflow_policy_history.py — iios.workflow.policies
----------------------------------------------------
WorkflowPolicyHistory — bounded, thread-safe history of governance
policy requests and responses.

C16 Enterprise Workflow & Process Orchestration — Phase 1, Module 3
"""
from __future__ import annotations

import threading
from collections import deque
from typing import Dict, List, Optional

from iios.common.logging.logging_manager import get_logger

from .constants import DEFAULT_MAX_HISTORY
from .workflow_policy_request import WorkflowPolicyRequest
from .workflow_policy_response import WorkflowPolicyResponse

_log = get_logger(__name__)


class WorkflowPolicyHistory:
    """
    Bounded, thread-safe history of governance policy evaluations.

    Stores both requests and responses indexed by their respective IDs
    and by workflow_id.  Oldest entries are evicted when capacity is
    exceeded.
    """

    def __init__(self, max_entries: int = DEFAULT_MAX_HISTORY) -> None:
        self._max = max_entries
        self._req_deque:  deque[WorkflowPolicyRequest]      = deque(maxlen=max_entries)
        self._resp_deque: deque[WorkflowPolicyResponse]     = deque(maxlen=max_entries)
        self._req_by_id:  Dict[str, WorkflowPolicyRequest]  = {}
        self._resp_by_id: Dict[str, WorkflowPolicyResponse] = {}
        self._by_wf:      Dict[str, List[str]]              = {}  # workflow_id → [request_id]
        self._lock        = threading.Lock()

    # ----------------------------------------------------------------
    # Recording
    # ----------------------------------------------------------------

    def record_request(self, request: WorkflowPolicyRequest) -> None:
        with self._lock:
            if len(self._req_deque) == self._max and self._req_deque:
                oldest = self._req_deque[0]
                self._req_by_id.pop(oldest.request_id, None)
            self._req_deque.append(request)
            self._req_by_id[request.request_id] = request
            self._by_wf.setdefault(request.workflow_id, []).append(request.request_id)

    def record_response(self, response: WorkflowPolicyResponse) -> None:
        with self._lock:
            if len(self._resp_deque) == self._max and self._resp_deque:
                oldest = self._resp_deque[0]
                self._resp_by_id.pop(oldest.response_id, None)
            self._resp_deque.append(response)
            self._resp_by_id[response.response_id] = response

    # ----------------------------------------------------------------
    # Retrieval
    # ----------------------------------------------------------------

    def get_request(self, request_id: str) -> Optional[WorkflowPolicyRequest]:
        with self._lock:
            return self._req_by_id.get(request_id)

    def get_response(self, response_id: str) -> Optional[WorkflowPolicyResponse]:
        with self._lock:
            return self._resp_by_id.get(response_id)

    def recent_requests(self, n: int = 20) -> List[WorkflowPolicyRequest]:
        """Return the N most-recent requests (newest first)."""
        with self._lock:
            items = list(self._req_deque)
        return list(reversed(items[-n:]))

    def recent_responses(self, n: int = 20) -> List[WorkflowPolicyResponse]:
        """Return the N most-recent responses (newest first)."""
        with self._lock:
            items = list(self._resp_deque)
        return list(reversed(items[-n:]))

    def by_workflow(self, workflow_id: str) -> List[WorkflowPolicyRequest]:
        """Return all requests for a given workflow_id."""
        with self._lock:
            ids  = list(self._by_wf.get(workflow_id, []))
            reqs = [self._req_by_id[rid] for rid in ids if rid in self._req_by_id]
        return reqs

    # ----------------------------------------------------------------
    # Introspection
    # ----------------------------------------------------------------

    def request_count(self) -> int:
        with self._lock:
            return len(self._req_deque)

    def response_count(self) -> int:
        with self._lock:
            return len(self._resp_deque)

    def clear(self) -> int:
        """Clear all history.  Returns number of requests cleared."""
        with self._lock:
            n = len(self._req_deque)
            self._req_deque.clear()
            self._resp_deque.clear()
            self._req_by_id.clear()
            self._resp_by_id.clear()
            self._by_wf.clear()
        return n
