"""
integration_policy_history.py — iios.integration.policies
----------------------------------------------------------
Bounded history of governance evaluation requests and responses.

C15 Enterprise Integration & Connectivity — Phase 1, Module 3
"""
from __future__ import annotations

import threading
from collections import deque
from typing import Deque, Dict, List, Optional

from .constants import DEFAULT_MAX_HISTORY
from .integration_policy_request import IntegrationPolicyRequest
from .integration_policy_response import IntegrationPolicyResponse


class IntegrationPolicyHistory:
    """
    Thread-safe bounded history of policy requests and responses.
    Older entries are evicted when the capacity is reached (ring buffer).
    """

    def __init__(self, max_history: int = DEFAULT_MAX_HISTORY) -> None:
        self._max        = max_history
        self._requests:  Deque[IntegrationPolicyRequest]  = deque(maxlen=max_history)
        self._responses: Deque[IntegrationPolicyResponse] = deque(maxlen=max_history)
        self._req_idx:   Dict[str, IntegrationPolicyRequest]  = {}
        self._rsp_idx:   Dict[str, IntegrationPolicyResponse] = {}
        self._lock       = threading.Lock()

    # ── record ────────────────────────────────────────────────────────

    def record_request(self, request: IntegrationPolicyRequest) -> None:
        with self._lock:
            if len(self._requests) == self._max and self._requests:
                evicted = self._requests[0]
                self._req_idx.pop(evicted.request_id, None)
            self._requests.append(request)
            self._req_idx[request.request_id] = request

    def record_response(self, response: IntegrationPolicyResponse) -> None:
        with self._lock:
            if len(self._responses) == self._max and self._responses:
                evicted = self._responses[0]
                self._rsp_idx.pop(evicted.response_id, None)
            self._responses.append(response)
            self._rsp_idx[response.response_id] = response

    # ── lookup ────────────────────────────────────────────────────────

    def get_request(self, request_id: str) -> Optional[IntegrationPolicyRequest]:
        with self._lock:
            return self._req_idx.get(request_id)

    def get_response(self, response_id: str) -> Optional[IntegrationPolicyResponse]:
        with self._lock:
            return self._rsp_idx.get(response_id)

    def response_for_request(self, request_id: str) -> Optional[IntegrationPolicyResponse]:
        with self._lock:
            for resp in self._responses:
                if resp.request_id == request_id:
                    return resp
        return None

    # ── bulk ──────────────────────────────────────────────────────────

    def recent_requests(self, n: int = 20) -> List[IntegrationPolicyRequest]:
        with self._lock:
            items = list(self._requests)
        return items[-n:]

    def recent_responses(self, n: int = 20) -> List[IntegrationPolicyResponse]:
        with self._lock:
            items = list(self._responses)
        return items[-n:]

    # ── metrics ───────────────────────────────────────────────────────

    def request_count(self)  -> int:
        with self._lock: return len(self._requests)

    def response_count(self) -> int:
        with self._lock: return len(self._responses)

    def count(self) -> int:
        return self.request_count() + self.response_count()

    # ── management ────────────────────────────────────────────────────

    def clear(self) -> None:
        with self._lock:
            self._requests.clear()
            self._responses.clear()
            self._req_idx.clear()
            self._rsp_idx.clear()
