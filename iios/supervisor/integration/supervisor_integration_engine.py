"""
supervisor_integration_engine.py — iios.supervisor.integration
---------------------------------------------------------------
PRIMARY PUBLIC INTERFACE for the entire AI Supervisor & Autonomous Governance
subsystem.

All external components MUST use this class.  They MUST NOT directly access:
  - AI Supervisor Lifecycle        (M1)
  - AI Supervisor Engine           (M2)
  - AI Governance Policy Framework (M3)
  - Autonomous Governance Framework(M4)
  - AI Supervisor Snapshot         (M5)

Responsibilities (this module ONLY):
  - Accept integration requests via :meth:`submit`
  - Start / stop all M1-M5 subsystems
  - Expose health, status, statistics, snapshot, history, validate, query

This module MUST NOT:
  - Evaluate governance policies  (M3's job)
  - Perform AI reasoning          (M4's job)
  - Detect anomalies              (M4's job)
  - Execute trades                (ExecutionEngine's job)

C13 AI Supervisor & Autonomous Governance — Phase 1, Module 6
"""
from __future__ import annotations

import threading
from typing import Any, Callable, Dict, List, Optional

from iios.common.logging.audit_logger import get_audit_logger
from iios.common.logging.logging_manager import get_logger
from iios.investment.workflow.engine_lifecycle import LifecycleAwareMixin

from .constants import (
    ACTOR_SYSTEM,
    INTEGRATION_SYSTEM_ID,
    ComponentType,
    VERSION,
)
from .exceptions import SupervisorIntegrationNotRunningError
from .supervisor_component_factory import SupervisorComponentFactory
from .supervisor_component_registry import SupervisorComponentRegistry
from .supervisor_integration_events import (
    make_integration_initialized_event,
    make_integration_stopped_event,
)
from .supervisor_integration_health import SupervisorIntegrationHealth
from .supervisor_integration_history import SupervisorIntegrationHistory
from .supervisor_integration_manager import SupervisorIntegrationManager
from .supervisor_integration_registry import SupervisorIntegrationRegistry
from .supervisor_integration_request import SupervisorIntegrationRequest
from .supervisor_integration_response import SupervisorIntegrationResponse
from .supervisor_integration_snapshot import SupervisorIntegrationSnapshot
from .supervisor_integration_statistics import SupervisorIntegrationStatistics
from .supervisor_integration_status import SupervisorIntegrationStatus
from .supervisor_integration_validation import SupervisorIntegrationValidator

_log   = get_logger(__name__)
_audit = get_audit_logger(__name__, engine_id=INTEGRATION_SYSTEM_ID)


