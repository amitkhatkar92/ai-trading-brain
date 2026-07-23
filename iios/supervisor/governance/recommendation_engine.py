"""
recommendation_engine.py — iios.supervisor.governance
------------------------------------------------------
Governance recommendation generation engine.

Generates actionable recommendations from enterprise state, anomaly data,
and the self-healing plan.  Stateless.

C13 AI Supervisor & Autonomous Governance — Phase 1, Module 4
"""
from __future__ import annotations

from typing import List

from .constants import (
    EnterpriseState,
    GovernanceDecision,
    RecommendationPriority,
    SupervisionDomain,
)
from .autonomous_governance_response import (
    AnomalyReport,
    EnterpriseGovernanceReport,
    EnterpriseStateReport,
    GovernanceRecommendation,
    GovernanceRecommendations,
    IncidentReport,
    SelfHealingPlan,
)


class RecommendationEngine:
    """
    Stateless governance recommendation engine.

    Generates recommendations based on current enterprise state and the
    outputs of the upstream analytical engines.
    """

    def generate(
        self,
        enterprise_state:    EnterpriseStateReport,
        governance_report:   EnterpriseGovernanceReport,
        anomaly_report:      AnomalyReport,
        incident_report:     IncidentReport,
        self_healing_plan:   SelfHealingPlan,
    ) -> GovernanceRecommendations:
        """
        Generate governance recommendations.

        Parameters
        ----------
        enterprise_state : EnterpriseStateReport
        governance_report : EnterpriseGovernanceReport
        anomaly_report : AnomalyReport
        incident_report : IncidentReport
        self_healing_plan : SelfHealingPlan

        Returns
        -------
        GovernanceRecommendations
        """
        recs: List[GovernanceRecommendation] = []

        # 1. Emergency / critical state → immediate escalation.
        if enterprise_state.is_emergency:
            recs.append(GovernanceRecommendation.create(
                subsystem_id    = "platform",
                title           = "EMERGENCY: Immediate escalation required",
                priority        = RecommendationPriority.CRITICAL,
                description     = enterprise_state.rationale,
                action          = "Halt autonomous operations and escalate to operations team",
                expected_impact = "Prevent further degradation of platform stability",
                confidence      = 0.95,
            ))

        if enterprise_state.is_critical and not enterprise_state.is_emergency:
            recs.append(GovernanceRecommendation.create(
                subsystem_id    = "platform",
                title           = "CRITICAL: Investigate platform issues",
                priority        = RecommendationPriority.CRITICAL,
                description     = f"Enterprise state is CRITICAL: {enterprise_state.rationale}",
                action          = "Trigger intensive monitoring and incident response",
                expected_impact = "Stabilise platform and prevent escalation to EMERGENCY",
                confidence      = 0.90,
            ))

        # 2. Governance violations.
        for violation in governance_report.violations:
            recs.append(GovernanceRecommendation.create(
                subsystem_id    = "governance",
                title           = "Governance policy violation",
                priority        = RecommendationPriority.HIGH,
                description     = violation,
                action          = "Review and remediate governance policy breach",
                expected_impact = "Restore governance compliance",
                confidence      = 0.85,
            ))

        # 3. Per-incident recommendations.
        for incident in incident_report.incidents:
            subsystem = incident.affected_subsystems[0] if incident.affected_subsystems else "platform"
            recs.append(GovernanceRecommendation.create(
                subsystem_id    = subsystem,
                title           = f"Resolve incident: {incident.title}",
                priority        = self._incident_priority(incident),
                description     = incident.description,
                action          = f"Investigate and resolve incident in {subsystem}",
                expected_impact = "Reduce active incident count and improve subsystem health",
                confidence      = 0.75,
            ))

        # 4. Self-healing actions that require approval.
        for action in self_healing_plan.actions:
            if action.requires_approval:
                recs.append(GovernanceRecommendation.create(
                    subsystem_id    = action.subsystem_id,
                    title           = f"Approve self-healing: {action.description[:80]}",
                    priority        = action.priority,
                    description     = f"Self-healing action requires approval: {action.action_type.value}",
                    action          = "Review and approve self-healing action",
                    expected_impact = action.expected_outcome,
                    confidence      = 0.70,
                ))

        # 5. Reduce monitoring if platform is optimal.
        if enterprise_state.enterprise_state == EnterpriseState.OPTIMAL and not anomaly_report.anomalies:
            recs.append(GovernanceRecommendation.create(
                subsystem_id    = "platform",
                title           = "Platform optimal — reduce supervision intensity",
                priority        = RecommendationPriority.INFORMATIONAL,
                description     = f"Platform health score: {enterprise_state.stability_score:.2f}",
                action          = "Consider switching to REDUCED supervision strategy",
                expected_impact = "Reduced computational overhead",
                confidence      = 0.80,
            ))

        # Sort by priority, then confidence descending.
        recs.sort(key=lambda r: (r.priority.value, -r.confidence))
        return GovernanceRecommendations.create(tuple(recs))

    @staticmethod
    def _incident_priority(incident) -> RecommendationPriority:
        from .constants import IncidentSeverity
        mapping = {
            IncidentSeverity.CRITICAL: RecommendationPriority.CRITICAL,
            IncidentSeverity.HIGH:     RecommendationPriority.HIGH,
            IncidentSeverity.MEDIUM:   RecommendationPriority.MEDIUM,
            IncidentSeverity.LOW:      RecommendationPriority.LOW,
            IncidentSeverity.INFO:     RecommendationPriority.INFORMATIONAL,
        }
        return mapping.get(incident.severity, RecommendationPriority.MEDIUM)
