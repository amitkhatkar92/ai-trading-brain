"""
iios/execution/recovery/failover/failover_engine.py
===================================================
FailoverEngine — PRIMARY ENTRY POINT for the Execution Failover Framework.

Accepts an approved RecoveryPolicyDecision (from M3) plus resource
context keywords, converts it to a FailoverRequest, delegates execution
to FailoverManager, and returns a FailoverResponse.

C7 Execution Recovery & Resilience — Phase 1, Module 4
"""
from __future__ import annotations

import time
import uuid
from typing import Any, Dict, Optional

from iios.common.logging.logging_manager import get_logger
from iios.common.logging.audit_logger import get_audit_logger
from iios.investment.workflow.engine_lifecycle import EngineState, LifecycleAwareMixin

from .constants import (
    ACTOR_ENGINE,
    ENGINE_ID,
    VERSION,
    DEFAULT_FAILOVER_ACTION,
    DEFAULT_FAILOVER_TYPE,
    STRATEGY_TO_FAILOVER_MAP,
    FailoverAction,
    FailoverType,
)
from .exceptions import FailoverNotRunningError
from .failover_context import make_failover_context
from .failover_events import (
    make_failover_completed,
    make_failover_failed,
    make_failover_started,
    make_manual_escalation_requested,
)
from .failover_factory import FailoverFactory
from .failover_history import FailoverHistory
from .failover_manager import FailoverManager
from .failover_request import make_failover_request
from .failover_response import FailoverResponse
from .failover_statistics import FailoverStatistics

_log   = get_logger(__name__)
_audit = get_audit_logger(__name__)


