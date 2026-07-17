"""iios/execution/gateway/integration/gateway_integration_history.py
==================================================
GatewayIntegrationHistory — thread-safe bounded log of
integration requests, responses, and events.

C6 Execution Intelligence — Phase 5, Module 6
"""
from __future__ import annotations

import threading
from collections import deque
from typing import Callable, List, Optional

from .constants import (
    DEFAULT_MAX_HISTORY,
    IntegrationRequestStatus,
)
from .gateway_integration_events import IntegrationEvent
from .gateway_integration_request import GatewayIntegrationRequest
from .gateway_integration_response import GatewayIntegrationResponse


class GatewayIntegrationHistory:
    """
    Thread-safe bounded deque storing integration requests,
    responses, and domain events.

    When the maximum capacity is reached, the oldest entry is
    dropped (FIFO eviction) to make room for the newest.
    """

    def __init__(
        self,
        max_requests:  int = DEFAULT_MAX_HISTORY,
        max_responses: int = DEFAULT_MAX_HISTORY,
        max_events:    int = DEFAULT_MAX_HISTORY,
    ) -> None:
        self._max_requests  = max(1, max_requests)
        self._max_responses = max(1, max_responses)
        self._max_events    = max(1, max_events)

        self._requests:  deque = deque(maxlen=self._max_requests)
        self._responses: deque = deque(maxlen=self._max_responses)
        self._events:    deque = deque(maxlen=self._max_events)

        self._lock = threading.Lock()

    # ── Writers ───────────────────────────────────────────────────────────────

    def append_request(self, request: GatewayIntegrationRequest) -> None:
        with self._lock:
            self._requests.append(request)

    def append_response(self, response: GatewayIntegrationResponse) -> None:
        with self._lock:
            self._responses.append(response)

    def append_event(self, event: IntegrationEvent) -> None:
        with self._lock:
            self._events.append(event)

    def clear(self) -> None:
        with self._lock:
            self._requests.clear()
            self._responses.clear()
            self._events.clear()

    # ── Request queries ───────────────────────────────────────────────────────

    def requests(self) -> List[GatewayIntegrationRequest]:
        with self._lock:
            return list(self._requests)

    def latest_request(self) -> Optional[GatewayIntegrationRequest]:
        with self._lock:
            return self._requests[-1] if self._requests else None

    def by_execution_id(
        self, execution_id: str
    ) -> List[GatewayIntegrationRequest]:
        with self._lock:
            return [r for r in self._requests if r.execution_id == execution_id]

    def by_portfolio_id(
        self, portfolio_id: str
    ) -> List[GatewayIntegrationRequest]:
        with self._lock:
            return [r for r in self._requests if r.portfolio_id == portfolio_id]

    def by_strategy_id(
        self, strategy_id: str
    ) -> List[GatewayIntegrationRequest]:
        with self._lock:
            return [r for r in self._requests if r.strategy_id == strategy_id]

    # ── Response queries ──────────────────────────────────────────────────────

    def responses(self) -> List[GatewayIntegrationResponse]:
        with self._lock:
            return list(self._responses)

    def latest_response(self) -> Optional[GatewayIntegrationResponse]:
        with self._lock:
            return self._responses[-1] if self._responses else None

    def completed_responses(self) -> List[GatewayIntegrationResponse]:
        with self._lock:
            return [
                r for r in self._responses
                if r.status == IntegrationRequestStatus.COMPLETED
            ]

    def failed_responses(self) -> List[GatewayIntegrationResponse]:
        with self._lock:
            return [
                r for r in self._responses
                if r.status == IntegrationRequestStatus.FAILED
            ]

    def responses_for_execution(
        self, execution_id: str
    ) -> List[GatewayIntegrationResponse]:
        with self._lock:
            return [r for r in self._responses if r.execution_id == execution_id]

    # ── Event queries ─────────────────────────────────────────────────────────

    def events(self) -> List[IntegrationEvent]:
        with self._lock:
            return list(self._events)

    def latest_event(self) -> Optional[IntegrationEvent]:
        with self._lock:
            return self._events[-1] if self._events else None

    def events_matching(
        self, predicate: Callable[[IntegrationEvent], bool]
    ) -> List[IntegrationEvent]:
        with self._lock:
            return [e for e in self._events if predicate(e)]

    # ── State ─────────────────────────────────────────────────────────────────

    @property
    def request_count(self) -> int:
        with self._lock:
            return len(self._requests)

    @property
    def response_count(self) -> int:
        with self._lock:
            return len(self._responses)

    @property
    def event_count(self) -> int:
        with self._lock:
            return len(self._events)
