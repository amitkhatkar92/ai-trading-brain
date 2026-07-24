"""
supervisor_snapshot_factory.py — iios.supervisor.snapshot
-----------------------------------------------------------
Factory for creating SupervisorSnapshot instances.

Provides:
  - Builder access
  - Integration helper for building from M4 governance summaries
  - Ready-made test scenarios (healthy, emergency, degraded)

C13 AI Supervisor & Autonomous Governance — Phase 1, Module 5
"""
from __future__ import annotations

import uuid
from typing import Any, Optional

from .constants import (
    PLATFORM_DEPENDENCIES,
    PLATFORM_VERSION,
    VERSION,
    AutomationReadiness,
    GovernanceStatus,
    OperationalStatus,
    PlatformStatus,
    SnapshotEnterpriseState,
    SnapshotGovernanceState,
    SnapshotLifecycleState,
    SnapshotStatus,
    SubsystemSummaryStatus,
    SupervisorScope,
    SupervisorType,
)
from .supervisor_snapshot import (
    AnomalySummary,
    AuditSummary,
    DependencySummary,
    EnterpriseSummary,
    GovernanceSummary,
    SelfHealingSummary,
    SnapshotStatistics,
    SubsystemSummaryItem,
    SubsystemsSummary,
    SupervisionSummary,
    SupervisorSnapshot,
)
from .supervisor_snapshot_builder import SupervisorSnapshotBuilder
from .supervisor_snapshot_metadata import SupervisorSnapshotMetadata


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _uniform_subsystems(
    status:       SubsystemSummaryStatus,
    health_score: float,
    issues:       tuple = (),
) -> SubsystemsSummary:
    _mk = lambda sid: SubsystemSummaryItem.create(  # noqa: E731
        sid, status=status, health_score=health_score, issues=issues
    )
    return SubsystemsSummary(
        execution_intelligence = _mk("execution_intelligence"),
        execution_recovery     = _mk("execution_recovery"),
        execution_analytics    = _mk("execution_analytics"),
        decision_intelligence  = _mk("decision_intelligence"),
        portfolio_intelligence = _mk("portfolio_intelligence"),
        risk_intelligence      = _mk("risk_intelligence"),
        market_intelligence    = _mk("market_intelligence"),
        infrastructure         = _mk("infrastructure"),
        enterprise_modules     = _mk("enterprise_modules"),
    )


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

