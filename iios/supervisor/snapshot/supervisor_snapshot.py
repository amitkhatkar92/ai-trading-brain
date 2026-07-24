"""
supervisor_snapshot.py — iios.supervisor.snapshot
---------------------------------------------------
SupervisorSnapshot — the immutable published representation of the
complete AI Supervisor & Autonomous Governance subsystem.

Downstream subsystems MUST consume SupervisorSnapshot instead of
directly accessing:
  - AI Supervisor Engine (M2)
  - AI Governance Policy Framework (M3)
  - Autonomous Governance Framework (M4)

MUST NOT:
  - Evaluate governance policies
  - Perform AI reasoning
  - Perform optimization
  - Execute trades

C13 AI Supervisor & Autonomous Governance — Phase 1, Module 5
"""
from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple

from .constants import (
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
from .supervisor_snapshot_metadata import SupervisorSnapshotMetadata


# ===========================================================================
# Section: Enterprise Summary
# ===========================================================================

@dataclass(frozen=True)
class EnterpriseSummary:
    """Aggregated enterprise health and status."""
    enterprise_health:          float             = 1.0
    platform_status:            PlatformStatus    = PlatformStatus.UNKNOWN
    operational_status:         OperationalStatus = OperationalStatus.UNKNOWN
    governance_status:          GovernanceStatus  = GovernanceStatus.UNKNOWN
    enterprise_stability_score: float             = 0.0
    enterprise_confidence:      float             = 0.0
    overall_supervisor_score:   float             = 0.0

    @classmethod
    def create(
        cls,
        *,
        enterprise_health:          float             = 1.0,
        platform_status:            PlatformStatus    = PlatformStatus.UNKNOWN,
        operational_status:         OperationalStatus = OperationalStatus.UNKNOWN,
        governance_status:          GovernanceStatus  = GovernanceStatus.UNKNOWN,
        enterprise_stability_score: float             = 0.0,
        enterprise_confidence:      float             = 0.0,
        overall_supervisor_score:   float             = 0.0,
    ) -> "EnterpriseSummary":
        return cls(
            enterprise_health          = max(0.0, min(1.0, enterprise_health)),
            platform_status            = platform_status,
            operational_status         = operational_status,
            governance_status          = governance_status,
            enterprise_stability_score = max(0.0, min(1.0, enterprise_stability_score)),
            enterprise_confidence      = max(0.0, min(1.0, enterprise_confidence)),
            overall_supervisor_score   = max(0.0, min(1.0, overall_supervisor_score)),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "enterprise_health":          self.enterprise_health,
            "platform_status":            self.platform_status.value,
            "operational_status":         self.operational_status.value,
            "governance_status":          self.governance_status.value,
            "enterprise_stability_score": self.enterprise_stability_score,
            "enterprise_confidence":      self.enterprise_confidence,
            "overall_supervisor_score":   self.overall_supervisor_score,
        }


# ===========================================================================
# Section: Subsystem Summary
# ===========================================================================

@dataclass(frozen=True)
class SubsystemSummaryItem:
    """Summary of a single subsystem's operational state."""
    subsystem_id:    str
    status:          SubsystemSummaryStatus = SubsystemSummaryStatus.UNKNOWN
    health_score:    float                  = 0.0
    issues:          Tuple[str, ...]        = ()
    component_count: int                    = 0

    @classmethod
    def create(
        cls,
        subsystem_id: str,
        *,
        status:          SubsystemSummaryStatus       = SubsystemSummaryStatus.UNKNOWN,
        health_score:    float                        = 0.0,
        issues:          Optional[Tuple[str, ...]]    = None,
        component_count: int                          = 0,
    ) -> "SubsystemSummaryItem":
        return cls(
            subsystem_id    = subsystem_id,
            status          = status,
            health_score    = max(0.0, min(1.0, health_score)),
            issues          = issues or (),
            component_count = component_count,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "subsystem_id":   self.subsystem_id,
            "status":         self.status.value,
            "health_score":   self.health_score,
            "issues":         list(self.issues),
            "component_count": self.component_count,
        }


@dataclass(frozen=True)
class SubsystemsSummary:
    """Summary of all nine supervised subsystems."""
    execution_intelligence: SubsystemSummaryItem
    execution_recovery:     SubsystemSummaryItem
    execution_analytics:    SubsystemSummaryItem
    decision_intelligence:  SubsystemSummaryItem
    portfolio_intelligence: SubsystemSummaryItem
    risk_intelligence:      SubsystemSummaryItem
    market_intelligence:    SubsystemSummaryItem
    infrastructure:         SubsystemSummaryItem
    enterprise_modules:     SubsystemSummaryItem

    @classmethod
    def unknown(cls) -> "SubsystemsSummary":
        """All subsystems in UNKNOWN state."""
        _mk = lambda sid: SubsystemSummaryItem.create(sid)  # noqa: E731
        return cls(
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

    def all_items(self) -> Tuple[SubsystemSummaryItem, ...]:
        return (
            self.execution_intelligence,
            self.execution_recovery,
            self.execution_analytics,
            self.decision_intelligence,
            self.portfolio_intelligence,
            self.risk_intelligence,
            self.market_intelligence,
            self.infrastructure,
            self.enterprise_modules,
        )

    def healthy_count(self) -> int:
        return sum(1 for i in self.all_items() if i.status == SubsystemSummaryStatus.HEALTHY)

    def critical_count(self) -> int:
        return sum(1 for i in self.all_items() if i.status == SubsystemSummaryStatus.CRITICAL)

    def to_dict(self) -> Dict[str, Any]:
        return {item.subsystem_id: item.to_dict() for item in self.all_items()}


# ===========================================================================
# Section: Governance Summary
# ===========================================================================

@dataclass(frozen=True)
class GovernanceSummary:
    """Consolidated governance decision and policy outcome."""
    governance_decision: str             = "unknown"
    policy_outcome:      str             = ""
    policy_violations:   Tuple[str, ...] = ()
    escalations:         int             = 0
    human_reviews:       int             = 0
    emergency_actions:   int             = 0

    @classmethod
    def create(
        cls,
        *,
        governance_decision: str                       = "unknown",
        policy_outcome:      str                       = "",
        policy_violations:   Optional[Tuple[str, ...]] = None,
        escalations:         int                       = 0,
        human_reviews:       int                       = 0,
        emergency_actions:   int                       = 0,
    ) -> "GovernanceSummary":
        return cls(
            governance_decision = governance_decision,
            policy_outcome      = policy_outcome,
            policy_violations   = policy_violations or (),
            escalations         = max(0, escalations),
            human_reviews       = max(0, human_reviews),
            emergency_actions   = max(0, emergency_actions),
        )

    @property
    def has_violations(self) -> bool:
        return len(self.policy_violations) > 0

    @property
    def requires_escalation(self) -> bool:
        return self.escalations > 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "governance_decision": self.governance_decision,
            "policy_outcome":      self.policy_outcome,
            "policy_violations":   list(self.policy_violations),
            "escalations":         self.escalations,
            "human_reviews":       self.human_reviews,
            "emergency_actions":   self.emergency_actions,
        }


# ===========================================================================
# Section: Supervision Summary
# ===========================================================================

@dataclass(frozen=True)
class SupervisionSummary:
    """Summary of active supervision state."""
    supervision_status: OperationalStatus = OperationalStatus.UNKNOWN
    platform_health:    float             = 0.0
    active_alerts:      int               = 0
    warnings:           int               = 0
    critical_events:    int               = 0
    enterprise_risks:   Tuple[str, ...]   = ()

    @classmethod
    def create(
        cls,
        *,
        supervision_status: OperationalStatus          = OperationalStatus.UNKNOWN,
        platform_health:    float                      = 0.0,
        active_alerts:      int                        = 0,
        warnings:           int                        = 0,
        critical_events:    int                        = 0,
        enterprise_risks:   Optional[Tuple[str, ...]]  = None,
    ) -> "SupervisionSummary":
        return cls(
            supervision_status = supervision_status,
            platform_health    = max(0.0, min(1.0, platform_health)),
            active_alerts      = max(0, active_alerts),
            warnings           = max(0, warnings),
            critical_events    = max(0, critical_events),
            enterprise_risks   = enterprise_risks or (),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "supervision_status": self.supervision_status.value,
            "platform_health":    self.platform_health,
            "active_alerts":      self.active_alerts,
            "warnings":           self.warnings,
            "critical_events":    self.critical_events,
            "enterprise_risks":   list(self.enterprise_risks),
        }


# ===========================================================================
# Section: Anomaly Summary
# ===========================================================================

@dataclass(frozen=True)
class AnomalySummary:
    """Summary of anomalies detected during the governance cycle."""
    detected_anomalies:    int                = 0
    severity_distribution: Dict[str, int]     = field(default_factory=dict)
    affected_subsystems:   Tuple[str, ...]    = ()
    root_causes:           Tuple[str, ...]    = ()
    incident_correlations: int                = 0

    @classmethod
    def create(
        cls,
        *,
        detected_anomalies:    int                         = 0,
        severity_distribution: Optional[Dict[str, int]]   = None,
        affected_subsystems:   Optional[Tuple[str, ...]]  = None,
        root_causes:           Optional[Tuple[str, ...]]  = None,
        incident_correlations: int                        = 0,
    ) -> "AnomalySummary":
        return cls(
            detected_anomalies    = max(0, detected_anomalies),
            severity_distribution = severity_distribution or {},
            affected_subsystems   = affected_subsystems or (),
            root_causes           = root_causes or (),
            incident_correlations = max(0, incident_correlations),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "detected_anomalies":    self.detected_anomalies,
            "severity_distribution": self.severity_distribution,
            "affected_subsystems":   list(self.affected_subsystems),
            "root_causes":           list(self.root_causes),
            "incident_correlations": self.incident_correlations,
        }


# ===========================================================================
# Section: Self-Healing Summary
# ===========================================================================

@dataclass(frozen=True)
class SelfHealingSummary:
    """Summary of self-healing recommendations and recovery plans."""
    recommended_actions:  int                 = 0
    recovery_plans:       int                 = 0
    mitigation_plans:     int                 = 0
    priority_actions:     Tuple[str, ...]     = ()
    automation_readiness: AutomationReadiness = AutomationReadiness.UNKNOWN

    @classmethod
    def create(
        cls,
        *,
        recommended_actions:  int                         = 0,
        recovery_plans:       int                         = 0,
        mitigation_plans:     int                         = 0,
        priority_actions:     Optional[Tuple[str, ...]]  = None,
        automation_readiness: AutomationReadiness         = AutomationReadiness.UNKNOWN,
    ) -> "SelfHealingSummary":
        return cls(
            recommended_actions  = max(0, recommended_actions),
            recovery_plans       = max(0, recovery_plans),
            mitigation_plans     = max(0, mitigation_plans),
            priority_actions     = priority_actions or (),
            automation_readiness = automation_readiness,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "recommended_actions":  self.recommended_actions,
            "recovery_plans":       self.recovery_plans,
            "mitigation_plans":     self.mitigation_plans,
            "priority_actions":     list(self.priority_actions),
            "automation_readiness": self.automation_readiness.value,
        }


# ===========================================================================
# Section: Dependency Summary
# ===========================================================================

@dataclass(frozen=True)
class DependencySummary:
    """Summary of the subsystem dependency graph and service health."""
    dependency_graph:       Dict[str, Tuple[str, ...]] = field(default_factory=dict)
    critical_dependencies:  int                        = 0
    unavailable_components: Tuple[str, ...]            = ()
    service_health:         Dict[str, float]           = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        *,
        dependency_graph:       Optional[Dict[str, Tuple[str, ...]]] = None,
        critical_dependencies:  int                                   = 0,
        unavailable_components: Optional[Tuple[str, ...]]            = None,
        service_health:         Optional[Dict[str, float]]           = None,
    ) -> "DependencySummary":
        return cls(
            dependency_graph       = dependency_graph or {},
            critical_dependencies  = max(0, critical_dependencies),
            unavailable_components = unavailable_components or (),
            service_health         = service_health or {},
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dependency_graph":       {k: list(v) for k, v in self.dependency_graph.items()},
            "critical_dependencies":  self.critical_dependencies,
            "unavailable_components": list(self.unavailable_components),
            "service_health":         self.service_health,
        }


