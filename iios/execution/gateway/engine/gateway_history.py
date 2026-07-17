"""iios/execution/gateway/engine/gateway_history.py
==================================================
GatewayEngineHistory — bounded, thread-safe history store for
operations and responses in the Execution Gateway Engine.

C6 Execution Intelligence — Phase 5, Module 2
"""
from __future__ import annotations

import threading
from collections import deque
from typing import Any, Callable, Dict, List, Optional

from .constants import DEFAULT_MAX_HISTORY
from .gateway_operation import GatewayOperation
from .gateway_response import GatewayResponse


class GatewayEngineHistory:
    """
    Bounded, thread-safe history store for GatewayOperation and GatewayResponse
    objects.

    When the history reaches ``max_size``, the oldest entry of the relevant
    type is evicted.
    """

    def __init__(self, max_size: int = DEFAULT_MAX_HISTORY) -> None:
        self._max_size    = max(1, max_size)
        self._operations: deque[GatewayOperation] = deque()
        self._responses:  deque[GatewayResponse]  = deque()
        self._evicted_ops  = 0
        self._evicted_resp = 0
        self._lock         = threading.Lock()

    # ── Append ────────────────────────────────────────────────────────────────

    def append_operation(self, operation: GatewayOperation) -> None:
        with self._lock:
            if len(self._operations) >= self._max_size:
                self._operations.popleft()
                self._evicted_ops += 1
            self._operations.append(operation)

    def append_response(self, response: GatewayResponse) -> None:
        with self._lock:
            if len(self._responses) >= self._max_size:
                self._responses.popleft()
                self._evicted_resp += 1
            self._responses.append(response)

    # ── Query — operations ────────────────────────────────────────────────────

    def operations(self) -> List[GatewayOperation]:
        with self._lock:
            return list(self._operations)

    def latest_operation(self) -> Optional[GatewayOperation]:
        with self._lock:
            return self._operations[-1] if self._operations else None

    def operations_for_request(self, request_id: str) -> List[GatewayOperation]:
        with self._lock:
            return [op for op in self._operations if op.request_id == request_id]

    def operations_by_type(
        self,
        predicate: Callable[[GatewayOperation], bool],
    ) -> List[GatewayOperation]:
        with self._lock:
            return [op for op in self._operations if predicate(op)]

    # ── Query — responses ─────────────────────────────────────────────────────

    def responses(self) -> List[GatewayResponse]:
        with self._lock:
            return list(self._responses)

    def latest_response(self) -> Optional[GatewayResponse]:
        with self._lock:
            return self._responses[-1] if self._responses else None

    def responses_for_request(self, request_id: str) -> List[GatewayResponse]:
        with self._lock:
            return [r for r in self._responses if r.request_id == request_id]

    def successful_responses(self) -> List[GatewayResponse]:
        with self._lock:
            return [r for r in self._responses if r.is_completed]

    def failed_responses(self) -> List[GatewayResponse]:
        with self._lock:
            return [r for r in self._responses if r.is_failed]

    # ── Counts ────────────────────────────────────────────────────────────────

    @property
    def operation_count(self) -> int:
        with self._lock:
            return len(self._operations)

    @property
    def response_count(self) -> int:
        with self._lock:
            return len(self._responses)

    @property
    def evicted_operations(self) -> int:
        return self._evicted_ops

    @property
    def evicted_responses(self) -> int:
        return self._evicted_resp

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "operation_count":   len(self._operations),
                "response_count":    len(self._responses),
                "evicted_operations": self._evicted_ops,
                "evicted_responses":  self._evicted_resp,
                "max_size":          self._max_size,
            }
