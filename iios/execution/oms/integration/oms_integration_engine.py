"""iios/execution/oms/integration/oms_integration_engine.py
==================================================
OMSIntegrationEngine — THE ONLY PUBLIC ENTRY POINT to the OMS.

All other IIOS modules must interact with the Order Management System
exclusively through this engine.  It coordinates all five OMS components:

  - Order Manager
  - Order Book
  - Order Router
  - Order Queue
  - Order Persistence

This module does NOT implement:
  - Broker communication
  - Execution algorithms
  - Risk management
  - Position management
  - Monitoring

C6 Execution Intelligence — Phase 2, Module 6
"""
from __future__ import annotations

import threading
import time
from typing import Any

from iios.investment.workflow.engine_lifecycle import EngineState, LifecycleAwareMixin
from iios.common.logging.audit_logger import get_audit_logger
from iios.common.logging.logging_manager import get_logger

from iios.execution.oms.integration.constants import (
    ENGINE_SYSTEM_ID,
    VERSION,
    ComponentType,
    OMSState,
)
from iios.execution.oms.integration.exceptions import (
    OMSInitializationError,
    OMSNotInitializedError,
)
from iios.execution.oms.integration.oms_component_factory import OMSComponentFactory
from iios.execution.oms.integration.oms_component_registry import OMSComponentRegistry
from iios.execution.oms.integration.oms_integration_history import IntegrationHistory
from iios.execution.oms.integration.oms_integration_manager import OMSIntegrationManager
from iios.execution.oms.integration.oms_integration_request import IntegrationRequest
from iios.execution.oms.integration.oms_integration_response import IntegrationResponse
from iios.execution.oms.integration.oms_integration_snapshot import OMSSnapshot
from iios.execution.oms.integration.oms_integration_statistics import IntegrationStatistics
from iios.execution.oms.integration.oms_integration_validation import ValidationReport
from iios.execution.oms.integration.oms_component_health import ComponentHealth
from iios.execution.oms.integration.oms_component_status import ComponentStatus