# ===========================================================================
# Section: Audit Summary
# ===========================================================================

@dataclass(frozen=True)
class AuditSummary:
    """Audit trail and governance compliance record."""
    governance_version:       str             = VERSION
    reasoning_model_versions: Dict[str, str]  = field(default_factory=dict)
    validation_summary:       str             = ""
    audit_trail:              Tuple[str, ...] = ()

    @classmethod
    def create(
        cls,
        *,
        governance_version:       str                         = VERSION,
        reasoning_model_versions: Optional[Dict[str, str]]   = None,
        validation_summary:       str                         = "",
        audit_trail:              Optional[Tuple[str, ...]]  = None,
    ) -> "AuditSummary":
        return cls(
            governance_version        = governance_version,
            reasoning_model_versions  = reasoning_model_versions or {},
            validation_summary        = validation_summary,
            audit_trail               = audit_trail or (),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "governance_version":       self.governance_version,
            "reasoning_model_versions": self.reasoning_model_versions,
            "validation_summary":       self.validation_summary,
            "audit_trail":              list(self.audit_trail),
        }


# ===========================================================================
# Section: Snapshot Statistics
# ===========================================================================

@dataclass(frozen=True)
class SnapshotStatistics:
    """Performance metrics for the snapshot generation cycle."""
    assessment_duration:  float = 0.0   # seconds
    supervision_duration: float = 0.0   # seconds
    snapshot_size:        int   = 0     # bytes estimate
    component_count:      int   = 0

    @classmethod
    def create(
        cls,
        *,
        assessment_duration:  float = 0.0,
        supervision_duration: float = 0.0,
        snapshot_size:        int   = 0,
        component_count:      int   = 0,
    ) -> "SnapshotStatistics":
        return cls(
            assessment_duration  = max(0.0, assessment_duration),
            supervision_duration = max(0.0, supervision_duration),
            snapshot_size        = max(0, snapshot_size),
            component_count      = max(0, component_count),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "assessment_duration":  self.assessment_duration,
            "supervision_duration": self.supervision_duration,
            "snapshot_size":        self.snapshot_size,
            "component_count":      self.component_count,
        }


