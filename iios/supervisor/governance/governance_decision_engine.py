"""
governance_decision_engine.py — iios.supervisor.governance
-----------------------------------------------------------
Final governance decision engine.

Derives the authoritative GovernanceDecision for the current cycle
from all analytical outputs.  Stateless.

C13 AI Supervisor & Autonomous Governance — Phase 1, Module 4
"""
from __future__ import annotations

from .constants import EnterpriseState, GovernanceDecision
from .autonomous_governance_response import (
    AnomalyReport,
    EnterpriseGovernanceReport,
    EnterpriseStateReport,
    IncidentReport,
    SelfHealingPlan,
)


class GovernanceDecisionEngine:
    """
    Stateless governance decision engine.

    Applies a priority-ordered rule set to emit a single GovernanceDecision.

    Priority order (highest to lowest):
    1. Governance report says HALT           → HALT
    2. Enterprise state is EMERGENCY         → HALT
    3. Enterprise state is CRITICAL          → ESCALATE
    4. Governance report says ESCALATE       → ESCALATE
    5. Enterprise state is DEGRADED          → INVESTIGATE
    6. Governance report says INVESTIGATE    → INVESTIGATE
    7. Governance score < compliance pass    → INVESTIGATE
    8. Self-healing plan requires approval   → DEFER
    9. Default                               → CONTINUE
    """

    def decide(
        self,
        governance_report: EnterpriseGovernanceReport,
        enterprise_state:  EnterpriseStateReport,
        anomaly_report:    AnomalyReport,
        incident_report:   IncidentReport,
        self_healing_plan: SelfHealingPlan,
    ) -> GovernanceDecision:
        """
        Derive the final governance decision.

        Returns
        -------
        GovernanceDecision
        """
        if governance_report.governance_decision == GovernanceDecision.HALT:
            return GovernanceDecision.HALT
        if enterprise_state.is_emergency:
            return GovernanceDecision.HALT
        if enterprise_state.is_critical:
            return GovernanceDecision.ESCALATE
        if governance_report.governance_decision == GovernanceDecision.ESCALATE:
            return GovernanceDecision.ESCALATE
        if enterprise_state.enterprise_state == EnterpriseState.DEGRADED:
            return GovernanceDecision.INVESTIGATE
        if governance_report.governance_decision == GovernanceDecision.INVESTIGATE:
            return GovernanceDecision.INVESTIGATE
        if governance_report.governance_score < 0.80:
            return GovernanceDecision.INVESTIGATE
        if self_healing_plan.approval_required > 0:
            return GovernanceDecision.DEFER
        return GovernanceDecision.CONTINUE
