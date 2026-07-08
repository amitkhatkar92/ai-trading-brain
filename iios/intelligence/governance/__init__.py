"""
iios/intelligence/governance/__init__.py
========================================
Public API for the Intelligence Quality & Explainability Engine.
"""
from __future__ import annotations

# ── Constants & enums ─────────────────────────────────────────────────────────
from .quality_constants import (
    IntelligenceType,
    QualityLevel,
    ApprovalStatus,
    CertificationStatus,
    AuditEventType,
    DriftType,
    ExplanationType,
    EvaluationDimension,
    GOVERNANCE_ENGINE_VERSION,
    QUALITY_SCORE_EXCELLENT,
    QUALITY_SCORE_GOOD,
    QUALITY_SCORE_ACCEPTABLE,
    MIN_CERTIFIABLE_SCORE,
    MIN_APPROVAL_SCORE,
    CERTIFICATION_TTL_S,
    APPROVAL_TTL_S,
)

# ── Exceptions ────────────────────────────────────────────────────────────────
from .quality_exceptions import (
    IntelligenceQualityError,
    QualityError,
    QualityBelowThresholdError,
    QualityRecordNotFoundError,
    QualityAlreadyExistsError,
    ExplainabilityError,
    TraceNotFoundError,
    ExplanationGenerationError,
    AuditError,
    AuditRecordNotFoundError,
    AuditWriteError,
    CertificationError,
    CertificationNotFoundError,
    CertificationExpiredError,
    CertificationRevokedError,
    CertificationFailedError,
    PolicyViolationError,
    MonitoringError,
    DriftAlertError,
    EvaluationError,
    EvaluationMetricError,
    GovernanceEngineError,
    GovernanceEngineNotInitializedError,
    GovernanceEngineAlreadyRunningError,
)

# ── Models ────────────────────────────────────────────────────────────────────
from .quality_result import QualityRecord, QualityApproval
from .audit.audit_record import AuditRecord
from .certification.certification_record import CertificationRecord
from .monitoring.drift_detector import DriftAlert
from .evaluation.evaluation_dashboard import DashboardSnapshot

# ── Engine & manager ──────────────────────────────────────────────────────────
from .governance_engine import (
    IntelligenceQualityEngine,
    get_governance_engine,
    reset_governance_engine,
)
from .governance_manager import (
    GovernanceManager,
    get_governance_manager,
    reset_governance_manager,
)

__all__ = [
    # enums / constants
    "IntelligenceType",
    "QualityLevel",
    "ApprovalStatus",
    "CertificationStatus",
    "AuditEventType",
    "DriftType",
    "ExplanationType",
    "EvaluationDimension",
    "GOVERNANCE_ENGINE_VERSION",
    "QUALITY_SCORE_EXCELLENT",
    "QUALITY_SCORE_GOOD",
    "QUALITY_SCORE_ACCEPTABLE",
    "MIN_CERTIFIABLE_SCORE",
    "MIN_APPROVAL_SCORE",
    "CERTIFICATION_TTL_S",
    "APPROVAL_TTL_S",
    # exceptions
    "IntelligenceQualityError",
    "QualityError",
    "QualityBelowThresholdError",
    "QualityRecordNotFoundError",
    "QualityAlreadyExistsError",
    "ExplainabilityError",
    "TraceNotFoundError",
    "ExplanationGenerationError",
    "AuditError",
    "AuditRecordNotFoundError",
    "AuditWriteError",
    "CertificationError",
    "CertificationNotFoundError",
    "CertificationExpiredError",
    "CertificationRevokedError",
    "CertificationFailedError",
    "PolicyViolationError",
    "MonitoringError",
    "DriftAlertError",
    "EvaluationError",
    "EvaluationMetricError",
    "GovernanceEngineError",
    "GovernanceEngineNotInitializedError",
    "GovernanceEngineAlreadyRunningError",
    # models
    "QualityRecord",
    "QualityApproval",
    "AuditRecord",
    "CertificationRecord",
    "DriftAlert",
    "DashboardSnapshot",
    # engine
    "IntelligenceQualityEngine",
    "get_governance_engine",
    "reset_governance_engine",
    "GovernanceManager",
    "get_governance_manager",
    "reset_governance_manager",
]
