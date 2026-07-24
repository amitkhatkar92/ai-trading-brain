"""
supervisor_integration_response.py — iios.supervisor.integration
-----------------------------------------------------------------
Integration response and auxiliary summary value objects.

Exports
-------
PlatformHealthSummary          — condensed platform health summary
IntegrationGovernanceSummary   — condensed governance outcome summary
EnterpriseAssessment           — condensed enterprise state assessment
SupervisorIntegrationResponse  — full integration response

C13 AI Supervisor & Autonomous Governance — Phase 1, Module 6
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple

from .constants import VERSION


# ---------------------------------------------------------------------------
# PlatformHealthSummary
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PlatformHealthSummary:
    """
    Condensed platform health summary derived from the M2 engine output.

    Fields
    ------
    summary_id :         Unique identifier.
    overall_health :     Composite health score [0.0–1.0].
    platform_status :    Human-readable platform status string.
    active_alerts :      Number of active health alerts.
    subsystem_statuses : Per-subsystem status map.
    generated_at :       Wall-clock generation time.
    framework_version :  Framework version string.
    """
    summary_id:         str
    overall_health:     float
    platform_status:    str
    active_alerts:      int
    subsystem_statuses: Dict[str, str]
    generated_at:       float = field(default_factory=time.time)
    framework_version:  str   = VERSION

    @classmethod
    def create(
        cls,
        overall_health:     float                    = 1.0,
        platform_status:    str                      = "HEALTHY",
        active_alerts:      int                      = 0,
        subsystem_statuses: Optional[Dict[str, str]] = None,
        *,
        summary_id: Optional[str] = None,
    ) -> "PlatformHealthSummary":
        return cls(
            summary_id         = summary_id or str(uuid.uuid4()),
            overall_health     = max(0.0, min(1.0, overall_health)),
            platform_status    = platform_status,
            active_alerts      = max(0, active_alerts),
            subsystem_statuses = subsystem_statuses or {},
        )

    @property
    def is_healthy(self) -> bool:
        return self.overall_health >= 0.90 and self.active_alerts == 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "summary_id":         self.summary_id,
            "overall_health":     self.overall_health,
            "platform_status":    self.platform_status,
            "active_alerts":      self.active_alerts,
            "subsystem_statuses": self.subsystem_statuses,
            "is_healthy":         self.is_healthy,
            "generated_at":       self.generated_at,
        }


# ---------------------------------------------------------------------------
# IntegrationGovernanceSummary
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class IntegrationGovernanceSummary:
    """
    Condensed governance outcome derived from M3 + M4 pipeline.

    Fields
    ------
    summary_id :         Unique identifier.
    final_action :       Final governance action string (from M3).
    governance_decision: Autonomous governance decision string (from M4).
    is_compliant :       True when outcome is permissive.
    violations :         Tuple of governance violation descriptions.
    policy_rationale :   Human-readable M3 policy rationale.
    generated_at :       Wall-clock generation time.
    framework_version :  Framework version string.
    """
    summary_id:          str
    final_action:        str
    governance_decision: str
    is_compliant:        bool
    violations:          Tuple[str, ...]
    policy_rationale:    str
    generated_at:        float = field(default_factory=time.time)
    framework_version:   str   = VERSION

    @classmethod
    def create(
        cls,
        final_action:        str           = "APPROVE",
        governance_decision: str           = "CONTINUE",
        is_compliant:        bool          = True,
        violations:          Tuple[str, ...] = (),
        policy_rationale:    str           = "",
        *,
        summary_id: Optional[str] = None,
    ) -> "IntegrationGovernanceSummary":
        return cls(
            summary_id          = summary_id or str(uuid.uuid4()),
            final_action        = final_action,
            governance_decision = governance_decision,
            is_compliant        = is_compliant,
            violations          = violations,
            policy_rationale    = policy_rationale,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "summary_id":          self.summary_id,
            "final_action":        self.final_action,
            "governance_decision": self.governance_decision,
            "is_compliant":        self.is_compliant,
            "violations":          list(self.violations),
            "policy_rationale":    self.policy_rationale,
            "generated_at":        self.generated_at,
        }


# ---------------------------------------------------------------------------
# EnterpriseAssessment
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EnterpriseAssessment:
    """
    Condensed enterprise state assessment derived from the M4 output.

    Fields
    ------
    assessment_id :   Unique identifier.
    enterprise_state: Human-readable enterprise state string.
    stability_score : Stability score [0.0–1.0].
    confidence :      Assessment confidence [0.0–1.0].
    anomaly_count :   Total anomalies detected.
    incident_count :  Total incidents correlated.
    reasoning :       Human-readable assessment summary.
    generated_at :    Wall-clock generation time.
    framework_version: Framework version string.
    """
    assessment_id:    str
    enterprise_state: str
    stability_score:  float
    confidence:       float
    anomaly_count:    int
    incident_count:   int
    reasoning:        str
    generated_at:     float = field(default_factory=time.time)
    framework_version: str  = VERSION

    @classmethod
    def create(
        cls,
        enterprise_state: str   = "STABLE",
        stability_score:  float = 1.0,
        confidence:       float = 1.0,
        anomaly_count:    int   = 0,
        incident_count:   int   = 0,
        reasoning:        str   = "",
        *,
        assessment_id: Optional[str] = None,
    ) -> "EnterpriseAssessment":
        return cls(
            assessment_id    = assessment_id or str(uuid.uuid4()),
            enterprise_state = enterprise_state,
            stability_score  = max(0.0, min(1.0, stability_score)),
            confidence       = max(0.0, min(1.0, confidence)),
            anomaly_count    = max(0, anomaly_count),
            incident_count   = max(0, incident_count),
            reasoning        = reasoning,
        )

    @property
    def is_stable(self) -> bool:
        return self.stability_score >= 0.90

    def to_dict(self) -> Dict[str, Any]:
        return {
            "assessment_id":   self.assessment_id,
            "enterprise_state": self.enterprise_state,
            "stability_score": self.stability_score,
            "confidence":      self.confidence,
            "anomaly_count":   self.anomaly_count,
            "incident_count":  self.incident_count,
            "reasoning":       self.reasoning,
            "is_stable":       self.is_stable,
            "generated_at":    self.generated_at,
        }


# ---------------------------------------------------------------------------
# SupervisorIntegrationResponse
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SupervisorIntegrationResponse:
    """
    Immutable output of a single AI Supervisor Integration cycle.

    Fields
    ------
    response_id :            Unique response identifier.
    integration_id :         Integration run identifier.
    request_id :             Originating request identifier.
    session_id :             Owning lifecycle session identifier.
    is_success :             True when the full pipeline succeeded.
    error_message :          Non-empty on failure.
    supervisor_snapshot :    M5 supervisor snapshot (None on failure).
    platform_health_summary: Condensed platform health from M2.
    governance_summary :     Condensed governance outcome from M3+M4.
    enterprise_assessment :  Condensed enterprise assessment from M4.
    processing_time_s :      Total pipeline processing time (seconds).
    generated_at :           Wall-clock response creation time.
    framework_version :      Framework version string.
    """
    response_id:             str
    integration_id:          str
    request_id:              str
    session_id:              str
    is_success:              bool
    error_message:           str
    supervisor_snapshot:     Optional[Any]                       # SupervisorSnapshot from M5
    platform_health_summary: PlatformHealthSummary
    governance_summary:      IntegrationGovernanceSummary
    enterprise_assessment:   EnterpriseAssessment
    processing_time_s:       float
    generated_at:            float = field(default_factory=time.time)
    framework_version:       str   = VERSION

    # ------------------------------------------------------------------
    # Factories
    # ------------------------------------------------------------------

    @classmethod
    def create_success(
        cls,
        integration_id:          str,
        request_id:              str,
        session_id:              str                              = "",
        supervisor_snapshot:     Optional[Any]                   = None,
        platform_health_summary: Optional[PlatformHealthSummary] = None,
        governance_summary:      Optional[IntegrationGovernanceSummary] = None,
        enterprise_assessment:   Optional[EnterpriseAssessment]  = None,
        processing_time_s:       float                           = 0.0,
        *,
        response_id: Optional[str] = None,
    ) -> "SupervisorIntegrationResponse":
        return cls(
            response_id             = response_id or str(uuid.uuid4()),
            integration_id          = integration_id,
            request_id              = request_id,
            session_id              = session_id,
            is_success              = True,
            error_message           = "",
            supervisor_snapshot     = supervisor_snapshot,
            platform_health_summary = platform_health_summary or PlatformHealthSummary.create(),
            governance_summary      = governance_summary or IntegrationGovernanceSummary.create(),
            enterprise_assessment   = enterprise_assessment or EnterpriseAssessment.create(),
            processing_time_s       = max(0.0, processing_time_s),
        )

    @classmethod
    def create_failure(
        cls,
        integration_id:    str,
        request_id:        str,
        error:             str = "",
        session_id:        str = "",
        processing_time_s: float = 0.0,
        *,
        response_id: Optional[str] = None,
    ) -> "SupervisorIntegrationResponse":
        return cls(
            response_id             = response_id or str(uuid.uuid4()),
            integration_id          = integration_id,
            request_id              = request_id,
            session_id              = session_id,
            is_success              = False,
            error_message           = error,
            supervisor_snapshot     = None,
            platform_health_summary = PlatformHealthSummary.create(
                overall_health=0.0, platform_status="UNKNOWN",
            ),
            governance_summary      = IntegrationGovernanceSummary.create(
                final_action="HALT", governance_decision="HALT", is_compliant=False,
            ),
            enterprise_assessment   = EnterpriseAssessment.create(
                enterprise_state="UNKNOWN", stability_score=0.0, confidence=0.0,
                reasoning=error,
            ),
            processing_time_s       = max(0.0, processing_time_s),
        )

    # ------------------------------------------------------------------
    # Derived properties
    # ------------------------------------------------------------------

    @property
    def has_snapshot(self) -> bool:
        return self.supervisor_snapshot is not None

    @property
    def is_healthy(self) -> bool:
        return self.is_success and self.platform_health_summary.is_healthy

    def to_dict(self) -> Dict[str, Any]:
        return {
            "response_id":       self.response_id,
            "integration_id":   self.integration_id,
            "request_id":       self.request_id,
            "session_id":       self.session_id,
            "is_success":       self.is_success,
            "error_message":    self.error_message,
            "has_snapshot":     self.has_snapshot,
            "processing_time_s": self.processing_time_s,
            "platform_health":  self.platform_health_summary.to_dict(),
            "governance":       self.governance_summary.to_dict(),
            "enterprise":       self.enterprise_assessment.to_dict(),
            "generated_at":     self.generated_at,
            "framework_version": self.framework_version,
        }
