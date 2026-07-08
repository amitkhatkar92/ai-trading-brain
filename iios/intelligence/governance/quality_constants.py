"""
iios/intelligence/governance/quality_constants.py
==================================================
Shared constants and enumerations for the Intelligence Quality &
Explainability Engine (IQE).
"""
from __future__ import annotations

from enum import Enum


class IntelligenceType(str, Enum):
    """Category of intelligence product being evaluated."""
    FORECAST      = "forecast"
    HYPOTHESIS    = "hypothesis"
    REASONING     = "reasoning"
    DECISION      = "decision"
    AGENT_OUTPUT  = "agent_output"
    SIGNAL        = "signal"
    SCENARIO      = "scenario"
    DEBATE_OUTCOME = "debate_outcome"
    PROBABILITY   = "probability"
    GENERIC       = "generic"


class QualityLevel(str, Enum):
    """Ordinal quality band assigned after scoring."""
    EXCELLENT  = "excellent"    # score >= 0.90
    GOOD       = "good"         # score >= 0.75
    ACCEPTABLE = "acceptable"   # score >= 0.60
    POOR       = "poor"         # score >= 0.40
    REJECTED   = "rejected"     # score <  0.40


class ApprovalStatus(str, Enum):
    """Decision Layer gate status for an evaluated product."""
    PENDING  = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED  = "expired"


class CertificationStatus(str, Enum):
    """Certification lifecycle state."""
    UNCERTIFIED = "uncertified"
    PENDING     = "pending"
    CERTIFIED   = "certified"
    EXPIRED     = "expired"
    REVOKED     = "revoked"
    FAILED      = "failed"


class AuditEventType(str, Enum):
    """Type of event recorded in the audit log."""
    EVALUATION    = "evaluation"
    CERTIFICATION = "certification"
    APPROVAL      = "approval"
    REJECTION     = "rejection"
    EXPIRY        = "expiry"
    REVOCATION    = "revocation"
    DRIFT_ALERT   = "drift_alert"
    MONITORING    = "monitoring"
    RE_EVALUATION = "re_evaluation"


class DriftType(str, Enum):
    """Category of detected drift."""
    CONFIDENCE   = "confidence"
    QUALITY      = "quality"
    ACCURACY     = "accuracy"
    DISTRIBUTION = "distribution"
    CONCEPT      = "concept"


class ExplanationType(str, Enum):
    """Format / granularity of an explanation."""
    HUMAN_READABLE   = "human_readable"
    MACHINE_READABLE = "machine_readable"
    TRACE            = "trace"
    SUMMARY          = "summary"
    DETAILED         = "detailed"


class EvaluationDimension(str, Enum):
    """The seven quality dimensions measured per product."""
    ACCURACY       = "accuracy"
    CONSISTENCY    = "consistency"
    COMPLETENESS   = "completeness"
    TIMELINESS     = "timeliness"
    RELIABILITY    = "reliability"
    CONFIDENCE     = "confidence"
    EXPLAINABILITY = "explainability"


# ── Version ──────────────────────────────────────────────────────────────────
GOVERNANCE_ENGINE_VERSION = "1.0.0"

# ── Quality thresholds ────────────────────────────────────────────────────────
QUALITY_SCORE_EXCELLENT  = 0.90
QUALITY_SCORE_GOOD       = 0.75
QUALITY_SCORE_ACCEPTABLE = 0.60
MIN_CERTIFIABLE_SCORE    = 0.60     # score below this → cannot be certified
MIN_APPROVAL_SCORE       = 0.60     # score below this → auto-rejected by governance

# ── TTL values ────────────────────────────────────────────────────────────────
CERTIFICATION_TTL_S = 86_400.0    # 24 h
APPROVAL_TTL_S      =  3_600.0    #  1 h
AUDIT_RETENTION_S   = 30 * 86_400.0  # 30 days

# ── Capacity limits ───────────────────────────────────────────────────────────
MAX_QUALITY_RECORDS = 50_000
MAX_AUDIT_RECORDS   = 100_000
MAX_CERT_RECORDS    = 10_000
MAX_DRIFT_HISTORY   = 1_000        # per source_id

# ── Default evaluation dimension weights ──────────────────────────────────────
DEFAULT_DIMENSION_WEIGHTS: dict[str, float] = {
    "accuracy":       0.25,
    "consistency":    0.20,
    "completeness":   0.15,
    "timeliness":     0.10,
    "reliability":    0.15,
    "confidence":     0.10,
    "explainability": 0.05,
}

# ── Drift thresholds ──────────────────────────────────────────────────────────
DRIFT_WINDOW_N                = 20     # samples to compute rolling mean
CONFIDENCE_DRIFT_THRESHOLD    = 0.15   # |Δ confidence| > this → drift alert
QUALITY_DRIFT_THRESHOLD       = 0.15   # |Δ quality score| > this → drift alert

# ── System identifiers ────────────────────────────────────────────────────────
GOVERNANCE_SYSTEM_ID  = "iios:governance:system"
AUTO_CERTIFIER_ID     = "iios:governance:auto_certifier"
