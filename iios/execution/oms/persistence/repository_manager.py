"""iios/execution/oms/persistence/repository_manager.py
==================================================
RepositoryManager — primary facade for the IIOS Order Persistence layer.

Delegates all CRUD operations to the registered StorageContract, emits
domain events, and maintains aggregated statistics.

C6 Execution Intelligence — Phase 2, Module 5
"""
from __future__ import annotations

import threading
import time
from typing import Any

from iios.investment.workflow.engine_lifecycle import EngineState, LifecycleAwareMixin
from iios.common.logging.audit_logger import get_audit_logger
from iios.common.logging.logging_manager import get_logger

from iios.execution.oms.persistence.constants import (
    MANAGER_SYSTEM_ID,
    VERSION,
    OperationType,
)
from iios.execution.oms.persistence.exceptions import (
    RepositoryNotRunning,
)
from iios.execution.oms.persistence.repository_context import RepositoryContext
from iios.execution.oms.persistence.repository_events import (
    PersistenceEvent,
    make_record_archived,
    make_record_restored,
    make_record_saved,
    make_record_updated,
    make_repository_validated,
)
from iios.execution.oms.persistence.repository_factory import RepositoryFactory
from iios.execution.oms.persistence.repository_registry import RepositoryRegistry
from iios.execution.oms.persistence.repository_request import RepositoryRequest
from iios.execution.oms.persistence.repository_response import RepositoryResponse
from iios.execution.oms.persistence.repository_validation import RepositoryValidator
from iios.execution.oms.persistence.storage_contract import StorageContract
from iios.execution.oms.persistence.storage_metadata import (
    HealthStatus,
    StorageStatistics,
)


