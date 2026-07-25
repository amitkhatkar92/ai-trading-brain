"""
workflow_manager.py — iios.workflow.engine
-------------------------------------------
WorkflowManager — top-level public API for workflow operations.

C16 Enterprise Workflow & Process Orchestration — Phase 1, Module 2
"""
from __future__ import annotations

import threading
from typing import Any, Dict, List, Optional

from iios.common.logging.logging_manager import get_logger

from .constants import DEFAULT_ENGINE_ID, WorkflowEngineState
from .exceptions import WorkflowEngineNotReadyError
from .workflow_engine import WorkflowEngine
from .workflow_events import WorkflowEngineEventBus
from .workflow_health import WorkflowEngineHealthReport
from .workflow_history import WorkflowEngineHistory
from .workflow_request import WorkflowEngineRequest
from .workflow_response import WorkflowEngineResponse
from .workflow_statistics import WorkflowEngineStatisticsReport
from .workflow_status import WorkflowEngineStatus
from .workflow_validation import WorkflowEngineValidationReport

_log = get_logger(__name__)


class WorkflowManager:
    """
    Top-level public API for the Workflow Engine.

    Thread-safe.  Wraps a WorkflowEngine and exposes lifecycle and
    operational methods.  Must call start() before execute().

    Usage::

        manager = WorkflowManager()
        manager.start()
        response = manager.execute(request)
        manager.stop()
    """

    def __init__(
        self,
        engine_id: str                         = DEFAULT_ENGINE_ID,
        engine:    Optional[WorkflowEngine]    = None,
    ) -> None:
        self._engine_id = engine_id
        self._engine    = engine or WorkflowEngine(engine_id=engine_id)
        self._started   = False
        self._lock      = threading.Lock()

    # ----------------------------------------------------------------
    # Manager lifecycle
    # ----------------------------------------------------------------

    def start(self) -> None:
        """Initialize and start the engine.  Idempotent."""
        with self._lock:
            if self._started:
                return
            if self._engine.state == WorkflowEngineState.STOPPED:
                self._engine = WorkflowEngine(engine_id=self._engine_id)
            self._engine.initialize()
            self._started = True
        _log.info(f"WorkflowManager started: engine={self._engine_id!r}")

    def stop(self) -> None:
        """Stop the engine.  Idempotent."""
        with self._lock:
            if not self._started:
                return
            self._engine.stop()
            self._started = False
        _log.info(f"WorkflowManager stopped: engine={self._engine_id!r}")

    def is_started(self) -> bool:
        with self._lock:
            return self._started

    # ----------------------------------------------------------------
    # Workflow operations
    # ----------------------------------------------------------------

    def execute(self, request: WorkflowEngineRequest) -> WorkflowEngineResponse:
        """
        Execute a single workflow request.

        Raises:
            WorkflowEngineNotReadyError if start() has not been called.
        """
        with self._lock:
            started = self._started
        if not started:
            raise WorkflowEngineNotReadyError(
                "WorkflowManager has not been started — call start() first"
            )
        return self._engine.execute(request)

    def execute_batch(
        self,
        requests: List[WorkflowEngineRequest],
    ) -> List[WorkflowEngineResponse]:
        """Execute a list of requests independently, in order."""
        return [self.execute(req) for req in requests]

    def validate(
        self,
        request: WorkflowEngineRequest,
    ) -> WorkflowEngineValidationReport:
        """Validate a request (does not require start())."""
        return self._engine.validate(request)

    def cancel(self, request_id: str, *, reason: str = "cancelled by manager") -> bool:
        """Cancel an active workflow by request_id."""
        return self._engine.cancel(request_id, reason=reason)

    # ----------------------------------------------------------------
    # Observability
    # ----------------------------------------------------------------

    def health(self) -> WorkflowEngineHealthReport:
        return self._engine.health()

    def status(self) -> WorkflowEngineStatus:
        return self._engine.status()

    def statistics(self) -> WorkflowEngineStatisticsReport:
        return self._engine.statistics()

    def history(self) -> WorkflowEngineHistory:
        return self._engine.history()

    def event_bus(self) -> WorkflowEngineEventBus:
        return self._engine.event_bus()

    @property
    def engine_id(self) -> str:
        return self._engine_id
