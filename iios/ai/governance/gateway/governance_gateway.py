"""
governance_gateway.py -- iios.ai.governance.gateway
=====================================================
:class:`GovernanceGateway` — single public entry point for the A8
AI Governance Platform.

A8 AI Governance Platform — Phase 3, Module 8
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from ..audit.audit_manager             import AuditReport
from ..audit.audit_record              import AuditEventType, AuditRecord
from ..compliance.compliance           import ComplianceFramework, ComplianceReport, ComplianceRule
from ..container.governance_container  import GovernanceContainer
from ..core.governance_context         import GovernanceContext
from ..core.governance_decision        import GovernanceDecision
from ..core.governance_metadata        import GovernanceDomain, GovernanceSeverity
from ..core.governance_policy          import GovernancePolicy, PolicyEffect, PolicyScope
from ..exceptions.governance_exceptions import AIGovernanceException
from ..explainability.explainability    import Explanation
from ..lifecycle                        import AILifecycleAwareMixin
from ..permissions.access_control       import CapabilityRestriction, RolePolicy
from ..policy.policy_rule               import PolicyViolation
from ..risk.risk_governance             import RiskPolicy, RiskViolation
from ..snapshot.governance_snapshot     import GovernanceFrameworkSnapshot

SYSTEM_ID = "iios:ai:governance:gateway"
VERSION   = "1.0.0"


class GovernanceGateway(AILifecycleAwareMixin):
    """
    Single public entry point for the A8 AI Governance Platform.

    Usage::

        gw = GovernanceGateway()
        gw.start()

        context  = GovernanceContext.create("model.invoke", "model_abc", "agent_x")
        decision = gw.evaluate_policy(context)

        gw.record_audit(...)
        explanation = gw.generate_explanation(decision, "agent_x")

        gw.stop()
    """

    SYSTEM_ID: str = SYSTEM_ID
    VERSION:   str = VERSION

    def __init__(self) -> None:
        super().__init__()
        self._container: Optional[GovernanceContainer] = None

    # ── lifecycle ─────────────────────────────────────────────────────────────

    def _on_start(self) -> None:
        self._container = GovernanceContainer()

    def _on_stop(self) -> None:
        self._container = None

    @property
    def _c(self) -> GovernanceContainer:
        if self._container is None:
            raise AIGovernanceException(
                "[AI-1300] GovernanceGateway is not running — call start() first"
            )
        return self._container

    # ── TASK 1: Policy evaluation ─────────────────────────────────────────────

    def evaluate_policy(
        self,
        context:      GovernanceContext,
        risk_context: Optional[Dict[str, float]] = None,
        explain:      bool                       = True,
    ) -> GovernanceDecision:
        """Full governance evaluation: policy + risk + audit + explanation."""
        return self._c.governance.evaluate(context, risk_context, explain)

    def register_policy(self, policy: GovernancePolicy) -> None:
        self._c.policy_registry.register(policy)

    def deregister_policy(self, policy_id: str) -> None:
        self._c.policy_registry.deregister(policy_id)

    def list_policies(self) -> List[GovernancePolicy]:
        return self._c.policy_registry.list_policies(active_only=False)

    def list_violations(self, limit: int = 100) -> List[PolicyViolation]:
        return self._c.policy_engine.violations(limit)

    # ── TASK 2: Direct policy evaluation (policy engine only) ─────────────────

    def evaluate_policy_only(self, context: GovernanceContext) -> GovernanceDecision:
        """Evaluate policies without risk/audit/explanation side-effects."""
        return self._c.policy_engine.evaluate(context)

    # ── TASK 3: Permissions ────────────────────────────────────────────────────

    def authorize(self, principal_id: str, capability: str) -> None:
        """Raise AIPermissionDeniedError if not authorized."""
        self._c.permissions.authorize(principal_id, capability)

    def is_authorized(self, principal_id: str, capability: str) -> bool:
        return self._c.permissions.is_authorized(principal_id, capability)

    def assign_role(self, principal_id: str, role_name: str) -> None:
        self._c.permissions.assign_role(principal_id, role_name)

    def revoke_role(self, principal_id: str, role_name: str) -> None:
        self._c.permissions.revoke_role(principal_id, role_name)

    def create_role(self, role: RolePolicy) -> None:
        self._c.permissions.create_role(role)

    def list_roles(self) -> List[RolePolicy]:
        return self._c.permissions.list_roles()

    def add_restriction(self, restriction: CapabilityRestriction) -> None:
        self._c.permissions.add_restriction(restriction)

    # ── TASK 4: Audit ─────────────────────────────────────────────────────────

    def record_audit(
        self,
        event_type:   AuditEventType,
        subject_id:   str,
        principal_id: str,
        action:       str,
        resource:     str,
        outcome:      str,
        notes:        str = "",
        **context: Any,
    ) -> AuditRecord:
        return self._c.audit.record(
            event_type, subject_id, principal_id, action, resource, outcome, notes, **context
        )

    def query_audit(
        self,
        subject_id: Optional[str] = None,
        event_type: Optional[AuditEventType] = None,
        since:      Optional[float] = None,
        limit:      int = 500,
    ) -> List[AuditRecord]:
        return self._c.audit.query(subject_id, event_type, since, limit)

    def generate_audit_report(self, subject_id: str) -> AuditReport:
        return self._c.audit.generate_report(subject_id)

    def verify_audit_integrity(self) -> bool:
        return self._c.audit.verify_chain_integrity()

    # ── TASK 5: Explainability ────────────────────────────────────────────────

    def generate_explanation(
        self,
        decision:   GovernanceDecision,
        subject_id: str,
        **kwargs: Any,
    ) -> Explanation:
        return self._c.explainability.generate_and_store(decision, subject_id, **kwargs)

    def get_explanation(self, explanation_id: str) -> Explanation:
        return self._c.explainability.get(explanation_id)

    def explanations_for_decision(self, decision_id: str) -> List[Explanation]:
        return self._c.explainability.for_decision(decision_id)

    # ── TASK 6: Compliance ────────────────────────────────────────────────────

    def check_compliance(
        self,
        subject_id: str,
        subject:    Any,
        framework:  Optional[ComplianceFramework] = None,
        raise_on_blocking: bool = False,
    ) -> ComplianceReport:
        return self._c.compliance.check(subject_id, subject, framework, raise_on_blocking)

    def add_compliance_rule(self, rule: ComplianceRule) -> None:
        self._c.compliance.add_rule(rule)

    def list_compliance_rules(self) -> List[ComplianceRule]:
        return self._c.compliance.list_rules()

    # ── TASK 7: Risk governance ───────────────────────────────────────────────

    def add_risk_policy(self, policy: RiskPolicy) -> None:
        self._c.risk.add_policy(policy)

    def evaluate_risk(
        self,
        subject_id:   str,
        risk_context: Dict[str, float],
        raise_on_exceed: bool = False,
    ) -> List[RiskViolation]:
        return self._c.risk.evaluate(subject_id, risk_context, raise_on_exceed)

    def list_risk_violations(self, subject_id: Optional[str] = None) -> List[RiskViolation]:
        return self._c.risk.violations(subject_id)

    # ── Introspection ─────────────────────────────────────────────────────────

    def health(self) -> Dict[str, Any]:
        c = self._c
        return {
            "is_running":             self.is_ai_running,
            "total_policies":         c.policy_registry.count(),
            "active_policies":        len(c.policy_registry.list_policies(active_only=True)),
            "total_audit_records":    c.audit.total_count(),
            "total_explanations":     c.explainability.total_count(),
            "total_risk_violations":  c.risk.violation_count(),
            "total_roles":            len(c.permissions.list_roles()),
            "compliance_rules":       c.compliance.rule_count(),
            "policy_violations":      c.policy_engine.violation_count(),
            "system_id":              SYSTEM_ID,
            "version":                VERSION,
        }

    def status(self) -> Dict[str, Any]:
        return self.health()

    def snapshot(self) -> GovernanceFrameworkSnapshot:
        c = self._c
        return GovernanceFrameworkSnapshot.build(
            is_running             = self.is_ai_running,
            total_policies         = c.policy_registry.count(),
            active_policies        = len(c.policy_registry.list_policies(active_only=True)),
            total_audit_records    = c.audit.total_count(),
            total_explanations     = c.explainability.total_count(),
            total_risk_violations  = c.risk.violation_count(),
            total_roles            = len(c.permissions.list_roles()),
            compliance_rules       = c.compliance.rule_count(),
        )
