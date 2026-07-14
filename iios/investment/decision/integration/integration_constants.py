"""iios/investment/decision/integration/integration_constants.py
All enumerations and threshold constants for the Integration Engine.
"""
from __future__ import annotations

import math
from enum import Enum


# ─── Status enumerations ──────────────────────────────────────────────────────

class IntegrationStatus(str, Enum):
    INITIALIZING = "initializing"
    READY        = "ready"
    RUNNING      = "running"
    DEGRADED     = "degraded"
    STOPPED      = "stopped"

    @property
    def is_operational(self) -> bool:
        return self in {IntegrationStatus.READY, IntegrationStatus.RUNNING,
                        IntegrationStatus.DEGRADED}


class SnapshotStatus(str, Enum):
    COMPLETE = "complete"    # all required components present
    PARTIAL  = "partial"     # some components missing
    STALE    = "stale"       # snapshot exists but freshness expired
    FAILED   = "failed"      # integration error


class ValidationStatus(str, Enum):
    VALID   = "valid"
    WARNING = "warning"
    INVALID = "invalid"

    @property
    def is_blocking(self) -> bool:
        return self == ValidationStatus.INVALID


class ConflictSeverity(str, Enum):
    CRITICAL = "critical"
    HIGH     = "high"
    MEDIUM   = "medium"
    LOW      = "low"

    @property
    def blocks_publishing(self) -> bool:
        return self == ConflictSeverity.CRITICAL


class ConflictType(str, Enum):
    EVIDENCE_REASONING          = "evidence_reasoning"
    REASONING_CONFIDENCE        = "reasoning_confidence"
    CONFIDENCE_RISK             = "confidence_risk"
    COMMITTEE_CONFIDENCE        = "committee_confidence"
    COMMITTEE_RISK              = "committee_risk"
    COMMITTEE_RECOMMENDATION    = "committee_recommendation"
    CROSS_ENGINE                = "cross_engine"
    POLICY                      = "policy"
    DATA_STALENESS              = "data_staleness"
    SUBJECT_MISMATCH            = "subject_mismatch"


class ConflictResolutionStrategy(str, Enum):
    CONSERVATIVE  = "conservative"   # use more cautious value
    LATEST        = "latest"         # use most recently computed
    HIGHER_WEIGHT = "higher_weight"  # use higher-weight engine
    ESCALATE      = "escalate"       # cannot resolve deterministically


class QualityGrade(str, Enum):
    A = "A"  # ≥ 85
    B = "B"  # ≥ 70
    C = "C"  # ≥ 55
    D = "D"  # ≥ 40
    F = "F"  # < 40

    @classmethod
    def from_score(cls, score: float) -> "QualityGrade":
        if score >= 85:  return cls.A
        if score >= 70:  return cls.B
        if score >= 55:  return cls.C
        if score >= 40:  return cls.D
        return cls.F


class HealthStatus(str, Enum):
    HEALTHY   = "healthy"
    DEGRADED  = "degraded"
    UNHEALTHY = "unhealthy"

    @property
    def is_healthy(self) -> bool:
        return self != HealthStatus.UNHEALTHY


class ComponentId(str, Enum):
    """Identifiers for each upstream decision intelligence component."""
    EVIDENCE        = "evidence"
    REASONING       = "reasoning"
    CONFIDENCE      = "confidence"
    RISK            = "risk"
    EXPLANATION     = "explanation"
    COMMITTEE       = "committee"
    RECOMMENDATION  = "recommendation"

    @classmethod
    def required(cls) -> frozenset:
        """Components required for a COMPLETE snapshot."""
        return frozenset({
            cls.EVIDENCE, cls.REASONING, cls.CONFIDENCE,
            cls.RISK, cls.EXPLANATION, cls.COMMITTEE,
        })

    @classmethod
    def all_components(cls) -> frozenset:
        return frozenset(cls)


# ─── Numeric thresholds ───────────────────────────────────────────────────────

# Aggregation
COMPLETENESS_THRESHOLD_COMPLETE: float = 1.0   # all required components present
COMPLETENESS_THRESHOLD_PARTIAL:  float = 0.50  # at least half present

# Consistency validation
EVIDENCE_CONFIDENCE_MIN_FOR_VALID:   float = 30.0
REASONING_CONSISTENCY_THRESHOLD:     float = 0.35  # max allowed Δ logic consistency
CONFIDENCE_RISK_MAX_DELTA:           float = 40.0  # max |confidence + risk - 100|
COMMITTEE_CONFIDENCE_MAX_DELTA:      float = 35.0  # max |committee_conf - overall_conf|
CONFLICT_SEVERITY_SCORE_CRITICAL:    float = 80.0
CONFLICT_SEVERITY_SCORE_HIGH:        float = 60.0
CONFLICT_SEVERITY_SCORE_MEDIUM:      float = 40.0

# Quality weights
QUALITY_WEIGHT_COMPLETENESS:  float = 0.30
QUALITY_WEIGHT_CONSISTENCY:   float = 0.25
QUALITY_WEIGHT_FRESHNESS:     float = 0.15
QUALITY_WEIGHT_CONFIDENCE:    float = 0.20
QUALITY_WEIGHT_AUDIT:         float = 0.10

# Confidence weights (for integrated confidence)
CONF_WEIGHT_EVIDENCE:     float = 0.20
CONF_WEIGHT_REASONING:    float = 0.20
CONF_WEIGHT_CONFIDENCE:   float = 0.25
CONF_WEIGHT_RISK:         float = 0.20
CONF_WEIGHT_COMMITTEE:    float = 0.15

# Freshness
SNAPSHOT_MAX_AGE_SECONDS:      float = 300.0   # 5 minutes
COMPONENT_MAX_AGE_SECONDS:     float = 600.0   # 10 minutes

# History
INTEGRATION_HISTORY_WINDOW:    int   = 500
QUALITY_HISTORY_WINDOW:        int   = 200
CONFLICT_HISTORY_WINDOW:       int   = 300

# Health
HEALTH_CONSECUTIVE_FAIL_DEGRADED: int = 3
HEALTH_CONSECUTIVE_FAIL_UNHEALTHY: int = 7
