"""
supervisor_component_factory.py — iios.supervisor.integration
--------------------------------------------------------------
Factory that creates and wires all M1-M5 component instances.

Responsibilities
----------------
- Instantiate M1 SupervisorLifecycle
- Instantiate M2 SupervisorEngine
- Instantiate M3 AIGovernancePolicyEngine
- Instantiate M4 AutonomousGovernanceEngine
- Instantiate M5 SupervisorSnapshotFactory
- Populate a SupervisorComponentRegistry with all five components

This module MUST NOT perform AI reasoning, anomaly detection,
governance evaluation, or trade execution.

C13 AI Supervisor & Autonomous Governance — Phase 1, Module 6
"""
from __future__ import annotations

from typing import Any, Optional

from iios.common.logging.logging_manager import get_logger

from .constants import ComponentType
from .supervisor_component_registry import SupervisorComponentRegistry

_log = get_logger(__name__)


class SupervisorComponentFactory:
    """
    Factory that constructs all M1-M5 subsystem instances and registers them.

    All ``create_*`` methods accept no required arguments — each subsystem
    is constructed with safe defaults.  Callers may inject pre-built instances
    for testing or customisation.
    """

    # ------------------------------------------------------------------
    # Individual creators
    # ------------------------------------------------------------------

    def create_lifecycle(self, **kwargs: Any) -> Any:
        """Create and return an M1 SupervisorLifecycle instance."""
        from iios.supervisor.lifecycle.supervisor_lifecycle import SupervisorLifecycle
        return SupervisorLifecycle(**kwargs)

    def create_engine(self, **kwargs: Any) -> Any:
        """Create and return an M2 SupervisorEngine instance."""
        from iios.supervisor.engine.supervisor_engine import SupervisorEngine
        return SupervisorEngine(**kwargs)

    def create_policy_engine(self, **kwargs: Any) -> Any:
        """Create and return an M3 AIGovernancePolicyEngine instance."""
        from iios.supervisor.policies.ai_governance_policy_engine import (
            AIGovernancePolicyEngine,
        )
        return AIGovernancePolicyEngine(**kwargs)

    def create_governance_engine(self, **kwargs: Any) -> Any:
        """Create and return an M4 AutonomousGovernanceEngine instance."""
        from iios.supervisor.governance.autonomous_governance_engine import (
            AutonomousGovernanceEngine,
        )
        return AutonomousGovernanceEngine(**kwargs)

    def create_snapshot_factory(self, **kwargs: Any) -> Any:
        """Create and return an M5 SupervisorSnapshotFactory instance."""
        from iios.supervisor.snapshot.supervisor_snapshot_factory import (
            SupervisorSnapshotFactory,
        )
        return SupervisorSnapshotFactory(**kwargs)

    # ------------------------------------------------------------------
    # All-at-once wiring
    # ------------------------------------------------------------------

    def create_all(
        self,
        registry:          Optional[SupervisorComponentRegistry] = None,
        *,
        lifecycle:         Optional[Any] = None,
        engine:            Optional[Any] = None,
        policy_engine:     Optional[Any] = None,
        governance_engine: Optional[Any] = None,
        snapshot_factory:  Optional[Any] = None,
    ) -> SupervisorComponentRegistry:
        """
        Create all five M1-M5 components (using provided instances or defaults)
        and register them in *registry*.

        Returns the populated registry.
        """
        reg = registry or SupervisorComponentRegistry()

        components = {
            ComponentType.LIFECYCLE:  lifecycle         or self.create_lifecycle(),
            ComponentType.ENGINE:     engine            or self.create_engine(),
            ComponentType.POLICY:     policy_engine     or self.create_policy_engine(),
            ComponentType.GOVERNANCE: governance_engine or self.create_governance_engine(),
            ComponentType.SNAPSHOT:   snapshot_factory  or self.create_snapshot_factory(),
        }

        for comp_type, comp in components.items():
            reg.register(comp_type, comp)
            _log.info(f"SupervisorComponentFactory registered {comp_type.value}")

        return reg
