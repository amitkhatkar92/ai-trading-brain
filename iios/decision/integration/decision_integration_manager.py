"""
decision_integration_manager.py — iios.decision.integration
============================================================
Manages the lifecycle of the integration subsystem components.

:class:`DecisionIntegrationManager` is responsible for starting, stopping,
and restarting all registered M1-M5 components in the correct order.

C9 Decision Intelligence — Phase 1, Module 6
"""
from __future__ import annotations

import threading
from typing import List, Optional

from iios.common.logging.logging_manager import get_logger
from iios.common.logging.audit_logger import get_audit_logger

from .constants import (
    ACTOR_MANAGER,
    ACTOR_SYSTEM,
    INTEGRATION_SYSTEM_ID,
    ComponentType,
    VERSION,
)
from .decision_component_registry import DecisionComponentRegistry
from .decision_component_factory import DecisionComponentFactory
from .exceptions import (
    IntegrationConfigurationError,
    IntegrationNotRunningError,
)

_log   = get_logger(__name__)
_audit = get_audit_logger(__name__, engine_id=INTEGRATION_SYSTEM_ID)

# Start/stop order for components
_START_ORDER: List[ComponentType] = [
    ComponentType.LIFECYCLE,
    ComponentType.SNAPSHOT,
    ComponentType.ENGINE,
    ComponentType.POLICY_FRAMEWORK,
    ComponentType.OPTIMIZATION_FRAMEWORK,
]

_STOP_ORDER: List[ComponentType] = list(reversed(_START_ORDER))


class DecisionIntegrationManager:
    """
    Manages start/stop/restart of all M1-M5 components.

    Usage
    -----
    ::

        manager = DecisionIntegrationManager()
        manager.start()
        ...
        manager.stop()

    Custom components can be injected before calling ``start()``::

        manager = DecisionIntegrationManager(component_registry=registry)
        manager.start()

    Parameters
    ----------
    component_registry : Pre-populated registry.  When omitted, the factory
                         creates default M1-M5 instances.
    """

    def __init__(
        self,
        component_registry: Optional[DecisionComponentRegistry] = None,
    ) -> None:
        self._lock     = threading.Lock()
        self._registry = component_registry or DecisionComponentFactory().create_default()
        self._started  = False

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Start all registered components in dependency order."""
        with self._lock:
            if self._started:
                return
            _log.info("DecisionIntegrationManager: starting components")
            for ct in _START_ORDER:
                self._start_component(ct)
            self._started = True
            _audit.log_lifecycle_event(
                engine_id  = INTEGRATION_SYSTEM_ID,
                from_state = "stopped",
                to_state   = "running",
                version    = VERSION,
                actor      = ACTOR_SYSTEM,
            )
            _log.info("DecisionIntegrationManager: all components started")

    def stop(self) -> None:
        """Stop all registered components in reverse dependency order."""
        with self._lock:
            if not self._started:
                return
            _log.info("DecisionIntegrationManager: stopping components")
            for ct in _STOP_ORDER:
                self._stop_component(ct)
            self._started = False
            _audit.log_lifecycle_event(
                engine_id  = INTEGRATION_SYSTEM_ID,
                from_state = "running",
                to_state   = "stopped",
                version    = VERSION,
                actor      = ACTOR_SYSTEM,
            )
            _log.info("DecisionIntegrationManager: all components stopped")

    def restart(self) -> None:
        """Stop then start all components."""
        self.stop()
        self.start()

    def is_started(self) -> bool:
        with self._lock:
            return self._started

    @property
    def registry(self) -> DecisionComponentRegistry:
        return self._registry

    # ------------------------------------------------------------------
    # Private
    # ------------------------------------------------------------------

    def _start_component(self, ct: ComponentType) -> None:
        """Start a single component if registered and not already running."""
        comp = self._registry.find(ct)
        if comp is None:
            return
        if hasattr(comp, "start"):
            try:
                # Only start if not already running
                if not self._registry.is_ready(ct):
                    comp.start()
                    _log.debug(f"DecisionIntegrationManager: started {ct.value}")
            except Exception as exc:
                _log.warning(
                    f"DecisionIntegrationManager: failed to start {ct.value}: {exc}"
                )

    def _stop_component(self, ct: ComponentType) -> None:
        """Stop a single component if registered and running."""
        comp = self._registry.find(ct)
        if comp is None:
            return
        if hasattr(comp, "stop"):
            try:
                comp.stop()
                _log.debug(f"DecisionIntegrationManager: stopped {ct.value}")
            except Exception as exc:
                _log.warning(
                    f"DecisionIntegrationManager: failed to stop {ct.value}: {exc}"
                )
