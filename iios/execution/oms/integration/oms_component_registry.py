"""iios/execution/oms/integration/oms_component_registry.py
==================================================
OMSComponentRegistry — LifecycleAwareMixin registry for OMS component instances.

C6 Execution Intelligence — Phase 2, Module 6
"""
from __future__ import annotations

import threading
import time
from typing import Any, Iterator

from iios.investment.workflow.engine_lifecycle import EngineState, LifecycleAwareMixin
from iios.common.logging.audit_logger import get_audit_logger
from iios.common.logging.logging_manager import get_logger

from iios.execution.oms.integration.constants import (
    COMPONENT_LABELS,
    REGISTRY_SYSTEM_ID,
    VERSION,
    ComponentType,
    OMSState,
    REQUIRED_COMPONENTS,
)
from iios.execution.oms.integration.exceptions import (
    ComponentRegistrationError,
    OMSComponentMissingError,
    OMSComponentNotRunningError,
    OMSRegistryCapacityError,
)
from iios.execution.oms.integration.oms_component_health import ComponentHealth
from iios.execution.oms.integration.oms_component_status import ComponentStatus


class OMSComponentRegistry(LifecycleAwareMixin):
    """
    Thread-safe registry that holds exactly one instance per ComponentType.

    Provides lifecycle coordination (start_all / stop_all) and
    health / status aggregation across all registered components.
    """

    def __init__(self) -> None:
        super().__init__()
        self._components: dict[ComponentType, Any] = {}
        self._lock       = threading.RLock()
        self._log        = get_logger(__name__, engine_id=REGISTRY_SYSTEM_ID)
        self._audit      = get_audit_logger(__name__, engine_id=REGISTRY_SYSTEM_ID)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def _on_start(self) -> None:
        self._audit.log_lifecycle_event(
            REGISTRY_SYSTEM_ID, EngineState.STOPPED, EngineState.RUNNING, VERSION
        )
        self._log.info("OMSComponentRegistry started.")

    def _on_stop(self) -> None:
        self._audit.log_lifecycle_event(
            REGISTRY_SYSTEM_ID, EngineState.RUNNING, EngineState.STOPPED, VERSION
        )
        self._log.info("OMSComponentRegistry stopped.", registered=self.count)

    def _assert_running(self) -> None:
        if self.lifecycle_state() != EngineState.RUNNING:
            from iios.execution.oms.integration.exceptions import OMSNotInitializedError
            raise OMSNotInitializedError(
                "OMSComponentRegistry is not running",
                code="OI-001",
            )

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(self, component_type: ComponentType, component: Any) -> None:
        """Register one OMS component.  Replaces any existing registration."""
        self._assert_running()
        if component is None:
            raise ComponentRegistrationError(
                component_type.value, reason="component is None"
            )
        with self._lock:
            self._components[component_type] = component
            self._log.info(
                "OMS component registered.",
                component_type=component_type.value,
                label=COMPONENT_LABELS.get(component_type.value, component_type.value),
            )

    def unregister(self, component_type: ComponentType) -> bool:
        """Remove a component.  Returns True if removed."""
        with self._lock:
            removed = self._components.pop(component_type, None)
            if removed:
                self._log.info(
                    "OMS component unregistered.",
                    component_type=component_type.value,
                )
            return removed is not None

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def get(self, component_type: ComponentType) -> Any | None:
        with self._lock:
            return self._components.get(component_type)

    def require(self, component_type: ComponentType) -> Any:
        """Return component or raise OMSComponentMissingError."""
        component = self.get(component_type)
        if component is None:
            raise OMSComponentMissingError(component_type.value)
        return component

    def all(self) -> dict[ComponentType, Any]:
        with self._lock:
            return dict(self._components)

    def all_registered(self) -> list[ComponentType]:
        with self._lock:
            return list(self._components.keys())

    def missing(self) -> list[ComponentType]:
        """Return which required components are not yet registered."""
        with self._lock:
            return [ct for ct in REQUIRED_COMPONENTS if ct not in self._components]

    @property
    def count(self) -> int:
        with self._lock:
            return len(self._components)

    @property
    def is_complete(self) -> bool:
        """True when all required components are registered."""
        with self._lock:
            return all(ct in self._components for ct in REQUIRED_COMPONENTS)

    # ------------------------------------------------------------------
    # Lifecycle coordination
    # ------------------------------------------------------------------

    def start_all(self) -> None:
        """Start every registered component that is not yet running."""
        with self._lock:
            snapshot = dict(self._components)
        for ct, component in snapshot.items():
            try:
                if component.lifecycle_state() != EngineState.RUNNING:
                    component.start()
                    self._log.info(
                        "Component started.",
                        component_type=ct.value,
                    )
            except Exception as exc:  # noqa: BLE001
                self._log.info(
                    "Component failed to start.",
                    component_type=ct.value,
                    error=str(exc),
                )

    def stop_all(self) -> None:
        """Stop every registered component that is still running."""
        with self._lock:
            snapshot = dict(self._components)
        for ct, component in reversed(list(snapshot.items())):
            try:
                if component.lifecycle_state() == EngineState.RUNNING:
                    component.stop()
                    self._log.info(
                        "Component stopped.",
                        component_type=ct.value,
                    )
            except Exception as exc:  # noqa: BLE001
                self._log.info(
                    "Component failed to stop cleanly.",
                    component_type=ct.value,
                    error=str(exc),
                )

    # ------------------------------------------------------------------
    # Health / status
    # ------------------------------------------------------------------

    def health_all(self) -> list[ComponentHealth]:
        """Return a ComponentHealth for every registered component."""
        with self._lock:
            snapshot = dict(self._components)
        results = []
        for ct, component in snapshot.items():
            t0 = time.time()
            try:
                # Try calling health() with no args (most components).
                # RepositoryManager.health(repository_id) requires an arg,
                # so catch TypeError and fall back to lifecycle-state check.
                if hasattr(component, "health"):
                    try:
                        h = component.health()
                    except TypeError:
                        # Persistence manager needs a repo_id arg; use default
                        try:
                            reg = getattr(component, "_registry", None)
                            if reg and reg.count > 0:
                                default_repo = reg.default()
                                repo_id = getattr(default_repo, "repository_id", "")
                                h = component.health(repo_id)
                            else:
                                # No repos yet — report healthy if running
                                h = None
                        except Exception:
                            h = None

                    is_healthy = getattr(h, "is_healthy", True) if h is not None else (
                        component.lifecycle_state() == EngineState.RUNNING
                    )
                    message = getattr(h, "message", "") if h is not None else ""
                else:
                    is_healthy = (component.lifecycle_state() == EngineState.RUNNING)
                    message    = ""
            except Exception as exc:  # noqa: BLE001
                is_healthy = False
                message    = str(exc)

            results.append(ComponentHealth(
                component_type = ct,
                component_id   = ct.value.lower(),
                is_healthy     = is_healthy,
                latency_ms     = (time.time() - t0) * 1000.0,
                message        = message,
            ))
        return results

    def status_all(self) -> list[ComponentStatus]:
        """Return a ComponentStatus for every registered component."""
        with self._lock:
            snapshot = dict(self._components)
        results = []
        for ct, component in snapshot.items():
            try:
                state      = component.lifecycle_state()
                is_running = (state == EngineState.RUNNING)
                state_val  = state.value
            except Exception:  # noqa: BLE001
                is_running = False
                state_val  = "unknown"
            results.append(ComponentStatus(
                component_type  = ct,
                component_id    = ct.value.lower(),
                lifecycle_state = state_val,
                is_running      = is_running,
            ))
        return results

    def __iter__(self) -> Iterator[tuple[ComponentType, Any]]:
        with self._lock:
            snapshot = list(self._components.items())
        return iter(snapshot)

    def __len__(self) -> int:
        return self.count
