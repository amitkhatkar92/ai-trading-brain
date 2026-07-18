"""
iios/execution/recovery/integration/recovery_integration_manager.py
===================================================================
RecoveryIntegrationManager — LifecycleAwareMixin that coordinates the
full integration workflow: validate → register → submit to M2 →
snapshot with M5 → publish events → respond.

C7 Execution Recovery & Resilience — Phase 1, Module 6
"""
from __future__ import annotations

import time
import uuid
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from iios.common.logging.logging_manager import get_logger
from iios.common.logging.audit_logger import get_audit_logger
from iios.investment.workflow.engine_lifecycle import EngineState, LifecycleAwareMixin

# M2
from iios.execution.recovery.engine import (
    make_failure_context,
    make_recovery_request,
)
# M5
from iios.execution.recovery.snapshot import ExecutionRecoverySnapshot

from .constants import (
    ACTOR_INTEGRATION,
    MANAGER_ID,
    VERSION,
    IntegrationStatus,
)
from .exceptions import (
    IntegrationDuplicateError,
    IntegrationNotRunningError,
    IntegrationValidationError,
)
from .recovery_component_registry import RecoveryComponentRegistry
from .recovery_integration_context import IntegrationContext
from .recovery_integration_events import (
    make_recovery_completed,
    make_recovery_initialized,
    make_recovery_started,
    make_recovery_stopped,
    make_recovery_snapshot_published,
    make_recovery_validated,
)
from .recovery_integration_health import ComponentHealthReport, IntegrationHealthMonitor
from .recovery_integration_history import IntegrationHistory
from .recovery_integration_registry import IntegrationRegistry
from .recovery_integration_request import IntegrationRequest
from .recovery_integration_response import IntegrationResponse, make_integration_response
from .recovery_integration_statistics import IntegrationStatistics
from .recovery_integration_status import IntegrationStatusReport, make_status_report
from .recovery_integration_validation import IntegrationValidator, IntegrationValidationResult

_log   = get_logger(__name__)
_audit = get_audit_logger(__name__, engine_id=MANAGER_ID)

_RUNNING = frozenset({EngineState.RUNNING, "running"})


