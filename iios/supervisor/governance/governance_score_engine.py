"""
governance_score_engine.py — iios.supervisor.governance
--------------------------------------------------------
Governance compliance scoring engine.

Computes governance_score, compliance_score, policy_adherence_score and
GovernanceDecision from the policy response action and enterprise state.
Stateless.

C13 AI Supervisor & Autonomous Governance — Phase 1, Module 4
"""
from __future__ import annotations

from typing import List, Tuple

from .constants import (
    GOVERNANCE_COMPLIANCE_PASS,
    EnterpriseState,
    GovernanceDecision,
)
from .autonomous_governance_context import AutonomousGovernanceContext
from .autonomous_governance_response import (
    EnterpriseGovernanceReport,
    EnterpriseStateReport,
)


# Policy response actions that indicate compliance problems.
_DENY_ACTIONS      = frozenset({"reject", "block", "emergency_stop"})
_ESCALATE_ACTIONS  = frozenset({"escalate", "require_human_approval", "require_manual_review"})


class GovernanceScoreEngine:
    """
    Stateless governance scoring engine.

    Derives compliance metrics from the approved policy action (stored in
    the context's governance_policy_response dict) and the enterprise state.
    """

    def score(
        self,
        context:          AutonomousGovernanceContext,
        enterprise_state: EnterpriseStateReport,
    ) -> EnterpriseGovernanceReport:
        """
        Compute governance compliance scores and decision.

        Parameters
        ----------
        context : AutonomousGovernanceContext
        enterprise_state : EnterpriseStateReport

        Returns
        -------
        EnterpriseGovernanceReport
        """
        gpr = context.governance_policy_response
        policy_action = ""
        if gpr:
            policy_action = str(gpr.get("final_action", "approve")).lower()

        violations: List[str] = []
        notes:      List[str] = []

        # Policy adherence.
        if policy_action in _DENY_ACTIONS:
            policy_adherence = 0.0
            violations.append(f"Governance policy action is {policy_action!r}")
        elif policy_action in _ESCALATE_ACTIONS:
            policy_adherence = 0.5
            notes.append(f"Governance policy requires escalation: {policy_action!r}")
        else:
            policy_adherence = 1.0

        # Enterprise state penalty.
        if enterprise_state.enterprise_state in (EnterpriseState.EMERGENCY, EnterpriseState.CRITICAL):
            state_penalty = 0.40
            violations.append(f"Enterprise state is {enterprise_state.enterprise_state.value}")
        elif enterprise_state.enterprise_state == EnterpriseState.DEGRADED:
            state_penalty = 0.20
        else:
            state_penalty = 0.0

        compliance_score = max(0.0, (policy_adherence - state_penalty))
        governance_score = (compliance_score + policy_adherence) / 2.0

        decision = self._decide(compliance_score, policy_action, enterprise_state)

        return EnterpriseGovernanceReport.create(
            compliance_score       = compliance_score,
            governance_decision    = decision,
            policy_adherence_score = policy_adherence,
            governance_score       = governance_score,
            violations             = tuple(violations),
            compliance_notes       = tuple(notes),
        )

    # ------------------------------------------------------------------

    @staticmethod
    def _decide(
        compliance_score: float,
        policy_action:    str,
        state:            EnterpriseStateReport,
    ) -> GovernanceDecision:
        if policy_action == "emergency_stop" or state.enterprise_state == EnterpriseState.EMERGENCY:
            return GovernanceDecision.HALT
        if policy_action in _DENY_ACTIONS:
            return GovernanceDecision.HALT
        if policy_action in _ESCALATE_ACTIONS or state.enterprise_state == EnterpriseState.CRITICAL:
            return GovernanceDecision.ESCALATE
        if state.enterprise_state == EnterpriseState.DEGRADED:
            return GovernanceDecision.INVESTIGATE
        if compliance_score < GOVERNANCE_COMPLIANCE_PASS:
            return GovernanceDecision.INVESTIGATE
        return GovernanceDecision.CONTINUE
