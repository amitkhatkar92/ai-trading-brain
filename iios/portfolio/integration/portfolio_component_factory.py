"""
portfolio_component_factory.py — iios.portfolio.integration
============================================================
PortfolioComponentFactory — creates and wires all five integrated
portfolio subsystem components.

C10 Portfolio Intelligence — Phase 1, Module 6
"""
from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from .portfolio_component_registry import PortfolioComponentRegistry


class PortfolioComponentFactory:
    """
    Creates all five integrated portfolio subsystem components.

    Components are created with their default configurations unless
    overrides are supplied via a config dict.

    Usage::
        factory = PortfolioComponentFactory()
        registry = factory.create_all()
        # All components are created and registered; start them next.
    """

    # ------------------------------------------------------------------
    # Individual component factories
    # ------------------------------------------------------------------

    @staticmethod
    def create_lifecycle(**kwargs: Any) -> Any:
        """Create a PortfolioLifecycle instance."""
        from iios.portfolio.lifecycle import PortfolioLifecycle
        return PortfolioLifecycle(**kwargs)

    @staticmethod
    def create_engine(**kwargs: Any) -> Any:
        """Create a PortfolioEngine instance."""
        from iios.portfolio.engine import PortfolioEngine
        return PortfolioEngine(**kwargs)

    @staticmethod
    def create_policy(**kwargs: Any) -> Any:
        """Create a PortfolioPolicyEngine instance."""
        from iios.portfolio.policies import PortfolioPolicyEngine
        return PortfolioPolicyEngine(**kwargs)

    @staticmethod
    def create_optimization(**kwargs: Any) -> Any:
        """Create a PortfolioOptimizationEngine instance."""
        from iios.portfolio.optimization import PortfolioOptimizationEngine
        return PortfolioOptimizationEngine(**kwargs)

    @staticmethod
    def create_snapshot_registry(**kwargs: Any) -> Any:
        """Create a PortfolioSnapshotRegistry instance."""
        from iios.portfolio.snapshot import PortfolioSnapshotRegistry
        return PortfolioSnapshotRegistry(**kwargs)

    # ------------------------------------------------------------------
    # Bundled creation
    # ------------------------------------------------------------------

    def create_all(
        self,
        lifecycle_kwargs:    Optional[Dict[str, Any]] = None,
        engine_kwargs:       Optional[Dict[str, Any]] = None,
        policy_kwargs:       Optional[Dict[str, Any]] = None,
        optimization_kwargs: Optional[Dict[str, Any]] = None,
        snapshot_kwargs:     Optional[Dict[str, Any]] = None,
    ) -> PortfolioComponentRegistry:
        """
        Create all five components and register them in a new
        :class:`PortfolioComponentRegistry`.

        Returns
        -------
        PortfolioComponentRegistry
            Pre-populated with all five components.
            Components are NOT started — call ``start_all()`` next.
        """
        registry = PortfolioComponentRegistry()
        registry.register_lifecycle(
            self.create_lifecycle(**(lifecycle_kwargs or {}))
        )
        registry.register_engine(
            self.create_engine(**(engine_kwargs or {}))
        )
        registry.register_policy(
            self.create_policy(**(policy_kwargs or {}))
        )
        registry.register_optimization(
            self.create_optimization(**(optimization_kwargs or {}))
        )
        registry.register_snapshot(
            self.create_snapshot_registry(**(snapshot_kwargs or {}))
        )
        return registry

    # ------------------------------------------------------------------
    # Start / stop helpers
    # ------------------------------------------------------------------

    @staticmethod
    def start_all(registry: PortfolioComponentRegistry) -> None:
        """
        Start all components that support a ``start()`` method.

        Components without a ``start()`` method are silently skipped.
        """
        for comp in (
            registry.get_lifecycle(),
            registry.get_engine(),
            registry.get_policy(),
            registry.get_optimization(),
        ):
            if comp is not None and hasattr(comp, "start"):
                comp.start()
        # SnapshotRegistry has no start() — always available

    @staticmethod
    def stop_all(registry: PortfolioComponentRegistry) -> None:
        """
        Stop all components that support a ``stop()`` method.

        Components without a ``stop()`` method are silently skipped.
        Stops in reverse order to avoid dependency issues.
        """
        for comp in reversed((
            registry.get_lifecycle(),
            registry.get_engine(),
            registry.get_policy(),
            registry.get_optimization(),
        )):
            if comp is not None and hasattr(comp, "stop"):
                try:
                    comp.stop()
                except Exception:
                    pass   # best-effort stop
