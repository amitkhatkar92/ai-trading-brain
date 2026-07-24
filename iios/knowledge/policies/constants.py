"""
constants.py — iios.knowledge.policies
========================================
Enumerations, state machine, identifiers, and defaults for the
Institutional Knowledge Governance Policy Framework.

C14 Enterprise Knowledge Intelligence — Phase 1, Module 3
"""
from __future__ import annotations

from enum import Enum, IntEnum

# ---------------------------------------------------------------------------
# System identifiers
# ---------------------------------------------------------------------------
GOVERNANCE_SYSTEM_ID: str = "iios:knowledge:governance"
EVALUATOR_SYSTEM_ID:  str = "iios:knowledge:governance:evaluator"
REGISTRY_SYSTEM_ID:   str = "iios:knowledge:governance:registry"
CHAIN_SYSTEM_ID:      str = "iios:knowledge:governance:chain"
AUDIT_SYSTEM_ID:      str = "iios:knowledge:governance:audit"

# ---------------------------------------------------------------------------
# Versioning
# ---------------------------------------------------------------------------
VERSION:        str = "1.0.0"
SCHEMA_VERSION: str = "1.0"

# ---------------------------------------------------------------------------
# Actor constants
# ---------------------------------------------------------------------------
ACTOR_GOVERNANCE: str = "iios:knowledge:governance"
ACTOR_EVALUATOR:  str = "iios:knowledge:governance:evaluator"
ACTOR_AUDITOR:    str = "iios:knowledge:governance:audit"
ACTOR_OPERATOR:   str = "operator"
ACTOR_SYSTEM:     str = "iios:system"

# ---------------------------------------------------------------------------
# Default limits
# ---------------------------------------------------------------------------
DEFAULT_MAX_POLICIES:         int   = 1_000
DEFAULT_MAX_HISTORY:          int   = 5_000
DEFAULT_MAX_AUDIT_ENTRIES:    int   = 50_000
DEFAULT_MAX_CHAIN_DEPTH:      int   = 10
DEFAULT_EVALUATION_TIMEOUT_S: float = 30.0


# ---------------------------------------------------------------------------
# GovernanceEngineState — (9 states)
# ---------------------------------------------------------------------------
class GovernanceEngineState(str, Enum):
    """States of the governance policy engine processing cycle."""
    IDLE       = "idle"
    LOADING    = "loading"
    VALIDATING = "validating"
    EVALUATING = "evaluating"
    RESOLVING  = "resolving"
    AUDITING   = "auditing"
    COMPLETED  = "completed"
    FAILED     = "failed"
    STOPPED    = "stopped"


# ---------------------------------------------------------------------------
# PolicyType — (15 types)
# ---------------------------------------------------------------------------
class PolicyType(str, Enum):
    """Knowledge governance policy types."""
    CLASSIFICATION = "knowledge_classification"
    QUALITY        = "knowledge_quality"
    VALIDATION     = "knowledge_validation"
    VERSIONING     = "knowledge_versioning"
    RETENTION      = "knowledge_retention"
    PUBLICATION    = "knowledge_publication"
    SECURITY       = "knowledge_security"
    PRIVACY        = "knowledge_privacy"
    COMPLIANCE     = "knowledge_compliance"
    ACCESS         = "knowledge_access"
    PROVENANCE     = "knowledge_provenance"
    LINEAGE        = "knowledge_lineage"
    LIFECYCLE      = "knowledge_lifecycle"
    AUDIT          = "knowledge_audit"
    ENTERPRISE     = "enterprise_knowledge_governance"


# ---------------------------------------------------------------------------
# PolicyAction — (8 actions)
# ---------------------------------------------------------------------------
class PolicyAction(str, Enum):
    """Actions a governance policy rule can produce."""
    APPROVE                  = "approve"
    APPROVE_WITH_CONDITIONS  = "approve_with_conditions"
    REJECT                   = "reject"
    BLOCK                    = "block"
    ESCALATE                 = "escalate"
    REQUIRE_MANUAL_REVIEW    = "require_manual_review"
    REQUIRE_STEWARD_APPROVAL = "require_steward_approval"
    ARCHIVE                  = "archive"


# ---------------------------------------------------------------------------
# PolicyPriority — IntEnum (lower value = higher priority)
# ---------------------------------------------------------------------------
class PolicyPriority(IntEnum):
    """Governance policy priority levels."""
    CRITICAL      = 0
    HIGH          = 1
    MEDIUM        = 2
    LOW           = 3
    INFORMATIONAL = 4


