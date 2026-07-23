"""
agent_orchestration_engine.py — iios.supervisor.governance
-----------------------------------------------------------
Agent orchestration engine.

Determines which analytical engines to activate for a given governance
cycle based on available snapshot data and the requested supervision
domains.  Stateless.

C13 AI Supervisor & Autonomous Governance — Phase 1, Module 4
"""
from __future__ import annotations

from typing import Dict, List, Set

from .constants import GovernanceCapability, SupervisionDomain
from .autonomous_governance_context import AutonomousGovernanceContext
from .autonomous_governance_request import AutonomousGovernanceRequest


class AgentOrchestrationEngine:
    """
    Stateless agent orchestration engine.

    Produces an orchestration plan: an ordered list of
    GovernanceCapability values indicating which analytical engines
    should run for the current supervision cycle.
    """

    # Capabilities always active.
    _ALWAYS_ACTIVE: List[GovernanceCapability] = [
        GovernanceCapability.PLATFORM_HEALTH_ASSESSMENT,
        GovernanceCapability.DEPENDENCY_ANALYSIS,
        GovernanceCapability.ANOMALY_DETECTION,
        GovernanceCapability.ENTERPRISE_STATE_ASSESSMENT,
        GovernanceCapability.AUTONOMOUS_SUPERVISION,
    ]

    # Capabilities activated when anomalies are expected (any snapshot present).
    _CONDITIONAL: List[GovernanceCapability] = [
        GovernanceCapability.INCIDENT_CORRELATION,
        GovernanceCapability.ROOT_CAUSE_ANALYSIS,
        GovernanceCapability.SELF_HEALING_RECOMMENDATIONS,
        GovernanceCapability.GOVERNANCE_RECOMMENDATIONS,
        GovernanceCapability.OPERATIONAL_INTELLIGENCE,
    ]

    # Capabilities activated only for enterprise-wide supervision.
    _ENTERPRISE_ONLY: List[GovernanceCapability] = [
        GovernanceCapability.CROSS_SUBSYSTEM_COORDINATION,
        GovernanceCapability.ENTERPRISE_REASONING,
    ]

    def orchestrate(self, request: AutonomousGovernanceRequest) -> List[GovernanceCapability]:
        """
        Return the ordered list of capabilities to activate.

        Parameters
        ----------
        request : AutonomousGovernanceRequest

        Returns
        -------
        List[GovernanceCapability]
        """
        active: List[GovernanceCapability] = list(self._ALWAYS_ACTIVE)

        # Activate conditional capabilities if any non-empty snapshot is present.
        ctx = request.context
        has_data = bool(
            ctx.execution_snapshot or ctx.risk_snapshot or ctx.market_snapshot
            or ctx.decision_snapshot or ctx.portfolio_snapshot
        )
        if has_data:
            active.extend(self._CONDITIONAL)

        # Activate enterprise-only capabilities if ENTERPRISE domain is in scope.
        if SupervisionDomain.ENTERPRISE in request.domains:
            active.extend(self._ENTERPRISE_ONLY)
        elif len(request.domains) >= 5:
            active.extend(self._ENTERPRISE_ONLY)

        # Deduplicate while preserving order.
        seen: Set[GovernanceCapability] = set()
        ordered: List[GovernanceCapability] = []
        for cap in active:
            if cap not in seen:
                seen.add(cap)
                ordered.append(cap)

        return ordered

    def describe_plan(self, capabilities: List[GovernanceCapability]) -> Dict[str, str]:
        """Return a description dict for the orchestration plan."""
        return {cap.value: f"Activate {cap.value.replace('_', ' ')}" for cap in capabilities}