class RecoveryIntegrationManager(LifecycleAwareMixin):
    """
    Coordinates the end-to-end recovery integration workflow.

    Lifecycle:
        start() → submit() calls accepted
        stop()  → submit() raises IntegrationNotRunningError

    Thread safety:
        Each submit() call is independent; shared state (statistics, history,
        registry) uses their own locking primitives.
    """

    VERSION   = VERSION
    SYSTEM_ID = MANAGER_ID

    def __init__(self, components: RecoveryComponentRegistry) -> None:
        super().__init__()
        self._components     = components
        self._registry       = IntegrationRegistry()
        self._validator      = IntegrationValidator()
        self._stats          = IntegrationStatistics()
        self._history        = IntegrationHistory()
        self._health_monitor = IntegrationHealthMonitor()
        self._start_time:    Optional[float] = None

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def _on_start(self) -> None:
        self._start_time = time.time()
        self._registry.start()
        _log.info("RecoveryIntegrationManager started", system_id=MANAGER_ID)

    def _on_stop(self) -> None:
        self._registry.stop()
        _log.info("RecoveryIntegrationManager stopped", system_id=MANAGER_ID)

    def _assert_running(self) -> None:
        if self.lifecycle_state() not in _RUNNING:
            raise IntegrationNotRunningError()

    # ── Public API ────────────────────────────────────────────────────────────

    def submit(self, request: IntegrationRequest) -> IntegrationResponse:
        """
        Run the full integration workflow for the given request.

        Raises:
            IntegrationNotRunningError  — manager not started
            IntegrationValidationError  — request failed validation
            IntegrationDuplicateError   — request_id already processed
        """
        self._assert_running()
        t0 = time.perf_counter()

        # 1. Validate
        validation = self._validator.validate_request(request)
        if not validation.is_valid:
            raise IntegrationValidationError(
                f"Invalid request {request.request_id!r}: {validation.errors}",
                errors=tuple(validation.errors),
            )
        self._history.append_event(make_recovery_validated(request.request_id, actor=ACTOR_INTEGRATION))

        # 2. Idempotency check (raises IntegrationDuplicateError if duplicate)
        self._registry.register_active(request.request_id)

        # 3. Track stats & history
        self._stats.record_request()
        self._stats.record_session()
        self._history.append_request(request)
        self._history.append_event(make_recovery_started(request.request_id, actor=ACTOR_INTEGRATION))

        snapshot: Optional[ExecutionRecoverySnapshot] = None
        is_successful = False
        error_message = ""

        try:
            # 4. Build M2 inputs
            failure_ctx = make_failure_context(
                subsystem_id   = request.subsystem_id,
                failure_type   = request.failure_type,
                failure_reason = request.failure_reason,
                severity       = request.failure_severity,
            )
            m2_request = make_recovery_request(
                execution_session_id = request.execution_session_id,
                subsystem_id         = request.subsystem_id,
                failure_context      = failure_ctx,
                recovery_reason      = request.recovery_reason,
                workflow_id          = request.workflow_id,
            )

            # 5. Submit to M2
            t_recovery_start = time.perf_counter()
            m2_response = self._components.engine.start_recovery(m2_request)
            recovery_ms = (time.perf_counter() - t_recovery_start) * 1_000

            # 6. Retrieve M1 session
            m1_session = self._components.engine.get_session_for_request(m2_request.request_id)

            # 7. Build M5 snapshot (builder must be started)
            builder = self._components.snapshot_builder
            # Ensure builder is started (it may lack lifecycle if not started)
            if hasattr(builder, "lifecycle_state"):
                state_str = str(builder.lifecycle_state()).lower()
                if "running" not in state_str:
                    try:
                        builder.start()
                    except Exception:
                        pass

            snapshot = builder.build(
                lifecycle_session = m1_session,
                engine_response   = m2_response,
                execution_id      = request.execution_session_id,
                workflow_id       = request.workflow_id,
                gateway_id        = request.gateway_id,
                broker_id         = request.broker_id,
                portfolio_id      = request.portfolio_id,
                strategy_id       = request.strategy_id,
            )

            # 8. Persist in M5 store / cache / registry
            snap_id     = getattr(snapshot, "snapshot_id",          str(uuid.uuid4()))
            session_id  = getattr(snapshot, "recovery_session_id",   "")
            try:
                self._components.snapshot_store.save(snapshot)
            except Exception as exc:
                _log.warning("Snapshot store failed", error=str(exc))

            try:
                self._components.snapshot_cache.put(snapshot)
            except Exception as exc:
                _log.warning("Snapshot cache failed", error=str(exc))

            try:
                self._components.snapshot_registry.register(snap_id, session_id)
            except Exception as exc:
                _log.warning("Snapshot registry failed", error=str(exc))

            # 9. Stats and events
            self._stats.record_success()
            self._stats.record_recovery_time(recovery_ms)
            self._stats.record_snapshot_published()
            self._history.append_event(
                make_recovery_snapshot_published(request.request_id, snap_id, actor=ACTOR_INTEGRATION)
            )
            is_successful = True

        except IntegrationDuplicateError:
            raise
        except IntegrationValidationError:
            raise
        except Exception as exc:
            self._stats.record_failure()
            error_message = str(exc)
            _log.error(
                "Recovery integration failed",
                request_id=request.request_id,
                error=error_message,
            )

        finally:
            # 10. Always mark completed
            self._registry.complete(request.request_id)
            self._history.append_event(
                make_recovery_completed(request.request_id, actor=ACTOR_INTEGRATION)
            )

        response_ms     = (time.perf_counter() - t0) * 1_000
        recovery_dur_ms = response_ms  # best approx when no separate timer
        status = IntegrationStatus.ACTIVE if is_successful else IntegrationStatus.DEGRADED
        self._stats.record_response_time(response_ms)

        response = make_integration_response(
            request_id           = request.request_id,
            integration_status   = status,
            is_successful        = is_successful,
            recovery_duration_ms = recovery_dur_ms,
            response_time_ms     = response_ms,
            recovery_snapshot    = snapshot,
            error_message        = error_message,
        )
        self._history.append_response(response)
        return response

    # ── Supporting methods ────────────────────────────────────────────────────

    def validate(self, request: IntegrationRequest) -> IntegrationValidationResult:
        """Validate without submitting."""
        return self._validator.validate_request(request)

    def health(self) -> ComponentHealthReport:
        return self._health_monitor.check_health(self._components)

    def status(self) -> IntegrationStatusReport:
        overall = IntegrationStatus.ACTIVE if self._components.is_all_running() else IntegrationStatus.DEGRADED
        return make_status_report(
            components         = self._components,
            overall_status     = overall,
            active_requests    = self._registry.active_count,
            processed_requests = self._registry.processed_count,
        )

    def statistics(self) -> IntegrationStatistics:
        return self._stats.copy()

    def snapshot(self, snapshot_id: str = "") -> Optional[ExecutionRecoverySnapshot]:
        """Retrieve a snapshot by ID, or the latest if snapshot_id is empty."""
        store = self._components.snapshot_store
        if snapshot_id:
            try:
                return store.get(snapshot_id)
            except Exception:
                return None
        else:
            try:
                return store.latest()
            except Exception:
                return None

    def history(self) -> IntegrationHistory:
        return self._history

    def query(self, **criteria) -> List[ExecutionRecoverySnapshot]:
        """Delegate to M5 snapshot store using available query methods."""
        store = self._components.snapshot_store
        try:
            # Support common criteria keys that map to indexed query methods
            if "recovery_session_id" in criteria:
                return store.by_session(criteria["recovery_session_id"])
            if "execution_session_id" in criteria:
                return store.by_execution(criteria["execution_session_id"])
            if "workflow_id" in criteria:
                return store.by_workflow(criteria["workflow_id"])
            if "gateway_id" in criteria:
                return store.by_gateway(criteria["gateway_id"])
            if "broker_id" in criteria:
                return store.by_broker(criteria["broker_id"])
            # Fallback: return all
            return store.all()
        except Exception:
            return []
