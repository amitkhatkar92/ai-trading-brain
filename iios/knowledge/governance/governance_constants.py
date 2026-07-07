"""
iios/knowledge/governance/governance_constants.py
==================================================
Governance workflow enumerations and operational constants.
"""

from __future__ import annotations

from enum import Enum
from typing import Final

__all__ = [
    "ApprovalStatus",
    "CertificationStatus",
    "PolicyType",
    "GovernanceAction",
    "MonitorEventType",
    "RiskLevel",
    "CertificationLevel",
    "DEFAULT_CERTIFICATION_TTL_DAYS",
    "DEFAULT_RENEWAL_NOTICE_DAYS",
    "MAX_GOVERNANCE_RECORDS_PER_ITEM",
    "MAX_CERTIFICATIONS_PER_ITEM",
    "MAX_POLICIES",
    "MAX_AUDIT_ENTRIES",
    "SENSITIVE_DOMAINS",
    "REQUIRED_FIELDS_FOR_APPROVAL",
    "GOVERNANCE_NAMESPACE",
    "SYSTEM_GOVERNANCE_ACTOR",
    "GOVERNANCE_SCHEMA_VERSION",
]


class ApprovalStatus(str, Enum):
    """Lifecycle state of a knowledge governance record."""

    PENDING       = "pending"         # submitted; awaiting decision
    UNDER_REVIEW  = "under_review"    # assigned to a reviewer
    APPROVED      = "approved"        # accepted into the knowledge base
    AUTO_APPROVED = "auto_approved"   # approved by policy (no manual review)
    REJECTED      = "rejected"        # declined; record flagged INVALID
    REVOKED       = "revoked"         # previously approved; approval withdrawn
    ESCALATED     = "escalated"       # raised to senior reviewer


class CertificationStatus(str, Enum):
    """Lifecycle state of a knowledge certification."""

    UNCERTIFIED = "uncertified"
    CERTIFIED   = "certified"
    EXPIRED     = "expired"
    REVOKED     = "revoked"


class PolicyType(str, Enum):
    """Type of governance policy."""

    AUTO_APPROVE    = "auto_approve"     # auto-approve if conditions met
    AUTO_REJECT     = "auto_reject"      # auto-reject if conditions met
    REQUIRE_MANUAL  = "require_manual"   # always escalate to human
    BLOCK           = "block"            # hard block — no approval possible
    EXPIRY_BASED    = "expiry_based"     # enforce TTL and recertification
    DOMAIN_SPECIFIC = "domain_specific"  # applies to specific domain only
    THRESHOLD_GATE  = "threshold_gate"   # gate on quality threshold


class GovernanceAction(str, Enum):
    """Governance workflow action types."""

    SUBMIT           = "submit"
    APPROVE          = "approve"
    AUTO_APPROVE     = "auto_approve"
    REJECT           = "reject"
    REVIEW           = "review"
    ESCALATE         = "escalate"
    CERTIFY          = "certify"
    REVOKE_CERT      = "revoke_certification"
    RETIRE           = "retire"
    RESTORE          = "restore"
    ARCHIVE          = "archive"
    POLICY_ADDED     = "policy_added"
    POLICY_CHANGED   = "policy_changed"
    POLICY_REMOVED   = "policy_removed"
    QUALITY_FLAGGED  = "quality_flagged"
    REVOKE_APPROVAL  = "revoke_approval"
    RE_CERTIFY       = "re_certify"


class MonitorEventType(str, Enum):
    """Types of events emitted by the quality monitor."""

    QUALITY_DEGRADED     = "quality.degraded"
    FRESHNESS_EXPIRED    = "freshness.expired"
    CERTIFICATION_EXPIRED= "certification.expired"
    REFERENCE_BROKEN     = "reference.broken"
    STALE_KNOWLEDGE      = "knowledge.stale"
    DUPLICATE_DETECTED   = "duplicate.detected"
    MISSING_METADATA     = "metadata.missing"
    ONTOLOGY_DRIFT       = "ontology.drift"
    POLICY_VIOLATION     = "policy.violation"


class RiskLevel(str, Enum):
    """Risk level associated with a governance decision or policy."""

    LOW      = "low"
    MEDIUM   = "medium"
    HIGH     = "high"
    CRITICAL = "critical"


class CertificationLevel(str, Enum):
    """Tier of certification granted."""

    STANDARD  = "standard"   # baseline review
    SILVER    = "silver"     # deeper review + source check
    GOLD      = "gold"       # expert review + cross-validation
    PLATINUM  = "platinum"   # highest rigour; audited externally


# ── Operational constants ─────────────────────────────────────────────────────

DEFAULT_CERTIFICATION_TTL_DAYS:   Final[int] = 90
DEFAULT_RENEWAL_NOTICE_DAYS:      Final[int] = 14
MAX_GOVERNANCE_RECORDS_PER_ITEM:  Final[int] = 1_000
MAX_CERTIFICATIONS_PER_ITEM:      Final[int] = 100
MAX_POLICIES:                     Final[int] = 500
MAX_AUDIT_ENTRIES:                Final[int] = 50_000

GOVERNANCE_NAMESPACE:      Final[str] = "iios.governance"
SYSTEM_GOVERNANCE_ACTOR:  Final[str] = "iios:governance"
GOVERNANCE_SCHEMA_VERSION: Final[str] = "1.0.0"

# Domain values that require manual approval (no auto-approve)
SENSITIVE_DOMAINS: Final[frozenset[str]] = frozenset({
    "compliance",
    "risk",
})

# Fields that must be set before approval is considered
REQUIRED_FIELDS_FOR_APPROVAL: Final[frozenset[str]] = frozenset({
    "title",
    "content",
    "knowledge_type",
})
