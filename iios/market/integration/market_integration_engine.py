"""
market_integration_engine.py — iios.market.integration
========================================================
**Primary public interface** for the complete Market Intelligence subsystem.

:class:`MarketIntegrationEngine` is the ONLY entry point external components
may use to interact with Market Intelligence.

Public API
----------
::

    engine = MarketIntegrationEngine()
    engine.initialize()
    engine.start()

    request  = MarketIntegrationRequest.market_overview("NSE")
    response = engine.submit(request)

    snapshot = engine.snapshot("NSE")
    status   = engine.status()
    health   = engine.health()
    stats    = engine.statistics()
    hist     = engine.history()
    result   = engine.validate(request)
    results  = engine.query(exchange="NSE")

    engine.stop()

Non-Responsibilities (intentional exclusions)
---------------------------------------------
* Market analytics / regime calculations   → M4
* Policy evaluation                        → M3
* Trading decisions                        → Decision Intelligence
* Execution routing                        → Execution Intelligence

C12 Market Intelligence — Phase 1, Module 6
"""
from __future__ import annotations

import threading
import time
import uuid
from typing import Any, Callable, Dict, List, Optional

from iios.common.logging.audit_logger import get_audit_logger
from iios.common.logging.logging_manager import get_logger
from iios.investment.workflow.engine_lifecycle import LifecycleAwareMixin

from .constants import (
    ACTOR_ENGINE,
    ACTOR_SYSTEM,
    COMPONENT_ANALYTICS_ENGINE,
    COMPONENT_ENGINE,
    COMPONENT_LIFECYCLE,
    COMPONENT_POLICY_ENGINE,
    COMPONENT_SNAPSHOT_CACHE,
    COMPONENT_SNAPSHOT_HISTORY,
    COMPONENT_SNAPSHOT_REGISTRY,
    COMPONENT_SNAPSHOT_STORE,
    DEFAULT_MAX_HISTORY,
    DEFAULT_MAX_REGISTRY,
    INTEGRATION_SYSTEM_ID,
    VERSION,
    ComponentStatus,
    IntegrationStatus,
)
from .exceptions import (
    MarketIntegrationConfigurationError,
    MarketIntegrationNotRunningError,
    MarketIntegrationSubsystemError,
)
from .market_component_factory import MarketComponentFactory
from .market_component_registry import MarketComponentRegistry
from .market_integration_events import (
    MarketIntegrationEvent,
    market_completed_event,
    market_failed_event,
    market_integration_started_event,
    market_integration_stopped_event,
    market_request_received_event,
    market_snapshot_published_event,
    market_validated_event,
)
from .market_integration_health import MarketIntegrationHealth
from .market_integration_history import MarketIntegrationHistory
from .market_integration_manager import MarketIntegrationManager
from .market_integration_registry import MarketIntegrationRegistry
from .market_integration_request import MarketIntegrationRequest
from .market_integration_response import MarketIntegrationResponse
from .market_integration_snapshot import MarketIntegrationSnapshot
from .market_integration_statistics import MarketIntegrationStatistics
from .market_integration_status import MarketIntegrationStatus
from .market_integration_validation import (
    MarketIntegrationValidation,
    MarketIntegrationValidationResult,
)

_log   = get_logger(__name__)
_audit = get_audit_logger(__name__, engine_id=INTEGRATION_SYSTEM_ID)


