"""iios/execution/monitoring/integration/execution_monitoring_integration_engine.py
==================================================
ExecutionMonitoringIntegrationEngine — the ONLY public entry point
into the Execution Monitoring subsystem.

Integrates:
  - M1  MonitoringLifecycle
  - M3  MetricsEngine
  - M4  AlertManager

Exposes public API:
  initialize(), start(), stop(), restart(),
  health(), status(), statistics(), snapshot(),
  history(), validate(), submit(), query()

C6 Execution Intelligence — Phase 6, Module 6
"""
from __future__ import annotations

import threading
import time
import uuid
from typing import Any, Callable, Dict, List, Optional, Tuple

from iios.common.logging.audit_logger import get_audit_logger
from iios.common.logging.logging_manager import get_logger
from iios.investment.workflow.engine_lifecycle import EngineState, LifecycleAwareMixin

from .constants import (
    ACTOR_ENGINE,
    ENGINE_SYSTEM_ID,
    ComponentType,
    HealthStatus,
    IntegrationState,
    VERSION,
)
from .exceptions import (
    IntegrationAlreadyRunningError,
    IntegrationComponentError,
    IntegrationNotRunningError,
    IntegrationValidationError,
    IntegrationWorkflowError,
)
from .monitoring_component_factory import ComponentFactory
from .monitoring_component_registry import ComponentRegistry
from .monitoring_integration_context import (
    MonitoringIntegrationContext,
    make_monitoring_integration_context,
)
from .monitoring_integration_events import (
    IntegrationEvent,
    make_monitoring_completed,
    make_monitoring_health_changed,
    make_monitoring_initialized,
    make_monitoring_restarted,
    make_monitoring_snapshot_published,
    make_monitoring_started,
    make_monitoring_stopped,
    make_monitoring_validated,
)
from .monitoring_integration_health import (
    IntegrationHealth,
    compute_integration_health,
    make_component_health,
)
from .monitoring_integration_history import IntegrationHistory
from .monitoring_integration_registry import IntegrationRegistry
from .monitoring_integration_request import (
    MonitoringIntegrationRequest,
    make_monitoring_integration_request,
)
from .monitoring_integration_response import (
    MonitoringIntegrationResponse,
    make_monitoring_integration_response,
)
from .monitoring_integration_snapshot import (
    MonitoringIntegrationSnapshot,
    make_integration_snapshot,
)
from .monitoring_integration_statistics import IntegrationStatistics
from .monitoring_integration_status import IntegrationStatusRecord
from .monitoring_integration_validation import IntegrationValidator, IntegrationValidationResult

_log   = get_logger(__name__)
_audit = get_audit_logger(__name__)