class RepositoryManager(LifecycleAwareMixin):
    """
    Primary facade for all persistence operations.

    Usage
    -----
    manager = RepositoryManager()
    manager.start()
    manager.register_repository(InMemoryOrderRepository())

    ctx = RepositoryContext(operation=OperationType.SAVE, ...)
    req = factory.make_save_request("ord-1", payload={...})
    resp = manager.save(ctx, req)
    """

    def __init__(
        self,
        registry:  RepositoryRegistry | None  = None,
        factory:   RepositoryFactory  | None  = None,
        validator: RepositoryValidator | None = None,
        max_events: int = 10_000,
    ) -> None:
        super().__init__()
        self._registry  = registry  or RepositoryRegistry()
        self._factory   = factory   or RepositoryFactory()
        self._validator = validator or RepositoryValidator()
        self._max_events = max_events
        self._events:   list[PersistenceEvent] = []
        self._lock      = threading.RLock()
        self._log       = get_logger(__name__, engine_id=MANAGER_SYSTEM_ID)
        self._audit     = get_audit_logger(__name__, engine_id=MANAGER_SYSTEM_ID)

        # Aggregate counters
        self._ops_total   = 0
        self._ops_success = 0
        self._ops_failed  = 0

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def _on_start(self) -> None:
        if self._registry.lifecycle_state() != EngineState.RUNNING:
            self._registry.start()
        self._audit.log_lifecycle_event(
            MANAGER_SYSTEM_ID, EngineState.STOPPED, EngineState.RUNNING, VERSION
        )
        self._log.info("RepositoryManager started.")

    def _on_stop(self) -> None:
        if self._registry.lifecycle_state() == EngineState.RUNNING:
            self._registry.stop()
        self._audit.log_lifecycle_event(
            MANAGER_SYSTEM_ID, EngineState.RUNNING, EngineState.STOPPED, VERSION
        )
        self._log.info(
            "RepositoryManager stopped.",
            ops_total=self._ops_total,
            ops_success=self._ops_success,
        )

    def _assert_running(self) -> None:
        if self.lifecycle_state() != EngineState.RUNNING:
            raise RepositoryNotRunning(
                "RepositoryManager is not running",
                code="PE-005",
            )

    # ------------------------------------------------------------------
    # Repository registration
    # ------------------------------------------------------------------

    def register_repository(self, repo: StorageContract) -> None:
        self._assert_running()
        self._registry.register(repo)

    def unregister_repository(self, repository_id: str) -> bool:
        self._assert_running()
        return self._registry.unregister(repository_id)

    # ------------------------------------------------------------------
    # CRUD — all operations delegate to the resolved repository
    # ------------------------------------------------------------------

    def save(
        self,
        context: RepositoryContext,
        request: RepositoryRequest,
    ) -> RepositoryResponse:
        self._assert_running()
        self._validator.validate_request(request)
        repo = self._resolve(context, request)
        resp = repo.save(request)
        self._record(resp)
        if resp.succeeded:
            self._emit(make_record_saved(
                resp.record_id, resp.repository_id,
                resp.record_version, request.correlation_id,
            ))
        return resp

    def update(
        self,
        context: RepositoryContext,
        request: RepositoryRequest,
    ) -> RepositoryResponse:
        self._assert_running()
        self._validator.validate_request(request)
        repo = self._resolve(context, request)
        resp = repo.update(request)
        self._record(resp)
        if resp.succeeded:
            self._emit(make_record_updated(
                resp.record_id, resp.repository_id,
                resp.record_version, request.correlation_id,
            ))
        return resp

    def delete(
        self,
        context: RepositoryContext,
        request: RepositoryRequest,
    ) -> RepositoryResponse:
        self._assert_running()
        self._validator.validate_request(request)
        repo = self._resolve(context, request)
        resp = repo.delete(request)
        self._record(resp)
        return resp

    def archive(
        self,
        context: RepositoryContext,
        request: RepositoryRequest,
    ) -> RepositoryResponse:
        self._assert_running()
        self._validator.validate_request(request)
        repo = self._resolve(context, request)
        resp = repo.archive(request)
        self._record(resp)
        if resp.succeeded:
            self._emit(make_record_archived(
                resp.record_id, resp.repository_id, resp.record_version
            ))
        return resp

    def restore(
        self,
        context: RepositoryContext,
        request: RepositoryRequest,
    ) -> RepositoryResponse:
        self._assert_running()
        self._validator.validate_request(request)
        repo = self._resolve(context, request)
        resp = repo.restore(request)
        self._record(resp)
        if resp.succeeded:
            self._emit(make_record_restored(
                resp.record_id, resp.repository_id, resp.record_version
            ))
        return resp

    def find(
        self,
        context: RepositoryContext,
        request: RepositoryRequest,
    ) -> RepositoryResponse:
        self._assert_running()
        self._validator.validate_request(request)
        repo = self._resolve(context, request)
        resp = repo.find(request)
        self._record(resp)
        return resp

    def search(
        self,
        context: RepositoryContext,
        request: RepositoryRequest,
    ) -> RepositoryResponse:
        self._assert_running()
        self._validator.validate_request(request)
        repo = self._resolve(context, request)
        resp = repo.search(request)
        self._record(resp)
        return resp

    # ------------------------------------------------------------------
    # Direct convenience methods (no context required)
    # ------------------------------------------------------------------

    def exists(self, repository_id: str, record_id: str) -> bool:
        self._assert_running()
        repo = self._registry.get(repository_id)
        if repo is None:
            return False
        return repo.exists(record_id)

    def health(self, repository_id: str) -> HealthStatus | None:
        """Return health of a specific repository."""
        repo = self._registry.get(repository_id)
        return repo.health() if repo else None

    def statistics(self, repository_id: str) -> StorageStatistics | None:
        """Return statistics for a specific repository."""
        repo = self._registry.get(repository_id)
        return repo.statistics() if repo else None

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate_repository(self, repository_id: str) -> bool:
        """Return True if the named repository satisfies the storage contract."""
        repo = self._registry.get(repository_id)
        if repo is None:
            return False
        violations = self._validator.validate_contract(repo)
        is_valid   = len(violations) == 0
        self._emit(make_repository_validated(repository_id, is_valid))
        return is_valid

    # ------------------------------------------------------------------
    # Observability
    # ------------------------------------------------------------------

    def events(self) -> list[PersistenceEvent]:
        with self._lock:
            return list(self._events)

    def latest_events(self, n: int = 50) -> list[PersistenceEvent]:
        with self._lock:
            return list(self._events[-n:])

    def summary(self) -> dict[str, Any]:
        return {
            "ops_total":    self._ops_total,
            "ops_success":  self._ops_success,
            "ops_failed":   self._ops_failed,
            "event_count":  len(self._events),
            "repositories": self._registry.count,
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _resolve(
        self,
        context: RepositoryContext,
        request: RepositoryRequest,
    ) -> StorageContract:
        """Find the target repository or fall back to the default."""
        repo_id = request.repository_id or context.repository_id or ""
        if repo_id:
            repo = self._registry.get(repo_id)
        else:
            repo = self._registry.default()
        if repo is None:
            from iios.execution.oms.persistence.exceptions import RecordNotFoundError
            raise RecordNotFoundError(
                repo_id or "<default>",
                code="PE-009",
                context={"reason": "no registered repository found"},
            )
        return repo

    def _record(self, resp: RepositoryResponse) -> None:
        with self._lock:
            self._ops_total += 1
            if resp.succeeded:
                self._ops_success += 1
            else:
                self._ops_failed  += 1

    def _emit(self, event: PersistenceEvent) -> None:
        with self._lock:
            if len(self._events) >= self._max_events:
                self._events.pop(0)
            self._events.append(event)
