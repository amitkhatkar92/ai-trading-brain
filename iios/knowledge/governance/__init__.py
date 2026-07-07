"""
iios/knowledge/governance/__init__.py
======================================
Knowledge Quality & Governance Engine — public surface.

All public symbols are re-exported here so callers can write::

    from iios.knowledge.governance import (
        get_knowledge_governor,
        KnowledgeGovernor,
        ApprovalResult,
    )
"""

from __future__ import annotations

# ── Constants ─────────────────────────────────────────────────────────────────
from .quality_constants import (
    QualityDimension,
    QualityTier,
    ViolationSeverity,
    ViolationType,
    GOVERNANCE_NAMESPACE,
    SYSTEM_GOVERNANCE_ACTOR,
    DEFAULT_MIN_KQI,
    AUTO_APPROVE_KQI_THRESHOLD,
    DIMENSION_WEIGHTS,
    GOVERNANCE_SCHEMA_VERSION,
    MONITOR_STALENESS_DAYS,
)
from .governance_constants import (
    ApprovalStatus,
    CertificationStatus,
    PolicyType,
    GovernanceAction,
    MonitorEventType,
    RiskLevel,
    CertificationLevel,
    DEFAULT_CERTIFICATION_TTL_DAYS,
    DEFAULT_RENEWAL_NOTICE_DAYS,
    SENSITIVE_DOMAINS,
    REQUIRED_FIELDS_FOR_APPROVAL,
    GOVERNANCE_SCHEMA_VERSION as _GOV_SCHEMA,  # same value; export once
)

# ── Exceptions ────────────────────────────────────────────────────────────────
from .quality_exceptions import (
    QualityError,
    QualityValidationError,
    QualityThresholdError,
    QualityScoreError,
    QualityEngineError,
    QualityViolationError,
    QualityMonitorError,
    QualityRegistryError,
)
from .governance_exceptions import (
    GovernanceError,
    ApprovalError,
    ApprovalNotFoundError,
    ApprovalAlreadyExistsError,
    ApprovalRejectedError,
    PolicyError,
    PolicyNotFoundError,
    PolicyAlreadyExistsError,
    PolicyViolationError,
    CertificationError,
    CertificationNotFoundError,
    CertificationExpiredError,
    GovernanceAuditError,
    KnowledgeGovernorError,
)

# ── Models ────────────────────────────────────────────────────────────────────
from .models.quality_score     import QualityScore, DimensionScore, compute_tier, compute_kqi
from .models.quality_violation import QualityViolation
from .models.governance_record import GovernanceRecord
from .models.certification     import Certification
from .models.policy            import GovernancePolicy, PolicyCondition
from .models.governance_audit  import GovernanceAuditEntry

# ── Services — quality ────────────────────────────────────────────────────────
from .quality_engine   import QualityEngine, get_quality_engine, reset_quality_engine
from .quality_validator import (
    QualityValidator, get_quality_validator, reset_quality_validator,
)
from .quality_monitor  import (
    QualityMonitor, MonitorReport, get_quality_monitor, reset_quality_monitor,
)

# ── Services — governance ─────────────────────────────────────────────────────
from .governance_engine import (
    GovernanceEngine, get_governance_engine, reset_governance_engine,
)
from .policy_manager import (
    PolicyManager, get_policy_manager, reset_policy_manager,
)
from .certification_manager import (
    CertificationManager, get_certification_manager, reset_certification_manager,
)
from .governance_audit import (
    GovernanceAuditLog, get_governance_audit_log, reset_governance_audit_log,
)

# ── Master façade ─────────────────────────────────────────────────────────────
from .knowledge_governor import (
    KnowledgeGovernor,
    ApprovalResult,
    get_knowledge_governor,
    reset_knowledge_governor,
)

# ── Contexts ──────────────────────────────────────────────────────────────────
from .quality_context import (
    QualityContext,
    get_quality_context,
    reset_quality_context,
    quality_operation,
    current_quality_actor,
    current_quality_operation_id,
)
from .governance_context import (
    GovernanceContext,
    get_governance_context,
    reset_governance_context,
    governance_operation,
    current_governance_actor,
    current_governance_operation_id,
)

# ── Registries ────────────────────────────────────────────────────────────────
from .quality_registry import (
    QualityRegistry, get_quality_registry, reset_quality_registry,
)
from .governance_registry import (
    GovernanceRegistry, get_governance_registry, reset_governance_registry,
)

__all__ = [
    # constants
    "QualityDimension", "QualityTier", "ViolationSeverity", "ViolationType",
    "GOVERNANCE_NAMESPACE", "SYSTEM_GOVERNANCE_ACTOR", "DEFAULT_MIN_KQI",
    "AUTO_APPROVE_KQI_THRESHOLD", "DIMENSION_WEIGHTS", "GOVERNANCE_SCHEMA_VERSION",
    "MONITOR_STALENESS_DAYS",
    "ApprovalStatus", "CertificationStatus", "PolicyType", "GovernanceAction",
    "MonitorEventType", "RiskLevel", "CertificationLevel",
    "DEFAULT_CERTIFICATION_TTL_DAYS", "DEFAULT_RENEWAL_NOTICE_DAYS",
    "SENSITIVE_DOMAINS", "REQUIRED_FIELDS_FOR_APPROVAL",
    # exceptions
    "QualityError", "QualityValidationError", "QualityThresholdError",
    "QualityScoreError", "QualityEngineError", "QualityViolationError",
    "QualityMonitorError", "QualityRegistryError",
    "GovernanceError", "ApprovalError", "ApprovalNotFoundError",
    "ApprovalAlreadyExistsError", "ApprovalRejectedError", "PolicyError",
    "PolicyNotFoundError", "PolicyAlreadyExistsError", "PolicyViolationError",
    "CertificationError", "CertificationNotFoundError", "CertificationExpiredError",
    "GovernanceAuditError", "KnowledgeGovernorError",
    # models
    "QualityScore", "DimensionScore", "compute_tier", "compute_kqi",
    "QualityViolation", "GovernanceRecord", "Certification",
    "GovernancePolicy", "PolicyCondition", "GovernanceAuditEntry",
    # quality services
    "QualityEngine", "get_quality_engine", "reset_quality_engine",
    "QualityValidator", "get_quality_validator", "reset_quality_validator",
    "QualityMonitor", "MonitorReport", "get_quality_monitor", "reset_quality_monitor",
    # governance services
    "GovernanceEngine", "get_governance_engine", "reset_governance_engine",
    "PolicyManager", "get_policy_manager", "reset_policy_manager",
    "CertificationManager", "get_certification_manager", "reset_certification_manager",
    "GovernanceAuditLog", "get_governance_audit_log", "reset_governance_audit_log",
    # master façade
    "KnowledgeGovernor", "ApprovalResult",
    "get_knowledge_governor", "reset_knowledge_governor",
    # contexts
    "QualityContext", "get_quality_context", "reset_quality_context",
    "quality_operation", "current_quality_actor", "current_quality_operation_id",
    "GovernanceContext", "get_governance_context", "reset_governance_context",
    "governance_operation", "current_governance_actor",
    "current_governance_operation_id",
    # registries
    "QualityRegistry", "get_quality_registry", "reset_quality_registry",
    "GovernanceRegistry", "get_governance_registry", "reset_governance_registry",
]
