"""
root_cause_analysis_engine.py — iios.supervisor.governance
-----------------------------------------------------------
Root cause analysis engine.

Assigns a RootCauseCategory to each incident based on its affected
subsystem, severity, and available snapshot context.  Stateless.

C13 AI Supervisor & Autonomous Governance — Phase 1, Module 4
"""
from __future__ import annotations

from typing import List, Tuple

from .constants import IncidentSeverity, RootCauseCategory, SupervisionDomain
from .autonomous_governance_context import AutonomousGovernanceContext
from .autonomous_governance_response import (
    DependencyReport,
    GovernanceIncident,
    IncidentReport,
    RootCause,
    RootCauseReport,
)

# Subsystems with known root-cause categories.
_INFRA_DOMAINS = {SupervisionDomain.PLATFORM_INFRASTRUCTURE.value}
_DATA_DOMAINS  = {
    SupervisionDomain.MARKET_INTELLIGENCE.value,
    SupervisionDomain.RISK_INTELLIGENCE.value,
}
_APP_DOMAINS   = {
    SupervisionDomain.EXECUTION_INTELLIGENCE.value,
    SupervisionDomain.DECISION_INTELLIGENCE.value,
    SupervisionDomain.PORTFOLIO_INTELLIGENCE.value,
    SupervisionDomain.EXECUTION_RECOVERY.value,
    SupervisionDomain.EXECUTION_ANALYTICS.value,
}


class RootCauseAnalysisEngine:
    """
    Stateless root cause analysis engine.

    Applies a rule-based heuristic to classify the root cause of each
    incident.  One RootCause is emitted per incident.
    """

    def analyze(
        self,
        incident_report:   IncidentReport,
        dependency_report: DependencyReport,
        context:           AutonomousGovernanceContext,
    ) -> RootCauseReport:
        """
        Perform root cause analysis on all incidents.

        Parameters
        ----------
        incident_report : IncidentReport
        dependency_report : DependencyReport
        context : AutonomousGovernanceContext

        Returns
        -------
        RootCauseReport
        """
        root_causes: List[RootCause] = []
        for incident in incident_report.incidents:
            rc = self._analyze_incident(incident, dependency_report, context)
            root_causes.append(rc)
        return RootCauseReport.create(tuple(root_causes))

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _analyze_incident(
        self,
        incident:          GovernanceIncident,
        dependency_report: DependencyReport,
        context:           AutonomousGovernanceContext,
    ) -> RootCause:
        affected = set(incident.affected_subsystems)

        # 1. Infrastructure root cause.
        if affected & _INFRA_DOMAINS:
            return RootCause.create(
                incident_id = incident.incident_id,
                category    = RootCauseCategory.INFRASTRUCTURE,
                description = f"Infrastructure issue in: {', '.join(affected & _INFRA_DOMAINS)}",
                confidence  = 0.85,
                evidence    = (f"Affected subsystems: {list(affected)}",),
            )

        # 2. Data / market root cause.
        if affected & _DATA_DOMAINS:
            # Check if market snapshot has data quality indicators.
            mkt = context.market_snapshot
            if mkt.get("data_quality") == "poor" or mkt.get("stale_data"):
                return RootCause.create(
                    incident_id = incident.incident_id,
                    category    = RootCauseCategory.DATA,
                    description = "Poor data quality detected in market/risk snapshot",
                    confidence  = 0.80,
                    evidence    = ("market_snapshot.data_quality=poor",),
                )
            return RootCause.create(
                incident_id = incident.incident_id,
                category    = RootCauseCategory.EXTERNAL,
                description = f"Possible external market/data issue affecting: {', '.join(affected & _DATA_DOMAINS)}",
                confidence  = 0.65,
                evidence    = (f"Affected domains: {list(affected)}",),
            )

        # 3. Application-layer root cause.
        if affected & _APP_DOMAINS:
            # Check if a dependency is unhealthy (cascading failure).
            cascading = self._has_upstream_issue(affected, dependency_report)
            if cascading:
                return RootCause.create(
                    incident_id = incident.incident_id,
                    category    = RootCauseCategory.SOFTWARE,
                    description = f"Possible cascading failure from upstream dependency: {cascading}",
                    confidence  = 0.70,
                    evidence    = (f"Upstream: {cascading}",),
                )
            return RootCause.create(
                incident_id = incident.incident_id,
                category    = RootCauseCategory.SOFTWARE,
                description = f"Application-layer anomaly in: {', '.join(affected & _APP_DOMAINS)}",
                confidence  = 0.60,
                evidence    = (f"Affected subsystems: {list(affected)}",),
            )

        # 4. Unknown.
        return RootCause.create(
            incident_id = incident.incident_id,
            category    = RootCauseCategory.UNKNOWN,
            description = f"Root cause undetermined for incident: {incident.title}",
            confidence  = 0.30,
        )

    @staticmethod
    def _has_upstream_issue(
        affected:          set,
        dependency_report: DependencyReport,
    ) -> str:
        """Return the first critical upstream dependency that is also affected."""
        for dep in dependency_report.dependencies:
            if dep.from_subsystem in affected and dep.to_subsystem in affected:
                return dep.to_subsystem
        return ""
