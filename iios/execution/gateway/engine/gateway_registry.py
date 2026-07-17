"""iios/execution/gateway/engine/gateway_registry.py
==================================================
GatewayEngineRegistry — thread-safe registry of EngineGatewayRequest
objects, compliant with LifecycleAwareMixin.

C6 Execution Intelligence — Phase 5, Module 2
"""
from __future__ import annotations

import threading
from typing import Any, Dict, List, Optional

from iios.investment.workflow.engine_lifecycle import EngineState, LifecycleAwareMixin
from iios.common.logging.audit_logger import get_audit_logger
from iios.common.logging.logging_manager import get_logger

from .constants import (
    ACTIVE_REQUEST_STATUSES,
    DEFAULT_MAX_REQUESTS,
    REGISTRY_SYSTEM_ID,
    VERSION,
    RequestStatus,
)
from .exceptions import (
    DuplicateEngineRequestError,
    GatewayEngineNotRunningError,
    GatewayEngineRequestNotFoundError,
    GatewayRegistryCapacityError,
)
from .gateway_request import EngineGatewayRequest

_log   = get_logger(__name__, engine_id=REGISTRY_SYSTEM_ID)
_audit = get_audit_logger(__name__, engine_id=REGISTRY_SYSTEM_ID)


class GatewayEngineRegistry(LifecycleAwareMixin):
    """
    Thread-safe registry of EngineGatewayRequest objects.

    Write operations (register, unregister) require the registry to be
    running.  Read operations (get, filters) are permitted at any time.
    """

    def __init__(self, max_requests: int = DEFAULT_MAX_REQUESTS) -> None:
        super().__init__()
        self._max_requests = max(1, max_requests)
        self._store:       Dict[str, EngineGatewayRequest] = {}
        self._lock         = threading.Lock()

    # ── LifecycleAwareMixin ───────────────────────────────────────────────────

    def _assert_running(self) -> None:
        if self.lifecycle_state() != EngineState.RUNNING:
            raise GatewayEngineNotRunningError()

    def _on_start(self) -> None:
        _audit.log_lifecycle_event(
            REGISTRY_SYSTEM_ID, EngineState.STOPPED, EngineState.RUNNING, VERSION
        )
        _log.info("GatewayEngineRegistry started.", version=VERSION)

    def _on_stop(self) -> None:
        _audit.log_lifecycle_event(
            REGISTRY_SYSTEM_ID, EngineState.RUNNING, EngineState.STOPPED, VERSION
        )
        _log.info(
            "GatewayEngineRegistry stopped.",
            registered_count=len(self._store),
        )

    # ── Write operations ──────────────────────────────────────────────────────

    def register(self, request: EngineGatewayRequest) -> None:
        self._assert_running()
        with self._lock:
            if len(self._store) >= self._max_requests:
                raise GatewayRegistryCapacityError(self._max_requests)
            if request.request_id in self._store:
                raise DuplicateEngineRequestError(request.request_id)
            self._store[request.request_id] = request
        _log.debug("Request registered.", request_id=request.request_id)

    def unregister(self, request_id: str) -> None:
        self._assert_running()
        with self._lock:
            if request_id not in self._store:
                raise GatewayEngineRequestNotFoundError(request_id)
            del self._store[request_id]
        _log.debug("Request unregistered.", request_id=request_id)

    # ── Read operations ───────────────────────────────────────────────────────

    def get(self, request_id: str) -> EngineGatewayRequest:
        with self._lock:
            request = self._store.get(request_id)
        if request is None:
            raise GatewayEngineRequestNotFoundError(request_id)
        return request

    def get_optional(self, request_id: str) -> Optional[EngineGatewayRequest]:
        with self._lock:
            return self._store.get(request_id)

    def exists(self, request_id: str) -> bool:
        with self._lock:
            return request_id in self._store

    def all(self) -> List[EngineGatewayRequest]:
        with self._lock:
            return list(self._store.values())

    # ── Filtered queries ──────────────────────────────────────────────────────

    def active(self) -> List[EngineGatewayRequest]:
        with self._lock:
            return [r for r in self._store.values() if r.status in ACTIVE_REQUEST_STATUSES]

    def completed(self) -> List[EngineGatewayRequest]:
        with self._lock:
            return [r for r in self._store.values() if r.status == RequestStatus.COMPLETED]

    def failed(self) -> List[EngineGatewayRequest]:
        with self._lock:
            return [r for r in self._store.values() if r.status == RequestStatus.FAILED]

    def cancelled(self) -> List[EngineGatewayRequest]:
        with self._lock:
            return [r for r in self._store.values() if r.status == RequestStatus.CANCELLED]

    def by_status(self, status: RequestStatus) -> List[EngineGatewayRequest]:
        with self._lock:
            return [r for r in self._store.values() if r.status == status]

    def by_portfolio_id(self, portfolio_id: str) -> List[EngineGatewayRequest]:
        with self._lock:
            return [r for r in self._store.values() if r.portfolio_id == portfolio_id]

    def by_strategy_id(self, strategy_id: str) -> List[EngineGatewayRequest]:
        with self._lock:
            return [r for r in self._store.values() if r.strategy_id == strategy_id]

    def by_execution_id(self, execution_id: str) -> List[EngineGatewayRequest]:
        with self._lock:
            return [r for r in self._store.values() if r.execution_id == execution_id]

    # ── Counts ────────────────────────────────────────────────────────────────

    @property
    def count(self) -> int:
        with self._lock:
            return len(self._store)

    @property
    def active_count(self) -> int:
        with self._lock:
            return sum(1 for r in self._store.values() if r.status in ACTIVE_REQUEST_STATUSES)

    @property
    def capacity(self) -> int:
        return self._max_requests

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "count":        len(self._store),
                "active_count": sum(
                    1 for r in self._store.values()
                    if r.status in ACTIVE_REQUEST_STATUSES
                ),
                "capacity":     self._max_requests,
            }
