"""
decision_integration_engine.py — iios.decision.integration
============================================================
PRIMARY PUBLIC INTERFACE for the Decision Intelligence subsystem.

:class:`DecisionIntegrationEngine` is the ONLY entry point that external
modules should use.  It integrates the five decision subsystems
(M1-M5) into a single institutional service.

This module:
  - DOES     orchestrate M1-M5 components
  - DOES     expose a clean public API
  - DOES     publish M5 :class:`~iios.decision.snapshot.DecisionSnapshot`
  - DOES NOT duplicate policy evaluation
  - DOES NOT duplicate optimization logic
  - DOES NOT execute trades
  - DOES NOT expose internal M1-M4 objects

C9 Decision Intelligence — Phase 1, Module 6
"""
from __future__ import annotations

import threading
import time
from typing import Any, Callable, Dict, List, Optional

from iios.investment.workflow.engine_lifecycle import EngineState, LifecycleAwareMixin
from iios.common.logging.logging_manager import get_logger
from iios.common.logging.audit_logger import get_audit_logger

from .constants import (
    ACTOR_ENGINE,
    ACTOR_SYSTEM,
    INTEGRATION_SYSTEM_ID,
    ComponentType,
    IntegrationPhase,
    IntegrationStatus,
    OverallHealth,
    VERSION,
)
from .decision_component_registry import DecisionComponentRegistry
from .decision_component_factory import DecisionComponentFactory
from .decision_integration_context import DecisionIntegrationContext
from .decision_integration_events import (
    DecisionIntegrationEvent,
    make_integration_initialized,
    make_integration_started,
    make_integration_stopped,
    make_integration_restarted,
    make_request_completed,
    make_request_failed,
    make_request_submitted,
    make_snapshot_published,
)
from .decision_integration_health import (
    DecisionIntegrationHealth,
    DecisionIntegrationHealthMonitor,
)
from .decision_integration_history import DecisionIntegrationHistory
from .decision_integration_manager import DecisionIntegrationManager
from .decision_integration_registry import DecisionIntegrationRegistry
from .decision_integration_request import DecisionIntegrationRequest
from .decision_integration_response import DecisionIntegrationResponse
from .decision_integration_snapshot import DecisionIntegrationSnapshot
from .decision_integration_statistics import DecisionIntegrationStatistics
from .decision_integration_status import (
    DecisionIntegrationStatus,
    DecisionIntegrationStatusMonitor,
)
from .decision_integration_validation import (
    DecisionIntegrationValidator,
    IntegrationValidationResult,
)
from .exceptions import (
    IntegrationNotRunningError,
    IntegrationRequestError,
    IntegrationValidationError,
    IntegrationWorkflowError,
)

_log   = get_logger(__name__)
_audit = get_audit_logger(__name__, engine_id=INTEGRATION_SYSTEM_ID)

_RUNNING = frozenset({EngineState.RUNNING, "running"})


