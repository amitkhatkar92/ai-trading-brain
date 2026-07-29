"""
governance_events.py -- iios.ai.governance.events
===================================================
Immutable event types for the A8 AI Governance Platform.

A8 AI Governance Platform — Phase 3, Module 8
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from enum import Enum
from typing import Any, FrozenSet, Optional, Tuple


class GovernanceEventType(str, Enum):
    """All governance event types."""
    POLICY_EVALUATED          = "policy_evaluated"
    POLICY_VIOLATED           = "policy_violated"
    POLICY_REGISTERED         = "policy_registered"
    PERMISSION_GRANTED        = "permission_granted"
    PERMISSION_DENIED         = "permission_denied"
    ROLE_ASSIGNED             = "role_assigned"
    AUDIT_RECORDED            = "audit_recorded"
    EXPLANATION_GENERATED     = "explanation_generated"
    COMPLIANCE_CHECKED        = "compliance_checked"
    COMPLIANCE_VIOLATED       = "compliance_violated"
    GOVERNANCE_DECISION_ISSUED = "governance_decision_issued"
    RISK_THRESHOLD_EXCEEDED   = "risk_threshold_exceeded"
    ESCALATION_TRIGGERED      = "escalation_triggered"


@dataclass(frozen=True)
class GovernanceEvent:
    """Base immutable governance event."""

    event_id:   str
    event_type: GovernanceEventType
    source_id:  str
    occurred_at: float
    metadata:   FrozenSet[Tuple[str, Any]]

    @classmethod
    def _base(
        cls,
        event_type: GovernanceEventType,
        source_id:  str,
        **metadata: Any,
    ) -> dict:
        return {
            "event_id":    str(uuid.uuid4()),
            "event_type":  event_type,
            "source_id":   source_id,
            "occurred_at": time.time(),
            "metadata":    frozenset(metadata.items()),
        }


# ── Policy events ─────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class PolicyEvaluatedEvent(GovernanceEvent):
    policy_id: str
    allowed: bool
    action: str

    @classmethod
    def create(cls, source_id: str, policy_id: str, allowed: bool, action: str, **m: Any) -> "PolicyEvaluatedEvent":
        return cls(**GovernanceEvent._base(GovernanceEventType.POLICY_EVALUATED, source_id, **m),
                   policy_id=policy_id, allowed=allowed, action=action)


@dataclass(frozen=True)
class PolicyViolatedEvent(GovernanceEvent):
    policy_id: str
    principal_id: str
    action: str

    @classmethod
    def create(cls, source_id: str, policy_id: str, principal_id: str, action: str, **m: Any) -> "PolicyViolatedEvent":
        return cls(**GovernanceEvent._base(GovernanceEventType.POLICY_VIOLATED, source_id, **m),
                   policy_id=policy_id, principal_id=principal_id, action=action)


@dataclass(frozen=True)
class PolicyRegisteredEvent(GovernanceEvent):
    policy_id: str
    policy_name: str

    @classmethod
    def create(cls, source_id: str, policy_id: str, policy_name: str, **m: Any) -> "PolicyRegisteredEvent":
        return cls(**GovernanceEvent._base(GovernanceEventType.POLICY_REGISTERED, source_id, **m),
                   policy_id=policy_id, policy_name=policy_name)


# ── Permission events ─────────────────────────────────────────────────────────

@dataclass(frozen=True)
class PermissionGrantedEvent(GovernanceEvent):
    principal_id: str
    action: str
    resource: str

    @classmethod
    def create(cls, source_id: str, principal_id: str, action: str, resource: str, **m: Any) -> "PermissionGrantedEvent":
        return cls(**GovernanceEvent._base(GovernanceEventType.PERMISSION_GRANTED, source_id, **m),
                   principal_id=principal_id, action=action, resource=resource)


@dataclass(frozen=True)
class PermissionDeniedEvent(GovernanceEvent):
    principal_id: str
    action: str
    resource: str
    reason: str

    @classmethod
    def create(cls, source_id: str, principal_id: str, action: str, resource: str, reason: str, **m: Any) -> "PermissionDeniedEvent":
        return cls(**GovernanceEvent._base(GovernanceEventType.PERMISSION_DENIED, source_id, **m),
                   principal_id=principal_id, action=action, resource=resource, reason=reason)


# ── Audit events ──────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class AuditRecordedEvent(GovernanceEvent):
    audit_id: str
    subject_id: str
    action: str

    @classmethod
    def create(cls, source_id: str, audit_id: str, subject_id: str, action: str, **m: Any) -> "AuditRecordedEvent":
        return cls(**GovernanceEvent._base(GovernanceEventType.AUDIT_RECORDED, source_id, **m),
                   audit_id=audit_id, subject_id=subject_id, action=action)


# ── Explainability events ─────────────────────────────────────────────────────

@dataclass(frozen=True)
class ExplanationGeneratedEvent(GovernanceEvent):
    explanation_id: str
    decision_id: str

    @classmethod
    def create(cls, source_id: str, explanation_id: str, decision_id: str, **m: Any) -> "ExplanationGeneratedEvent":
        return cls(**GovernanceEvent._base(GovernanceEventType.EXPLANATION_GENERATED, source_id, **m),
                   explanation_id=explanation_id, decision_id=decision_id)


# ── Compliance events ─────────────────────────────────────────────────────────

@dataclass(frozen=True)
class ComplianceCheckedEvent(GovernanceEvent):
    subject_id: str
    passed: bool
    rules_evaluated: int

    @classmethod
    def create(cls, source_id: str, subject_id: str, passed: bool, rules_evaluated: int, **m: Any) -> "ComplianceCheckedEvent":
        return cls(**GovernanceEvent._base(GovernanceEventType.COMPLIANCE_CHECKED, source_id, **m),
                   subject_id=subject_id, passed=passed, rules_evaluated=rules_evaluated)


@dataclass(frozen=True)
class ComplianceViolatedEvent(GovernanceEvent):
    subject_id: str
    rule_id: str
    severity: str

    @classmethod
    def create(cls, source_id: str, subject_id: str, rule_id: str, severity: str, **m: Any) -> "ComplianceViolatedEvent":
        return cls(**GovernanceEvent._base(GovernanceEventType.COMPLIANCE_VIOLATED, source_id, **m),
                   subject_id=subject_id, rule_id=rule_id, severity=severity)


# ── Governance decision events ────────────────────────────────────────────────

@dataclass(frozen=True)
class GovernanceDecisionIssuedEvent(GovernanceEvent):
    decision_id: str
    decision_type: str
    subject_id: str

    @classmethod
    def create(cls, source_id: str, decision_id: str, decision_type: str, subject_id: str, **m: Any) -> "GovernanceDecisionIssuedEvent":
        return cls(**GovernanceEvent._base(GovernanceEventType.GOVERNANCE_DECISION_ISSUED, source_id, **m),
                   decision_id=decision_id, decision_type=decision_type, subject_id=subject_id)


# ── Risk events ───────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class RiskThresholdExceededEvent(GovernanceEvent):
    subject_id: str
    threshold_name: str
    actual_value: float
    threshold_value: float

    @classmethod
    def create(cls, source_id: str, subject_id: str, threshold_name: str,
               actual_value: float, threshold_value: float, **m: Any) -> "RiskThresholdExceededEvent":
        return cls(**GovernanceEvent._base(GovernanceEventType.RISK_THRESHOLD_EXCEEDED, source_id, **m),
                   subject_id=subject_id, threshold_name=threshold_name,
                   actual_value=actual_value, threshold_value=threshold_value)


@dataclass(frozen=True)
class EscalationTriggeredEvent(GovernanceEvent):
    subject_id: str
    reason: str
    severity: str

    @classmethod
    def create(cls, source_id: str, subject_id: str, reason: str, severity: str, **m: Any) -> "EscalationTriggeredEvent":
        return cls(**GovernanceEvent._base(GovernanceEventType.ESCALATION_TRIGGERED, source_id, **m),
                   subject_id=subject_id, reason=reason, severity=severity)