class ExecutionMonitoringIntegrationEngine(LifecycleAwareMixin):
    """
    The sole public entry point for the Execution Monitoring subsystem.

    All external modules MUST interact with the monitoring sub-system
    exclusively through this class.  The engine:

    1. Owns ``MonitoringLifecycle`` (M1), ``MetricsEngine`` (M3), and
       ``AlertManager`` (M4).
    2. Coordinates the complete monitoring workflow on each ``submit()``.
    3. Exposes a rich query, health, and status API.
    4. Is thread-safe.

    Usage::

        engine = ExecutionMonitoringIntegrationEngine()
        engine.start()

        ctx  = make_monitoring_integration_context("sess-1", "port-A")
        req  = make_monitoring_integration_request(
            "sess-1", "port-A", ctx,
            metrics={"p99_latency": 42.0, "failure_rate": 0.01},
        )
        resp = engine.submit(req)

        health_report = engine.health()
        engine.stop()
    """

    def __init__(
        self,
        *,
        max_sessions:   int   = 5_000,
        max_history:    int   = 1_000,
        max_requests:   int   = 10_000,
        escalation_age_sec: float = 300.0,
        # Inject sub-components for testing; pass None to auto-create
        lifecycle:      Any   = None,
        metrics_engine: Any   = None,
        alert_manager:  Any   = None,
    ) -> None:
        super().__init__()

        # Sub-components — resolved in _on_start if not injected
        self._lifecycle      = lifecycle
        self._metrics_engine = metrics_engine
        self._alert_manager  = alert_manager

        self._escalation_age_sec = escalation_age_sec
        self._max_sessions       = max_sessions
        self._max_history        = max_history

        # Infrastructure
        self._factory    = ComponentFactory()
        self._components = ComponentRegistry()
        self._registry   = IntegrationRegistry(
            max_responses=max_requests,
            max_snapshots=max_requests,
        )
        self._history    = IntegrationHistory(
            max_responses=max_history,
            max_snapshots=max_history,
            max_events=max_history,
        )
        self._stats     = IntegrationStatistics()
        self._validator = IntegrationValidator()

        # Event listeners
        self._listeners:      List[Callable[[IntegrationEvent], None]] = []
        self._listeners_lock  = threading.Lock()

        # Snapshot version counters per session
        self._snapshot_versions: Dict[str, int] = {}
        self._op_lock = threading.RLock()   # RLock: submit re-enters helper methods

        # Started-at timestamp (set in _on_start)
        self._started_at: Optional[float] = None

    # ── LifecycleAwareMixin hooks ──────────────────────────────────────────────

    def _on_start(self) -> None:
        self._factory.start()
        self._registry.start()

        # Auto-create sub-components if not injected
        if self._lifecycle is None:
            self._lifecycle = self._factory.create_lifecycle(
                max_sessions=self._max_sessions,
                max_history=self._max_history,
            )
        if self._metrics_engine is None:
            self._metrics_engine = self._factory.create_metrics_engine(
                max_history=self._max_history,
            )
        if self._alert_manager is None:
            self._alert_manager = self._factory.create_alert_manager(
                max_history=self._max_history,
                escalation_age_sec=self._escalation_age_sec,
            )

        # Start all sub-components
        self._lifecycle.start()
        self._metrics_engine.start()
        self._alert_manager.start()

        # Register default alert rules
        self._alert_manager.register_default_rules()

        # Register in component registry
        self._components.register(
            ComponentType.LIFECYCLE, "MonitoringLifecycle", self._lifecycle
        )
        self._components.register(
            ComponentType.METRICS_ENGINE, "MetricsEngine", self._metrics_engine
        )
        self._components.register(
            ComponentType.ALERT_MANAGER, "AlertManager", self._alert_manager
        )

        self._started_at = time.time()

        _audit.log_lifecycle_event(
            ENGINE_SYSTEM_ID,
            EngineState.STOPPED,
            EngineState.RUNNING,
            VERSION,
        )
        _log.info(
            "ExecutionMonitoringIntegrationEngine started.",
            system_id=ENGINE_SYSTEM_ID,
            version=VERSION,
        )

    def _on_stop(self) -> None:
        # Stop sub-components in reverse order
        try:
            self._alert_manager.stop()
        except Exception as exc:
            _log.warning("AlertManager stop failed.", error=str(exc))

        try:
            self._metrics_engine.stop()
        except Exception as exc:
            _log.warning("MetricsEngine stop failed.", error=str(exc))

        try:
            self._lifecycle.stop()
        except Exception as exc:
            _log.warning("MonitoringLifecycle stop failed.", error=str(exc))

        self._registry.stop()
        self._factory.stop()
        self._components.clear()

        _audit.log_lifecycle_event(
            ENGINE_SYSTEM_ID,
            EngineState.RUNNING,
            EngineState.STOPPED,
            VERSION,
        )
        _log.info(
            "ExecutionMonitoringIntegrationEngine stopped.",
            system_id=ENGINE_SYSTEM_ID,
            total_requests=self._stats.requests_received,
        )

    # ── Guard ─────────────────────────────────────────────────────────────────

    def _assert_running(self) -> None:
        if self.lifecycle_state() not in (EngineState.RUNNING, "running"):
            raise IntegrationNotRunningError()

    # ── Public lifecycle API ──────────────────────────────────────────────────

    def initialize(self) -> None:
        """
        Initialise the engine if not yet started.

        Idempotent — safe to call when already running.
        """
        if self.lifecycle_state() not in (EngineState.RUNNING, "running"):
            self.start()
        _log.info("ExecutionMonitoringIntegrationEngine initialised.")

    def restart(self) -> None:
        """Stop all sub-components and start them again."""
        _log.info("ExecutionMonitoringIntegrationEngine restarting.")
        self.stop()
        self.start()
        # emit restart event (use a placeholder session_id for engine events)
        ev = make_monitoring_restarted(
            "__engine__", actor=ACTOR_ENGINE, reason="restart requested"
        )
        self._history.append_event(ev)
        self._emit(ev)
        _log.info("ExecutionMonitoringIntegrationEngine restarted.")

    # ── Health API ────────────────────────────────────────────────────────────

    def health(self) -> IntegrationHealth:
        """Return a live health report across all sub-components."""
        self._stats.record_health_check()

        component_statuses = []
        for entry in self._components.all_entries():
            try:
                running = entry.is_running()
            except Exception as exc:  # noqa: BLE001
                component_statuses.append(
                    make_component_health(
                        entry.component_type,
                        entry.component_name,
                        is_running=False,
                        error=str(exc),
                    )
                )
                continue
            component_statuses.append(
                make_component_health(
                    entry.component_type,
                    entry.component_name,
                    is_running=running,
                )
            )

        if not component_statuses:
            # Engine not yet started — return UNKNOWN
            component_statuses = [
                make_component_health(ComponentType.INTEGRATION, "integration", is_running=False, error="not started")
            ]

        return compute_integration_health(component_statuses)

    # ── Status API ────────────────────────────────────────────────────────────

    def status(self) -> IntegrationStatusRecord:
        """Return a comprehensive status snapshot."""
        from .monitoring_integration_status import IntegrationStatusRecord
        lc_state = self.lifecycle_state()
        if lc_state in (EngineState.RUNNING, "running"):
            state = IntegrationState.RUNNING
        elif lc_state in (EngineState.STOPPED, "stopped"):
            state = IntegrationState.STOPPED
        else:
            state = IntegrationState.STOPPED

        h = self.health()
        uptime = (
            time.time() - self._started_at
            if self._started_at is not None else 0.0
        )

        stats = self._stats.copy()
        return IntegrationStatusRecord(
            state           = state,
            health          = h,
            active_sessions = 0,
            total_requests  = stats.requests_received,
            total_errors    = stats.requests_failed,
            uptime_seconds  = uptime,
            started_at      = self._started_at,
        )

    # ── Statistics API ────────────────────────────────────────────────────────

    def statistics(self) -> IntegrationStatistics:
        """Return a copy of the accumulated integration statistics."""
        return self._stats.copy()

    # ── History API ───────────────────────────────────────────────────────────

    def history(self) -> IntegrationHistory:
        """Return the integration history (responses, snapshots, events)."""
        return self._history

    # ── Validation API ────────────────────────────────────────────────────────

    def validate(self, request: MonitoringIntegrationRequest) -> IntegrationValidationResult:
        """
        Validate a MonitoringIntegrationRequest without processing it.

        Returns an IntegrationValidationResult.  Does NOT emit events
        or update statistics.
        """
        return self._validator.validate_request(request)

    # ── Snapshot API ──────────────────────────────────────────────────────────

    def snapshot(
        self,
        session_id:   str,
        portfolio_id: str,
        *,
        gateway_id:  Optional[str] = None,
        strategy_id: Optional[str] = None,
    ) -> MonitoringIntegrationSnapshot:
        """
        Build and return an integration snapshot for a session.

        Uses the current state of the registry.  Does NOT trigger a
        new monitoring cycle.
        """
        self._assert_running()
        existing = self._registry.latest_snapshot_for_session(session_id)
        if existing is not None:
            return existing

        # No prior snapshot — return an empty one
        version = self._next_snapshot_version(session_id)
        snap = make_integration_snapshot(
            session_id    = session_id,
            portfolio_id  = portfolio_id,
            snapshot_version = version,
            health_status = HealthStatus.UNKNOWN.value,
            gateway_id    = gateway_id,
            strategy_id   = strategy_id,
        )
        self._registry.store_snapshot(snap)
        self._history.append_snapshot(snap)
        return snap

    # ── Submit API (core workflow) ────────────────────────────────────────────

    def submit(
        self, request: MonitoringIntegrationRequest
    ) -> MonitoringIntegrationResponse:
        """
        Execute the full integration monitoring workflow.

        Workflow:
        1. Validate request.
        2. Create monitoring session (M1 lifecycle).
        3. Advance lifecycle: CREATED → INITIALIZING → STARTING → ACTIVE.
        4. Build AlertContext from request.metrics.
        5. Evaluate alerts (M4).
        6. Build integration snapshot.
        7. Advance lifecycle: ACTIVE → STOPPING → STOPPED.
        8. Persist response and snapshot.
        9. Return MonitoringIntegrationResponse.
        """
        self._assert_running()
        t0 = time.perf_counter()
        self._stats.record_request_received()

        # ── Step 1: Validate ──────────────────────────────────────────────────
        val = self._validator.validate_request(request)
        if not val.is_valid:
            self._stats.record_validation_failure()
            self._stats.record_request_failed()
            err_msg = "; ".join(val.errors)
            resp = make_monitoring_integration_response(
                request.request_id,
                request.session_id,
                request.portfolio_id,
                errors=(err_msg,),
                evaluation_duration_ms=0.0,
            )
            self._history.append_response(resp)
            return resp

        session_id   = request.session_id
        portfolio_id = request.portfolio_id
        ctx          = request.context
        errors: List[str] = []
        monitoring_session_id: Optional[str] = None

        # ── Step 2–3: Lifecycle session ───────────────────────────────────────
        try:
            mon_session = self._lifecycle.create(
                session_id,
                portfolio_id,
                gateway_id  = ctx.gateway_id,
                strategy_id = ctx.strategy_id,
                workflow_id = ctx.workflow_id,
                order_id    = ctx.order_id,
            )
            monitoring_session_id = mon_session.session_id
            self._stats.record_session_created()

            self._lifecycle.initialize(monitoring_session_id, actor=ACTOR_ENGINE)
            self._lifecycle.begin(monitoring_session_id, actor=ACTOR_ENGINE)
            self._lifecycle.mark_active(monitoring_session_id, actor=ACTOR_ENGINE)

            ev_init = make_monitoring_initialized(session_id, actor=ACTOR_ENGINE)
            self._history.append_event(ev_init)
            self._emit(ev_init)

            ev_start = make_monitoring_started(session_id, actor=ACTOR_ENGINE)
            self._history.append_event(ev_start)
            self._emit(ev_start)

        except Exception as exc:
            errors.append(f"lifecycle: {exc}")
            _log.warning("Lifecycle setup failed.", session_id=session_id, error=str(exc))

        # ── Step 4–5: Metrics cycle ───────────────────────────────────────────
        self._stats.record_metrics_cycle()
        # Nothing to compute — metrics are pre-computed by the caller (M3).
        # We simply acknowledge the cycle.

        # ── Step 5–6: Alert evaluation ────────────────────────────────────────
        generated_ids: List[str] = []
        suppressed_ids: List[str] = []
        alert_snapshot = None

        try:
            from iios.execution.monitoring.alerts.alert_context import make_alert_context

            alert_ctx = make_alert_context(
                session_id    = session_id,
                portfolio_id  = portfolio_id,
                metrics       = request.metrics,
                window_metrics= request.window_metrics,
                gateway_id    = ctx.gateway_id,
                strategy_id   = ctx.strategy_id,
            )
            alerts = self._alert_manager.evaluate(alert_ctx)
            generated_ids  = [a.alert_id for a in alerts]
            self._stats.record_alerts(len(generated_ids))

            alert_snapshot = self._alert_manager.snapshot(session_id, portfolio_id)

        except Exception as exc:
            errors.append(f"alerts: {exc}")
            _log.warning("Alert evaluation failed.", session_id=session_id, error=str(exc))

        # ── Step 7: Build integration snapshot ───────────────────────────────
        snap_version  = self._next_snapshot_version(session_id)
        health_status = (
            HealthStatus.HEALTHY.value
            if not errors
            else HealthStatus.DEGRADED.value
        )

        alert_counts: Dict[str, int] = {}
        active_alert_ids: Tuple[str, ...] = ()
        total_active = 0
        highest_sev: Optional[str] = None

        if alert_snapshot is not None:
            alert_counts     = dict(alert_snapshot.alert_counts_by_severity)
            active_alert_ids = tuple(alert_snapshot.active_alert_ids)
            total_active     = alert_snapshot.total_active
            highest_sev      = alert_snapshot.highest_severity

        snap = make_integration_snapshot(
            session_id               = session_id,
            portfolio_id             = portfolio_id,
            snapshot_version         = snap_version,
            metrics                  = dict(request.metrics),
            window_metrics           = {k: dict(v) for k, v in request.window_metrics.items()},
            active_alert_ids         = active_alert_ids,
            alert_counts_by_severity = alert_counts,
            total_active_alerts      = total_active,
            highest_severity         = highest_sev,
            lifecycle_state          = "active" if not errors else "failed",
            health_status            = health_status,
            gateway_id               = ctx.gateway_id,
            strategy_id              = ctx.strategy_id,
        )
        self._registry.store_snapshot(snap)
        self._history.append_snapshot(snap)
        self._stats.record_snapshot_published()

        ev_snap = make_monitoring_snapshot_published(session_id, actor=ACTOR_ENGINE)
        self._history.append_event(ev_snap)
        self._emit(ev_snap)

        # ── Step 8: Lifecycle wind-down ───────────────────────────────────────
        final_state = "stopped"
        if monitoring_session_id:
            try:
                self._lifecycle.cease(monitoring_session_id, actor=ACTOR_ENGINE)
                self._lifecycle.mark_stopped(monitoring_session_id, actor=ACTOR_ENGINE)
                self._stats.record_session_completed()
            except Exception as exc:
                errors.append(f"lifecycle stop: {exc}")
                try:
                    self._lifecycle.fail(
                        monitoring_session_id,
                        reason=str(exc),
                        actor=ACTOR_ENGINE,
                    )
                except Exception:  # noqa: BLE001
                    pass
                self._stats.record_session_failed()
                final_state = "failed"

        # ── Step 9: Build response ────────────────────────────────────────────
        duration_ms = (time.perf_counter() - t0) * 1_000
        resp = make_monitoring_integration_response(
            request.request_id,
            session_id,
            portfolio_id,
            snapshot_id            = snap.snapshot_id,
            metrics_count          = len(request.metrics),
            alerts_generated       = tuple(generated_ids),
            alerts_suppressed      = tuple(suppressed_ids),
            lifecycle_state        = final_state,
            evaluation_duration_ms = duration_ms,
            errors                 = tuple(errors),
        )

        self._registry.store_response(resp)
        self._history.append_response(resp)

        if errors:
            self._stats.record_request_failed()
        else:
            self._stats.record_request_completed(duration_ms)

        ev_done = make_monitoring_completed(session_id, actor=ACTOR_ENGINE)
        self._history.append_event(ev_done)
        self._emit(ev_done)

        _log.info(
            "Integration monitoring cycle completed.",
            session_id       = session_id,
            duration_ms      = round(duration_ms, 2),
            alerts_generated = len(generated_ids),
            has_errors       = bool(errors),
        )
        return resp

    # ── Query API ─────────────────────────────────────────────────────────────

    def query(
        self,
        session_id: Optional[str]   = None,
        *,
        with_errors:  bool          = False,
        with_alerts:  bool          = False,
        limit:        Optional[int] = None,
    ) -> List[MonitoringIntegrationResponse]:
        """
        Query historical integration responses.

        Parameters
        ----------
        session_id:   Filter by session.  None returns all.
        with_errors:  Include only responses that have errors.
        with_alerts:  Include only responses that generated alerts.
        limit:        Maximum number of results (most recent first).
        """
        self._assert_running()

        if session_id is not None:
            results = self._history.responses_for_session(session_id)
        else:
            results = self._history.responses()

        if with_errors:
            results = [r for r in results if r.has_errors]
        if with_alerts:
            results = [r for r in results if r.has_alerts]

        # Most recent first
        results = list(reversed(results))

        if limit is not None:
            results = results[:limit]

        return results

    # ── Event dispatch ────────────────────────────────────────────────────────

    def add_event_listener(
        self, listener: Callable[[IntegrationEvent], None]
    ) -> None:
        with self._listeners_lock:
            self._listeners.append(listener)

    def remove_event_listener(
        self, listener: Callable[[IntegrationEvent], None]
    ) -> None:
        with self._listeners_lock:
            self._listeners = [l for l in self._listeners if l != listener]

    def _emit(self, event: IntegrationEvent) -> None:
        with self._listeners_lock:
            listeners = list(self._listeners)
        for listener in listeners:
            try:
                listener(event)
            except Exception as exc:  # noqa: BLE001
                _log.warning(
                    "Integration event listener raised.",
                    listener=repr(listener),
                    error=str(exc),
                )

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _next_snapshot_version(self, session_id: str) -> int:
        with self._op_lock:
            v = self._snapshot_versions.get(session_id, 0) + 1
            self._snapshot_versions[session_id] = v
            return v