class DecisionIntegrationEngine(LifecycleAwareMixin):
    """
    Primary public interface for the Decision Intelligence subsystem.

    Integrates M1 Decision Lifecycle, M2 Decision Engine, M3 Decision Policy
    Framework, M4 Decision Optimization Framework, and M5 Decision Snapshot
    into a single institutional service.

    External modules MUST use this class.  M1-M5 internals are never
    exposed directly.

    Public API
    ----------
    initialize()  — Pre-start configuration hook.
    start()       — Start the engine and all components.
    stop()        — Stop the engine and all components.
    restart()     — Restart all components.
    health()      — Return aggregate health report.
    status()      — Return service-level status.
    statistics()  — Return performance statistics.
    snapshot()    — Return a named or latest integration snapshot.
    history()     — Return integration history.
    validate()    — Validate a request without executing.
    submit()      — Execute the full decision workflow.
    query()       — Look up a previously completed response.

    Usage
    -----
    ::

        engine = DecisionIntegrationEngine()
        engine.start()

        request = DecisionIntegrationRequest.create("dec-001")
        response = engine.submit(request)
        print(response.status)        # IntegrationStatus.SUCCESS
        print(response.snapshot_id)   # M5 DecisionSnapshot ID

        engine.stop()

    Parameters
    ----------
    component_registry :  Optional pre-wired :class:`DecisionComponentRegistry`.
                          When omitted, :class:`DecisionComponentFactory` creates
                          default M1-M5 instances.
    max_in_flight :       Maximum simultaneous in-flight requests.
    max_history :         Maximum completed responses retained.
    """

    def __init__(
        self,
        component_registry: Optional[DecisionComponentRegistry] = None,
        *,
        max_in_flight: int = 1_000,
        max_history:   int = 5_000,
    ) -> None:
        super().__init__()
        self._lock        = threading.RLock()
        self._started_at: Optional[float] = None

        self._manager    = DecisionIntegrationManager(component_registry)
        self._validator  = DecisionIntegrationValidator()
        self._statistics = DecisionIntegrationStatistics()
        self._history    = DecisionIntegrationHistory()
        self._registry   = DecisionIntegrationRegistry(
            max_in_flight = max_in_flight,
            max_completed = max_history,
        )
        self._health_monitor  = DecisionIntegrationHealthMonitor()
        self._status_monitor  = DecisionIntegrationStatusMonitor()
        self._listeners:  List[Callable[[DecisionIntegrationEvent], None]] = []

    # ==================================================================
    # LifecycleAwareMixin hooks
    # ==================================================================

    def _on_start(self) -> None:
        self._manager.start()
        self._started_at = time.monotonic()
        _audit.log_lifecycle_event(
            engine_id  = INTEGRATION_SYSTEM_ID,
            from_state = "stopped",
            to_state   = "running",
            version    = VERSION,
            actor      = ACTOR_SYSTEM,
        )
        _log.info("DecisionIntegrationEngine: started")
        self._emit(make_integration_started())

    def _on_stop(self) -> None:
        self._manager.stop()
        _audit.log_lifecycle_event(
            engine_id  = INTEGRATION_SYSTEM_ID,
            from_state = "running",
            to_state   = "stopped",
            version    = VERSION,
            actor      = ACTOR_SYSTEM,
        )
        _log.info("DecisionIntegrationEngine: stopped")
        self._emit(make_integration_stopped())

    # ==================================================================
    # Public API
    # ==================================================================

    def initialize(self) -> None:
        """
        Pre-start initialisation hook.

        Can be called before :meth:`start` to perform additional
        configuration.  Safe to call multiple times.
        """
        _log.info("DecisionIntegrationEngine: initialize() called")
        self._emit(make_integration_initialized())

    def restart(self) -> None:
        """Restart the engine and all components."""
        _log.info("DecisionIntegrationEngine: restart requested")
        self.stop()
        self.start()
        self._emit(make_integration_restarted())

    def health(self) -> DecisionIntegrationHealth:
        """
        Return the aggregate health of the Decision Intelligence subsystem.

        Returns
        -------
        DecisionIntegrationHealth
        """
        is_running = self._is_running()
        return self._health_monitor.check(
            self._manager.registry,
            engine_is_running=is_running,
        )

    def status(self) -> DecisionIntegrationStatus:
        """
        Return the current service-level status.

        Returns
        -------
        DecisionIntegrationStatus
        """
        is_running = self._is_running()
        uptime     = (time.monotonic() - self._started_at) if self._started_at else 0.0
        h          = self._health_monitor.last() or self.health()
        return self._status_monitor.snapshot(
            self._manager.registry,
            self._statistics,
            h,
            is_running = is_running,
            uptime_s   = uptime,
        )

    def statistics(self) -> Dict[str, Any]:
        """
        Return performance statistics.

        Returns
        -------
        dict
            Keys: requests_submitted, requests_completed, requests_failed,
            requests_in_flight, sessions_created, snapshots_published,
            policy_evaluations, optimized_decisions, average_response_time_s,
            ema_response_time_s, throughput_per_minute, subsystem_availability.
        """
        return self._statistics.snapshot()

    def snapshot(
        self,
        integration_id: Optional[str] = None,
    ) -> Optional[DecisionIntegrationSnapshot]:
        """
        Return an integration snapshot by ID, or the latest one.

        Parameters
        ----------
        integration_id : Optional snapshot lookup key.

        Returns
        -------
        DecisionIntegrationSnapshot or None
        """
        latest = self._history.latest_response()
        if latest is None:
            return None
        if integration_id is not None:
            # Search history
            for resp in self._history.responses():
                if getattr(resp, "response_id", "") == integration_id:
                    return _response_to_integration_snapshot(resp)
            return None
        return _response_to_integration_snapshot(latest)

    def history(self) -> DecisionIntegrationHistory:
        """
        Return the integration history object.

        Returns
        -------
        DecisionIntegrationHistory
        """
        return self._history

    def validate(
        self,
        request: DecisionIntegrationRequest,
    ) -> IntegrationValidationResult:
        """
        Validate a request without executing the workflow.

        Parameters
        ----------
        request : :class:`DecisionIntegrationRequest` to validate.

        Returns
        -------
        IntegrationValidationResult
        """
        return self._validator.validate_request(
            request,
            component_registry=self._manager.registry,
        )

    def submit(
        self,
        request: DecisionIntegrationRequest,
    ) -> DecisionIntegrationResponse:
        """
        Execute the full decision workflow.

        Workflow
        --------
        1. Validate the request.
        2. Create a lifecycle session (M1).
        3. Advance lifecycle through INITIALIZING → COLLECTING → EVALUATING → READY.
        4. Invoke the Decision Engine (M2) if available.
        5. Invoke the Policy Framework (M3) if available.
        6. Invoke the Optimization Framework (M4) if available.
        7. Build and publish a Decision Snapshot (M5).
        8. Advance lifecycle to ACTIVE → COMPLETED.
        9. Return :class:`DecisionIntegrationResponse`.

        Parameters
        ----------
        request : :class:`DecisionIntegrationRequest`

        Returns
        -------
        DecisionIntegrationResponse

        Raises
        ------
        IntegrationNotRunningError
            When the engine is not started.
        IntegrationRequestError
            When the request argument is None.
        IntegrationValidationError
            When validation fails and the request is structurally invalid.
        """
        self._assert_running()

        if request is None:
            raise IntegrationRequestError("Integration request must not be None")

        ctx = DecisionIntegrationContext(request.request_id, request.decision_id)

        # Validate
        ctx.enter_phase(IntegrationPhase.VALIDATING)
        validation = self._validator.validate_request(
            request, component_registry=self._manager.registry
        )
        if not validation.is_valid:
            raise IntegrationValidationError(
                "Integration request failed validation",
                failed_checks=tuple(c.value for c in validation.failed_checks),
            )

        # Register in-flight
        self._registry.register_in_flight(request)
        self._statistics.record_request_submitted()
        self._emit(make_request_submitted(
            request.request_id,
            request.decision_id,
            scope    = request.decision_scope,
            priority = request.decision_priority,
        ))

        try:
            response = self._execute_workflow(request, ctx)
        except Exception as exc:
            ctx.error = exc
            response  = self._build_failure_response(request, ctx, exc)
            self._statistics.record_request_failed(ctx.elapsed_s())
            self._emit(make_request_failed(
                request.request_id,
                request.decision_id,
                ctx.session_id,
                error_message = str(exc),
                error_code    = getattr(exc, "error_code", "DI-007"),
            ))
        else:
            self._statistics.record_request_completed(ctx.elapsed_s())
            self._emit(make_request_completed(
                request.request_id,
                request.decision_id,
                ctx.session_id,
                status       = response.status.value,
                total_time_s = response.total_time_s,
                snapshot_id  = response.snapshot_id,
            ))
        finally:
            self._registry.deregister_in_flight(request.request_id)
            self._registry.complete(request.request_id, response)
            self._history.record_response(response)

        return response

    def query(
        self,
        request_id: Optional[str] = None,
        *,
        session_id:  Optional[str] = None,
        decision_id: Optional[str] = None,
    ) -> Optional[DecisionIntegrationResponse]:
        """
        Look up a previously completed response.

        Exactly one of *request_id*, *session_id*, or *decision_id* should
        be provided.  When *decision_id* is given, the most recent response
        for that decision is returned.

        Returns
        -------
        DecisionIntegrationResponse or None
        """
        if request_id is not None:
            return self._registry.find_completed(request_id)
        if session_id is not None:
            return self._registry.find_by_session(session_id)
        if decision_id is not None:
            by_dec = self._registry.find_by_decision(decision_id)
            return by_dec[-1] if by_dec else None
        return None

    # ==================================================================
    # Listeners
    # ==================================================================

    def add_listener(
        self,
        listener: Callable[[DecisionIntegrationEvent], None],
    ) -> None:
        with self._lock:
            if listener not in self._listeners:
                self._listeners.append(listener)

    def remove_listener(
        self,
        listener: Callable[[DecisionIntegrationEvent], None],
    ) -> None:
        with self._lock:
            try:
                self._listeners.remove(listener)
            except ValueError:
                pass

    # ==================================================================
    # Internal workflow
    # ==================================================================

    def _execute_workflow(
        self,
        request: DecisionIntegrationRequest,
        ctx:     DecisionIntegrationContext,
    ) -> DecisionIntegrationResponse:
        """
        Run the full integration workflow.  Returns a response on any outcome
        that is not an unhandled exception (including FAILED / PARTIAL).
        """
        registry = self._manager.registry

        # ------------------------------------------------------------------
        # Phase: LIFECYCLE — Create session
        # ------------------------------------------------------------------
        ctx.enter_phase(IntegrationPhase.LIFECYCLE)
        lc_t0   = time.monotonic()
        session = None

        lc = registry.find(ComponentType.LIFECYCLE)
        if lc is not None:
            from iios.decision.lifecycle.constants import (
                DecisionScope,
                DecisionType,
                DecisionPriority,
                DecisionTrigger,
            )
            # Map strings → enums with safe fallback
            scope    = _enum_or(DecisionScope,    request.decision_scope,    DecisionScope.ORDER)
            dtype    = _enum_or(DecisionType,     request.decision_type,     DecisionType.ORDER)
            priority = _enum_or(DecisionPriority, request.decision_priority, DecisionPriority.MEDIUM)
            trigger  = _enum_or(DecisionTrigger,  request.decision_trigger,  DecisionTrigger.AUTOMATIC)

            session = lc.create(
                request.decision_id,
                workflow_id       = request.workflow_id,
                portfolio_id      = request.portfolio_id,
                strategy_id       = request.strategy_id,
                decision_scope    = scope,
                decision_type     = dtype,
                decision_priority = priority,
                decision_trigger  = trigger,
                decision_reason   = request.decision_reason,
            )
            ctx.session    = session
            ctx.session_id = session.session_id
            self._statistics.record_session_created()

            # Advance lifecycle: CREATED → INITIALIZING → COLLECTING → EVALUATING → READY
            lc.initialize(session.session_id)
            lc.collect(session.session_id)
            lc.evaluate(session.session_id)
            lc.ready(session.session_id)

        lifecycle_time_s = time.monotonic() - lc_t0

        # ------------------------------------------------------------------
        # Phase: ENGINE
        # ------------------------------------------------------------------
        ctx.enter_phase(IntegrationPhase.ENGINE)
        engine_t0    = time.monotonic()
        engine_response = None

        eng = registry.find(ComponentType.ENGINE)
        if eng is not None:
            from iios.decision.engine import DecisionRequest as EngineRequest
            eng_req = EngineRequest.create(
                request.decision_id,
                workflow_id  = request.workflow_id,
                portfolio_id = request.portfolio_id,
                strategy_id  = request.strategy_id,
                inputs       = dict(request.inputs),
                metadata     = dict(request.metadata),
                deadline_s   = request.deadline_s,
            )
            engine_response         = eng.submit(eng_req)
            ctx.engine_response     = engine_response

        engine_time_s = time.monotonic() - engine_t0

        # ------------------------------------------------------------------
        # Phase: POLICY
        # ------------------------------------------------------------------
        ctx.enter_phase(IntegrationPhase.POLICY)
        policy_t0       = time.monotonic()
        policy_response = None

        policy_eng = registry.find(ComponentType.POLICY_FRAMEWORK)
        if policy_eng is not None and ctx.session is not None:
            try:
                from iios.decision.policies import (
                    DecisionPolicyFactory,
                )
                factory = policy_eng.factory()
                context = factory.create_context(
                    request_id  = request.request_id,
                    decision_id = request.decision_id,
                    inputs      = dict(request.inputs),
                )
                pol_req = factory.create_request(context)
                policy_response     = policy_eng.evaluate(pol_req)
                ctx.policy_response = policy_response
                self._statistics.record_policy_evaluation()
            except Exception as exc:
                _log.warning(
                    f"DecisionIntegrationEngine: policy evaluation skipped: {exc}"
                )

        policy_time_s = time.monotonic() - policy_t0

        # ------------------------------------------------------------------
        # Phase: OPTIMIZATION
        # ------------------------------------------------------------------
        ctx.enter_phase(IntegrationPhase.OPTIMIZATION)
        opt_t0               = time.monotonic()
        optimization_response = None

        opt_eng = registry.find(ComponentType.OPTIMIZATION_FRAMEWORK)
        if opt_eng is not None and ctx.session is not None:
            try:
                from iios.decision.optimization import (
                    DecisionOptimizationRequest as OptRequest,
                    DecisionOptimizationContext,
                    DecisionCandidate,
                )
                opt_ctx = DecisionOptimizationContext.create(
                    session_id   = ctx.session_id or request.request_id,
                    decision_id  = request.decision_id,
                    workflow_id  = request.workflow_id,
                    portfolio_id = request.portfolio_id,
                    strategy_id  = request.strategy_id,
                    inputs       = dict(request.inputs),
                )
                # Build candidates from engine response (if available),
                # or create a minimal single-candidate set.
                candidates = _extract_candidates(ctx, opt_ctx)
                opt_req    = OptRequest.create(context=opt_ctx, candidates=candidates)
                optimization_response     = opt_eng.optimize(opt_req)
                ctx.optimization_response = optimization_response
                self._statistics.record_optimized_decision()
            except Exception as exc:
                _log.warning(
                    f"DecisionIntegrationEngine: optimization skipped: {exc}"
                )

        optimization_time_s = time.monotonic() - opt_t0

        # ------------------------------------------------------------------
        # Phase: SNAPSHOT — Build and publish M5 DecisionSnapshot
        # ------------------------------------------------------------------
        ctx.enter_phase(IntegrationPhase.SNAPSHOT)
        snap_t0           = time.monotonic()
        decision_snapshot = None

        snapshot_store = registry.find(ComponentType.SNAPSHOT)
        if snapshot_store is not None and ctx.session is not None:
            from iios.decision.snapshot import DecisionSnapshotBuilder
            builder = DecisionSnapshotBuilder()
            decision_snapshot = builder.build(
                ctx.session,
                engine_response       = ctx.engine_response,
                policy_response       = ctx.policy_response,
                optimization_response = ctx.optimization_response,
                execution_session_id  = request.request_id,
                decision_metadata     = dict(request.metadata),
            )
            ctx.decision_snapshot = decision_snapshot
            try:
                snapshot_store.save(decision_snapshot)
            except Exception as exc:
                _log.warning(
                    f"DecisionIntegrationEngine: snapshot store save failed: {exc}"
                )
            self._statistics.record_snapshot_published()
            self._emit(make_snapshot_published(
                request.request_id,
                request.decision_id,
                ctx.session_id,
                decision_snapshot.snapshot_id,
                decision_status = decision_snapshot.decision_status.value,
                decision_score  = decision_snapshot.decision_score,
            ))

        snapshot_time_s = time.monotonic() - snap_t0

        # ------------------------------------------------------------------
        # Phase: COMPLETING — Advance lifecycle to ACTIVE → COMPLETED
        # ------------------------------------------------------------------
        ctx.enter_phase(IntegrationPhase.COMPLETING)

        if lc is not None and ctx.session is not None:
            try:
                lc.activate(ctx.session_id)
                lc.complete(ctx.session_id)
            except Exception as exc:
                _log.warning(
                    f"DecisionIntegrationEngine: lifecycle completion failed: {exc}"
                )

        ctx.close_phase()
        total_time_s = ctx.elapsed_s()

        # ------------------------------------------------------------------
        # Build response
        # ------------------------------------------------------------------
        snap_id    = decision_snapshot.snapshot_id if decision_snapshot else ""
        d_status   = (
            decision_snapshot.decision_status.value
            if decision_snapshot else ""
        )
        d_score    = decision_snapshot.decision_score    if decision_snapshot else 0.0
        d_conf     = decision_snapshot.decision_confidence if decision_snapshot else 0.0
        d_explain  = decision_snapshot.decision_explanation if decision_snapshot else ""
        selected   = (
            decision_snapshot.selected_decision
            if decision_snapshot else None
        )

        # Determine overall integration status
        if decision_snapshot is not None:
            status = IntegrationStatus.SUCCESS
        elif ctx.session is not None:
            status = IntegrationStatus.PARTIAL
        else:
            status = IntegrationStatus.FAILED

        component_results = {
            ComponentType.LIFECYCLE.value:              lc is not None,
            ComponentType.ENGINE.value:                 engine_response is not None,
            ComponentType.POLICY_FRAMEWORK.value:       policy_response is not None,
            ComponentType.OPTIMIZATION_FRAMEWORK.value: optimization_response is not None,
            ComponentType.SNAPSHOT.value:               decision_snapshot is not None,
        }

        return DecisionIntegrationResponse.create(
            request_id           = request.request_id,
            decision_id          = request.decision_id,
            session_id           = ctx.session_id,
            status               = status,
            snapshot_id          = snap_id,
            selected_decision    = selected,
            decision_status      = d_status,
            decision_score       = d_score,
            decision_confidence  = d_conf,
            decision_explanation = d_explain,
            component_results    = component_results,
            lifecycle_time_s     = lifecycle_time_s,
            engine_time_s        = engine_time_s,
            policy_time_s        = policy_time_s,
            optimization_time_s  = optimization_time_s,
            snapshot_time_s      = snapshot_time_s,
            total_time_s         = total_time_s,
        )

    # ------------------------------------------------------------------
    # Failure response builder
    # ------------------------------------------------------------------

    def _build_failure_response(
        self,
        request: DecisionIntegrationRequest,
        ctx:     DecisionIntegrationContext,
        exc:     Exception,
    ) -> DecisionIntegrationResponse:
        return DecisionIntegrationResponse.create(
            request_id    = request.request_id,
            decision_id   = request.decision_id,
            session_id    = ctx.session_id,
            status        = IntegrationStatus.FAILED,
            error_message = str(exc),
            error_code    = getattr(exc, "error_code", "DI-007"),
            total_time_s  = ctx.elapsed_s(),
        )

    # ------------------------------------------------------------------
    # Lifecycle guard
    # ------------------------------------------------------------------

    def _is_running(self) -> bool:
        try:
            state = self.lifecycle_state()
            if hasattr(state, "value"):
                return state.value == "running"
            return str(state).lower() == "running"
        except Exception:
            return False

    def _assert_running(self) -> None:
        if not self._is_running():
            raise IntegrationNotRunningError()

    # ------------------------------------------------------------------
    # Event dispatch
    # ------------------------------------------------------------------

    def _emit(self, event: DecisionIntegrationEvent) -> None:
        self._history.record_event(event)
        with self._lock:
            listeners = list(self._listeners)
        for listener in listeners:
            try:
                listener(event)
            except Exception as exc:
                _log.warning(
                    f"DecisionIntegrationEngine: listener raised {exc!r}"
                )

    # ------------------------------------------------------------------
    # Repr
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        state = self.lifecycle_state() if hasattr(self, "lifecycle_state") else "?"
        return f"DecisionIntegrationEngine(state={state!r})"


