"""
incident_analysis_engine.py — iios.supervisor.governance
---------------------------------------------------------
Incident correlation engine.

Groups detected anomalies into incidents by subsystem and severity.
Stateless.

C13 AI Supervisor & Autonomous Governance — Phase 1, Module 4
"""
from __future__ import annotations

from collections import defaultdict
from typing import Dict, List, Tuple

from .constants import AnomalySeverity, IncidentSeverity
from .autonomous_governance_response import (
    AnomalyReport,
    GovernanceAnomaly,
    GovernanceIncident,
    IncidentReport,
)


_SEVERITY_MAP = {
    AnomalySeverity.CRITICAL: IncidentSeverity.CRITICAL,
    AnomalySeverity.HIGH:     IncidentSeverity.HIGH,
    AnomalySeverity.MEDIUM:   IncidentSeverity.MEDIUM,
    AnomalySeverity.LOW:      IncidentSeverity.LOW,
    AnomalySeverity.INFO:     IncidentSeverity.INFO,
}


class IncidentAnalysisEngine:
    """
    Stateless incident correlation engine.

    Grouping strategy:
    1. Anomalies within the same subsystem are merged into a single incident.
    2. The incident severity equals the maximum anomaly severity in the group.
    """

    def correlate(self, anomaly_report: AnomalyReport) -> IncidentReport:
        """
        Correlate anomalies into incidents.

        Parameters
        ----------
        anomaly_report : AnomalyReport

        Returns
        -------
        IncidentReport
        """
        if not anomaly_report.anomalies:
            return IncidentReport.create((), correlated_from_anomalies=0)

        # Group anomalies by subsystem.
        groups: Dict[str, List[GovernanceAnomaly]] = defaultdict(list)
        for anomaly in anomaly_report.anomalies:
            groups[anomaly.subsystem_id].append(anomaly)

        from .constants import INCIDENT_SEVERITY_ORDER
        incidents: List[GovernanceIncident] = []
        for subsystem_id, group in groups.items():
            max_severity = max(
                group,
                key=lambda a: INCIDENT_SEVERITY_ORDER.get(
                    _SEVERITY_MAP[a.severity].value, 0
                ),
            )
            inc_severity = _SEVERITY_MAP[max_severity.severity]
            descriptions = "; ".join(
                a.description for a in group if a.description
            )[:200]
            incident = GovernanceIncident.create(
                title               = f"{subsystem_id} — {len(group)} anomaly(s) detected",
                anomaly_ids         = tuple(a.anomaly_id for a in group),
                affected_subsystems = (subsystem_id,),
                severity            = inc_severity,
                description         = descriptions,
            )
            incidents.append(incident)

        return IncidentReport.create(
            tuple(incidents),
            correlated_from_anomalies=len(anomaly_report.anomalies),
        )
