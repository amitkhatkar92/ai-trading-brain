"""
supervision_strategy_engine.py — iios.supervisor.governance
------------------------------------------------------------
Supervision strategy selection engine.

Determines the appropriate supervision intensity strategy based on the
current enterprise state and anomaly conditions.  Stateless.

C13 AI Supervisor & Autonomous Governance — Phase 1, Module 4
"""
from __future__ import annotations

from .constants import EnterpriseState, SupervisionStrategyType
from .autonomous_governance_response import (
    AnomalyReport,
    EnterpriseStateReport,
    IncidentReport,
)


class SupervisionStrategyEngine:
    """
    Stateless supervision strategy selection engine.

    Returns a SupervisionStrategyType based on enterprise state,
    anomaly severity, and incident count.
    """

    def select(
        self,
        enterprise_state: EnterpriseStateReport,
        anomaly_report:   AnomalyReport,
        incident_report:  IncidentReport,
    ) -> SupervisionStrategyType:
        """
        Select the supervision strategy for the current cycle.

        Returns
        -------
        SupervisionStrategyType
        """
        state = enterprise_state.enterprise_state

        if state == EnterpriseState.EMERGENCY:
            return SupervisionStrategyType.EMERGENCY
        if state == EnterpriseState.CRITICAL:
            return SupervisionStrategyType.INTENSIVE
        if state == EnterpriseState.DEGRADED or anomaly_report.high_count >= 2:
            return SupervisionStrategyType.ELEVATED
        if state == EnterpriseState.OPTIMAL and not anomaly_report.anomalies:
            return SupervisionStrategyType.REDUCED
        return SupervisionStrategyType.STANDARD

    def describe(self, strategy: SupervisionStrategyType) -> str:
        """Return a human-readable description of the strategy."""
        descriptions = {
            SupervisionStrategyType.EMERGENCY:  "All engines running at maximum frequency; human escalation active",
            SupervisionStrategyType.INTENSIVE:  "High-frequency monitoring; anomaly detection and RCA prioritised",
            SupervisionStrategyType.ELEVATED:   "Above-normal monitoring; faster anomaly detection cycles",
            SupervisionStrategyType.STANDARD:   "Normal monitoring cadence; all engines active",
            SupervisionStrategyType.REDUCED:    "Reduced-frequency monitoring; platform is healthy",
        }
        return descriptions.get(strategy, "Standard monitoring")
