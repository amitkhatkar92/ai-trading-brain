"""iios/execution/execution_engine.py

The mandatory entry point for every execution inside IIOS.
"""
from __future__ import annotations

import asyncio
import logging
import threading
import time
from typing import Any

from iios.execution.core.execution_history    import ExecutionHistory
from iios.execution.core.execution_request    import ExecutionRequest
from iios.execution.core.execution_result     import ExecutionResult
from iios.execution.core.execution_session    import ExecutionSession
from iios.execution.core.execution_statistics import ExecutionStatistics
from iios.execution.events.event_bus          import ExecutionEventBus
from iios.execution.execution_constants       import (
    DEFAULT_MAX_HISTORY,
    DEFAULT_MAX_SESSIONS,
    DEFAULT_WORKER_THREADS,
    EXECUTION_ENGINE_SYSTEM_ID,
    EXECUTION_ENGINE_VERSION,
)
from iios.execution.execution_exceptions      import (
    EngineAlreadyRunningError,
    EngineNotInitializedError,
    EngineShutdownError,
)
from iios.execution.execution_manager         import ExecutionManager
from iios.execution.execution_registry        import ExecutionRegistry
from iios.execution.monitoring.execution_monitor import ExecutionMonitor
from iios.execution.sessions.session_manager     import SessionManager
from iios.execution.workflow.workflow_engine      import WorkflowEngine

logger = logging.getLogger(__name__)