class SupervisorIntegrationEngine(LifecycleAwareMixin):
    """
    AI Supervisor Integration Engine — sole public entry point.

    Orchestrates the complete M1→M2→M3→M4→M5 pipeline for every
    :class:`SupervisorIntegrationRequest`.

    Parameters
    ----------
    component_registry : Pre-built component registry (optional).
    component_factory :  Factory for building M1-M5 components (optional).
    statistics :         Statistics accumulator (optional).
    history :            History store (optional).
    int_registry :       Integration request registry (optional).
    validator :          Integration validator (optional).
    health_rep :         Health reporter (optional).
    status_rep :         Status reporter (optional).
    manager :            Pipeline manager (optional).
    lifecycle :          M1 component (optional — auto-created if absent).
    engine :             M2 component (optional — auto-created if absent).
    policy_engine :      M3 component (optional — auto-created if absent).
    governance_engine :  M4 component (optional — auto-created if absent).
    snapshot_factory :   M5 component (optional — auto-created if absent).
    """

    def __init__(
        self,
        component_registry: Optional[SupervisorComponentRegistry] = None,
        component_factory:  Optional[SupervisorComponentFactory]   = None,
        statistics:         Optional[SupervisorIntegrationStatistics] = None,
        history:            Optional[SupervisorIntegrationHistory]    = None,
        int_registry:       Optional[SupervisorIntegrationRegistry]   = None,
        validator:          Optional[SupervisorIntegrationValidator]  = None,
        health_rep:         Optional[SupervisorIntegrationHealth]     = None,
        status_rep:         Optional[SupervisorIntegrationStatus]     = None,
        manager:            Optional[SupervisorIntegrationManager]    = None,
        *,
        lifecycle:         Optional[Any] = None,
        engine:            Optional[Any] = None,
        policy_engine:     Optional[Any] = None,
        governance_engine: Optional[Any] = None,
        snapshot_factory:  Optional[Any] = None,
    ) -> None:
        super().__init__()

        # Subsystem dependencies
        self._factory      = component_factory  or SupervisorComponentFactory()
        self._stats        = statistics         or SupervisorIntegrationStatistics()
        self._history      = history            or SupervisorIntegrationHistory()
        self._int_registry = int_registry       or SupervisorIntegrationRegistry()
        self._validator    = validator          or SupervisorIntegrationValidator()
        self._health_rep   = health_rep         or SupervisorIntegrationHealth()
        self._status_rep   = status_rep         or SupervisorIntegrationStatus()

        # Listeners
        self._listeners:     List[Callable] = []
        self._listener_lock: threading.Lock = threading.Lock()

        # Component registry: use provided or build from injected components
        self._components = component_registry or self._factory.create_all(
            lifecycle         = lifecycle,
            engine            = engine,
            policy_engine     = policy_engine,
            governance_engine = governance_engine,
            snapshot_factory  = snapshot_factory,
        )

        # Pipeline manager
        self._manager = manager or SupervisorIntegrationManager(
            component_registry = self._components,
            statistics         = self._stats,
            history            = self._history,
            registry           = self._int_registry,
            validator          = self._validator,
            event_listeners    = self._listeners,
        )

        # Latest published integration snapshot (thread-safe)
        self._latest_snapshot_lock = threading.Lock()
        self._latest_snapshot: Optional[SupervisorIntegrationSnapshot] = None

    # ------------------------------------------------------------------
    # LifecycleAwareMixin hooks
    # ------------------------------------------------------------------

    def _on_start(self) -> None:
        """Start all M1-M5 subsystem components."""
        for comp_type in ComponentType:
            comp = self._components.get_optional(comp_type)
            if comp is not None and hasattr(comp, "start"):
                try:
                    comp.start()
                except Exception as exc:  # noqa: BLE001
                    _log.info(f"Component {comp_type.value} start non-fatal error: {exc}")

        _audit.log_lifecycle_event(
            INTEGRATION_SYSTEM_ID, "stopped", "running", VERSION, actor=ACTOR_SYSTEM
        )
        event = make_integration_initialized_event(INTEGRATION_SYSTEM_ID)
        self._history.record_event(event)
        self._notify_listeners(event)
        _log.info(f"SupervisorIntegrationEngine started (version={VERSION})")

    def _on_stop(self) -> None:
        """Stop all M1-M5 subsystem components (reverse order)."""
        for comp_type in reversed(list(ComponentType)):
            comp = self._components.get_optional(comp_type)
            if comp is not None and hasattr(comp, "stop"):
                try:
                    comp.stop()
                except Exception as exc:  # noqa: BLE001
                    _log.info(f"Component {comp_type.value} stop non-fatal error: {exc}")

        _audit.log_lifecycle_event(
            INTEGRATION_SYSTEM_ID, "running", "stopped", VERSION, actor=ACTOR_SYSTEM
        )
        event = make_integration_stopped_event(INTEGRATION_SYSTEM_ID)
        self._history.record_event(event)
        self._notify_listeners(event)
        _log.info("SupervisorIntegrationEngine stopped")

    # ------------------------------------------------------------------
    # Guard
    # ------------------------------------------------------------------

    def _assert_running(self) -> None:
        if self.lifecycle_state().value != "running":
            raise SupervisorIntegrationNotRunningError()

    # ------------------------------------------------------------------
    # Lifecycle management
    # ------------------------------------------------------------------

    def initialize(self) -> None:
        """Alias for :meth:`start` — provided for spec compliance."""
        if self.lifecycle_state().value != "running":
            self.start()

    def restart(self) -> None:
        """Stop then start the engine and all M1-M5 components."""
        if self.lifecycle_state().value == "running":
            self.stop()
        self.start()

    # ------------------------------------------------------------------
    # Primary public interface
    # ------------------------------------------------------------------

    def submit(
        self, request: SupervisorIntegrationRequest
    ) -> SupervisorIntegrationResponse:
        """
        Execute the full integration pipeline for *request*.

        This is the ONLY entry point for external subsystems into the AI
        Supervisor & Autonomous Governance domain.

        Parameters
        ----------
        request : Fully constructed integration request.

        Returns
        -------
        SupervisorIntegrationResponse
            Always returned — never raises.

        Raises
        ------
        SupervisorIntegrationNotRunningError
            If the engine is not in the ``running`` lifecycle state.
        """
        self._assert_running()
        response = self._manager.run_integration(request)

        # Cache the latest published integration snapshot (if any)
        if response.is_success and response.supervisor_snapshot is not None:
            snap = SupervisorIntegrationSnapshot.create(
                integration_id      = request.integration_id,
                request_id          = request.request_id,
                supervisor_snapshot = response.supervisor_snapshot,
                session_id          = response.session_id,
            )
            with self._latest_snapshot_lock:
                self._latest_snapshot = snap

        return response

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    def health(self) -> Dict[str, Any]:
        """Return a plain-dict health report."""
        return self._health_rep.assess(self, self._components, self._stats)

    def status(self) -> Dict[str, Any]:
        """Return a plain-dict status report."""
        return self._status_rep.build_status(
            self, self._stats, self._history, self._components
        )

    def statistics(self) -> Dict[str, Any]:
        """Return a plain-dict statistics snapshot."""
        return self._stats.snapshot()

    def snapshot(self) -> Optional[SupervisorIntegrationSnapshot]:
        """Return the latest published integration snapshot, or None."""
        with self._latest_snapshot_lock:
            return self._latest_snapshot

    def history(self) -> Dict[str, int]:
        """Return event / request / response counts from the history store."""
        return self._history.counts()

    def validate(
        self, request: SupervisorIntegrationRequest
    ) -> Dict[str, Any]:
        """Validate *request* without executing the pipeline."""
        result = self._validator.validate_request(request)
        return result.to_dict()

    def query(self, key: str, **kwargs: Any) -> Any:
        """
        Flexible introspection query.

        Supported keys
        --------------
        ``"health"``      → :meth:`health`
        ``"status"``      → :meth:`status`
        ``"statistics"``  → :meth:`statistics`
        ``"snapshot"``    → :meth:`snapshot`
        ``"history"``     → :meth:`history`
        ``"components"``  → component registry counts dict
        """
        dispatch = {
            "health":     self.health,
            "status":     self.status,
            "statistics": self.statistics,
            "snapshot":   self.snapshot,
            "history":    self.history,
            "components": self._components.all_components,
        }
        fn = dispatch.get(key)
        if fn is not None:
            return fn()
        return None

    # ------------------------------------------------------------------
    # Listener management
    # ------------------------------------------------------------------

    def add_listener(self, listener: Callable) -> None:
        with self._listener_lock:
            self._listeners.append(listener)

    def remove_listener(self, listener: Callable) -> None:
        with self._listener_lock:
            try:
                self._listeners.remove(listener)
            except ValueError:
                pass

    def _notify_listeners(self, event: Any) -> None:
        with self._listener_lock:
            listeners = list(self._listeners)
        for fn in listeners:
            try:
                fn(event)
            except Exception:  # noqa: BLE001
                pass
