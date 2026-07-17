"""iios/execution/gateway/integration/gateway_component_factory.py
==================================================
GatewayComponentFactory — all-static factory for creating
pre-configured gateway subsystem components.

C6 Execution Intelligence — Phase 5, Module 6
"""
from __future__ import annotations

from iios.execution.gateway.brokers import BrokerManager
from iios.execution.gateway.engine import ExecutionGatewayEngine
from iios.execution.gateway.lifecycle import GatewayLifecycle
from iios.execution.gateway.routing import RoutingEngine
from iios.execution.gateway.snapshot import GatewaySnapshotStore

from .constants import (
    DEFAULT_MAX_HISTORY,
    DEFAULT_MAX_REQUESTS,
)
from .gateway_component_registry import GatewayComponentRegistry


class GatewayComponentFactory:
    """
    All-static factory for creating fully configured gateway components.

    Each factory method returns a STOPPED instance.  Start order is
    managed by GatewayComponentRegistry.start_all() or the calling engine.
    """

    @staticmethod
    def create_lifecycle(
        max_requests: int = DEFAULT_MAX_REQUESTS,
        max_history:  int = DEFAULT_MAX_HISTORY,
    ) -> GatewayLifecycle:
        return GatewayLifecycle(
            max_requests=max_requests,
            max_history=max_history,
        )

    @staticmethod
    def create_engine(
        max_requests:   int = DEFAULT_MAX_REQUESTS,
        max_queue_size: int = 1_000,
        max_sessions:   int = 500,
        max_history:    int = DEFAULT_MAX_HISTORY,
    ) -> ExecutionGatewayEngine:
        return ExecutionGatewayEngine(
            max_requests=max_requests,
            max_queue_size=max_queue_size,
            max_sessions=max_sessions,
            max_history=max_history,
        )

    @staticmethod
    def create_broker_manager(
        max_brokers: int = 20,
        max_history: int = DEFAULT_MAX_HISTORY,
    ) -> BrokerManager:
        return BrokerManager(
            max_brokers=max_brokers,
            max_history=max_history,
        )

    @staticmethod
    def create_routing_engine(
        max_policies:   int = 50,
        max_candidates: int = 100,
        max_history:    int = DEFAULT_MAX_HISTORY,
    ) -> RoutingEngine:
        return RoutingEngine(
            max_policies=max_policies,
            max_candidates=max_candidates,
            max_history=max_history,
        )

    @staticmethod
    def create_snapshot_store(
        max_snapshots:  int = 10_000,
        max_history:    int = DEFAULT_MAX_HISTORY,
        max_cache_size: int = 500,
    ) -> GatewaySnapshotStore:
        return GatewaySnapshotStore(
            max_snapshots=max_snapshots,
            max_history=max_history,
            max_cache_size=max_cache_size,
        )

    @staticmethod
    def create_all(
        max_requests:    int = DEFAULT_MAX_REQUESTS,
        max_history:     int = DEFAULT_MAX_HISTORY,
        max_brokers:     int = 20,
        max_policies:    int = 50,
        max_candidates:  int = 100,
        max_snapshots:   int = 10_000,
        max_cache_size:  int = 500,
    ) -> GatewayComponentRegistry:
        """
        Create and register all five components in a fresh registry.

        Returns a GatewayComponentRegistry with all components
        registered but NOT yet started.
        """
        registry = GatewayComponentRegistry()

        registry.register_lifecycle(
            GatewayComponentFactory.create_lifecycle(
                max_requests=max_requests,
                max_history=max_history,
            )
        )
        registry.register_engine(
            GatewayComponentFactory.create_engine(
                max_requests=max_requests,
                max_history=max_history,
            )
        )
        registry.register_broker_manager(
            GatewayComponentFactory.create_broker_manager(
                max_brokers=max_brokers,
                max_history=max_history,
            )
        )
        registry.register_routing_engine(
            GatewayComponentFactory.create_routing_engine(
                max_policies=max_policies,
                max_candidates=max_candidates,
                max_history=max_history,
            )
        )
        registry.register_snapshot_store(
            GatewayComponentFactory.create_snapshot_store(
                max_snapshots=max_snapshots,
                max_history=max_history,
                max_cache_size=max_cache_size,
            )
        )
        return registry
