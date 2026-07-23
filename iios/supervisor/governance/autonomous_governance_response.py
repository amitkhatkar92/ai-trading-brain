"""
autonomous_governance_response.py — iios.supervisor.governance
---------------------------------------------------------------
All report value objects and the AutonomousGovernanceSummary for
the Autonomous Governance Framework.

Exports
-------
GovernanceAnomaly            — individual anomaly value object
AnomalyReport                — aggregated anomaly report
GovernanceIncident           — individual incident value object
IncidentReport               — aggregated incident report
RootCause                    — individual root cause value object
RootCauseReport              — aggregated root cause report
SubsystemDependency          — individual dependency value object
DependencyReport             — subsystem dependency report
SubsystemHealth              — individual subsystem health value object
PlatformHealthReport         — aggregated platform health report
GovernanceRecommendation     — individual recommendation value object
GovernanceRecommendations    — aggregated recommendations
SelfHealingActionItem        — individual self-healing action value object
SelfHealingPlan              — aggregated self-healing plan
EnterpriseStateReport        — enterprise operational state report
EnterpriseGovernanceReport   — governance compliance report
AutonomousGovernanceSummary  — complete governance cycle output

C13 AI Supervisor & Autonomous Governance — Phase 1, Module 4
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple

from .constants import (
    VERSION,
    AnomalySeverity,
    DependencyType,
    EnterpriseState,
    GovernanceDecision,
    IncidentSeverity,
    RecommendationPriority,
    RootCauseCategory,
    SelfHealingActionType,
    SubsystemStatus,
    SupervisionStrategyType,
)


# ===========================================================================
# Anomaly Report
# ===========================================================================

@dataclass(frozen=True)
class GovernanceAnomaly:
    """A single detected enterprise anomaly."""
    anomaly_id:     str
    subsystem_id:   str
    field_path:     str
    observed_value: Any
    expected_range: str           # human-readable description of expected range
    severity:       AnomalySeverity
    description:    str           = ""
    detected_at:    float         = field(default_factory=time.time)
    metadata:       Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        subsystem_id:   str,
        field_path:     str,
        observed_value: Any,
        severity:       AnomalySeverity,
        *,
        anomaly_id:     Optional[str] = None,
        expected_range: str = "",
        description:    str = "",
        metadata:       Optional[Dict[str, Any]] = None,
    ) -> "GovernanceAnomaly":
        return cls(
            anomaly_id     = anomaly_id or str(uuid.uuid4()),
            subsystem_id   = subsystem_id,
            field_path     = field_path,
            observed_value = observed_value,
            expected_range = expected_range,
            severity       = severity,
            description    = description,
            metadata       = metadata or {},
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "anomaly_id":     self.anomaly_id,
            "subsystem_id":   self.subsystem_id,
            "field_path":     self.field_path,
            "observed_value": self.observed_value,
            "expected_range": self.expected_range,
            "severity":       self.severity.value,
            "description":    self.description,
            "detected_at":    self.detected_at,
        }


@dataclass(frozen=True)
class AnomalyReport:
    """Aggregated report of all detected anomalies."""
    report_id:      str
    anomalies:      Tuple[GovernanceAnomaly, ...]
    total:          int
    critical_count: int           = 0
    high_count:     int           = 0
    medium_count:   int           = 0
    low_count:      int           = 0
    info_count:     int           = 0
    generated_at:   float         = field(default_factory=time.time)
    framework_version: str        = VERSION

    @classmethod
    def create(
        cls,
        anomalies: Tuple[GovernanceAnomaly, ...],
        *,
        report_id: Optional[str] = None,
    ) -> "AnomalyReport":
        critical = sum(1 for a in anomalies if a.severity == AnomalySeverity.CRITICAL)
        high     = sum(1 for a in anomalies if a.severity == AnomalySeverity.HIGH)
        medium   = sum(1 for a in anomalies if a.severity == AnomalySeverity.MEDIUM)
        low      = sum(1 for a in anomalies if a.severity == AnomalySeverity.LOW)
        info     = sum(1 for a in anomalies if a.severity == AnomalySeverity.INFO)
        return cls(
            report_id      = report_id or str(uuid.uuid4()),
            anomalies      = anomalies,
            total          = len(anomalies),
            critical_count = critical,
            high_count     = high,
            medium_count   = medium,
            low_count      = low,
            info_count     = info,
        )

    @property
    def has_critical(self) -> bool:
        return self.critical_count > 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id":      self.report_id,
            "total":          self.total,
            "critical_count": self.critical_count,
            "high_count":     self.high_count,
            "medium_count":   self.medium_count,
            "low_count":      self.low_count,
            "info_count":     self.info_count,
            "generated_at":   self.generated_at,
        }


# ===========================================================================
# Incident Report
# ===========================================================================

@dataclass(frozen=True)
class GovernanceIncident:
    """A correlated group of anomalies forming an incident."""
    incident_id:           str
    title:                 str
    anomaly_ids:           Tuple[str, ...]
    affected_subsystems:   Tuple[str, ...]
    severity:              IncidentSeverity
    description:           str           = ""
    correlated_at:         float         = field(default_factory=time.time)
    metadata:              Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        title:               str,
        anomaly_ids:         Tuple[str, ...],
        affected_subsystems: Tuple[str, ...],
        severity:            IncidentSeverity,
        *,
        incident_id: Optional[str] = None,
        description: str = "",
        metadata:    Optional[Dict[str, Any]] = None,
    ) -> "GovernanceIncident":
        return cls(
            incident_id         = incident_id or str(uuid.uuid4()),
            title               = title,
            anomaly_ids         = anomaly_ids,
            affected_subsystems = affected_subsystems,
            severity            = severity,
            description         = description,
            metadata            = metadata or {},
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "incident_id":          self.incident_id,
            "title":                self.title,
            "anomaly_count":        len(self.anomaly_ids),
            "affected_subsystems":  list(self.affected_subsystems),
            "severity":             self.severity.value,
            "description":          self.description,
            "correlated_at":        self.correlated_at,
        }


@dataclass(frozen=True)
class IncidentReport:
    """Aggregated report of all correlated incidents."""
    report_id:                str
    incidents:                Tuple[GovernanceIncident, ...]
    total:                    int
    correlated_from_anomalies: int          = 0
    critical_count:           int           = 0
    high_count:               int           = 0
    generated_at:             float         = field(default_factory=time.time)
    framework_version:        str           = VERSION

    @classmethod
    def create(
        cls,
        incidents:                Tuple[GovernanceIncident, ...],
        correlated_from_anomalies: int = 0,
        *,
        report_id: Optional[str] = None,
    ) -> "IncidentReport":
        critical = sum(1 for i in incidents if i.severity == IncidentSeverity.CRITICAL)
        high     = sum(1 for i in incidents if i.severity == IncidentSeverity.HIGH)
        return cls(
            report_id                 = report_id or str(uuid.uuid4()),
            incidents                 = incidents,
            total                     = len(incidents),
            correlated_from_anomalies = correlated_from_anomalies,
            critical_count            = critical,
            high_count                = high,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id":                 self.report_id,
            "total":                     self.total,
            "correlated_from_anomalies": self.correlated_from_anomalies,
            "critical_count":            self.critical_count,
            "high_count":                self.high_count,
            "generated_at":              self.generated_at,
        }


# ===========================================================================
# Root Cause Report
# ===========================================================================

@dataclass(frozen=True)
class RootCause:
    """Root cause identified for a single incident."""
    root_cause_id:  str
    incident_id:    str
    category:       RootCauseCategory
    description:    str
    confidence:     float         = 0.5   # 0.0–1.0
    evidence:       Tuple[str, ...] = ()
    identified_at:  float         = field(default_factory=time.time)

    @classmethod
    def create(
        cls,
        incident_id: str,
        category:    RootCauseCategory,
        description: str,
        *,
        root_cause_id: Optional[str]       = None,
        confidence:    float               = 0.5,
        evidence:      Tuple[str, ...] = (),
    ) -> "RootCause":
        return cls(
            root_cause_id = root_cause_id or str(uuid.uuid4()),
            incident_id   = incident_id,
            category      = category,
            description   = description,
            confidence    = confidence,
            evidence      = evidence,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "root_cause_id": self.root_cause_id,
            "incident_id":   self.incident_id,
            "category":      self.category.value,
            "description":   self.description,
            "confidence":    self.confidence,
            "evidence":      list(self.evidence),
            "identified_at": self.identified_at,
        }


@dataclass(frozen=True)
class RootCauseReport:
    """Aggregated root cause analysis report."""
    report_id:          str
    root_causes:        Tuple[RootCause, ...]
    total:              int
    identified_count:   int           = 0   # root causes with confidence > 0.5
    unknown_count:      int           = 0
    generated_at:       float         = field(default_factory=time.time)
    framework_version:  str           = VERSION

    @classmethod
    def create(
        cls,
        root_causes: Tuple[RootCause, ...],
        *,
        report_id: Optional[str] = None,
    ) -> "RootCauseReport":
        identified = sum(1 for r in root_causes if r.category != RootCauseCategory.UNKNOWN)
        unknown    = sum(1 for r in root_causes if r.category == RootCauseCategory.UNKNOWN)
        return cls(
            report_id        = report_id or str(uuid.uuid4()),
            root_causes      = root_causes,
            total            = len(root_causes),
            identified_count = identified,
            unknown_count    = unknown,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id":        self.report_id,
            "total":            self.total,
            "identified_count": self.identified_count,
            "unknown_count":    self.unknown_count,
            "generated_at":     self.generated_at,
        }


# ===========================================================================
# Dependency Report
# ===========================================================================

@dataclass(frozen=True)
class SubsystemDependency:
    """Directional dependency between two subsystems."""
    from_subsystem:  str
    to_subsystem:    str
    dependency_type: DependencyType
    is_critical:     bool          = True
    description:     str           = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "from_subsystem":  self.from_subsystem,
            "to_subsystem":    self.to_subsystem,
            "dependency_type": self.dependency_type.value,
            "is_critical":     self.is_critical,
        }


@dataclass(frozen=True)
class DependencyReport:
    """Subsystem dependency graph analysis report."""
    report_id:            str
    dependencies:         Tuple[SubsystemDependency, ...]
    subsystems:           Tuple[str, ...]
    critical_paths:       Tuple[Tuple[str, ...], ...]
    isolated_subsystems:  Tuple[str, ...]
    total_dependencies:   int
    critical_dependencies: int
    generated_at:         float       = field(default_factory=time.time)
    framework_version:    str         = VERSION

    @classmethod
    def create(
        cls,
        dependencies:        Tuple[SubsystemDependency, ...],
        subsystems:          Tuple[str, ...],
        critical_paths:      Tuple[Tuple[str, ...], ...] = (),
        isolated_subsystems: Tuple[str, ...]             = (),
        *,
        report_id: Optional[str] = None,
    ) -> "DependencyReport":
        critical = sum(1 for d in dependencies if d.is_critical)
        return cls(
            report_id             = report_id or str(uuid.uuid4()),
            dependencies          = dependencies,
            subsystems            = subsystems,
            critical_paths        = critical_paths,
            isolated_subsystems   = isolated_subsystems,
            total_dependencies    = len(dependencies),
            critical_dependencies = critical,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id":             self.report_id,
            "total_dependencies":    self.total_dependencies,
            "critical_dependencies": self.critical_dependencies,
            "subsystem_count":       len(self.subsystems),
            "critical_path_count":   len(self.critical_paths),
            "isolated_count":        len(self.isolated_subsystems),
            "generated_at":          self.generated_at,
        }


# ===========================================================================
# Platform Health Report
# ===========================================================================

@dataclass(frozen=True)
class SubsystemHealth:
    """Point-in-time health assessment of a single subsystem."""
    subsystem_id:  str
    status:        SubsystemStatus
    health_score:  float           = 1.0   # 0.0–1.0
    issues:        Tuple[str, ...] = ()
    last_updated:  float           = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "subsystem_id": self.subsystem_id,
            "status":       self.status.value,
            "health_score": self.health_score,
            "issues":       list(self.issues),
            "last_updated": self.last_updated,
        }


@dataclass(frozen=True)
class PlatformHealthReport:
    """Aggregated platform health report across all supervised subsystems."""
    report_id:      str
    subsystem_health: Tuple[SubsystemHealth, ...]
    overall_score:  float
    platform_status: SubsystemStatus
    healthy_count:  int           = 0
    degraded_count: int           = 0
    impaired_count: int           = 0
    critical_count: int           = 0
    unknown_count:  int           = 0
    generated_at:   float         = field(default_factory=time.time)
    framework_version: str        = VERSION

    @classmethod
    def create(
        cls,
        subsystem_health: Tuple[SubsystemHealth, ...],
        *,
        report_id: Optional[str] = None,
    ) -> "PlatformHealthReport":
        if not subsystem_health:
            overall_score  = 1.0
            platform_status = SubsystemStatus.UNKNOWN
        else:
            overall_score  = sum(h.health_score for h in subsystem_health) / len(subsystem_health)
            if overall_score >= 0.90:
                platform_status = SubsystemStatus.HEALTHY
            elif overall_score >= 0.70:
                platform_status = SubsystemStatus.DEGRADED
            elif overall_score >= 0.50:
                platform_status = SubsystemStatus.IMPAIRED
            elif overall_score > 0.0:
                platform_status = SubsystemStatus.CRITICAL
            else:
                platform_status = SubsystemStatus.UNKNOWN

        healthy  = sum(1 for h in subsystem_health if h.status == SubsystemStatus.HEALTHY)
        degraded = sum(1 for h in subsystem_health if h.status == SubsystemStatus.DEGRADED)
        impaired = sum(1 for h in subsystem_health if h.status == SubsystemStatus.IMPAIRED)
        critical = sum(1 for h in subsystem_health if h.status == SubsystemStatus.CRITICAL)
        unknown  = sum(1 for h in subsystem_health if h.status == SubsystemStatus.UNKNOWN)
        return cls(
            report_id       = report_id or str(uuid.uuid4()),
            subsystem_health = subsystem_health,
            overall_score   = overall_score,
            platform_status = platform_status,
            healthy_count   = healthy,
            degraded_count  = degraded,
            impaired_count  = impaired,
            critical_count  = critical,
            unknown_count   = unknown,
        )

    @property
    def is_healthy(self) -> bool:
        return self.platform_status == SubsystemStatus.HEALTHY

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id":      self.report_id,
            "overall_score":  self.overall_score,
            "platform_status": self.platform_status.value,
            "healthy_count":  self.healthy_count,
            "degraded_count": self.degraded_count,
            "impaired_count": self.impaired_count,
            "critical_count": self.critical_count,
            "unknown_count":  self.unknown_count,
            "is_healthy":     self.is_healthy,
            "generated_at":   self.generated_at,
        }


# ===========================================================================
# Governance Recommendations
# ===========================================================================

@dataclass(frozen=True)
class GovernanceRecommendation:
    """A single actionable governance recommendation."""
    recommendation_id: str
    priority:          RecommendationPriority
    subsystem_id:      str
    title:             str
    description:       str           = ""
    action:            str           = ""
    expected_impact:   str           = ""
    confidence:        float         = 0.5   # 0.0–1.0
    metadata:          Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        subsystem_id: str,
        title:        str,
        priority:     RecommendationPriority,
        *,
        recommendation_id: Optional[str] = None,
        description:   str = "",
        action:        str = "",
        expected_impact: str = "",
        confidence:    float = 0.5,
        metadata:      Optional[Dict[str, Any]] = None,
    ) -> "GovernanceRecommendation":
        return cls(
            recommendation_id = recommendation_id or str(uuid.uuid4()),
            priority          = priority,
            subsystem_id      = subsystem_id,
            title             = title,
            description       = description,
            action            = action,
            expected_impact   = expected_impact,
            confidence        = confidence,
            metadata          = metadata or {},
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "recommendation_id": self.recommendation_id,
            "priority":          self.priority.value,
            "subsystem_id":      self.subsystem_id,
            "title":             self.title,
            "description":       self.description,
            "action":            self.action,
            "confidence":        self.confidence,
        }


@dataclass(frozen=True)
class GovernanceRecommendations:
    """Aggregated governance recommendations."""
    report_id:      str
    recommendations: Tuple[GovernanceRecommendation, ...]
    total:          int
    critical_count: int           = 0
    high_count:     int           = 0
    generated_at:   float         = field(default_factory=time.time)
    framework_version: str        = VERSION

    @classmethod
    def create(
        cls,
        recommendations: Tuple[GovernanceRecommendation, ...],
        *,
        report_id: Optional[str] = None,
    ) -> "GovernanceRecommendations":
        critical = sum(1 for r in recommendations if r.priority == RecommendationPriority.CRITICAL)
        high     = sum(1 for r in recommendations if r.priority == RecommendationPriority.HIGH)
        return cls(
            report_id      = report_id or str(uuid.uuid4()),
            recommendations = recommendations,
            total          = len(recommendations),
            critical_count = critical,
            high_count     = high,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id":      self.report_id,
            "total":          self.total,
            "critical_count": self.critical_count,
            "high_count":     self.high_count,
            "generated_at":   self.generated_at,
        }


# ===========================================================================
# Self-Healing Plan
# ===========================================================================

@dataclass(frozen=True)
class SelfHealingActionItem:
    """A single self-healing action recommended for execution."""
    action_id:         str
    priority:          RecommendationPriority
    subsystem_id:      str
    action_type:       SelfHealingActionType
    description:       str           = ""
    expected_outcome:  str           = ""
    estimated_impact:  str           = ""
    is_automated:      bool          = False
    requires_approval: bool          = True
    metadata:          Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        subsystem_id:  str,
        action_type:   SelfHealingActionType,
        priority:      RecommendationPriority,
        *,
        action_id:         Optional[str]             = None,
        description:       str                       = "",
        expected_outcome:  str                       = "",
        estimated_impact:  str                       = "",
        is_automated:      bool                      = False,
        requires_approval: bool                      = True,
        metadata:          Optional[Dict[str, Any]]  = None,
    ) -> "SelfHealingActionItem":
        return cls(
            action_id         = action_id or str(uuid.uuid4()),
            priority          = priority,
            subsystem_id      = subsystem_id,
            action_type       = action_type,
            description       = description,
            expected_outcome  = expected_outcome,
            estimated_impact  = estimated_impact,
            is_automated      = is_automated,
            requires_approval = requires_approval,
            metadata          = metadata or {},
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action_id":         self.action_id,
            "priority":          self.priority.value,
            "subsystem_id":      self.subsystem_id,
            "action_type":       self.action_type.value,
            "description":       self.description,
            "is_automated":      self.is_automated,
            "requires_approval": self.requires_approval,
        }


@dataclass(frozen=True)
class SelfHealingPlan:
    """Aggregated self-healing plan with prioritised actions."""
    plan_id:            str
    actions:            Tuple[SelfHealingActionItem, ...]
    total:              int
    automated_actions:  int           = 0
    approval_required:  int           = 0
    can_auto_execute:   bool          = False
    generated_at:       float         = field(default_factory=time.time)
    framework_version:  str           = VERSION

    @classmethod
    def create(
        cls,
        actions: Tuple[SelfHealingActionItem, ...],
        *,
        plan_id: Optional[str] = None,
    ) -> "SelfHealingPlan":
        automated = sum(1 for a in actions if a.is_automated)
        approval  = sum(1 for a in actions if a.requires_approval)
        return cls(
            plan_id           = plan_id or str(uuid.uuid4()),
            actions           = actions,
            total             = len(actions),
            automated_actions = automated,
            approval_required = approval,
            can_auto_execute  = automated > 0 and approval == 0,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "plan_id":            self.plan_id,
            "total":              self.total,
            "automated_actions":  self.automated_actions,
            "approval_required":  self.approval_required,
            "can_auto_execute":   self.can_auto_execute,
            "generated_at":       self.generated_at,
        }


# ===========================================================================
# Enterprise State Report
# ===========================================================================

@dataclass(frozen=True)
class EnterpriseStateReport:
    """Enterprise-wide operational state assessment."""
    report_id:          str
    enterprise_state:   EnterpriseState
    stability_score:    float   = 1.0   # 0.0–1.0
    availability_score: float   = 1.0
    compliance_score:   float   = 1.0
    risk_level:         str     = "low"
    active_incidents:   int     = 0
    active_anomalies:   int     = 0
    supervision_strategy: SupervisionStrategyType = SupervisionStrategyType.STANDARD
    rationale:          str     = ""
    generated_at:       float   = field(default_factory=time.time)
    framework_version:  str     = VERSION

    @classmethod
    def create(
        cls,
        enterprise_state:   EnterpriseState,
        stability_score:    float = 1.0,
        availability_score: float = 1.0,
        compliance_score:   float = 1.0,
        *,
        report_id:             Optional[str]            = None,
        risk_level:            str                       = "low",
        active_incidents:      int                       = 0,
        active_anomalies:      int                       = 0,
        supervision_strategy:  SupervisionStrategyType   = SupervisionStrategyType.STANDARD,
        rationale:             str                       = "",
    ) -> "EnterpriseStateReport":
        return cls(
            report_id             = report_id or str(uuid.uuid4()),
            enterprise_state      = enterprise_state,
            stability_score       = stability_score,
            availability_score    = availability_score,
            compliance_score      = compliance_score,
            risk_level            = risk_level,
            active_incidents      = active_incidents,
            active_anomalies      = active_anomalies,
            supervision_strategy  = supervision_strategy,
            rationale             = rationale,
        )

    @property
    def is_emergency(self) -> bool:
        return self.enterprise_state == EnterpriseState.EMERGENCY

    @property
    def is_critical(self) -> bool:
        return self.enterprise_state in (EnterpriseState.CRITICAL, EnterpriseState.EMERGENCY)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id":             self.report_id,
            "enterprise_state":      self.enterprise_state.value,
            "stability_score":       self.stability_score,
            "availability_score":    self.availability_score,
            "compliance_score":      self.compliance_score,
            "risk_level":            self.risk_level,
            "active_incidents":      self.active_incidents,
            "active_anomalies":      self.active_anomalies,
            "supervision_strategy":  self.supervision_strategy.value,
            "is_emergency":          self.is_emergency,
            "generated_at":          self.generated_at,
        }


# ===========================================================================
# Enterprise Governance Report
# ===========================================================================

@dataclass(frozen=True)
class EnterpriseGovernanceReport:
    """Enterprise governance compliance report."""
    report_id:              str
    compliance_score:       float          = 1.0
    governance_decision:    GovernanceDecision = GovernanceDecision.CONTINUE
    policy_adherence_score: float          = 1.0
    governance_score:       float          = 1.0
    violations:             Tuple[str, ...] = ()
    compliance_notes:       Tuple[str, ...] = ()
    generated_at:           float          = field(default_factory=time.time)
    framework_version:      str            = VERSION

    @classmethod
    def create(
        cls,
        compliance_score:       float              = 1.0,
        governance_decision:    GovernanceDecision  = GovernanceDecision.CONTINUE,
        policy_adherence_score: float              = 1.0,
        governance_score:       float              = 1.0,
        *,
        report_id:         Optional[str]          = None,
        violations:        Tuple[str, ...] = (),
        compliance_notes:  Tuple[str, ...] = (),
    ) -> "EnterpriseGovernanceReport":
        return cls(
            report_id              = report_id or str(uuid.uuid4()),
            compliance_score       = compliance_score,
            governance_decision    = governance_decision,
            policy_adherence_score = policy_adherence_score,
            governance_score       = governance_score,
            violations             = violations,
            compliance_notes       = compliance_notes,
        )

    @property
    def is_compliant(self) -> bool:
        return self.compliance_score >= 0.80 and not self.violations

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id":              self.report_id,
            "compliance_score":       self.compliance_score,
            "governance_decision":    self.governance_decision.value,
            "policy_adherence_score": self.policy_adherence_score,
            "governance_score":       self.governance_score,
            "violations":             list(self.violations),
            "is_compliant":           self.is_compliant,
            "generated_at":           self.generated_at,
        }


# ===========================================================================
# Autonomous Governance Summary
# ===========================================================================

@dataclass(frozen=True)
class AutonomousGovernanceSummary:
    """
    Complete output of a single autonomous governance assessment cycle.

    Contains all 10 governance reports plus metadata.
    """
    summary_id:          str
    supervision_id:      str
    subsystem_id:        str
    workflow_type:       str
    governance_report:   EnterpriseGovernanceReport
    platform_health:     PlatformHealthReport
    anomaly_report:      AnomalyReport
    incident_report:     IncidentReport
    root_cause_report:   RootCauseReport
    dependency_report:   DependencyReport
    recommendations:     GovernanceRecommendations
    self_healing_plan:   SelfHealingPlan
    enterprise_state:    EnterpriseStateReport
    final_decision:      GovernanceDecision   = GovernanceDecision.CONTINUE
    reasoning_summary:   str                  = ""
    elapsed_s:           float                = 0.0
    is_success:          bool                 = True
    error_message:       str                  = ""
    generated_at:        float                = field(default_factory=time.time)
    framework_version:   str                  = VERSION

    @classmethod
    def create_success(
        cls,
        supervision_id:    str,
        subsystem_id:      str,
        workflow_type:     str,
        governance_report: EnterpriseGovernanceReport,
        platform_health:   PlatformHealthReport,
        anomaly_report:    AnomalyReport,
        incident_report:   IncidentReport,
        root_cause_report: RootCauseReport,
        dependency_report: DependencyReport,
        recommendations:   GovernanceRecommendations,
        self_healing_plan: SelfHealingPlan,
        enterprise_state:  EnterpriseStateReport,
        *,
        summary_id:        Optional[str]  = None,
        final_decision:    GovernanceDecision = GovernanceDecision.CONTINUE,
        reasoning_summary: str            = "",
        elapsed_s:         float          = 0.0,
    ) -> "AutonomousGovernanceSummary":
        return cls(
            summary_id        = summary_id or str(uuid.uuid4()),
            supervision_id    = supervision_id,
            subsystem_id      = subsystem_id,
            workflow_type     = workflow_type,
            governance_report = governance_report,
            platform_health   = platform_health,
            anomaly_report    = anomaly_report,
            incident_report   = incident_report,
            root_cause_report = root_cause_report,
            dependency_report = dependency_report,
            recommendations   = recommendations,
            self_healing_plan = self_healing_plan,
            enterprise_state  = enterprise_state,
            final_decision    = final_decision,
            reasoning_summary = reasoning_summary,
            elapsed_s         = elapsed_s,
            is_success        = True,
            error_message     = "",
        )

    @classmethod
    def create_failure(
        cls,
        supervision_id: str,
        subsystem_id:   str,
        workflow_type:  str,
        error_message:  str,
        *,
        summary_id: Optional[str] = None,
        elapsed_s:  float         = 0.0,
    ) -> "AutonomousGovernanceSummary":
        empty_gov   = EnterpriseGovernanceReport.create(
            compliance_score=0.0, governance_decision=GovernanceDecision.HALT,
            governance_score=0.0,
        )
        empty_health = PlatformHealthReport.create(())
        empty_anomaly = AnomalyReport.create(())
        empty_incident = IncidentReport.create(())
        empty_rc = RootCauseReport.create(())
        empty_dep = DependencyReport.create((), ())
        empty_rec = GovernanceRecommendations.create(())
        empty_plan = SelfHealingPlan.create(())
        empty_state = EnterpriseStateReport.create(
            EnterpriseState.UNKNOWN, 0.0, 0.0, 0.0,
        )
        return cls(
            summary_id        = summary_id or str(uuid.uuid4()),
            supervision_id    = supervision_id,
            subsystem_id      = subsystem_id,
            workflow_type     = workflow_type,
            governance_report = empty_gov,
            platform_health   = empty_health,
            anomaly_report    = empty_anomaly,
            incident_report   = empty_incident,
            root_cause_report = empty_rc,
            dependency_report = empty_dep,
            recommendations   = empty_rec,
            self_healing_plan = empty_plan,
            enterprise_state  = empty_state,
            final_decision    = GovernanceDecision.HALT,
            reasoning_summary = f"Assessment failed: {error_message}",
            elapsed_s         = elapsed_s,
            is_success        = False,
            error_message     = error_message,
        )

    @property
    def is_emergency(self) -> bool:
        return self.enterprise_state.is_emergency

    @property
    def anomaly_count(self) -> int:
        return self.anomaly_report.total

    @property
    def incident_count(self) -> int:
        return self.incident_report.total

    def to_dict(self) -> Dict[str, Any]:
        return {
            "summary_id":       self.summary_id,
            "supervision_id":   self.supervision_id,
            "subsystem_id":     self.subsystem_id,
            "workflow_type":    self.workflow_type,
            "governance_report": self.governance_report.to_dict(),
            "platform_health":  self.platform_health.to_dict(),
            "anomaly_report":   self.anomaly_report.to_dict(),
            "incident_report":  self.incident_report.to_dict(),
            "root_cause_report": self.root_cause_report.to_dict(),
            "dependency_report": self.dependency_report.to_dict(),
            "recommendations":  self.recommendations.to_dict(),
            "self_healing_plan": self.self_healing_plan.to_dict(),
            "enterprise_state": self.enterprise_state.to_dict(),
            "final_decision":   self.final_decision.value,
            "reasoning_summary": self.reasoning_summary,
            "elapsed_s":        self.elapsed_s,
            "is_success":       self.is_success,
            "error_message":    self.error_message,
            "is_emergency":     self.is_emergency,
            "anomaly_count":    self.anomaly_count,
            "incident_count":   self.incident_count,
            "generated_at":     self.generated_at,
            "framework_version": self.framework_version,
        }