class ExecutionEngine:
    """
    Institutional-grade execution platform.

    Converts approved investment decisions into executed workflow results.
    Does NOT communicate with brokers — that responsibility belongs to
    Broker Adapters (future phase).

    Usage
    -----
    >>> engine = ExecutionEngine()
    >>> engine.initialize()
    >>> result = engine.submit(request)
    >>> engine.shutdown()

    Or use the module-level singleton:
    >>> engine = get_execution_engine()
    >>> engine.initialize()
    """

    def __init__(
        self,
        *,
        max_sessions:   int = DEFAULT_MAX_SESSIONS,
        max_history:    int = DEFAULT_MAX_HISTORY,
        worker_threads: int = DEFAULT_WORKER_THREADS,
    ) -> None:
        self._max_sessions   = max_sessions
        self._max_history    = max_history
        self._worker_threads = worker_threads

        self._initialized: bool       = False
        self._shutdown:    bool       = False
        self._started_at:  float      = 0.0
        self._lock:        threading.RLock = threading.RLock()

        # Internal subsystems (created on initialize()).
        self._event_bus: ExecutionEventBus | None = None
        self._manager:   ExecutionManager  | None = None

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def initialize(self) -> None:
        with self._lock:
            if self._shutdown:
                raise EngineShutdownError(
                    "Cannot re-initialize a shut-down ExecutionEngine"
                )
            if self._initialized:
                raise EngineAlreadyRunningError(
                    "ExecutionEngine is already initialized"
                )

            self._event_bus = ExecutionEventBus()
            self._manager   = ExecutionManager(
                event_bus=self._event_bus,
                worker_threads=self._worker_threads,
                max_history=self._max_history,
            )

            self._initialized = True
            self._started_at  = time.time()

        logger.info(
            "ExecutionEngine v%s initialized — system_id=%s",
            EXECUTION_ENGINE_VERSION,
            EXECUTION_ENGINE_SYSTEM_ID,
        )

    def shutdown(self, wait: bool = True) -> None:
        with self._lock:
            if not self._initialized:
                return
            if self._shutdown:
                return
            self._manager.shutdown(wait=wait)
            self._initialized = False
            self._shutdown    = True

        logger.info("ExecutionEngine shut down.")

    # ── Submit ────────────────────────────────────────────────────────────────

    def submit(self, request: ExecutionRequest) -> ExecutionResult:
        """
        Synchronously run the execution workflow and return the result.
        This is the primary entry point for the Decision Layer.
        """
        self._guard()
        return self._manager.submit(request)

    async def submit_async(self, request: ExecutionRequest) -> ExecutionResult:
        """
        Async entry point.  Runs the workflow in an executor thread so the
        event loop is not blocked.
        """
        self._guard()
        return await self._manager.submit_async(request)

    # ── Lifecycle controls ────────────────────────────────────────────────────

    def cancel(self, execution_id: str, *, reason: str = "cancelled by engine") -> bool:
        self._guard()
        return self._manager.cancel(execution_id, reason=reason)

    def pause(self, execution_id: str) -> bool:
        self._guard()
        return self._manager.pause(execution_id)

    def resume(self, execution_id: str) -> bool:
        self._guard()
        return self._manager.resume(execution_id)

    def replay(self, execution_id: str) -> ExecutionResult:
        self._guard()
        return self._manager.replay(execution_id)

    # ── Query ─────────────────────────────────────────────────────────────────

    def get_session(self, execution_id: str) -> ExecutionSession:
        self._guard()
        return self._manager.get_session(execution_id)

    def get_result(self, execution_id: str) -> ExecutionResult | None:
        self._guard()
        return self._manager.get_result(execution_id)

    def get_history(self, execution_id: str) -> list[ExecutionResult]:
        self._guard()
        return self._manager.get_history(execution_id)

    def list_active(self) -> list[ExecutionSession]:
        self._guard()
        return self._manager.list_active()

    def list_all(self) -> list[ExecutionSession]:
        self._guard()
        return self._manager.list_all()

    # ── Observability ─────────────────────────────────────────────────────────

    def stats(self) -> ExecutionStatistics:
        self._guard()
        return self._manager.statistics()

    def health(self) -> dict[str, Any]:
        if not self._initialized:
            return {"status": "not_initialized", "healthy": False}
        stats  = self._manager.statistics()
        uptime = time.time() - self._started_at
        return {
            "status":           "healthy",
            "healthy":          True,
            "version":          EXECUTION_ENGINE_VERSION,
            "system_id":        EXECUTION_ENGINE_SYSTEM_ID,
            "uptime_sec":       round(uptime, 2),
            "total_executions": stats.total_executions,
            "active_sessions":  stats.active_sessions,
            "success_rate":     round(stats.success_rate, 4),
        }

    def to_dict(self) -> dict[str, Any]:
        base: dict[str, Any] = {
            "version":     EXECUTION_ENGINE_VERSION,
            "system_id":   EXECUTION_ENGINE_SYSTEM_ID,
            "initialized": self._initialized,
            "shutdown":    self._shutdown,
            "started_at":  self._started_at,
        }
        if self._initialized and self._manager:
            base["manager"] = self._manager.to_dict()
        return base

    # ── Internal ──────────────────────────────────────────────────────────────

    def _guard(self) -> None:
        if self._shutdown:
            raise EngineShutdownError("ExecutionEngine has been shut down")
        if not self._initialized:
            raise EngineNotInitializedError(
                "ExecutionEngine must be initialized before use — call initialize() first"
            )

    @property
    def event_bus(self) -> ExecutionEventBus:
        self._guard()
        return self._manager.event_bus

    @property
    def is_initialized(self) -> bool:
        return self._initialized

    @property
    def is_shutdown(self) -> bool:
        return self._shutdown


# ── Module-level singleton ────────────────────────────────────────────────────

_engine:      ExecutionEngine | None = None
_engine_lock: threading.Lock         = threading.Lock()


def get_execution_engine() -> ExecutionEngine:
    """Return the process-level ExecutionEngine singleton."""
    global _engine
    with _engine_lock:
        if _engine is None:
            _engine = ExecutionEngine()
        return _engine


def reset_execution_engine() -> None:
    """Reset the singleton (used in tests — do not call in production)."""
    global _engine
    with _engine_lock:
        if _engine is not None and _engine.is_initialized:
            try:
                _engine.shutdown(wait=False)
            except Exception:
                pass
        _engine = None
