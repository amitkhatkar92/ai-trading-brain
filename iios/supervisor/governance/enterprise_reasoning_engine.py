"""
enterprise_reasoning_engine.py — iios.supervisor.governance
------------------------------------------------------------
Enterprise reasoning engine.

Synthesises a human-readable reasoning summary from all analytical
outputs.  Stateless.

C13 AI Supervisor & Autonomous Governance — Phase 1, Module 4
"""
from __future__ import annotations

from .constants import EnterpriseState, GovernanceDecision, ReasoningMode
from .autonomous_governance_response import (
    AnomalyReport,
    AutonomousGovernanceSummary,
    DependencyReport,
    EnterpriseGovernanceReport,
    EnterpriseStateReport,
    GovernanceRecommendations,
    IncidentReport,
    PlatformHealthReport,
    RootCauseReport,
    SelfHealingPlan,
)


class EnterpriseReasoningEngine:
    """
    Stateless enterprise reasoning engine.

    Produces a structured, deterministic reasoning summary that explains
    what the governance cycle found, why the decision was made, and what
    actions are recommended.
    """

    def reason(
        self,
        platform_health:   PlatformHealthReport,
        anomaly_report:    AnomalyReport,
        incident_report:   IncidentReport,
        root_cause_report: RootCauseReport,
        dependency_report: DependencyReport,
        enterprise_state:  EnterpriseStateReport,
        governance_report: EnterpriseGovernanceReport,
        recommendations:   GovernanceRecommendations,
        self_healing_plan: SelfHealingPlan,
        final_decision:    GovernanceDecision,
        mode:              ReasoningMode = ReasoningMode.COMPOSITE,
    ) -> str:
        """
        Produce a structured reasoning summary string.

        Returns
        -------
        str  — multi-sentence narrative suitable for audit records.
        """
        parts = []

        # 1. Platform health.
        ph_status = platform_health.platform_status.value.upper()
        parts.append(
            f"Platform health is {ph_status} "
            f"(overall_score={platform_health.overall_score:.2f}, "
            f"healthy={platform_health.healthy_count}, "
            f"degraded={platform_health.degraded_count}, "
            f"critical={platform_health.critical_count})."
        )

        # 2. Anomalies and incidents.
        if anomaly_report.total:
            parts.append(
                f"Detected {anomaly_report.total} anomalies "
                f"({anomaly_report.critical_count} critical, "
                f"{anomaly_report.high_count} high)."
            )
        else:
            parts.append("No anomalies detected.")

        if incident_report.total:
            parts.append(
                f"Correlated {incident_report.total} incidents "
                f"({incident_report.critical_count} critical) "
                f"from {incident_report.correlated_from_anomalies} anomalies."
            )

        # 3. Root causes.
        if root_cause_report.total:
            identified = root_cause_report.identified_count
            unknown    = root_cause_report.unknown_count
            parts.append(
                f"Root cause analysis: {identified} causes identified, "
                f"{unknown} unknown."
            )

        # 4. Dependency graph.
        parts.append(
            f"Dependency graph: {dependency_report.total_dependencies} links, "
            f"{dependency_report.critical_dependencies} critical, "
            f"{len(dependency_report.critical_paths)} critical path(s)."
        )

        # 5. Enterprise state.
        parts.append(
            f"Enterprise state: {enterprise_state.enterprise_state.value.upper()} "
            f"(stability={enterprise_state.stability_score:.2f}, "
            f"risk_level={enterprise_state.risk_level})."
        )

        # 6. Governance compliance.
        parts.append(
            f"Governance compliance score: {governance_report.compliance_score:.2f} "
            f"(policy_adherence={governance_report.policy_adherence_score:.2f})."
        )
        if governance_report.violations:
            parts.append(f"Violations: {'; '.join(governance_report.violations[:3])}.")

        # 7. Recommendations and self-healing.
        if recommendations.total:
            parts.append(
                f"Generated {recommendations.total} recommendations "
                f"({recommendations.critical_count} critical, "
                f"{recommendations.high_count} high)."
            )
        if self_healing_plan.total:
            parts.append(
                f"Self-healing plan: {self_healing_plan.total} action(s), "
                f"{self_healing_plan.automated_actions} automated."
            )

        # 8. Final decision.
        parts.append(
            f"Final governance decision: {final_decision.value.upper()}."
        )

        return " ".join(parts)
