"""
governance_manager.py -- iios.ai.governance.governance
========================================================
:class:`GovernanceManager` — high-level coordinator that integrates the Policy
Engine, PermissionManager, AuditManager, ExplainabilityManager,
ComplianceManager, and GovernanceRiskManager into a single
:meth:`evaluate` method.

A8 AI Governance Platform — Phase 3, Module 8
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from ..audit.audit_manager          import AuditManager
from ..audit.audit_record           import AuditEventType
from ..compliance.compliance        import ComplianceFramework, ComplianceManager, ComplianceReport
from ..core.governance_context      import GovernanceContext
from ..core.governance_decision     import GovernanceDecision
from ..core.governance_metadata     import GovernanceDomain, GovernanceMetadata, GovernanceSeverity
from ..events.governance_event_bus  import GovernanceEventBus
from ..events.governance_events     import (
    AuditRecordedEvent,
    GovernanceDecisionIssuedEvent,
    PolicyViolatedEvent,
)
from ..explainability.explainability import Explanation, ExplainabilityManager
from ..permissions.permission_manager import PermissionManager
from ..policy.policy_engine          import PolicyEngine
from ..risk.risk_governance          import GovernanceRiskManager, RiskViolation


class GovernanceManager:
    """
    High-level governance coordinator.

    Wires Policy → Permission → Audit → Explainability → Compliance → Risk
    in a single :meth:`evaluate` call.
    """

    def __init__(
        self,
        policy_engine:         PolicyEngine,
        permission_manager:    PermissionManager,
        audit_manager:         AuditManager,
        explainability_manager: ExplainabilityManager,
        compliance_manager:    ComplianceManager,
        risk_manager:          GovernanceRiskManager,
        event_bus:             GovernanceEventBus,
    ) -> None:
        self._policy      = policy_engine
        self._permissions = permission_manager
        self._audit       = audit_manager
        self._explain     = explainability_manager
        self._compliance  = compliance_manager
        self._risk        = risk_manager
        self._bus         = event_bus

    # ── core evaluation ───────────────────────────────────────────────────────

    def evaluate(
        self,
        context:      GovernanceContext,
        risk_context: Optional[Dict[str, float]] = None,
        explain:      bool                       = True,
    ) -> GovernanceDecision:
        """
        Full governance evaluation pipeline.

        1. Policy evaluation
        2. Risk assessment (if risk_context provided)
        3. Audit recording
        4. Explanation generation (if explain=True)

        :returns: :class:`GovernanceDecision`.
        """
        # Step 1 — policy evaluation
        decision = self._policy.evaluate(context)

        # Step 2 — risk assessment (elevates decision to ESCALATE if risk exceeded)
        if risk_context and not decision.is_denied():
            violations = self._risk.evaluate(context.principal_id, risk_context)
            if violations:
                critical_vs = [v for v in violations
                               if v.severity in (GovernanceSeverity.HIGH, GovernanceSeverity.CRITICAL)]
                if critical_vs:
                    decision = GovernanceDecision.escalate(
                        context    = context,
                        rationale  = f"Risk thresholds exceeded: {[v.threshold_name for v in critical_vs]}",
                        decided_by = "risk_engine",
                    )

        # Step 3 — audit
        outcome  = decision.decision_type.value
        audit_rec = self._audit.record(
            event_type   = AuditEventType.DECISION_ISSUED,
            subject_id   = context.principal_id,
            principal_id = context.principal_id,
            action       = context.action,
            resource     = context.resource,
            outcome      = outcome,
        )
        self._bus.publish(
            AuditRecordedEvent.create(
                "governance_manager", audit_rec.record_id,
                context.principal_id, context.action
            )
        )
        self._bus.publish(
            GovernanceDecisionIssuedEvent.create(
                "governance_manager", decision.decision_id,
                decision.decision_type.value, context.principal_id
            )
        )
        if decision.is_denied():
            self._bus.publish(
                PolicyViolatedEvent.create(
                    "governance_manager",
                    next(iter(decision.policy_ids), "unknown"),
                    context.principal_id,
                    context.action,
                )
            )

        # Step 4 — explanation
        if explain:
            self._explain.generate_and_store(decision, context.principal_id)

        return decision

    # ── permission shortcut ───────────────────────────────────────────────────

    def authorize(self, principal_id: str, capability: str) -> None:
        """Convenience wrapper — raises AIPermissionDeniedError if not authorized."""
        self._permissions.authorize(principal_id, capability)

    def is_authorized(self, principal_id: str, capability: str) -> bool:
        return self._permissions.is_authorized(principal_id, capability)

    # ── compliance shortcut ───────────────────────────────────────────────────

    def check_compliance(
        self,
        subject_id: str,
        subject:    Any,
        framework:  Optional[ComplianceFramework] = None,
    ) -> ComplianceReport:
        return self._compliance.check(subject_id, subject, framework)