class FailoverEngine(LifecycleAwareMixin):
    """
    Primary entry point for the Execution Failover Framework.

    Accepts a RecoveryPolicyDecision (duck-typed — must carry .decision_id,
    .execution_session_id, .subsystem_id, .strategy_type.value,
    .policy_name) plus resource/health keyword arguments.

    Lifecycle::
        engine.start()
        response = engine.execute(decision, backup_broker_available=True, ...)
        engine.stop()

    Thread-safe: execute() may be called concurrently.
    """

    def __init__(self) -> None:
        super().__init__()
        self._manager  = FailoverManager()
        self._factory  = FailoverFactory()
        self._stats    = FailoverStatistics()
        self._history  = FailoverHistory()

    def _on_start(self) -> None:
        self._factory.start()
        self._manager.start()
        _audit.log_lifecycle_event(ENGINE_ID, EngineState.STOPPED, EngineState.RUNNING, VERSION)
        _log.info("FailoverEngine started", version=VERSION)

    def _on_stop(self) -> None:
        self._manager.stop()
        self._factory.stop()
        _audit.log_lifecycle_event(ENGINE_ID, EngineState.RUNNING, EngineState.STOPPED, VERSION)
        _log.info("FailoverEngine stopped")

    def _assert_running(self) -> None:
        if self.lifecycle_state() not in (EngineState.RUNNING, "running"):
            raise FailoverNotRunningError()

    # ── Primary entry point ───────────────────────────────────────────────────

    def execute(
        self,
        decision: Any,
        *,
        backup_gateway_available:    bool  = False,
        backup_broker_available:     bool  = False,
        rollback_available:          bool  = False,
        restart_available:           bool  = True,
        monitoring_active:           bool  = True,
        is_within_risk_limits:       bool  = True,
        emergency_shutdown_requested: bool = False,
        primary_subsystem_healthy:   bool  = True,
        is_retry_exhausted:          bool  = False,
        retry_count:                 int   = 0,
        max_retries:                 int   = 3,
        restart_count:               int   = 0,
        has_monitoring_snapshot:     bool  = False,
        has_gateway_snapshot:        bool  = False,
        has_risk_snapshot:           bool  = False,
        metadata:                    Optional[Dict] = None,
    ) -> FailoverResponse:
        """
        Execute an approved RecoveryPolicyDecision.

        Parameters
        ----------
        decision:
            Any object with attributes matching RecoveryPolicyDecision
            (decision_id, execution_session_id, subsystem_id,
             strategy_type.value, policy_name).
        All remaining keyword arguments describe the current resource/health
        state that the executor needs to determine feasibility.
        """
        self._assert_running()
        start_ns = time.perf_counter_ns()

        # ── Extract fields from M3 decision ───────────────────────────────────
        source_decision_id   = getattr(decision, "decision_id", "") or str(uuid.uuid4())
        execution_session_id = getattr(decision, "execution_session_id", "") or str(uuid.uuid4())
        subsystem_id         = getattr(decision, "subsystem_id", "") or "unknown"
        strategy_type_value  = _get_strategy_value(decision)
        source_policy_name   = getattr(decision, "policy_name", "")
        failover_session_id  = str(uuid.uuid4())

        # ── Map M3 strategy → failover type + action ──────────────────────────
        failover_type, primary_action = STRATEGY_TO_FAILOVER_MAP.get(
            strategy_type_value,
            (DEFAULT_FAILOVER_TYPE, DEFAULT_FAILOVER_ACTION),
        )

        # ── Build context ─────────────────────────────────────────────────────
        context = make_failover_context(
            failover_session_id      = failover_session_id,
            execution_session_id     = execution_session_id,
            subsystem_id             = subsystem_id,
            failover_type            = failover_type,
            primary_action           = primary_action,
            source_decision_id       = source_decision_id,
            source_policy_name       = source_policy_name,
            recovery_strategy_type   = strategy_type_value,
            backup_gateway_available = backup_gateway_available,
            backup_broker_available  = backup_broker_available,
            rollback_available       = rollback_available,
            restart_available        = restart_available,
            monitoring_active        = monitoring_active,
            is_within_risk_limits    = is_within_risk_limits,
            emergency_shutdown_requested = emergency_shutdown_requested,
            primary_subsystem_healthy = primary_subsystem_healthy,
            is_retry_exhausted       = is_retry_exhausted,
            retry_count              = retry_count,
            max_retries              = max_retries,
            restart_count            = restart_count,
            has_monitoring_snapshot  = has_monitoring_snapshot,
            has_gateway_snapshot     = has_gateway_snapshot,
            has_risk_snapshot        = has_risk_snapshot,
            metadata                 = dict(metadata) if metadata else {},
        )

        # ── Build request ─────────────────────────────────────────────────────
        request = make_failover_request(
            failover_session_id  = failover_session_id,
            execution_session_id = execution_session_id,
            subsystem_id         = subsystem_id,
            failover_type        = failover_type,
            primary_action       = primary_action,
            source_decision_id   = source_decision_id,
            context              = context,
        )

        # ── Emit start event ──────────────────────────────────────────────────
        self._history.append_request(request)
        self._history.append_event(
            make_failover_started(
                failover_session_id, request.request_id,
                actor=ACTOR_ENGINE, action=primary_action.value,
            )
        )

        # ── Delegate to manager ───────────────────────────────────────────────
        try:
            response = self._manager.start_failover(request)
        except Exception as exc:
            elapsed_ms = (time.perf_counter_ns() - start_ns) / 1e6
            _log.error(
                "Failover execution error",
                session=failover_session_id,
                error=str(exc),
            )
            self._history.append_event(
                make_failover_failed(
                    failover_session_id, request.request_id,
                    actor=ACTOR_ENGINE, reason=str(exc),
                )
            )
            self._stats.record_execution(
                action=primary_action.value,
                failover_type=failover_type.value,
            )
            self._stats.record_failure()
            self._stats.record_recovery_time(elapsed_ms)
            raise

        # ── Update statistics ─────────────────────────────────────────────────
        elapsed_ms = (time.perf_counter_ns() - start_ns) / 1e6
        self._update_statistics(response, primary_action, failover_type, elapsed_ms)

        # ── Emit completion events ────────────────────────────────────────────
        self._history.append_response(response)
        event = (
            make_failover_completed
            if response.is_successful
            else make_failover_failed
        )
        kwargs: Dict = {"actor": ACTOR_ENGINE}
        if not response.is_successful:
            kwargs["reason"] = getattr(response.result, "error_message", "failed")
        self._history.append_event(
            event(failover_session_id, request.request_id, **kwargs)
        )

        if response.requires_manual_intervention:
            self._history.append_event(
                make_manual_escalation_requested(
                    failover_session_id, request.request_id,
                    actor=ACTOR_ENGINE,
                    reason="Manual intervention required post-failover",
                )
            )

        _log.info(
            "Failover complete",
            session=failover_session_id,
            action=response.result.action_executed.value,
            success=response.is_successful,
            operational=response.is_operational,
            elapsed_ms=f"{elapsed_ms:.2f}",
        )
        return response

    # ── Statistics / history accessors ────────────────────────────────────────

    @property
    def statistics(self) -> FailoverStatistics:
        return self._stats

    @property
    def history(self) -> FailoverHistory:
        return self._history

    # ── Internals ─────────────────────────────────────────────────────────────

    def _update_statistics(
        self,
        response: FailoverResponse,
        action: FailoverAction,
        failover_type: FailoverType,
        elapsed_ms: float,
    ) -> None:
        self._stats.record_execution(
            action=action.value, failover_type=failover_type.value
        )
        if response.is_successful:
            self._stats.record_success()
        else:
            self._stats.record_failure()
        if response.result.fallback_used:
            self._stats.record_fallback()
        if response.requires_manual_intervention:
            self._stats.record_manual_escalation()
        if response.verification_report is not None:
            self._stats.record_verification_run(
                passed=response.verification_report.is_verified
            )
        self._stats.record_recovery_time(elapsed_ms)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_strategy_value(decision: Any) -> str:
    """Extract M3 strategy type string from a RecoveryPolicyDecision."""
    st = getattr(decision, "strategy_type", None)
    if st is None:
        return ""
    # Enum value
    if hasattr(st, "value"):
        return st.value
    return str(st)
