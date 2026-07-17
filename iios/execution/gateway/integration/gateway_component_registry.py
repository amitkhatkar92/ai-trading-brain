"""iios/execution/gateway/integration/gateway_component_registry.py
==================================================
GatewayComponentRegistry — holds references to all five
integrated gateway components.

C6 Execution Intelligence — Phase 5, Module 6
"""
from __future__ import annotations

import threading
from typing import TYPE_CHECKING, Optional

from .constants import INTEGRATION_COMPONENT_REGISTRY_SYSTEM_ID
from .exceptions import ComponentNotRegisteredError

if TYPE_CHECKING:
    from iios.execution.gateway.brokers import BrokerManager
    from iios.execution.gateway.engine import ExecutionGatewayEngine
    from iios.execution.gateway.lifecycle import GatewayLifecycle
    from iios.execution.gateway.routing import RoutingEngine
    from iios.execution.gateway.snapshot import GatewaySnapshotStore


class GatewayComponentRegistry:
    """
    Thread-safe registry holding exactly one instance of each of the
    five gateway components.

    The registry does NOT own or manage the lifecycle of the
    components — GatewayIntegrationEngine does that.
    """

    SYSTEM_ID = INTEGRATION_COMPONENT_REGISTRY_SYSTEM_ID

    def __init__(self) -> None:
        self._lifecycle:      Optional["GatewayLifecycle"]      = None
        self._engine:         Optional["ExecutionGatewayEngine"] = None
        self._broker_manager: Optional["BrokerManager"]         = None
        self._routing_engine: Optional["RoutingEngine"]          = None
        self._snapshot_store: Optional["GatewaySnapshotStore"]   = None
        self._lock = threading.RLock()

    # ── Registration ──────────────────────────────────────────────────────────

    def register_lifecycle(self, lifecycle: "GatewayLifecycle") -> None:
        with self._lock:
            self._lifecycle = lifecycle

    def register_engine(self, engine: "ExecutionGatewayEngine") -> None:
        with self._lock:
            self._engine = engine

    def register_broker_manager(self, broker_manager: "BrokerManager") -> None:
        with self._lock:
            self._broker_manager = broker_manager

    def register_routing_engine(self, routing_engine: "RoutingEngine") -> None:
        with self._lock:
            self._routing_engine = routing_engine

    def register_snapshot_store(
        self, snapshot_store: "GatewaySnapshotStore"
    ) -> None:
        with self._lock:
            self._snapshot_store = snapshot_store

    # ── Access ────────────────────────────────────────────────────────────────

    @property
    def lifecycle(self) -> "GatewayLifecycle":
        with self._lock:
            if self._lifecycle is None:
                raise ComponentNotRegisteredError("LIFECYCLE")
            return self._lifecycle

    @property
    def engine(self) -> "ExecutionGatewayEngine":
        with self._lock:
            if self._engine is None:
                raise ComponentNotRegisteredError("ENGINE")
            return self._engine

    @property
    def broker_manager(self) -> "BrokerManager":
        with self._lock:
            if self._broker_manager is None:
                raise ComponentNotRegisteredError("BROKER_LAYER")
            return self._broker_manager

    @property
    def routing_engine(self) -> "RoutingEngine":
        with self._lock:
            if self._routing_engine is None:
                raise ComponentNotRegisteredError("ROUTING_ENGINE")
            return self._routing_engine

    @property
    def snapshot_store(self) -> "GatewaySnapshotStore":
        with self._lock:
            if self._snapshot_store is None:
                raise ComponentNotRegisteredError("SNAPSHOT_STORE")
            return self._snapshot_store

    # ── State ─────────────────────────────────────────────────────────────────

    @property
    def all_registered(self) -> bool:
        with self._lock:
            return all([
                self._lifecycle,
                self._engine,
                self._broker_manager,
                self._routing_engine,
                self._snapshot_store,
            ])

    def start_all(self) -> None:
        """Start all registered components that are not already running."""
        with self._lock:
            comps = [
                self._lifecycle,
                self._engine,
                self._broker_manager,
                self._routing_engine,
                self._snapshot_store,
            ]
        from iios.investment.workflow.engine_lifecycle import EngineState
        for comp in comps:
            if comp is not None:
                try:
                    if comp.lifecycle_state() != EngineState.RUNNING:
                        comp.start()
                except Exception:
                    pass  # health monitor will surface this

    def stop_all(self) -> None:
        """Stop all registered components in reverse order."""
        with self._lock:
            comps = [
                self._snapshot_store,
                self._routing_engine,
                self._broker_manager,
                self._engine,
                self._lifecycle,
            ]
        from iios.investment.workflow.engine_lifecycle import EngineState
        for comp in comps:
            if comp is not None:
                try:
                    if comp.lifecycle_state() == EngineState.RUNNING:
                        comp.stop()
                except Exception:
                    pass
