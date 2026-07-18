"""
iios/execution/recovery/integration/execution_recovery_integration_engine.py
=============================================================================
ExecutionRecoveryIntegrationEngine — the single public entry point for the
C7 Execution Recovery Integration subsystem.

Wires M2 (RecoveryEngine), M3 (PolicyEngine), M4 (FailoverEngine), and
M5 (Snapshot) into one institutional service.

External callers interact ONLY with this class.  All internal plumbing
(M2/M3/M4/M5 instances, manager, registry, validator) is hidden.

C7 Execution Recovery & Resilience — Phase 1, Module 6
"""
from __future__ import annotations

from typing import List, Optional

from iios.common.logging.audit_logger import get_audit_logger
from iios.common.logging.logging_manager import get_logger
from iios.execution.recovery.snapshot import ExecutionRecoverySnapshot
from iios.investment.workflow.engine_lifecycle import EngineState, LifecycleAwareMixin

from .constants import ENGINE_ID, VERSION, IntegrationStatus
from .exceptions import IntegrationNotRunningError
from .recovery_component_factory import RecoveryComponentFactory
from .recovery_component_registry import RecoveryComponentRegistry
from .recovery_integration_health import ComponentHealthReport
from .recovery_integration_history import IntegrationHistory
from .recovery_integration_manager import RecoveryIntegrationManager
from .recovery_integration_request import IntegrationRequest
from .recovery_integration_response import IntegrationResponse
from .recovery_integration_statistics import IntegrationStatistics
from .recovery_integration_status import IntegrationStatusReport
from .recovery_integration_validation import IntegrationValidationResult

_log   = get_logger(__name__)
_audit = get_audit_logger(__name__, engine_id=ENGINE_ID)

_RUNNING = frozenset({EngineState.RUNNING, "running"})


class ExecutionRecoveryIntegrationEngine(LifecycleAwareMixin):
    """
    Institutional entry point for the Execution Recovery Integration subsystem.

    Provides a clean, stable API for all external consumers:

        engine = ExecutionRecoveryIntegrationEngine()
        engine.start()                    # or .initialize()
        response = engine.submit(request)
        report   = engine.health()
        engine.stop()

    All component lifecycle (M2/M3/M4/M5) is managed internally.
    Callers never need to start/stop individual components.
    """

    VERSION   = VERSION
    SYSTEM_ID = ENGINE_ID

    def __init__(
        self,
        components: Optional[RecoveryComponentRegistry] = None,
    ) -> None:
        super().__init__()
        self._components: RecoveryComponentRegistry = (
            components if components is not None else RecoveryComponentFactory.create()
        )
        self._manager: Optional[RecoveryIntegrationManager] = None

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def _on_start(self) -> None:
        self._components.start_all()
        self._manager = RecoveryIntegrationManager(self._components)
        self._manager.start()
        _audit.log_lifecycle_event(
            ENGINE_ID, str(EngineState.STOPPED), str(EngineState.RUNNING), VERSION
        )
        _log.info(
            "ExecutionRecoveryIntegrationEngine started",
            system_id=ENGINE_ID,
            version=VERSION,
        )

    def _on_stop(self) -> None:
        if self._manager is not None:
            self._manager.stop()
        self._components.stop_all()
        _audit.log_lifecycle_event(
            ENGINE_ID, str(EngineState.RUNNING), str(EngineState.STOPPED), VERSION
        )
        _log.info(
            "ExecutionRecoveryIntegrationEngine stopped",
            system_id=ENGINE_ID,
        )

    def _assert_running(self) -> None:
        if self.lifecycle_state() not in _RUNNING:
            raise IntegrationNotRunningError()

    # ── Convenience alias ─────────────────────────────────────────────────────

    def initialize(self) -> None:
        """Alias for start() — provided for descriptive call sites."""
        self.start()

    # ── Public API ────────────────────────────────────────────────────────────

    def submit(self, request: IntegrationRequest) -> IntegrationResponse:
        """
        Submit an IntegrationRequest and run the full recovery workflow.

        Returns an IntegrationResponse containing the ExecutionRecoverySnapshot
        and outcome details.

        Raises:
            IntegrationNotRunningError  — engine not started
            IntegrationValidationError  — request failed validation
            IntegrationDuplicateError   — request_id already processed
        """
        self._assert_running()
        return self._manager.submit(request)

    def validate(self, request: IntegrationRequest) -> IntegrationValidationResult:
        """
        Validate a request without executing the workflow.

        Safe to call before submit(); does not mutate any state.
        """
        self._assert_running()
        return self._manager.validate(request)

    def health(self) -> ComponentHealthReport:
        """Return a per-component health report and overall system health."""
        self._assert_running()
        return self._manager.health()

    def status(self) -> IntegrationStatusReport:
        """Return a typed operational status report."""
        self._assert_running()
        return self._manager.status()

    def statistics(self) -> IntegrationStatistics:
        """Return an independent copy of runtime statistics."""
        self._assert_running()
        return self._manager.statistics()

    def snapshot(self, snapshot_id: str = "") -> Optional[ExecutionRecoverySnapshot]:
        """
        Retrieve an ExecutionRecoverySnapshot.

        If snapshot_id is provided, returns that specific snapshot.
        Otherwise returns the most recently published snapshot.
        """
        self._assert_running()
        return self._manager.snapshot(snapshot_id)

    def history(self) -> IntegrationHistory:
        """Return the live integration history (requests, responses, events)."""
        self._assert_running()
        return self._manager.history()

    def query(self, **criteria) -> List[ExecutionRecoverySnapshot]:
        """
        Query the snapshot store.

        Supported keyword criteria:
            recovery_session_id, execution_session_id, workflow_id,
            gateway_id, broker_id

        Returns all snapshots if no criteria are given.
        """
        self._assert_running()
        return self._manager.query(**criteria)
