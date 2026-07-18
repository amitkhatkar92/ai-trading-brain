"""
iios/execution/recovery/engine/execution_recovery_engine.py
===========================================================
ExecutionRecoveryEngine — PRIMARY ENTRY POINT for the Execution Recovery
& Resilience subsystem.

Coordinates all recovery activities across the execution subsystem.
Delegates:
  - Recovery decision logic → RecoveryPolicyFramework (M3) via port
  - Failover execution      → FailoverFramework (M4) via port

DOES NOT:
  - Determine recovery policies.
  - Implement failover strategies.
  - Execute trades.
  - Communicate with brokers.

C7 Execution Recovery & Resilience — Phase 1, Module 2
"""
from __future__ import annotations

import threading
from typing import Any, Callable, Dict, List, Optional

from iios.common.logging.audit_logger import get_audit_logger
from iios.common.logging.logging_manager import get_logger
from iios.investment.workflow.engine_lifecycle import EngineState, LifecycleAwareMixin

from iios.execution.recovery.lifecycle import RecoverySession

from .constants import (
    DEFAULT_MAX_CONCURRENT,
    DEFAULT_MAX_HISTORY,
    DEFAULT_MAX_REQUESTS,
    ENGINE_ID,
    SYSTEM_ID,
    VERSION,
)
from .exceptions import RecoveryEngineNotRunningError
from .recovery_dispatcher import FailoverFrameworkPort, PolicyFrameworkPort
from .recovery_events import (
    RecoveryEngineEvent,
    make_engine_started,
    make_engine_stopped,
)
from .recovery_history import RecoveryEngineHistory
from .recovery_manager import RecoveryManager
from .recovery_request import RecoveryRequest
from .recovery_response import RecoveryResponse
from .recovery_statistics import RecoveryEngineStatistics

_log   = get_logger(__name__)
_audit = get_audit_logger(__name__)


class ExecutionRecoveryEngine(LifecycleAwareMixin):
    """
    Primary entry point for the Execution Recovery & Resilience subsystem.

    Usage::

        engine = ExecutionRecoveryEngine()
        engine.start()

        request = make_recovery_request(
            execution_session_id = "exec-001",
            subsystem_id         = "execution_gateway",
            failure_context      = make_failure_context(
                subsystem_id   = "execution_gateway",
                failure_type   = "GATEWAY_TIMEOUT",
                failure_reason = "Connection timed out after 30s",
            ),
            recovery_reason = "Automatic recovery triggered by health monitor",
        )
        response = engine.start_recovery(request)

        engine.stop()
    """

    def __init__(
        self,
        max_requests:       int                             = DEFAULT_MAX_REQUESTS,
        max_history:        int                             = DEFAULT_MAX_HISTORY,
        max_concurrent:     int                             = DEFAULT_MAX_CONCURRENT,
        policy_framework:   Optional[PolicyFrameworkPort]   = None,
        failover_framework: Optional[FailoverFrameworkPort] = None,
        _lifecycle:         Optional[Any]                   = None,  # injected in tests
    ) -> None:
        super().__init__()
        self._manager = RecoveryManager(
            max_requests       = max_requests,
            max_history        = max_history,
            max_concurrent     = max_concurrent,
            policy_framework   = policy_framework,
            failover_framework = failover_framework,
            lifecycle          = _lifecycle,
        )

    # ── LifecycleAwareMixin hooks ─────────────────────────────────────────────

    def _on_start(self) -> None:
        self._manager.start()
        _audit.log_lifecycle_event(
            SYSTEM_ID,
            EngineState.STOPPED,
            EngineState.RUNNING,
            VERSION,
        )
        _log.info("ExecutionRecoveryEngine started.", system_id=ENGINE_ID, version=VERSION)
        self._manager._emit(make_engine_started(actor=ENGINE_ID))

    def _on_stop(self) -> None:
        self._manager._emit(make_engine_stopped(actor=ENGINE_ID))
        self._manager.stop()
        _audit.log_lifecycle_event(
            SYSTEM_ID,
            EngineState.RUNNING,
            EngineState.STOPPED,
            VERSION,
        )
        _log.info("ExecutionRecoveryEngine stopped.", system_id=ENGINE_ID)

    def _assert_running(self) -> None:
        if self.lifecycle_state() not in (EngineState.RUNNING, "running"):
            raise RecoveryEngineNotRunningError()

    # ── Public API — primary ──────────────────────────────────────────────────

    def start_recovery(self, request: RecoveryRequest) -> RecoveryResponse:
        """
        Initiate a recovery workflow for the given request.

        Validates the request, creates a lifecycle session, runs the
        10-stage pipeline, and returns a RecoveryResponse.

        Thread-safe; bounded concurrency via semaphore.
        """
        self._assert_running()
        return self._manager.start_recovery(request)

    def stop_recovery(
        self,
        request_id: str,
        reason: str,
        *,
        actor: str = "",
    ) -> None:
        """
        Abort an in-progress recovery workflow.

        Marks the associated M1 session as ABORTED and records the event.
        """
        self._assert_running()
        self._manager.stop_recovery(request_id, reason, actor=actor or ENGINE_ID)

    # ── Queries ───────────────────────────────────────────────────────────────

    def get_session_for_request(self, request_id: str) -> Optional[RecoverySession]:
        """Return the M1 RecoverySession for the given request_id, or None."""
        self._assert_running()
        return self._manager.get_session_for_request(request_id)

    def active_sessions(self) -> List[RecoverySession]:
        """Return all currently active M1 recovery sessions."""
        self._assert_running()
        return self._manager.active_sessions()

    def get_statistics(self) -> RecoveryEngineStatistics:
        """Return an independent snapshot of current engine statistics."""
        self._assert_running()
        return self._manager.statistics()

    def get_history(self) -> RecoveryEngineHistory:
        """Return the engine's history store (live reference)."""
        self._assert_running()
        return self._manager.history()

    def is_running(self) -> bool:
        """Return True if the engine is currently running."""
        return self.lifecycle_state() in (EngineState.RUNNING, "running")

    # ── Event listeners ───────────────────────────────────────────────────────

    def add_event_listener(
        self, listener: Callable[[RecoveryEngineEvent], None]
    ) -> None:
        """Register a listener to receive domain events."""
        self._manager.add_event_listener(listener)

    def remove_event_listener(
        self, listener: Callable[[RecoveryEngineEvent], None]
    ) -> None:
        """Deregister a domain event listener."""
        self._manager.remove_event_listener(listener)

    # ── Port injection (M3/M4 wiring) ────────────────────────────────────────

    def set_policy_framework(self, port: PolicyFrameworkPort) -> None:
        """
        Wire the Recovery Policy Framework (M3) into this engine.

        Call this after start() to enable policy-driven recovery decisions.
        """
        self._manager.set_policy_framework(port)

    def set_failover_framework(self, port: FailoverFrameworkPort) -> None:
        """
        Wire the Failover Framework (M4) into this engine.

        Call this after start() to enable policy-triggered failover.
        """
        self._manager.set_failover_framework(port)
