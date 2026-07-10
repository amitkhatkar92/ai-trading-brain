"""governance_constants.py — Enumerations and scalar constants for the Research Governance Framework."""
from __future__ import annotations

from enum import Enum


# ── Engine / lifecycle ────────────────────────────────────────────────────────

class GovernanceEngineStatus(str, Enum):
    STOPPED      = "stopped"
    INITIALIZING = "initializing"
    RUNNING      = "running"
    STOPPING     = "stopping"
    ERROR        = "error"


# ── Research lifecycle ────────────────────────────────────────────────────────

class ResearchStatus(str, Enum):
    DRAFT     = "draft"
    ACTIVE    = "active"
    REVIEW    = "review"
    PAUSED    = "paused"
    COMPLETED = "completed"
    ARCHIVED  = "archived"
    CANCELLED = "cancelled"


# ── Approval workflow ─────────────────────────────────────────────────────────

class ApprovalStatus(str, Enum):
    DRAFT           = "draft"
    PENDING         = "pending"
    PENDING_REVIEW  = "pending_review"
    IN_REVIEW       = "in_review"
    APPROVED        = "approved"
    REJECTED        = "rejected"
    ARCHIVED        = "archived"
    WITHDRAWN       = "withdrawn"
    CONDITIONALLY_APPROVED = "conditionally_approved"


class ReviewStage(str, Enum):
    PEER_REVIEW       = "peer_review"
    TECHNICAL_REVIEW  = "technical_review"
    RISK_REVIEW       = "risk_review"
    MANAGER_APPROVAL  = "manager_approval"
    FINAL_APPROVAL    = "final_approval"


class ReviewDecision(str, Enum):
    APPROVED   = "approved"
    REJECTED   = "rejected"
    DEFERRED   = "deferred"
    NEEDS_WORK = "needs_work"
    REVISE     = "revise"


# ── Artifact management ───────────────────────────────────────────────────────

class ArtifactType(str, Enum):
    DATASET       = "dataset"
    FEATURE_SET   = "feature_set"
    MODEL         = "model"
    CONFIGURATION = "configuration"
    REPORT        = "report"
    CHART         = "chart"
    LOG           = "log"
    CODE          = "code"
    EXPERIMENT    = "experiment"
    ATTACHMENT    = "attachment"
    CHECKPOINT    = "checkpoint"


class ArtifactStatus(str, Enum):
    DRAFT     = "draft"
    ACTIVE    = "active"
    ARCHIVED  = "archived"
    DELETED   = "deleted"
    LOCKED    = "locked"


# ── Lineage ───────────────────────────────────────────────────────────────────

class LineageNodeType(str, Enum):
    DATASET     = "dataset"
    FEATURE_SET = "feature_set"
    MODEL       = "model"
    EXPERIMENT  = "experiment"
    ARTIFACT    = "artifact"
    DECISION    = "decision"
    EXECUTION   = "execution"
    PIPELINE    = "pipeline"


class LineageEdgeType(str, Enum):
    DERIVED_FROM   = "derived_from"
    TRAINED_ON     = "trained_on"
    EVALUATED_ON   = "evaluated_on"
    PRODUCED_BY    = "produced_by"
    DEPENDS_ON     = "depends_on"
    TRANSFORMS     = "transforms"
    REPLACES       = "replaces"


# ── Provenance ────────────────────────────────────────────────────────────────

class ProvenanceType(str, Enum):
    DATASET    = "dataset"
    FEATURE    = "feature"
    MODEL      = "model"
    EXPERIMENT = "experiment"
    EXECUTION  = "execution"
    DECISION   = "decision"
    ARTIFACT   = "artifact"


# ── Reproducibility ───────────────────────────────────────────────────────────

class ReproducibilityStatus(str, Enum):
    REPRODUCIBLE          = "reproducible"
    PARTIALLY_REPRODUCIBLE = "partially_reproducible"
    NOT_REPRODUCIBLE      = "not_reproducible"
    UNKNOWN               = "unknown"
    PENDING               = "pending"
    VERIFIED              = "verified"
    FAILED                = "failed"


# ── Compliance & audit ────────────────────────────────────────────────────────

class ComplianceStatus(str, Enum):
    COMPLIANT     = "compliant"
    NON_COMPLIANT = "non_compliant"
    VIOLATED      = "violated"
    WARNING       = "warning"
    EXEMPT        = "exempt"
    PENDING       = "pending"


class AuditEventType(str, Enum):
    CREATED              = "created"
    UPDATED              = "updated"
    DELETED              = "deleted"
    APPROVED             = "approved"
    REJECTED             = "rejected"
    DEPLOYED             = "deployed"
    ACCESSED             = "accessed"
    EXPORTED             = "exported"
    POLICY_VIOLATION     = "policy_violation"
    STATUS_CHANGED       = "status_changed"
    REVIEWED             = "reviewed"
    # Research-specific aliases
    PROJECT_CREATED      = "project.created"
    PROJECT_UPDATED      = "project.updated"
    APPROVAL_GRANTED     = "approval.granted"
    APPROVAL_REJECTED    = "approval.rejected"
    ARTIFACT_REGISTERED  = "artifact.registered"
    COMPLIANCE_CHECKED   = "compliance.checked"
    LINEAGE_RECORDED     = "lineage.recorded"
    PROVENANCE_RECORDED  = "provenance.recorded"


class PolicyType(str, Enum):
    APPROVAL              = "approval"
    RETENTION             = "retention"
    ACCESS                = "access"
    REPRODUCIBILITY       = "reproducibility"
    COMPLIANCE            = "compliance"
    DATA_QUALITY          = "data_quality"
    NAMING                = "naming"
    RESEARCH_INTEGRITY    = "research_integrity"
    DATA_GOVERNANCE       = "data_governance"


# ── Scalar constants ──────────────────────────────────────────────────────────

GOVERNANCE_ENGINE_VERSION      = "1.0.0"
GV_ERROR_PREFIX                = "GV"

DEFAULT_MAX_RESEARCH_PROJECTS  = 10_000
DEFAULT_MAX_ARTIFACTS          = 100_000
DEFAULT_MAX_AUDIT_ENTRIES      = 1_000_000
DEFAULT_MAX_LINEAGE_NODES      = 500_000
DEFAULT_MAX_PROVENANCE_RECORDS = 500_000
DEFAULT_MAX_APPROVALS          = 50_000
DEFAULT_HISTORY_MAX_ENTRIES    = 100_000
DEFAULT_APPROVAL_TIMEOUT_DAYS  = 30
DEFAULT_RETENTION_DAYS         = 365 * 7   # 7 years
