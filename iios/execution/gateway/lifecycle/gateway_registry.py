"""iios/execution/gateway/lifecycle/gateway_registry.py
==================================================
GatewayRegistry — LifecycleAwareMixin registry of GatewayRequest objects.

Thread-safe storage and retrieval with filtering helpers.

C6 Execution Intelligence — Phase 5, Module 1
"""
from __future__ import annotations

import threading
from typing import Callable, List, Optional

from iios.investment.workflow.engine_lifecycle import EngineState, LifecycleAwareMixin
from iios.common.logging.audit_logger import get_audit_logger
from iios.common.logging.logging_manager import get_logger

from .constants import (
    ACTIVE_STATES,
    DEFAULT_MAX_REQUESTS,
    ENDED_STATES,
    FAILURE_STATES,
    REGISTRY_SYSTEM_ID,
    SUCCESS_STATES,
    TERMINAL_STATES,
    VERSION,
    GatewayState,
)
from .exceptions import (
    DuplicateGatewayRequestError,
    GatewayLifecycleNotRunningError,
    GatewayRegistryCapacityError,
    GatewayRequestNotFoundError,
)
from .gateway_request import GatewayRequest

_log   = get_logger(__name__, engine_id=REGISTRY_SYSTEM_ID)
_audit = get_audit_logger(__name__, engine_id=REGISTRY_SYSTEM_ID)


class GatewayRegistry(LifecycleAwareMixin):
    """
    Thread-safe registry for ``GatewayRequest`` objects.

    The registry must be started before any write operations.
    Read operations are permitted regardless of lifecycle state
    to allow inspection after shutdown.

    Requests are keyed by ``gateway_id``.
    """

    def __init__(self, max_requests: int = DEFAULT_MAX_REQUESTS) -> None:
        super().__init__()
        self._max    = max(1, max_requests)
        self._store: dict[str, GatewayRequest] = {}
        self._lock   = threading.Lock()

    # ── LifecycleAwareMixin ───────────────────────────────────────────────────

    def _assert_running(self) -> None:
        if self.lifecycle_state() != EngineState.RUNNING:
            raise GatewayLifecycleNotRunningError()

    def _on_start(self) -> None:
        _audit.log_lifecycle_event(
            REGISTRY_SYSTEM_ID, EngineState.STOPPED, EngineState.RUNNING, VERSION
        )
        _log.info("GatewayRegistry started.", max_requests=self._max)

    def _on_stop(self) -> None:
        _audit.log_lifecycle_event(
            REGISTRY_SYSTEM_ID, EngineState.RUNNING, EngineState.STOPPED, VERSION
        )
        _log.info("GatewayRegistry stopped.", request_count=len(self._store))

    # ── Write ─────────────────────────────────────────────────────────────────

    def register(self, request: GatewayRequest) -> None:
        """
        Register *request* in the registry.

        Raises
        ------
        GatewayLifecycleNotRunningError
            If the registry has not been started.
        GatewayRegistryCapacityError
            If the registry is at maximum capacity.
        DuplicateGatewayRequestError
            If a request with the same ``gateway_id`` already exists.
        """
        self._assert_running()
        with self._lock:
            if len(self._store) >= self._max:
                raise GatewayRegistryCapacityError(self._max)
            if request.gateway_id in self._store:
                raise DuplicateGatewayRequestError(request.gateway_id)
            self._store[request.gateway_id] = request

        _log.debug(
            "GatewayRequest registered.",
            gateway_id=request.gateway_id,
            state=request.state.value,
        )

    def unregister(self, gateway_id: str) -> None:
        """
        Remove a request from the registry.

        Raises
        ------
        GatewayRequestNotFoundError
            If the gateway_id does not exist.
        """
        self._assert_running()
        with self._lock:
            if gateway_id not in self._store:
                raise GatewayRequestNotFoundError(gateway_id)
            del self._store[gateway_id]

        _log.debug("GatewayRequest unregistered.", gateway_id=gateway_id)

    # ── Read ──────────────────────────────────────────────────────────────────

    def get(self, gateway_id: str) -> GatewayRequest:
        """
        Retrieve a request by ID.

        Raises
        ------
        GatewayRequestNotFoundError
            If no request with the given ID exists.
        """
        with self._lock:
            request = self._store.get(gateway_id)
        if request is None:
            raise GatewayRequestNotFoundError(gateway_id)
        return request

    def get_optional(self, gateway_id: str) -> Optional[GatewayRequest]:
        """Return the request for *gateway_id*, or None if not found."""
        with self._lock:
            return self._store.get(gateway_id)

    def exists(self, gateway_id: str) -> bool:
        """True if a request with *gateway_id* is registered."""
        with self._lock:
            return gateway_id in self._store

    def all(self) -> List[GatewayRequest]:
        """All registered requests, in insertion order."""
        with self._lock:
            return list(self._store.values())

    # ── Filtered queries ──────────────────────────────────────────────────────

    def _filter(self, predicate: Callable[[GatewayRequest], bool]) -> List[GatewayRequest]:
        with self._lock:
            return [r for r in self._store.values() if predicate(r)]

    def active(self) -> List[GatewayRequest]:
        """Requests in an active (non-ended) state."""
        return self._filter(lambda r: r.state in ACTIVE_STATES)

    def completed(self) -> List[GatewayRequest]:
        """Requests in COMPLETED state."""
        return self._filter(lambda r: r.state in SUCCESS_STATES)

    def failed(self) -> List[GatewayRequest]:
        """Requests in FAILED state."""
        return self._filter(lambda r: r.state == GatewayState.FAILED)

    def cancelled(self) -> List[GatewayRequest]:
        """Requests in CANCELLED state."""
        return self._filter(lambda r: r.state == GatewayState.CANCELLED)

    def archived(self) -> List[GatewayRequest]:
        """Requests in ARCHIVED (terminal) state."""
        return self._filter(lambda r: r.state in TERMINAL_STATES)

    def ended(self) -> List[GatewayRequest]:
        """Requests that have reached an outcome (COMPLETED / FAILED / CANCELLED / ARCHIVED)."""
        return self._filter(lambda r: r.state in ENDED_STATES)

    def by_execution_id(self, execution_id: str) -> List[GatewayRequest]:
        """All requests for *execution_id*."""
        return self._filter(lambda r: r.execution_id == execution_id)

    def by_portfolio_id(self, portfolio_id: str) -> List[GatewayRequest]:
        """All requests for *portfolio_id*."""
        return self._filter(lambda r: r.portfolio_id == portfolio_id)

    def by_strategy_id(self, strategy_id: str) -> List[GatewayRequest]:
        """All requests for *strategy_id*."""
        return self._filter(lambda r: r.strategy_id == strategy_id)

    def by_state(self, state: GatewayState) -> List[GatewayRequest]:
        """All requests in *state*."""
        return self._filter(lambda r: r.state == state)

    # ── Counters ──────────────────────────────────────────────────────────────

    @property
    def count(self) -> int:
        with self._lock:
            return len(self._store)

    @property
    def active_count(self) -> int:
        return len(self.active())

    @property
    def capacity(self) -> int:
        return self._max
