"""
workflow_gateway_registry.py — iios.workflow.gateway
-----------------------------------------------------
WorkflowGatewayRegistry — thread-safe in-memory registry of
active/recent gateway responses indexed by request_id and workflow_id.

C16 Enterprise Workflow & Process Orchestration — Phase 1, Module 6
"""
from __future__ import annotations

import threading
from typing import Dict, List, Optional

from .constants import DEFAULT_MAX_REGISTRY
from .exceptions import WorkflowGatewayRequestError
from .workflow_gateway_response import WorkflowGatewayResponse


class WorkflowGatewayRegistry:
    """
    Thread-safe, bounded in-memory registry of gateway responses.
    """

    def __init__(self, max_entries: int = DEFAULT_MAX_REGISTRY) -> None:
        self._max      = max_entries
        self._by_req:  Dict[str, WorkflowGatewayResponse] = {}
        self._by_wf:   Dict[str, List[str]]               = {}
        self._order:   List[str]                          = []
        self._lock     = threading.Lock()

    def register(self, response: WorkflowGatewayResponse) -> None:
        with self._lock:
            if len(self._order) >= self._max:
                # Evict oldest
                oldest_req = self._order.pop(0)
                old_resp   = self._by_req.pop(oldest_req, None)
                if old_resp:
                    wf_list = self._by_wf.get(old_resp.workflow_id, [])
                    if oldest_req in wf_list:
                        wf_list.remove(oldest_req)
            self._order.append(response.request_id)
            self._by_req[response.request_id] = response
            self._by_wf.setdefault(response.workflow_id, [])
            if response.request_id not in self._by_wf[response.workflow_id]:
                self._by_wf[response.workflow_id].append(response.request_id)

    def deregister(self, request_id: str) -> bool:
        with self._lock:
            resp = self._by_req.pop(request_id, None)
            if resp is None:
                return False
            if request_id in self._order:
                self._order.remove(request_id)
            wf_list = self._by_wf.get(resp.workflow_id, [])
            if request_id in wf_list:
                wf_list.remove(request_id)
        return True

    def get(self, request_id: str) -> Optional[WorkflowGatewayResponse]:
        with self._lock:
            return self._by_req.get(request_id)

    def get_by_workflow(self, workflow_id: str) -> List[WorkflowGatewayResponse]:
        with self._lock:
            ids   = list(self._by_wf.get(workflow_id, []))
            resps = [self._by_req[rid] for rid in ids if rid in self._by_req]
        return resps

    def latest_for_workflow(self, workflow_id: str) -> Optional[WorkflowGatewayResponse]:
        with self._lock:
            ids = list(self._by_wf.get(workflow_id, []))
        if not ids:
            return None
        return self._by_req.get(ids[-1])

    def exists(self, request_id: str) -> bool:
        with self._lock:
            return request_id in self._by_req

    def count(self) -> int:
        with self._lock:
            return len(self._by_req)

    def all_responses(self) -> List[WorkflowGatewayResponse]:
        with self._lock:
            return list(self._by_req.values())

    def clear(self) -> int:
        with self._lock:
            n = len(self._by_req)
            self._by_req.clear()
            self._by_wf.clear()
            self._order.clear()
        return n