class SupervisorSnapshotFactory:
    """
    Factory for creating SupervisorSnapshot instances.

    All created snapshots are immutable and frozen.
    No governance evaluation, reasoning, or execution occurs here.
    """

    # ------------------------------------------------------------------
    # Builder access
    # ------------------------------------------------------------------

    def create_builder(
        self,
        session_id:  str,
        workflow_id: str = "",
        **kwargs,
    ) -> SupervisorSnapshotBuilder:
        """Return a pre-configured builder."""
        return SupervisorSnapshotBuilder(session_id, workflow_id, **kwargs)

    # ------------------------------------------------------------------
    # Core factory methods
    # ------------------------------------------------------------------

    def create_minimal(
        self,
        session_id:  str = "",
        workflow_id: str = "",
    ) -> SupervisorSnapshot:
        """Create a minimal valid snapshot with all-default sections."""
        sid = session_id or str(uuid.uuid4())
        return (
            SupervisorSnapshotBuilder(sid, workflow_id)
            .with_status(SnapshotStatus.VALID)
            .with_lifecycle_state(SnapshotLifecycleState.RUNNING)
            .with_governance_state(SnapshotGovernanceState.ACTIVE)
            .with_enterprise_state(SnapshotEnterpriseState.UNKNOWN)
            .with_governance_summary(GovernanceSummary.create(governance_decision="continue"))
            .build()
        )

    def create_from_components(
        self,
        session_id:         str,
        workflow_id:        str   = "",
        *,
        enterprise_state:   SnapshotEnterpriseState = SnapshotEnterpriseState.NORMAL,
        governance_decision: str                    = "continue",
        platform_health:    float                   = 0.85,
        anomaly_count:      int                     = 0,
        incident_count:     int                     = 0,
        environment:        str                     = "production",
        metadata:           Optional[SupervisorSnapshotMetadata] = None,
    ) -> SupervisorSnapshot:
        """Create a snapshot from explicit component values."""
        gov_status  = (
            GovernanceStatus.COMPLIANT
            if governance_decision == "continue"
            else GovernanceStatus.NON_COMPLIANT
        )
        op_status   = (
            OperationalStatus.OPERATIONAL
            if platform_health >= 0.70
            else OperationalStatus.DEGRADED
        )
        plat_status = (
            PlatformStatus.HEALTHY
            if platform_health >= 0.70
            else PlatformStatus.DEGRADED
        )
        return (
            SupervisorSnapshotBuilder(session_id, workflow_id, environment=environment)
            .with_status(SnapshotStatus.PUBLISHED)
            .with_lifecycle_state(SnapshotLifecycleState.RUNNING)
            .with_governance_state(SnapshotGovernanceState.ACTIVE)
            .with_enterprise_state(enterprise_state)
            .with_enterprise_summary(EnterpriseSummary.create(
                enterprise_health          = platform_health,
                platform_status            = plat_status,
                operational_status         = op_status,
                governance_status          = gov_status,
                enterprise_stability_score = platform_health * 0.9,
                enterprise_confidence      = platform_health * 0.85,
                overall_supervisor_score   = platform_health * 0.88,
            ))
            .with_governance_summary(GovernanceSummary.create(
                governance_decision = governance_decision,
                policy_outcome      = f"policy_{governance_decision}",
            ))
            .with_supervision_summary(SupervisionSummary.create(
                supervision_status = op_status,
                platform_health    = platform_health,
                active_alerts      = anomaly_count,
            ))
            .with_anomaly_summary(AnomalySummary.create(
                detected_anomalies    = anomaly_count,
                incident_correlations = incident_count,
            ))
            .with_metadata(metadata or SupervisorSnapshotMetadata.create(environment=environment))
            .build()
        )

    def create_from_governance_summary(
        self,
        session_id:  str,
        workflow_id: str,
        summary:     Any,   # AutonomousGovernanceSummary from M4 (duck-typed)
        *,
        environment: str                                       = "production",
        metadata:    Optional[SupervisorSnapshotMetadata]      = None,
    ) -> SupervisorSnapshot:
        """
        Build a SupervisorSnapshot from an M4 AutonomousGovernanceSummary.

        Accesses M4 attributes via duck-typing to avoid circular imports.
        The snapshot is PURELY a consolidation of the summary — no
        governance evaluation or reasoning is performed.
        """
        # --- Enterprise state
        es_report   = getattr(summary, "enterprise_state", None)
        es_enum     = getattr(es_report, "enterprise_state", None)
        es_str      = getattr(es_enum, "value", "unknown") if es_enum else "unknown"
        _es_map     = {
            "optimal":   SnapshotEnterpriseState.OPTIMAL,
            "normal":    SnapshotEnterpriseState.NORMAL,
            "degraded":  SnapshotEnterpriseState.DEGRADED,
            "critical":  SnapshotEnterpriseState.CRITICAL,
            "emergency": SnapshotEnterpriseState.EMERGENCY,
        }
        enterprise_state = _es_map.get(es_str, SnapshotEnterpriseState.UNKNOWN)

        # --- Governance decision
        dec_obj     = getattr(summary, "final_decision", None)
        gov_decision = getattr(dec_obj, "value", "unknown") if dec_obj else "unknown"

        # --- Platform health
        ph_report  = getattr(summary, "platform_health", None)
        ph_score   = float(getattr(ph_report, "overall_score", 0.7) or 0.7)
        ph_score   = max(0.0, min(1.0, ph_score))

        # --- Anomaly info
        ar           = getattr(summary, "anomaly_report", None)
        anomaly_count = int(getattr(ar, "total", 0) or 0)
        crit_count   = int(getattr(ar, "critical_count", 0) or 0)
        high_count   = int(getattr(ar, "high_count", 0) or 0)
        med_count    = int(getattr(ar, "medium_count", 0) or 0)
        sev_dist     = {"critical": crit_count, "high": high_count, "medium": med_count}
        anomalies_list = getattr(ar, "anomalies", ()) or ()
        affected_subs = tuple(set(
            getattr(a, "subsystem_id", "") for a in anomalies_list
            if getattr(a, "subsystem_id", "")
        ))

        # --- Incident info
        ir            = getattr(summary, "incident_report", None)
        incident_count = int(getattr(ir, "total", 0) or 0)

        # --- Dependency info
        dr        = getattr(summary, "dependency_report", None)
        dep_crit  = int(getattr(dr, "critical_dependencies", 0) or 0)
        dep_graph = {k: tuple(v) for k, v in PLATFORM_DEPENDENCIES.items()}

        # --- Self-healing
        plan      = getattr(summary, "self_healing_plan", None)
        rec_count = int(getattr(plan, "total", 0) or 0)
        can_auto  = bool(getattr(plan, "can_auto_execute", False))
        automation_readiness = (
            AutomationReadiness.READY             if can_auto
            else AutomationReadiness.REQUIRES_APPROVAL if rec_count > 0
            else AutomationReadiness.UNKNOWN
        )

        # --- Governance compliance
        gov_report   = getattr(summary, "governance_report", None)
        is_compliant = bool(getattr(gov_report, "is_compliant", False))
        violations   = tuple(getattr(gov_report, "violations", ()) or ())
        gov_status   = (
            GovernanceStatus.COMPLIANT if is_compliant
            else GovernanceStatus.NON_COMPLIANT
        )

        # --- Root causes
        rc_report  = getattr(summary, "root_cause_report", None)
        rc_list    = getattr(rc_report, "root_causes", ()) or ()
        rc_cats    = tuple(
            getattr(getattr(rc, "category", None), "value", "unknown")
            for rc in rc_list
        )

        # --- Recommendations
        recs_obj   = getattr(summary, "recommendations", None)
        recs_count = int(getattr(recs_obj, "total", 0) or 0)

        # --- Reasoning
        reasoning  = str(getattr(summary, "reasoning_summary", "") or "")
        is_success = bool(getattr(summary, "is_success", False))
        is_emergency = bool(getattr(summary, "is_emergency", False))

        # --- Derive operational enums
        op_status   = (
            OperationalStatus.OPERATIONAL if ph_score >= 0.70
            else OperationalStatus.DEGRADED
        )
        plat_status = (
            PlatformStatus.HEALTHY   if ph_score >= 0.90
            else PlatformStatus.DEGRADED if ph_score >= 0.50
            else PlatformStatus.CRITICAL
        )
        _gs_map     = {
            "continue":    SnapshotGovernanceState.ACTIVE,
            "defer":       SnapshotGovernanceState.SUSPENDED,
            "escalate":    SnapshotGovernanceState.DEGRADED,
            "halt":        SnapshotGovernanceState.HALTED,
            "investigate": SnapshotGovernanceState.DEGRADED,
        }
        governance_state = _gs_map.get(gov_decision, SnapshotGovernanceState.UNKNOWN)
        snapshot_status  = SnapshotStatus.PUBLISHED if is_success else SnapshotStatus.INVALID

        return (
            SupervisorSnapshotBuilder(session_id, workflow_id, environment=environment)
            .with_status(snapshot_status)
            .with_lifecycle_state(SnapshotLifecycleState.RUNNING)
            .with_governance_state(governance_state)
            .with_enterprise_state(enterprise_state)
            .with_enterprise_summary(EnterpriseSummary.create(
                enterprise_health          = ph_score,
                platform_status            = plat_status,
                operational_status         = op_status,
                governance_status          = gov_status,
                enterprise_stability_score = ph_score * 0.9,
                enterprise_confidence      = ph_score * 0.85,
                overall_supervisor_score   = ph_score * 0.88,
            ))
            .with_governance_summary(GovernanceSummary.create(
                governance_decision = gov_decision,
                policy_outcome      = "approved" if is_compliant else "policy_action_required",
                policy_violations   = violations,
                escalations         = 1 if gov_decision == "escalate" else 0,
                emergency_actions   = 1 if (gov_decision == "halt" and is_emergency) else 0,
            ))
            .with_supervision_summary(SupervisionSummary.create(
                supervision_status = op_status,
                platform_health    = ph_score,
                active_alerts      = anomaly_count,
                critical_events    = crit_count,
            ))
            .with_anomaly_summary(AnomalySummary.create(
                detected_anomalies    = anomaly_count,
                severity_distribution = sev_dist,
                affected_subsystems   = affected_subs,
                root_causes           = rc_cats,
                incident_correlations = incident_count,
            ))
            .with_self_healing_summary(SelfHealingSummary.create(
                recommended_actions  = recs_count,
                recovery_plans       = rec_count,
                mitigation_plans     = max(0, recs_count - rec_count),
                automation_readiness = automation_readiness,
            ))
            .with_dependency_summary(DependencySummary.create(
                dependency_graph      = dep_graph,
                critical_dependencies = dep_crit,
            ))
            .with_audit_summary(AuditSummary.create(
                governance_version = VERSION,
                validation_summary = reasoning[:200] if reasoning else "",
            ))
            .with_metadata(metadata or SupervisorSnapshotMetadata.create(environment=environment))
            .build()
        )

    # ------------------------------------------------------------------
    # Test scenarios
    # ------------------------------------------------------------------

    def create_healthy(self, session_id: str = "") -> SupervisorSnapshot:
        """Fully healthy platform snapshot for testing."""
        sid = session_id or str(uuid.uuid4())
        return (
            SupervisorSnapshotBuilder(sid, environment="test")
            .with_status(SnapshotStatus.PUBLISHED)
            .with_lifecycle_state(SnapshotLifecycleState.RUNNING)
            .with_governance_state(SnapshotGovernanceState.ACTIVE)
            .with_enterprise_state(SnapshotEnterpriseState.OPTIMAL)
            .with_enterprise_summary(EnterpriseSummary.create(
                enterprise_health          = 0.95,
                platform_status            = PlatformStatus.HEALTHY,
                operational_status         = OperationalStatus.OPERATIONAL,
                governance_status          = GovernanceStatus.COMPLIANT,
                enterprise_stability_score = 0.93,
                enterprise_confidence      = 0.91,
                overall_supervisor_score   = 0.94,
            ))
            .with_subsystems_summary(_uniform_subsystems(SubsystemSummaryStatus.HEALTHY, 0.95))
            .with_governance_summary(GovernanceSummary.create(
                governance_decision = "continue",
                policy_outcome      = "approved",
            ))
            .with_supervision_summary(SupervisionSummary.create(
                supervision_status = OperationalStatus.OPERATIONAL,
                platform_health    = 0.95,
                active_alerts      = 0,
            ))
            .with_anomaly_summary(AnomalySummary.create())
            .with_self_healing_summary(SelfHealingSummary.create(
                automation_readiness = AutomationReadiness.READY,
            ))
            .with_dependency_summary(DependencySummary.create(
                dependency_graph      = {k: tuple(v) for k, v in PLATFORM_DEPENDENCIES.items()},
                critical_dependencies = 3,
            ))
            .with_audit_summary(AuditSummary.create(
                governance_version = VERSION,
                validation_summary = "All systems operational",
            ))
            .with_metadata(SupervisorSnapshotMetadata.create(environment="test"))
            .build()
        )

    def create_emergency(self, session_id: str = "") -> SupervisorSnapshot:
        """Emergency state snapshot for testing."""
        sid = session_id or str(uuid.uuid4())
        return (
            SupervisorSnapshotBuilder(sid, environment="test")
            .with_status(SnapshotStatus.PUBLISHED)
            .with_lifecycle_state(SnapshotLifecycleState.RUNNING)
            .with_governance_state(SnapshotGovernanceState.EMERGENCY)
            .with_enterprise_state(SnapshotEnterpriseState.EMERGENCY)
            .with_enterprise_summary(EnterpriseSummary.create(
                enterprise_health          = 0.10,
                platform_status            = PlatformStatus.CRITICAL,
                operational_status         = OperationalStatus.IMPAIRED,
                governance_status          = GovernanceStatus.ESCALATED,
                enterprise_stability_score = 0.05,
                enterprise_confidence      = 0.10,
                overall_supervisor_score   = 0.08,
            ))
            .with_subsystems_summary(
                _uniform_subsystems(SubsystemSummaryStatus.CRITICAL, 0.1, ("critical_failure",))
            )
            .with_governance_summary(GovernanceSummary.create(
                governance_decision = "halt",
                policy_outcome      = "emergency_stop",
                escalations         = 1,
                emergency_actions   = 1,
            ))
            .with_supervision_summary(SupervisionSummary.create(
                supervision_status = OperationalStatus.IMPAIRED,
                platform_health    = 0.10,
                active_alerts      = 5,
                critical_events    = 3,
                enterprise_risks   = ("critical_system_failure",),
            ))
            .with_anomaly_summary(AnomalySummary.create(
                detected_anomalies    = 5,
                severity_distribution = {"critical": 3, "high": 2},
                affected_subsystems   = ("risk_intelligence", "market_intelligence"),
            ))
            .with_self_healing_summary(SelfHealingSummary.create(
                recommended_actions  = 3,
                recovery_plans       = 2,
                automation_readiness = AutomationReadiness.REQUIRES_APPROVAL,
            ))
            .with_dependency_summary(DependencySummary.create(
                dependency_graph      = {k: tuple(v) for k, v in PLATFORM_DEPENDENCIES.items()},
                critical_dependencies = 6,
                unavailable_components = ("market_intelligence", "risk_intelligence"),
            ))
            .with_metadata(SupervisorSnapshotMetadata.create(environment="test"))
            .build()
        )

    def create_degraded(self, session_id: str = "") -> SupervisorSnapshot:
        """Degraded platform snapshot for testing."""
        sid = session_id or str(uuid.uuid4())
        return (
            SupervisorSnapshotBuilder(sid, environment="test")
            .with_status(SnapshotStatus.PUBLISHED)
            .with_lifecycle_state(SnapshotLifecycleState.RUNNING)
            .with_governance_state(SnapshotGovernanceState.DEGRADED)
            .with_enterprise_state(SnapshotEnterpriseState.DEGRADED)
            .with_enterprise_summary(EnterpriseSummary.create(
                enterprise_health          = 0.55,
                platform_status            = PlatformStatus.DEGRADED,
                operational_status         = OperationalStatus.DEGRADED,
                governance_status          = GovernanceStatus.NON_COMPLIANT,
                enterprise_stability_score = 0.50,
                enterprise_confidence      = 0.55,
                overall_supervisor_score   = 0.53,
            ))
            .with_governance_summary(GovernanceSummary.create(
                governance_decision = "investigate",
                policy_outcome      = "degraded_operation",
            ))
            .with_anomaly_summary(AnomalySummary.create(
                detected_anomalies    = 2,
                severity_distribution = {"high": 2},
            ))
            .with_metadata(SupervisorSnapshotMetadata.create(environment="test"))
            .build()
        )