# ===========================================================================
# SupervisorSnapshot — primary export
# ===========================================================================

@dataclass(frozen=True)
class SupervisorSnapshot:
    """
    Immutable published representation of the complete AI Supervisor
    & Autonomous Governance subsystem.

    Every downstream subsystem MUST consume SupervisorSnapshot rather
    than directly accessing the AI Supervisor Engine, Governance Policy
    Framework, or Autonomous Governance Framework.

    MUST NOT:
      - Evaluate governance policies
      - Perform AI reasoning
      - Perform optimization
      - Execute trades
    """

    # ------------------------------------------------------------------
    # Core identification
    # ------------------------------------------------------------------

    snapshot_id:            str
    supervisor_session_id:  str
    supervisor_workflow_id: str
    enterprise_session_id:  str
    platform_version:       str
    supervisor_scope:       SupervisorScope
    supervisor_type:        SupervisorType
    lifecycle_state:        SnapshotLifecycleState
    governance_state:       SnapshotGovernanceState
    enterprise_state:       SnapshotEnterpriseState
    supervisor_version:     str
    framework_version:      str
    snapshot_timestamp:     float
    created_at:             float
    updated_at:             float
    snapshot_status:        SnapshotStatus

    # ------------------------------------------------------------------
    # Content sections
    # ------------------------------------------------------------------

    enterprise_summary:   EnterpriseSummary
    subsystems_summary:   SubsystemsSummary
    governance_summary:   GovernanceSummary
    supervision_summary:  SupervisionSummary
    anomaly_summary:      AnomalySummary
    self_healing_summary: SelfHealingSummary
    dependency_summary:   DependencySummary
    audit_summary:        AuditSummary
    snapshot_statistics:  SnapshotStatistics
    metadata:             SupervisorSnapshotMetadata

    # ------------------------------------------------------------------
    # Derived properties
    # ------------------------------------------------------------------

    @property
    def is_valid(self) -> bool:
        """True when the snapshot has passed validation."""
        return self.snapshot_status in (SnapshotStatus.VALID, SnapshotStatus.PUBLISHED)

    @property
    def is_published(self) -> bool:
        return self.snapshot_status == SnapshotStatus.PUBLISHED

    @property
    def is_emergency(self) -> bool:
        return self.enterprise_state == SnapshotEnterpriseState.EMERGENCY

    @property
    def is_critical(self) -> bool:
        return self.enterprise_state in (
            SnapshotEnterpriseState.CRITICAL,
            SnapshotEnterpriseState.EMERGENCY,
        )

    @property
    def is_healthy(self) -> bool:
        return self.enterprise_summary.enterprise_health >= 0.70

    @property
    def anomaly_count(self) -> int:
        return self.anomaly_summary.detected_anomalies

    @property
    def governance_decision(self) -> str:
        return self.governance_summary.governance_decision

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        return {
            # Core identification
            "snapshot_id":            self.snapshot_id,
            "supervisor_session_id":  self.supervisor_session_id,
            "supervisor_workflow_id": self.supervisor_workflow_id,
            "enterprise_session_id":  self.enterprise_session_id,
            "platform_version":       self.platform_version,
            "supervisor_scope":       self.supervisor_scope.value,
            "supervisor_type":        self.supervisor_type.value,
            "lifecycle_state":        self.lifecycle_state.value,
            "governance_state":       self.governance_state.value,
            "enterprise_state":       self.enterprise_state.value,
            "supervisor_version":     self.supervisor_version,
            "framework_version":      self.framework_version,
            "snapshot_timestamp":     self.snapshot_timestamp,
            "created_at":             self.created_at,
            "updated_at":             self.updated_at,
            "snapshot_status":        self.snapshot_status.value,
            # Content sections
            "enterprise_summary":     self.enterprise_summary.to_dict(),
            "subsystems_summary":     self.subsystems_summary.to_dict(),
            "governance_summary":     self.governance_summary.to_dict(),
            "supervision_summary":    self.supervision_summary.to_dict(),
            "anomaly_summary":        self.anomaly_summary.to_dict(),
            "self_healing_summary":   self.self_healing_summary.to_dict(),
            "dependency_summary":     self.dependency_summary.to_dict(),
            "audit_summary":          self.audit_summary.to_dict(),
            "snapshot_statistics":    self.snapshot_statistics.to_dict(),
            "metadata":               self.metadata.to_dict(),
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), default=str)

    def estimated_size_bytes(self) -> int:
        """Rough estimate of serialized size in bytes."""
        try:
            return len(self.to_json().encode("utf-8"))
        except Exception:
            return 0
