"""
decision_component_factory.py — iios.decision.integration
==========================================================
Creates and configures default M1-M5 component instances for use by
:class:`DecisionIntegrationEngine`.

Callers who wish to inject custom components should do so via
:class:`DecisionComponentRegistry` directly rather than using this factory.

C9 Decision Intelligence — Phase 1, Module 6
"""
from __future__ import annotations

from .constants import ComponentType
from .decision_component_registry import DecisionComponentRegistry


class DecisionComponentFactory:
    """
    Creates a fully-wired :class:`DecisionComponentRegistry` containing
    default instances of M1-M5.

    Usage
    -----
    ::

        factory  = DecisionComponentFactory()
        registry = factory.create_default()
        # registry now holds lifecycle, engine, policy_framework,
        # optimization_framework, snapshot components

    Each component is created in a stopped state.  The integration manager
    calls ``start()`` on each component before allowing requests.
    """

    # ------------------------------------------------------------------
    # Public factory
    # ------------------------------------------------------------------

    def create_default(
        self,
        *,
        include_lifecycle:     bool = True,
        include_engine:        bool = True,
        include_policy:        bool = True,
        include_optimization:  bool = True,
        include_snapshot:      bool = True,
    ) -> DecisionComponentRegistry:
        """
        Instantiate and register default M1-M5 components.

        Parameters
        ----------
        include_lifecycle :    Register a :class:`DecisionLifecycle`.
        include_engine :       Register a :class:`DecisionEngine`
                               (optional — engine is not required for
                               a lifecycle-only integration).
        include_policy :       Register a :class:`DecisionPolicyEngine`.
        include_optimization : Register a :class:`DecisionOptimizationEngine`.
        include_snapshot :     Register snapshot builder + store.

        Returns
        -------
        DecisionComponentRegistry
            Populated registry with all requested components.
        """
        registry = DecisionComponentRegistry()

        if include_lifecycle:
            registry.register(
                ComponentType.LIFECYCLE,
                self._make_lifecycle(),
                description="Decision Lifecycle (M1)",
            )

        if include_engine:
            registry.register(
                ComponentType.ENGINE,
                self._make_engine(),
                is_optional=True,
                description="Decision Engine (M2)",
            )

        if include_policy:
            registry.register(
                ComponentType.POLICY_FRAMEWORK,
                self._make_policy(),
                is_optional=True,
                description="Decision Policy Framework (M3)",
            )

        if include_optimization:
            registry.register(
                ComponentType.OPTIMIZATION_FRAMEWORK,
                self._make_optimization(),
                is_optional=True,
                description="Decision Optimization Framework (M4)",
            )

        if include_snapshot:
            registry.register(
                ComponentType.SNAPSHOT,
                self._make_snapshot_store(),
                description="Decision Snapshot Store (M5)",
            )

        return registry

    # ------------------------------------------------------------------
    # Individual builders
    # ------------------------------------------------------------------

    def _make_lifecycle(self):
        from iios.decision.lifecycle import DecisionLifecycle
        return DecisionLifecycle()

    def _make_engine(self):
        from iios.decision.engine import DecisionEngine
        return DecisionEngine()

    def _make_policy(self):
        from iios.decision.policies import DecisionPolicyEngine
        return DecisionPolicyEngine()

    def _make_optimization(self):
        from iios.decision.optimization import DecisionOptimizationEngine
        return DecisionOptimizationEngine()

    def _make_snapshot_store(self):
        from iios.decision.snapshot import DecisionSnapshotStore
        return DecisionSnapshotStore()
