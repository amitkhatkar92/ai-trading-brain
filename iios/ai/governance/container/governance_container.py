"""
governance_container.py -- iios.ai.governance.container
=========================================================
Dependency-injection root for the A8 AI Governance Platform.

A8 AI Governance Platform — Phase 3, Module 8
"""
from __future__ import annotations

from ..audit.audit_manager           import AuditManager
from ..compliance.compliance         import ComplianceManager
from ..events.governance_event_bus   import GovernanceEventBus
from ..explainability.explainability import ExplainabilityManager
from ..governance.governance_manager import GovernanceManager
from ..permissions.permission_manager import PermissionManager
from ..policy.policy_engine          import PolicyEngine
from ..policy.policy_registry        import PolicyRegistry
from ..risk.risk_governance          import GovernanceRiskManager


class GovernanceContainer:
    """
    Dependency-injection root.

    Instantiating this class creates and wires all A8 sub-systems.
    A single instance is owned by the gateway.
    """

    def __init__(self) -> None:
        # Infrastructure
        self._event_bus     = GovernanceEventBus()

        # Domain managers
        self._policy_registry = PolicyRegistry()
        self._policy_engine   = PolicyEngine(registry=self._policy_registry)
        self._permissions     = PermissionManager()
        self._audit           = AuditManager()
        self._explainability  = ExplainabilityManager()
        self._compliance      = ComplianceManager()
        self._risk            = GovernanceRiskManager()

        # High-level coordinator
        self._governance = GovernanceManager(
            policy_engine          = self._policy_engine,
            permission_manager     = self._permissions,
            audit_manager          = self._audit,
            explainability_manager = self._explainability,
            compliance_manager     = self._compliance,
            risk_manager           = self._risk,
            event_bus              = self._event_bus,
        )

    # ── accessors ─────────────────────────────────────────────────────────────

    @property
    def event_bus(self) -> GovernanceEventBus:
        return self._event_bus

    @property
    def policy_registry(self) -> PolicyRegistry:
        return self._policy_registry

    @property
    def policy_engine(self) -> PolicyEngine:
        return self._policy_engine

    @property
    def permissions(self) -> PermissionManager:
        return self._permissions

    @property
    def audit(self) -> AuditManager:
        return self._audit

    @property
    def explainability(self) -> ExplainabilityManager:
        return self._explainability

    @property
    def compliance(self) -> ComplianceManager:
        return self._compliance

    @property
    def risk(self) -> GovernanceRiskManager:
        return self._risk

    @property
    def governance(self) -> GovernanceManager:
        return self._governance