# ---------------------------------------------------------------------------
# PolicyDomain — (11 domains)
# ---------------------------------------------------------------------------
class PolicyDomain(str, Enum):
    """Supported governance policy domains."""
    CLASSIFICATION = "classification_governance"
    METADATA       = "metadata_governance"
    VERSIONING     = "version_governance"
    RETENTION      = "retention_governance"
    PUBLICATION    = "publication_governance"
    ACCESS         = "access_governance"
    PRIVACY        = "privacy_governance"
    SECURITY       = "security_governance"
    COMPLIANCE     = "compliance_governance"
    AUDIT          = "audit_governance"
    ENTERPRISE     = "enterprise_governance"


# ---------------------------------------------------------------------------
# PolicyStatus
# ---------------------------------------------------------------------------
class PolicyStatus(str, Enum):
    """Lifecycle status of a governance policy definition."""
    PENDING    = "pending"
    ACTIVE     = "active"
    INACTIVE   = "inactive"
    DEPRECATED = "deprecated"
    ARCHIVED   = "archived"


# ---------------------------------------------------------------------------
# GovernanceDecision — (8 outcomes)
# ---------------------------------------------------------------------------
class GovernanceDecision(str, Enum):
    """Aggregate governance decision returned by the framework."""
    APPROVED                 = "approved"
    APPROVED_WITH_CONDITIONS = "approved_with_conditions"
    REJECTED                 = "rejected"
    BLOCKED                  = "blocked"
    ESCALATED                = "escalated"
    MANUAL_REVIEW            = "manual_review"
    STEWARD_APPROVAL         = "steward_approval"
    ARCHIVED                 = "archived"


# ---------------------------------------------------------------------------
# EvaluationStatus
# ---------------------------------------------------------------------------
class EvaluationStatus(str, Enum):
    """Status of a policy evaluation run."""
    PENDING    = "pending"
    EVALUATING = "evaluating"
    COMPLETED  = "completed"
    FAILED     = "failed"
    SKIPPED    = "skipped"


# ---------------------------------------------------------------------------
# PolicyChainMode — (6 modes)
# ---------------------------------------------------------------------------
class PolicyChainMode(str, Enum):
    """Chain evaluation modes."""
    SEQUENTIAL  = "sequential"
    PARALLEL    = "parallel"
    COMPOSITE   = "composite"
    NESTED      = "nested"
    CONDITIONAL = "conditional"
    PRIORITY    = "priority"


# ---------------------------------------------------------------------------
# ConditionOperator — (12 operators)
# ---------------------------------------------------------------------------
class ConditionOperator(str, Enum):
    """Comparison operators for policy conditions."""
    EQ          = "eq"
    NE          = "ne"
    GT          = "gt"
    LT          = "lt"
    GTE         = "gte"
    LTE         = "lte"
    CONTAINS    = "contains"
    NOT_CONTAINS = "not_contains"
    EXISTS      = "exists"
    NOT_EXISTS  = "not_exists"
    IN_LIST     = "in_list"
    NOT_IN_LIST = "not_in_list"


# ---------------------------------------------------------------------------
# GovernanceEventType — (9 event types)
# ---------------------------------------------------------------------------
class GovernanceEventType(str, Enum):
    """Event types emitted by the governance policy engine."""
    POLICY_LOADED        = "governance.policy_loaded"
    POLICY_VALIDATED     = "governance.policy_validated"
    GOVERNANCE_STARTED   = "governance.started"
    KNOWLEDGE_APPROVED   = "governance.knowledge_approved"
    KNOWLEDGE_REJECTED   = "governance.knowledge_rejected"
    KNOWLEDGE_BLOCKED    = "governance.knowledge_blocked"
    KNOWLEDGE_ESCALATED  = "governance.knowledge_escalated"
    REVIEW_REQUESTED     = "governance.review_requested"
    GOVERNANCE_COMPLETED = "governance.completed"


# ---------------------------------------------------------------------------
# PolicyValidationCode — (7 checks)
# ---------------------------------------------------------------------------
class PolicyValidationCode(str, Enum):
    """Structural validation check identifiers."""
    POLICY_INTEGRITY              = "POLICY_INTEGRITY"
    RULE_CONSISTENCY              = "RULE_CONSISTENCY"
    CONDITION_VALIDITY            = "CONDITION_VALIDITY"
    PRIORITY_INTEGRITY            = "PRIORITY_INTEGRITY"
    CONFLICT_RESOLUTION_INTEGRITY = "CONFLICT_RESOLUTION_INTEGRITY"
    AUDIT_COMPLETENESS            = "AUDIT_COMPLETENESS"
    EVALUATION_COMPLETENESS       = "EVALUATION_COMPLETENESS"
