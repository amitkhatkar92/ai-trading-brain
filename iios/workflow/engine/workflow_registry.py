"""
workflow_registry.py — iios.workflow.engine
--------------------------------------------
WorkflowEngineRegistry — tracks active requests and their
corresponding session IDs.

C16 Enterprise Workflow & Process Orchestration — Phase 1, Module 2
"""
from __future__ import annotations

import threading
from typing import Dict, List, Optional

from .constants import DEFAULT_MAX_SESSIONS
from .workflow_request import WorkflowEngineRequest
from .workflow_response import WorkflowEngineResponse


class WorkflowEngineRegistry:
    """
    Thread-safe registry that maps active request_ids to their
    session_ids and optionally to responses.
    """

    def __init__(self, max_active: int = DEFAULT_MAX_SESSIONS) -> None:
        self._max      = max_active
        self._requests: Dict[str, WorkflowEngineRequest]  = {}
        self._sessions: Dict[str, str]                    = {}   # request_id → session_id
        self._responses: Dict[str, WorkflowEngineResponse] = {}  # request_id → response
        self._lock     = threading.Lock()

    # ----------------------------------------------------------------
    # Write
    # ----------------------------------------------------------------

    def register(
        self,
        request:    WorkflowEngineRequest,
        session_id: str,
    ) -> None:
        with self._lock:
            self._requests[request.request_id] = request
            self._sessions[request.request_id] = session_id

    def record_response(
        self,
        request_id: str,
        response:   WorkflowEngineResponse,
    ) -> None:
        with self._lock:
            self._responses[request_id] = response

    def deregister(self, request_id: str) -> bool:
        with self._lock:
            removed = request_id in self._requests
            self._requests.pop(request_id, None)
            self._sessions.pop(request_id, None)
            return removed

    # ----------------------------------------------------------------
    # Read
    # ----------------------------------------------------------------

    def get_request(self, request_id: str) -> Optional[WorkflowEngineRequest]:
        with self._lock:
            return self._requests.get(request_id)

    def get_session_id(self, request_id: str) -> Optional[str]:
        with self._lock:
            return self._sessions.get(request_id)

    def get_response(self, request_id: str) -> Optional[WorkflowEngineResponse]:
        with self._lock:
            return self._responses.get(request_id)

    def all_request_ids(self) -> List[str]:
        with self._lock:
            return list(self._requests.keys())

    def all_session_ids(self) -> List[str]:
        with self._lock:
            return list(self._sessions.values())

    def exists(self, request_id: str) -> bool:
        with self._lock:
            return request_id in self._requests

    # ----------------------------------------------------------------
    # Introspection
    # ----------------------------------------------------------------

    def active_count(self) -> int:
        with self._lock:
            return len(self._requests)

    def response_count(self) -> int:
        with self._lock:
            return len(self._responses)

    def clear(self) -> None:
        with self._lock:
            self._requests.clear()
            self._sessions.clear()
            self._responses.clear()

    @property
    def max_active(self) -> int:
        return self._max
