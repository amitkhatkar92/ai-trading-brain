"""
enterprise_state_engine.py — iios.supervisor.governance
--------------------------------------------------------
Enterprise state assessment engine.

Aggregates platform health, anomaly, and incident data to determine the
overall enterprise operational state.  Stateless.

C13 AI Supervisor & Autonomous Governance — Phase 1, Module 4
"""
from __future__ import annotations

from .constants import (
    GOVERNANCE_STABILITY_PASS,
    HEALTH_CRITICAL_THRESHOLD,
    HEALTH_DEGRADED_THRESHOLD,
    HEALTH_NORMAL_THRESHOLD,
    HEALTH_OPTIMAL_THRESHOLD,
    AnomalySeverity,
    EnterpriseState,
    IncidentSeverity,
    SupervisionStrategyType,
)
from .autonomous_governance_response import (
    AnomalyReport,
    EnterpriseStateReport,
    IncidentReport,
    PlatformHealthReport,
)


class EnterpriseStateEngine:
    """
    Stateless enterprise state assessment engine.

    Decision logic (in order of precedence):
    1. Any CRITICAL anomaly or CRITICAL incident    → CRITICAL / EMERGENCY
    2. Any HIGH anomaly or HIGH incident             → DEGRADED
    3. Platform health < DEGRADED_THRESHOLD          → DEGRADED
    4. Platform health < NORMAL_THRESHOLD            → DEGRADED
    5. Platform health >= OPTIMAL_THRESHOLD          → OPTIMAL
    6. Platform health >= NORMAL_THRESHOLD           → NORMAL
    7. Fallback                                      → UNKNOWN
    """

    def assess(
        self,
        platform_health:  PlatformHealthReport,
        anomaly_report:   AnomalyReport,
        incident_report:  IncidentReport,
    ) -> EnterpriseStateReport:
        """
        Assess the overall enterprise state.

        Parameters
        ----------
        platform_health : PlatformHealthReport
        anomaly_report : AnomalyReport
        incident_report : IncidentReport

        Returns
        -------
        EnterpriseStateReport
        """
        score         = platform_health.overall_score
        n_critical_a  = anomaly_report.critical_count
        n_high_a      = anomaly_report.high_count
        n_critical_i  = incident_report.critical_count
        n_high_i      = incident_report.high_count

        # Determine state.
        if n_critical_a >= 3 or n_critical_i >= 2:
            state      = EnterpriseState.EMERGENCY
            risk_level = "critical"
            rationale  = f"Emergency: {n_critical_a} critical anomalies, {n_critical_i} critical incidents"
        elif n_critical_a >= 1 or n_critical_i >= 1:
            state      = EnterpriseState.CRITICAL
            risk_level = "high"
            rationale  = f"Critical: {n_critical_a} critical anomalies, {n_critical_i} critical incidents"
        elif n_high_a >= 3 or n_high_i >= 2:
            state      = EnterpriseState.DEGRADED
            risk_level = "high"
            rationale  = f"Degraded: {n_high_a} high anomalies, {n_high_i} high incidents"
        elif score < HEALTH_CRITICAL_THRESHOLD:
            state      = EnterpriseState.CRITICAL
            risk_level = "high"
            rationale  = f"Platform health critical: score={score:.2f}"
        elif score < HEALTH_DEGRADED_THRESHOLD or n_high_a >= 1 or n_high_i >= 1:
            state      = EnterpriseState.DEGRADED
            risk_level = "medium"
            rationale  = f"Platform degraded: score={score:.2f}, high_anomalies={n_high_a}"
        elif score < HEALTH_NORMAL_THRESHOLD:
            state      = EnterpriseState.DEGRADED
            risk_level = "medium"
            rationale  = f"Platform below normal: score={score:.2f}"
        elif score >= HEALTH_OPTIMAL_THRESHOLD and not anomaly_report.anomalies:
            state      = EnterpriseState.OPTIMAL
            risk_level = "low"
            rationale  = f"Platform optimal: score={score:.2f}"
        elif score >= HEALTH_NORMAL_THRESHOLD:
            state      = EnterpriseState.NORMAL
            risk_level = "low"
            rationale  = f"Platform normal: score={score:.2f}"
        else:
            state      = EnterpriseState.UNKNOWN
            risk_level = "unknown"
            rationale  = "Unable to determine enterprise state"

        # Derive supervision strategy.
        strategy = self._supervision_strategy(state)

        # Stability = health score adjusted for incident pressure.
        incident_penalty = min(0.4, incident_report.total * 0.05)
        stability = max(0.0, score - incident_penalty)
        availability = score

        return EnterpriseStateReport.create(
            enterprise_state    = state,
            stability_score     = stability,
            availability_score  = availability,
            compliance_score    = 1.0,  # filled later by governance_score_engine
            risk_level          = risk_level,
            active_incidents    = incident_report.total,
            active_anomalies    = anomaly_report.total,
            supervision_strategy = strategy,
            rationale           = rationale,
        )

    @staticmethod
    def _supervision_strategy(state: EnterpriseState) -> SupervisionStrategyType:
        mapping = {
            EnterpriseState.EMERGENCY: SupervisionStrategyType.EMERGENCY,
            EnterpriseState.CRITICAL:  SupervisionStrategyType.INTENSIVE,
            EnterpriseState.DEGRADED:  SupervisionStrategyType.ELEVATED,
            EnterpriseState.NORMAL:    SupervisionStrategyType.STANDARD,
            EnterpriseState.OPTIMAL:   SupervisionStrategyType.REDUCED,
            EnterpriseState.UNKNOWN:   SupervisionStrategyType.STANDARD,
        }
        return mapping.get(state, SupervisionStrategyType.STANDARD)
