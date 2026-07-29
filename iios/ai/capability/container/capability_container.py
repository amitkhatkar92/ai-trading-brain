"""
capability_container.py -- iios.ai.capability.container
=========================================================
Dependency-injection root for the A9 Enterprise Capability Platform.

A9 Enterprise Capability Platform — Phase 3, Module 9
"""
from __future__ import annotations

from ..connectors.connector_interface  import ConnectorRegistry
from ..engine.capability_executor      import CapabilityExecutor
from ..events.capability_event_bus     import CapabilityEventBus
from ..policy.capability_audit         import CapabilityAuditManager
from ..policy.capability_permission    import CapabilityAuthorization
from ..policy.capability_policy        import CapabilityPolicyEngine
from ..policy.capability_quota         import QuotaManager
from ..registry.capability_registry    import CapabilityRegistry
from ..skills.skill_interface          import SkillRegistry


class CapabilityContainer:
    """
    Dependency-injection root.

    Instantiating this class creates and wires all A9 sub-systems.
    A single instance is owned by the gateway.
    """

    def __init__(self) -> None:
        # Infrastructure
        self._event_bus    = CapabilityEventBus()

        # Domain stores
        self._registry     = CapabilityRegistry()
        self._connectors   = ConnectorRegistry()
        self._skills       = SkillRegistry()

        # Execution
        self._executor     = CapabilityExecutor()

        # Policy & security
        self._authorization = CapabilityAuthorization()
        self._policy_engine = CapabilityPolicyEngine()
        self._quota         = QuotaManager()
        self._audit         = CapabilityAuditManager()

    # ── accessors ─────────────────────────────────────────────────────────────

    @property
    def event_bus(self) -> CapabilityEventBus:
        return self._event_bus

    @property
    def registry(self) -> CapabilityRegistry:
        return self._registry

    @property
    def connectors(self) -> ConnectorRegistry:
        return self._connectors

    @property
    def skills(self) -> SkillRegistry:
        return self._skills

    @property
    def executor(self) -> CapabilityExecutor:
        return self._executor

    @property
    def authorization(self) -> CapabilityAuthorization:
        return self._authorization

    @property
    def policy_engine(self) -> CapabilityPolicyEngine:
        return self._policy_engine

    @property
    def quota(self) -> QuotaManager:
        return self._quota

    @property
    def audit(self) -> CapabilityAuditManager:
        return self._audit
