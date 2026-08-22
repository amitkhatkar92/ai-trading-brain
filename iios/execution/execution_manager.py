"""iios/execution/execution_manager.py"""
from __future__ import annotations

import asyncio
import concurrent.futures
import logging
import threading
from typing import Any

from iios.execution.core.execution_history    import ExecutionHistory
from iios.execution.core.execution_request    import ExecutionRequest
from iios.execution.core.execution_result     import ExecutionResult
from iios.execution.core.execution_session    import ExecutionSession
from iios.execution.core.execution_statistics import ExecutionStatistics
from iios.execution.events.event_bus          import ExecutionEventBus
from iios.execution.execution_constants       import (
    DEFAULT_MAX_HISTORY,
    DEFAULT_WORKER_THREADS,
    ExecutionStatus,
)
from iios.execution.execution_exceptions      import ExecutionNotFoundError
from iios.execution.execution_registry        import ExecutionRegistry
from iios.execution.monitoring.execution_monitor import ExecutionMonitor
from iios.execution.services.execution_service   import ExecutionService
from iios.execution.sessions.session_manager     import SessionManager
from iios.execution.workflow.workflow_engine      import WorkflowEngine

logger = logging.getLogger(__name__)


class ExecutionManager:
    """
    Central coordinator for all execution operations.

    Wires together SessionManager, WorkflowEngine, ExecutionRegistry,
    ExecutionHistory, ExecutionMonitor, and EventBus.

    All public methods are thread-safe.
    """

    def __init__(
        self,
        session_manager:    SessionManager      | None = None,
        workflow_engine:    WorkflowEngine      | None = None,
        registry:           ExecutionRegistry   | None = None,
        history:            ExecutionHistory    | None = None,
        monitor:            ExecutionMonitor    | None = None,
        event_bus:          ExecutionEventBus   | None = None,
        worker_threads:     int                        = DEFAULT_WORKER_THREADS,
        max_history:        int                        = DEFAULT_MAX_HISTORY,
    ) -> None:
        self._event_bus  = event_bus  or ExecutionEventBus()
        self._sessions   = session_manager or SessionManager()
        self._workflow   = workflow_engine or WorkflowEngine(event_bus=self._event_bus)
        self._registry   = registry  or ExecutionRegistry()
        self._history    = history   or ExecutionHistory(max_size=max_history)
        self._monitor    = monitor   or ExecutionMonitor()
        self._service    = ExecutionService(
            session_manager=self._sessions,
            workflow_engine=self._workflow,
        )
        self._stats      = ExecutionStatistics()
        self._executor   = concurrent.futures.ThreadPoolExecutor(
            max_workers=worker_threads,
            thread_name_prefix="iios-execution",
        )
        self._lock       = threading.RLock()

    # ── Submit ────────────────────────────────────────────────────────────────

    def submit(self, request: ExecutionRequest) -> ExecutionResult:
        """
        Synchronously execute the full workflow and return the result.
        """
        session = self._service.create(request)
        self._registry.register(session)
        self._monitor.on_execution_started(session.execution_id)

        logger.info(
            "ExecutionManager.submit: %s ticker=%s qty=%s",
            session.execution_id,
            request.ticker,
            request.quantity,
        )

        result = self._workflow.run(session)

        self._registry.update(session)
        self._registry.store_result(result)
        self._history.add(session.execution_id, result)

        with self._lock:
            if result.is_successful:
                self._monitor.on_execution_completed(session.execution_id, result)
                self._stats.record_completion(
                    success=True,
                    duration_ms=result.execution_time_ms,
                    fill_ratio=result.fill_ratio,
                    volume=result.quantity_executed,
                )
            elif result.status == ExecutionStatus.CANCELLED:
                self._monitor.on_execution_failed(session.execution_id, "cancelled")
                self._stats.record_cancellation()
            else:
                self._monitor.on_execution_failed(session.execution_id, result.error_message)
                self._stats.record_completion(
                    success=False,
                    duration_ms=result.execution_time_ms,
                )

        return result

    def submit_background(
        self, request: ExecutionRequest
    ) -> concurrent.futures.Future[ExecutionResult]:
        """Submit asynchronously via the internal thread pool."""
        return self._executor.submit(self.submit, request)

    async def submit_async(self, request: ExecutionRequest) -> ExecutionResult:
        """Async wrapper — runs submit() in the event loop's default executor."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, lambda: self.submit(request))

    # ── Cancel / pause / resume ───────────────────────────────────────────────

    def cancel(self, execution_id: str, *, reason: str = "cancelled") -> bool:
        try:
            ok = self._service.cancel(execution_id, reason=reason)
            if ok:
                session = self._sessions.get_session(execution_id)
                self._registry.update(session)
            return ok
        except ExecutionNotFoundError:
            logger.warning("ExecutionManager.cancel: unknown id %s", execution_id)
            return False

    def pause(self, execution_id: str) -> bool:
        try:
            ok = self._service.pause(execution_id)
            if ok:
                self._registry.update(self._sessions.get_session(execution_id))
            return ok
        except ExecutionNotFoundError:
            return False

    def resume(self, execution_id: str) -> bool:
        try:
            ok = self._service.resume(execution_id)
            if ok:
                self._registry.update(self._sessions.get_session(execution_id))
            return ok
        except ExecutionNotFoundError:
            return False

    # ── Replay ────────────────────────────────────────────────────────────────

    def replay(self, execution_id: str) -> ExecutionResult:
        result  = self._service.replay(execution_id)
        # The replay creates a new session — register it.
        new_session = self._sessions.get_session(result.execution_id)
        if not self._registry.session_exists(result.execution_id):
            self._registry.register(new_session)
        self._registry.store_result(result)
        self._history.add(result.execution_id, result)
        return result

    # ── Query ─────────────────────────────────────────────────────────────────

    def get_session(self, execution_id: str) -> ExecutionSession:
        return self._registry.get_session(execution_id)

    def get_result(self, execution_id: str) -> ExecutionResult | None:
        return self._registry.get_result(execution_id)

    def get_history(self, execution_id: str) -> list[ExecutionResult]:
        return self._history.get_all(execution_id)

    def list_active(self) -> list[ExecutionSession]:
        return self._registry.list_active()

    def list_all(self) -> list[ExecutionSession]:
        return self._registry.list_all()

    # ── Stats ─────────────────────────────────────────────────────────────────

    def statistics(self) -> ExecutionStatistics:
        with self._lock:
            self._stats.active_sessions = self._registry.active_count()
            self._stats.refresh_uptime()
        return self._stats

    # ── Infrastructure access (for engine) ────────────────────────────────────

    @property
    def event_bus(self) -> ExecutionEventBus:
        return self._event_bus

    @property
    def monitor(self) -> ExecutionMonitor:
        return self._monitor

    # ── Shutdown ──────────────────────────────────────────────────────────────

    def shutdown(self, wait: bool = True) -> None:
        logger.info("ExecutionManager: shutting down thread pool …")
        self._executor.shutdown(wait=wait)

    def to_dict(self) -> dict[str, Any]:
        return {
            "registry":   self._registry.to_dict(),
            "history":    self._history.to_dict(),
            "monitor":    self._monitor.summary(),
            "statistics": self._stats.to_dict(),
        }