# ===========================================================================
# Internal helpers
# ===========================================================================

def _enum_or(enum_class, value: str, default):
    """Map a string to an enum member, falling back to ``default``."""
    for member in enum_class:
        if member.value == value or member.name.lower() == value.lower():
            return member
    return default


def _extract_candidates(ctx: DecisionIntegrationContext, opt_ctx) -> list:
    """
    Build a minimal candidate list for the optimization engine.

    When the engine response contains a parsed candidate, use it.
    Otherwise create a single synthetic candidate from the decision_id.
    """
    from iios.decision.optimization import DecisionCandidate

    # Try to extract from engine snapshot
    eng_resp = ctx.engine_response
    if eng_resp is not None:
        snap = getattr(eng_resp, "snapshot", None)
        if snap is not None:
            dispatch_results = getattr(snap, "dispatch_results", {})
            if dispatch_results:
                candidate = DecisionCandidate.create(
                    decision_id      = ctx.decision_id,
                    candidate_source = "engine",
                    attributes       = dict(dispatch_results),
                )
                return [candidate]

    # Synthetic fallback
    candidate = DecisionCandidate.create(
        decision_id      = ctx.decision_id,
        candidate_source = "integration",
        attributes       = {},
    )
    return [candidate]


def _response_to_integration_snapshot(
    response,
) -> Optional[DecisionIntegrationSnapshot]:
    """Convert a :class:`DecisionIntegrationResponse` to an integration snapshot."""
    if response is None:
        return None
    return DecisionIntegrationSnapshot.create(
        request_id          = getattr(response, "request_id",  ""),
        decision_id         = getattr(response, "decision_id", ""),
        session_id          = getattr(response, "session_id",  ""),
        snapshot_id         = getattr(response, "snapshot_id", ""),
        decision_status     = getattr(response, "decision_status", ""),
        decision_score      = getattr(response, "decision_score", 0.0),
        decision_confidence = getattr(response, "decision_confidence", 0.0),
        total_time_s        = getattr(response, "total_time_s", 0.0),
        components_run      = tuple(
            k for k, v in getattr(response, "component_results", {}).items()
            if v
        ),
    )