class MarketIntegrationEngine(LifecycleAwareMixin):
    """
    Institutional Market Integration Engine — primary public interface for
    the complete Market Intelligence subsystem.

    All downstream subsystems MUST communicate through this engine.
    :class:`~iios.market.snapshot.MarketSnapshot` is the ONLY published
    artefact; no internal component may be accessed directly.

    Parameters
    ----------
    max_registry :  Maximum responses retained in the registry.
    max_history :   Maximum events / requests retained in history.
    factory :       Optional injected component factory.
    """

    def __init__(
        self,
        max_registry: int = DEFAULT_MAX_REGISTRY,
        max_history:  int = DEFAULT_MAX_HISTORY,
        factory:      Optional[MarketComponentFactory] = None,
    ) -> None:
        super().__init__()
        self._max_registry = max_registry
        self._max_history  = max_history
        self._factory      = factory or MarketComponentFactory()

        # Component registry — all subsystem instances live here
        self._components = MarketComponentRegistry()

        # Integration infrastructure
        self._registry   = MarketIntegrationRegistry(max_entries=max_registry)
        self._statistics = MarketIntegrationStatistics()
        self._history    = MarketIntegrationHistory(max_entries=max_history)
        self._health     = MarketIntegrationHealth()
        self._validator  = MarketIntegrationValidation(
            is_running_fn=self._is_engine_running,
        )
        self._manager    = MarketIntegrationManager(
            component_registry = self._components,
            listener_fn        = self._dispatch_event,
        )

        # State
        self._started_at:    float           = 0.0
        self._default_exchange: str          = ""

        # Event listeners
        self._listener_lock = threading.Lock()
        self._listeners: List[Callable[[MarketIntegrationEvent], None]] = []

        # Track latest snapshot id per exchange
        self._latest_snapshot_id: Dict[str, str] = {}
        self._state_lock = threading.RLock()

    # ==================================================================
    # Lifecycle hooks (LifecycleAwareMixin)
    # ==================================================================

    def _on_start(self) -> None:
        self._started_at = time.time()
        _log.info(
            "MarketIntegrationEngine starting",
            extra={"engine_id": INTEGRATION_SYSTEM_ID, "version": VERSION},
        )
        _audit.log_lifecycle_event(
            engine_id  = INTEGRATION_SYSTEM_ID,
            from_state = "stopped",
            to_state   = "running",
            version    = VERSION,
            actor      = ACTOR_SYSTEM,
        )
        # Start registered subsystem components
        for name in self._components.all_names():
            component = self._components.get(name)
            if component is not None and hasattr(component, "start"):
                try:
                    component.start()
                    self._components.set_status(name, ComponentStatus.AVAILABLE)
                    _log.info(f"Component started: {name}")
                except Exception as exc:
                    self._components.set_status(name, ComponentStatus.DEGRADED)
                    _log.warning(f"Component {name} failed to start: {exc}")

        # Register health probes
        self._register_health_probes()

        # Emit integration-started event
        ev = market_integration_started_event(
            integration_id = INTEGRATION_SYSTEM_ID,
            exchange       = self._default_exchange,
            actor          = ACTOR_ENGINE,
            version        = VERSION,
        )
        self._dispatch_event(ev)
        self._history.record_event(ev)

    def _on_stop(self) -> None:
        _log.info(
            "MarketIntegrationEngine stopping",
            extra={"engine_id": INTEGRATION_SYSTEM_ID},
        )
        # Stop registered subsystem components in reverse order
        names = list(reversed(self._components.all_names()))
        for name in names:
            component = self._components.get(name)
            if component is not None and hasattr(component, "stop"):
                try:
                    component.stop()
                    self._components.set_status(name, ComponentStatus.UNAVAILABLE)
                except Exception as exc:
                    _log.warning(f"Component {name} failed to stop: {exc}")

        _audit.log_lifecycle_event(
            engine_id  = INTEGRATION_SYSTEM_ID,
            from_state = "running",
            to_state   = "stopped",
            version    = VERSION,
            actor      = ACTOR_SYSTEM,
            uptime_s   = round(time.time() - self._started_at, 2),
        )

        ev = market_integration_stopped_event(
            integration_id = INTEGRATION_SYSTEM_ID,
            exchange       = self._default_exchange,
            actor          = ACTOR_ENGINE,
        )
        self._dispatch_event(ev)
        self._history.record_event(ev)

    # ==================================================================
    # Public API
    # ==================================================================

    def initialize(
        self,
        *,
        exchange:          str  = "",
        enable_analytics:  bool = True,
        enable_policy:     bool = True,
        create_components: bool = True,
    ) -> None:
        """
        Initialize the integration engine and its subsystem components.

        Must be called before :meth:`start`.

        Parameters
        ----------
        exchange :           Default exchange for health probes.
        enable_analytics :   Whether to create and wire the analytics engine.
        enable_policy :      Whether to create and wire the policy engine.
        create_components :  If True (default), create all subsystem instances.
        """
        self._default_exchange = exchange
        self._statistics.record_api_call("initialize")

        if create_components:
            self._create_and_register_components(
                enable_analytics = enable_analytics,
                enable_policy    = enable_policy,
            )

        _log.info(
            f"MarketIntegrationEngine initialized — exchange={exchange or '(any)'} "
            f"analytics={enable_analytics} policy={enable_policy}"
        )

    def restart(self) -> None:
        """Stop and restart the integration engine and all subsystems."""
        self._statistics.record_api_call("restart")
        if self.lifecycle_state().value == "running":
            self.stop()
        self.start()

    def health(self) -> Dict[str, Any]:
        """
        Return an aggregate health report for the entire subsystem.

        Always returns a dict — never raises.
        """
        self._statistics.record_api_call("health")
        return self._health.report()

    def status(self) -> MarketIntegrationStatus:
        """Return an immutable status snapshot of the integration engine."""
        self._statistics.record_api_call("status")
        stats = self._statistics.snapshot()
        return MarketIntegrationStatus(
            engine_id              = INTEGRATION_SYSTEM_ID,
            lifecycle_state        = self.lifecycle_state().value,
            request_count          = stats.get("requests_processed", 0),
            success_count          = stats.get("successful_requests", 0),
            failure_count          = stats.get("failed_requests", 0),
            rejection_count        = stats.get("rejected_requests", 0),
            snapshot_publications  = stats.get("snapshot_publications", 0),
            subsystem_states       = self._components.health_summary(),
            health                 = self._health.report(),
            statistics             = stats,
            started_at             = self._started_at,
            captured_at            = time.time(),
            framework_version      = VERSION,
        )

    def statistics(self) -> Dict[str, Any]:
        """Return the current statistics snapshot."""
        self._statistics.record_api_call("statistics")
        return self._statistics.snapshot()

    def snapshot(self, exchange: str = "") -> MarketIntegrationSnapshot:
        """
        Return an integration-level snapshot of current engine state,
        including the latest published MarketSnapshot ID.
        """
        self._statistics.record_api_call("snapshot")
        with self._state_lock:
            latest_sid = self._latest_snapshot_id.get(
                exchange or self._default_exchange, ""
            )
        stats = self._statistics.snapshot()
        return MarketIntegrationSnapshot.create(
            integration_id     = INTEGRATION_SYSTEM_ID,
            lifecycle_state    = self.lifecycle_state().value,
            exchange           = exchange or self._default_exchange,
            request_count      = stats.get("requests_processed", 0),
            success_count      = stats.get("successful_requests", 0),
            failure_count      = stats.get("failed_requests", 0),
            rejection_count    = stats.get("rejected_requests", 0),
            market_snapshot_id = latest_sid,
            health             = self._health.report(),
            statistics         = stats,
            component_statuses = self._components.health_summary(),
        )

    def get_market_snapshot(self, exchange: str = "") -> Any:
        """
        Retrieve the latest published :class:`~iios.market.snapshot.MarketSnapshot`
        for *exchange* from the snapshot cache.

        Returns ``None`` if no snapshot is cached yet.
        """
        self._statistics.record_api_call("get_market_snapshot")
        cache = self._components.get(COMPONENT_SNAPSHOT_CACHE)
        if cache is None:
            return None
        return cache.get(exchange or self._default_exchange)

    def history(self, n: int = 50) -> Dict[str, List[Any]]:
        """Return recent integration activity (requests, responses, events, errors)."""
        self._statistics.record_api_call("history")
        return {
            "requests":  self._history.recent_requests(n),
            "responses": self._history.recent_responses(n),
            "events":    self._history.recent_events(n),
            "errors":    self._history.recent_errors(n),
        }

    def validate(
        self,
        request: MarketIntegrationRequest,
    ) -> MarketIntegrationValidationResult:
        """
        Validate *request* without processing it.

        Returns a :class:`~.market_integration_validation.MarketIntegrationValidationResult`.
        """
        self._statistics.record_api_call("validate")
        return self._validator.validate(request)

    def submit(
        self,
        request: MarketIntegrationRequest,
    ) -> MarketIntegrationResponse:
        """
        Submit a market integration request for processing.

        This is the **primary entry point** for all market analysis requests.

        Workflow
        --------
        1. Validate request
        2. Dispatch to MarketEngine (→ M1/M2/M3/M4)
        3. Build and publish MarketSnapshot (M5)
        4. Return MarketIntegrationResponse

        Parameters
        ----------
        request : MarketIntegrationRequest
            Use the factory methods:
            :meth:`~.market_integration_request.MarketIntegrationRequest.market_overview`,
            :meth:`~.market_integration_request.MarketIntegrationRequest.regime_analysis`,
            etc.

        Returns
        -------
        MarketIntegrationResponse
            Always returns a response — failures are captured in
            ``response.status`` and ``response.error_message``.

        Raises
        ------
        MarketIntegrationNotRunningError
            If the engine has not been started.
        """
        self._assert_running()
        self._statistics.record_api_call("submit")
        self._statistics.record_request_received()
        self._history.record_request(request)

        # Emit received event
        recv_ev = market_request_received_event(
            integration_id = request.integration_id,
            exchange       = request.exchange,
            actor          = ACTOR_ENGINE,
            request_id     = request.request_id,
            request_type   = request.request_type.value,
        )
        self._dispatch_event(recv_ev)
        self._history.record_event(recv_ev)

        # Validate
        validation = self._validator.validate(request)
        if not validation.is_valid:
            self._statistics.record_request_rejected()
            self._statistics.record_validation_failure()
            response = MarketIntegrationResponse.create_rejected(
                request_id     = request.request_id,
                integration_id = request.integration_id,
                exchange       = request.exchange,
                request_type   = request.request_type,
                reason         = "; ".join(validation.failure_messages),
            )
            self._history.record_response(response)
            self._history.record_error(response.error_message)
            return response

        # Emit validated event
        val_ev = market_validated_event(
            integration_id = request.integration_id,
            exchange       = request.exchange,
            actor          = ACTOR_ENGINE,
            request_id     = request.request_id,
        )
        self._dispatch_event(val_ev)
        self._history.record_event(val_ev)

        # Run workflow
        response = self._manager.run(request)

        # Post-process
        if response.is_successful:
            self._statistics.record_request_succeeded()

            # Track latest snapshot
            if response.has_snapshot:
                with self._state_lock:
                    self._latest_snapshot_id[request.exchange] = response.snapshot_id
                self._statistics.record_snapshot_published()

                pub_ev = market_snapshot_published_event(
                    integration_id = request.integration_id,
                    exchange       = request.exchange,
                    actor          = ACTOR_ENGINE,
                    snapshot_id    = response.snapshot_id,
                )
                self._dispatch_event(pub_ev)
                self._history.record_event(pub_ev)

            done_ev = market_completed_event(
                integration_id = request.integration_id,
                exchange       = request.exchange,
                actor          = ACTOR_ENGINE,
                elapsed_s      = response.elapsed_s,
            )
            self._dispatch_event(done_ev)
            self._history.record_event(done_ev)

        else:
            self._statistics.record_request_failed()
            fail_ev = market_failed_event(
                integration_id = request.integration_id,
                exchange       = request.exchange,
                actor          = ACTOR_ENGINE,
                error          = response.error_message,
            )
            self._dispatch_event(fail_ev)
            self._history.record_event(fail_ev)
            self._history.record_error(response.error_message)

        self._statistics.record_elapsed(response.elapsed_s)
        self._registry.register(response)
        self._history.record_response(response)

        return response

    def query(
        self,
        *,
        exchange:   str                     = "",
        status:     Optional[IntegrationStatus] = None,
        n:          int                     = 100,
    ) -> List[MarketIntegrationResponse]:
        """
        Query recent integration responses.

        Parameters
        ----------
        exchange :  Filter by exchange (empty = no filter).
        status :    Filter by integration status.
        n :         Maximum number of results to return.
        """
        self._statistics.record_api_call("query")

        if exchange and status:
            results = self._registry.query(
                lambda r: r.exchange == exchange and r.status == status
            )
        elif exchange:
            results = self._registry.by_exchange(exchange)
        elif status:
            results = self._registry.by_status(status)
        else:
            results = self._registry.all_responses()

        return results[-n:] if n and len(results) > n else results

    # ==================================================================
    # Listener management
    # ==================================================================

    def add_listener(
        self, listener: Callable[[MarketIntegrationEvent], None]
    ) -> None:
        with self._listener_lock:
            if listener not in self._listeners:
                self._listeners.append(listener)

    def remove_listener(
        self, listener: Callable[[MarketIntegrationEvent], None]
    ) -> None:
        with self._listener_lock:
            self._listeners = [l for l in self._listeners if l != listener]

    # ==================================================================
    # Guards
    # ==================================================================

    def _assert_running(self) -> None:
        if self.lifecycle_state().value != "running":
            raise MarketIntegrationNotRunningError()

    def _is_engine_running(self) -> bool:
        return self.lifecycle_state().value == "running"

    # ==================================================================
    # Internal helpers
    # ==================================================================

    def _dispatch_event(self, event: Any) -> None:
        with self._listener_lock:
            listeners = list(self._listeners)
        for fn in listeners:
            try:
                fn(event)
            except Exception as exc:
                _log.debug("Listener raised: %s", exc)

    def _create_and_register_components(
        self,
        *,
        enable_analytics: bool = True,
        enable_policy:    bool = True,
    ) -> None:
        """Create and register all subsystem component instances."""
        # M2 Engine (wraps M1 lifecycle internally)
        engine = self._factory.create_engine()
        self._components.register(COMPONENT_ENGINE, engine)

        # M3 Policy Engine
        if enable_policy:
            policy_engine = self._factory.create_policy_engine()
            self._components.register(COMPONENT_POLICY_ENGINE, policy_engine)
            # Wire into M2 engine dispatcher
            if hasattr(engine, "_dispatcher"):
                engine._dispatcher.register_policy_framework(
                    policy_engine.evaluate
                    if hasattr(policy_engine, "evaluate")
                    else lambda *a, **kw: None
                )

        # M4 Analytics Engine
        if enable_analytics:
            analytics_engine = self._factory.create_analytics_engine()
            self._components.register(COMPONENT_ANALYTICS_ENGINE, analytics_engine)
            # Wire into M2 engine dispatcher
            if hasattr(engine, "_dispatcher"):
                engine._dispatcher.register_analytics_framework(
                    analytics_engine.assess
                    if hasattr(analytics_engine, "assess")
                    else lambda *a, **kw: None
                )

        # M5 Snapshot infrastructure
        snap_registry = self._factory.create_snapshot_registry()
        snap_store    = self._factory.create_snapshot_store()
        snap_cache    = self._factory.create_snapshot_cache()
        snap_history  = self._factory.create_snapshot_history()

        self._components.register(COMPONENT_SNAPSHOT_REGISTRY, snap_registry)
        self._components.register(COMPONENT_SNAPSHOT_STORE,    snap_store)
        self._components.register(COMPONENT_SNAPSHOT_CACHE,    snap_cache)
        self._components.register(COMPONENT_SNAPSHOT_HISTORY,  snap_history)

        _log.info(
            f"Components registered: {self._components.all_names()}"
        )

    def _register_health_probes(self) -> None:
        """Register health probes for each subsystem component."""
        for name in self._components.all_names():
            component = self._components.get(name)
            if component is None:
                continue
            if hasattr(component, "health"):
                # Component has its own health() method
                def _make_probe(comp, n=name):
                    def _probe():
                        try:
                            result = comp.health()
                            if isinstance(result, dict):
                                return result
                            return {"overall": "healthy"}
                        except Exception as exc:
                            return {"overall": "unhealthy", "error": str(exc)}
                    return _probe
                self._health.register_probe(name, _make_probe(component))
            else:
                # Fallback: check component status in registry
                _status = self._components.status(name)
                self._health.register_probe(
                    name,
                    lambda n=name, s=_status: {
                        "overall": s.value if s.value != "unknown" else "unknown"
                    },
                )
