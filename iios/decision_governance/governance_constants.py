"""iios/decision_governance/governance_constants.py"""
from __future__ import annotations

from enum import Enum


class GovernanceStatus(Enum):
    PENDING   = "pending"
    APPROVED  = "approved"
    REJECTED  = "rejected"
    ESCALATED = "escalated"
    EXPIRED   = "expired"
    CERTIFIED = "certified"
    REVOKED   = "revoked"


class ApprovalLevel(Enum):
    AUTO       = "auto"
    SINGLE     = "single"
    MULTI      = "multi"
    ESCALATION = "escalation"


class ApprovalMode(Enum):
    AUTOMATIC   = "automatic"
    MANUAL      = "manual"
    CONDITIONAL = "conditional"
    DELEGATED   = "delegated"


class ApprovalStatus(Enum):
    PENDING   = "pending"
    APPROVED  = "approved"
    REJECTED  = "rejected"
    ESCALATED = "escalated"
    EXPIRED   = "expired"


class PolicyType(Enum):
    GOVERNANCE    = "governance"
    INSTITUTIONAL = "institutional"
    COMPLIANCE    = "compliance"
    RISK          = "risk"
    APPROVAL      = "approval"
    EXCEPTION     = "exception"
    CUSTOM        = "custom"


class PolicyViolationSeverity(Enum):
    INFO     = "info"
    WARNING  = "warning"
    ERROR    = "error"
    CRITICAL = "critical"


class AuditEventType(Enum):
    SUBMITTED  = "submitted"
    VALIDATED  = "validated"
    APPROVED   = "approved"
    REJECTED   = "rejected"
    ESCALATED  = "escalated"
    EXPIRED    = "expired"
    CERTIFIED  = "certified"
    REVOKED    = "revoked"
    REPLAYED   = "replayed"
    COMPARED   = "compared"
    VIOLATION  = "violation"
    SNAPSHOT   = "snapshot"


class GovernanceMode(Enum):
    STRICT     = "strict"      # any blocking violation → reject
    LENIENT    = "lenient"     # violations are warnings; approval decides
    AUDIT_ONLY = "audit_only"  # record everything, never block
    BYPASS     = "bypass"      # no checks; used for testing/emergency


class AlertSeverity(Enum):
    INFO     = "info"
    WARNING  = "warning"
    ERROR    = "error"
    CRITICAL = "critical"


GOVERNANCE_ENGINE_VERSION   = "1.0.0"
GOVERNANCE_ENGINE_SYSTEM_ID = "iios:governance:engine"

MAX_HISTORY_PER_DECISION  = 100
DEFAULT_APPROVAL_TTL_SEC  = 3_600
DEFAULT_GOVERNANCE_MODE   = GovernanceMode.LENIENT
MAX_ESCALATION_DEPTH      = 5
DEFAULT_CERT_TTL_SEC      = 86_400   # 24 h
MAX_REGISTRY_SIZE         = 10_000
MAX_AUDIT_EVENTS          = 1_000_000
