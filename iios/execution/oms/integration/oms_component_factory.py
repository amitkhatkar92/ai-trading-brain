"""iios/execution/oms/integration/oms_component_factory.py
==================================================
OMSComponentFactory — creates default OMS component instances.

All components are created with safe defaults:
- No broker connections
- In-memory storage
- Paper trading mode where applicable

C6 Execution Intelligence — Phase 2, Module 6
"""
from __future__ import annotations

from typing import Any

from iios.execution.oms.integration.constants import ComponentType, FACTORY_SYSTEM_ID


class OMSComponentFactory:
    """
    Creates default OMS component instances for use by OMSIntegrationEngine.

    Components are returned un-started; the engine is responsible for
    calling start() on each component during initialization.
    """

    def create_order_manager(self) -> Any:
        """Create a default OrderManager."""
        from iios.execution.oms.order_manager import OrderManager
        return OrderManager()

    def create_order_book(self) -> Any:
        """Create a default OrderBook."""
        from iios.execution.oms.order_book import OrderBook
        return OrderBook()

    def create_order_router(self) -> Any:
        """Create a default OrderRouter."""
        from iios.execution.oms.order_router import OrderRouter
        return OrderRouter()

    def create_order_queue(self) -> Any:
        """Create a default OrderQueue."""
        from iios.execution.oms.order_queue import OrderQueue
        return OrderQueue()

    def create_persistence_manager(self) -> Any:
        """
        Create a default RepositoryManager backed by an InMemoryOrderRepository.

        The InMemoryOrderRepository is registered after the manager is started.
        """
        from iios.execution.oms.persistence import RepositoryManager
        return RepositoryManager()

    def create_all(self) -> dict[ComponentType, Any]:
        """
        Create all five default OMS components.

        Returns a dict keyed by ComponentType (in dependency order).
        """
        return {
            ComponentType.ORDER_MANAGER: self.create_order_manager(),
            ComponentType.ORDER_BOOK:    self.create_order_book(),
            ComponentType.ORDER_ROUTER:  self.create_order_router(),
            ComponentType.ORDER_QUEUE:   self.create_order_queue(),
            ComponentType.PERSISTENCE:   self.create_persistence_manager(),
        }

    def ensure_default_repository(self, persistence_manager: Any) -> None:
        """
        Register an InMemoryOrderRepository with the persistence manager
        if no repository is registered yet.

        Called by OMSIntegrationManager after all components are started.
        """
        from iios.execution.oms.persistence import (
            InMemoryOrderRepository,
            RepositoryManager,
        )
        if not isinstance(persistence_manager, RepositoryManager):
            return
        registry = persistence_manager._registry
        if registry.count == 0:
            persistence_manager.register_repository(
                InMemoryOrderRepository("oms:default")
            )