class OMSIntegrationEngine(LifecycleAwareMixin):
    """
    Primary entry point to the IIOS Order Management System.

    Usage
    -----
    # Option 1 — fully automatic (factory creates all components)
    engine = OMSIntegrationEngine()
    engine.initialize()   # creates, registers, and starts all components
    engine.start()        # lifecycle start

    # Option 2 — inject pre-built components
    engine = OMSIntegrationEngine(
        order_manager        = my_manager,
        order_book           = my_book,
        order_router         = my_router,
        order_queue          = my_queue,
        persistence_manager  = my_pm,
    )
    engine.initialize()
    engine.start()

    # Option 3 — start first, then initialize
    engine = OMSIntegrationEngine()
    engine.start()
    # (initialize() is called automatically in _on_start if not yet run)

    Public API
    ----------
    initialize()      — set up all components
    start()           — lifecycle start  (calls initialize() if needed)
    stop()            — lifecycle stop, stops all components
    health()          — list of ComponentHealth
    status()          — list of ComponentStatus
    statistics()      — IntegrationStatistics
    snapshot()        — OMSSnapshot (full system view)
    history()         — IntegrationHistory
    validate()        — ValidationReport
    query(request)    — IntegrationResponse
    """

    def __init__(
        self,
        order_manager:        Any | None = None,
        order_book:           Any | None = None,
        order_router:         Any | None = None,
        order_queue:          Any | None = None,
        persistence_manager:  Any | None = None,
        factory:              OMSComponentFactory | None  = None,
        manager:              OMSIntegrationManager | None = None,
    ) -> None:
        super().__init__()
        self._factory   = factory or OMSComponentFactory()
        self._manager   = manager or OMSIntegrationManager(factory=self._factory)
        self._log       = get_logger(__name__, engine_id=ENGINE_SYSTEM_ID)
        self._audit     = get_audit_logger(__name__, engine_id=ENGINE_SYSTEM_ID)
        self._lock      = threading.RLock()
        self._initialized = False

        # Stash injected components for initialize()
        self._injected: dict[ComponentType, Any] = {}
        if order_manager:
            self._injected[ComponentType.ORDER_MANAGER] = order_manager
        if order_book:
            self._injected[ComponentType.ORDER_BOOK] = order_book
        if order_router:
            self._injected[ComponentType.ORDER_ROUTER] = order_router
        if order_queue:
            self._injected[ComponentType.ORDER_QUEUE] = order_queue
        if persistence_manager:
            self._injected[ComponentType.PERSISTENCE] = persistence_manager

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def _on_start(self) -> None:
        if not self._initialized:
            self.initialize()
        self._audit.log_lifecycle_event(
            ENGINE_SYSTEM_ID, EngineState.STOPPED, EngineState.RUNNING, VERSION
        )
        self._log.info("OMSIntegrationEngine started.", version=VERSION)

    def _on_stop(self) -> None:
        if self._manager.lifecycle_state() == EngineState.RUNNING:
            self._manager.stop()
        with self._lock:
            self._initialized = False
        self._audit.log_lifecycle_event(
            ENGINE_SYSTEM_ID, EngineState.RUNNING, EngineState.STOPPED, VERSION
        )
        self._log.info("OMSIntegrationEngine stopped.")

    def _assert_running(self) -> None:
        if self.lifecycle_state() != EngineState.RUNNING:
            raise OMSNotInitializedError(
                "OMSIntegrationEngine is not running — call start() first",
                code="OI-001",
            )

    # ------------------------------------------------------------------
    # Public API — initialize
    # ------------------------------------------------------------------

    def initialize(
        self,
        order_manager:       Any | None = None,
        order_book:          Any | None = None,
        order_router:        Any | None = None,
        order_queue:         Any | None = None,
        persistence_manager: Any | None = None,
    ) -> None:
        """
        Initialize the OMS by setting up all five components.

        If a component is not provided here (or in the constructor), a
        default instance is created by the factory.

        Safe to call multiple times — subsequent calls are no-ops.
        """
        with self._lock:
            if self._initialized:
                return

        # Start the manager if not yet running
        if self._manager.lifecycle_state() != EngineState.RUNNING:
            self._manager.start()

        # Build the override map from constructor + call-site injections
        overrides: dict[ComponentType, Any] = {**self._injected}
        if order_manager:
            overrides[ComponentType.ORDER_MANAGER] = order_manager
        if order_book:
            overrides[ComponentType.ORDER_BOOK] = order_book
        if order_router:
            overrides[ComponentType.ORDER_ROUTER] = order_router
        if order_queue:
            overrides[ComponentType.ORDER_QUEUE] = order_queue
        if persistence_manager:
            overrides[ComponentType.PERSISTENCE] = persistence_manager

        # Register overrides directly; fill missing with factory defaults
        registry = self._manager._registry
        for ct, component in overrides.items():
            registry.register(ct, component)

        # Let the manager fill remaining gaps and start everything
        self._manager.initialize_defaults()

        with self._lock:
            self._initialized = True

        self._log.info("OMS initialized.", components=registry.count)

    # ------------------------------------------------------------------
    # Public API — health / status / statistics
    # ------------------------------------------------------------------

    def health(self) -> list[ComponentHealth]:
        """Return health of all registered OMS components."""
        self._assert_running()
        return self._manager.health_all()

    def status(self) -> list[ComponentStatus]:
        """Return lifecycle status of all registered OMS components."""
        self._assert_running()
        return self._manager.status_all()

    def statistics(self) -> IntegrationStatistics:
        """Return aggregated OMS statistics."""
        self._assert_running()
        return self._manager.statistics()

    # ------------------------------------------------------------------
    # Public API — snapshot
    # ------------------------------------------------------------------

    def snapshot(self) -> OMSSnapshot:
        """
        Generate and return an immutable OMS snapshot.

        The snapshot includes component snapshots, health, status,
        and aggregated statistics.  Safe to call concurrently.
        """
        self._assert_running()
        return self._manager.snapshot()

    # ------------------------------------------------------------------
    # Public API — history
    # ------------------------------------------------------------------

    def history(self) -> IntegrationHistory:
        """Return the integration-level event history."""
        self._assert_running()
        return self._manager.history()

    # ------------------------------------------------------------------
    # Public API — validation
    # ------------------------------------------------------------------

    def validate(self) -> ValidationReport:
        """
        Run cross-component validation.

        Checks:
        - All required components are registered
        - All components are running
        - State is internally consistent
        """
        self._assert_running()
        return self._manager.validate()

    # ------------------------------------------------------------------
    # Public API — query
    # ------------------------------------------------------------------

    def query(self, request: IntegrationRequest) -> IntegrationResponse:
        """
        Route a query to the appropriate OMS component and return the result.

        See IntegrationQueryType for all supported query types.
        """
        self._assert_running()
        return self._manager.query(request)

    # ------------------------------------------------------------------
    # Convenience accessors (for testing / introspection)
    # ------------------------------------------------------------------

    def get_component(self, component_type: ComponentType) -> Any | None:
        """Return the registered instance for a given ComponentType."""
        return self._manager._registry.get(component_type)

    @property
    def oms_state(self) -> OMSState:
        return self._manager.oms_state

    @property
    def is_initialized(self) -> bool:
        with self._lock:
            return self._initialized

    def events(self):
        return self._manager.events()

    def summary(self) -> dict:
        stats = self._manager.statistics()
        return {
            "oms_state":        self.oms_state.value,
            "is_initialized":   self.is_initialized,
            "component_count":  self._manager._registry.count,
            "orders_managed":   stats.orders_managed,
            "orders_active":    stats.orders_active,
            "snapshots":        stats.snapshots_published,
            "validations":      stats.validations_run,
            "queries_served":   stats.queries_served,
            "version":          VERSION,
        }
