"""iios/investment/portfolio/integration/integration_types.py

Enums, constants, parameters, and utility functions for the
Portfolio Intelligence Integration & Validation Engine.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Tuple


# ── Enums ──────────────────────────────────────────────────────────────────────

class EngineId(str, Enum):
    FRAMEWORK        = "framework"
    CONSTRUCTION     = "construction"
    ALLOCATION       = "allocation"
    OPTIMIZATION     = "optimization"
    DIVERSIFICATION  = "diversification"
    RISK             = "risk"
    PERFORMANCE      = "performance"
    REBALANCING      = "rebalancing"
    RECOMMENDATION   = "recommendation"


class AggregationStatus(str, Enum):
    COMPLETE  = "complete"
    PARTIAL   = "partial"
    STALE     = "stale"
    INVALID   = "invalid"


class ValidationStatus(str, Enum):
    PASSED  = "passed"
    WARNING = "warning"
    FAILED  = "failed"


class ConflictSeverity(str, Enum):
    CRITICAL = "critical"
    HIGH     = "high"
    MEDIUM   = "medium"
    LOW      = "low"
    INFO     = "info"


class ConflictResolutionStatus(str, Enum):
    RESOLVED   = "resolved"
    ESCALATED  = "escalated"
    UNRESOLVED = "unresolved"
    IGNORED    = "ignored"


class QualityGrade(str, Enum):
    A = "A"
    B = "B"
    C = "C"
    D = "D"
    F = "F"


class HealthStatus(str, Enum):
    HEALTHY  = "healthy"
    DEGRADED = "degraded"
    CRITICAL = "critical"
    OFFLINE  = "offline"


class SnapshotStatus(str, Enum):
    DRAFT      = "draft"
    VALIDATED  = "validated"
    PUBLISHED  = "published"
    STALE      = "stale"
    ARCHIVED   = "archived"


# ── Engine collections ────────────────────────────────────────────────────────

ALL_ENGINE_IDS: Tuple[EngineId, ...] = tuple(EngineId)

REQUIRED_ENGINES: Tuple[EngineId, ...] = (
    EngineId.FRAMEWORK,
    EngineId.CONSTRUCTION,
    EngineId.ALLOCATION,
    EngineId.OPTIMIZATION,
    EngineId.DIVERSIFICATION,
    EngineId.RISK,
    EngineId.PERFORMANCE,
    EngineId.REBALANCING,
    EngineId.RECOMMENDATION,
)

# ── Quality score thresholds ──────────────────────────────────────────────────

QUALITY_SCORE_EXCELLENT = 0.85
QUALITY_SCORE_GOOD      = 0.70
QUALITY_SCORE_AVERAGE   = 0.55
QUALITY_SCORE_POOR      = 0.40

# ── Default parameter values ──────────────────────────────────────────────────

DEFAULT_MIN_COMPLETENESS    = 0.70
DEFAULT_MIN_CONSISTENCY     = 0.75
DEFAULT_FRESHNESS_HOURS     = 4.0
DEFAULT_MIN_CONFIDENCE      = 0.50
DEFAULT_MIN_QUALITY_PUBLISH = 0.60
DEFAULT_SNAPSHOT_HISTORY    = 100
DEFAULT_QUALITY_HISTORY     = 200


# ── Parameters dataclass ──────────────────────────────────────────────────────

@dataclass(frozen=True)
class IntegrationParameters:
    """All configurable thresholds for the integration engine. No hardcoded values."""
    min_completeness:        float = DEFAULT_MIN_COMPLETENESS
    min_consistency:         float = DEFAULT_MIN_CONSISTENCY
    freshness_hours:         float = DEFAULT_FRESHNESS_HOURS
    min_confidence:          float = DEFAULT_MIN_CONFIDENCE
    min_quality_to_publish:  float = DEFAULT_MIN_QUALITY_PUBLISH
    snapshot_history_size:   int   = DEFAULT_SNAPSHOT_HISTORY
    quality_history_size:    int   = DEFAULT_QUALITY_HISTORY
    escalate_critical:       bool  = True
    require_all_engines:     bool  = False
    # Quality dimension weights (must sum to 1.0)
    weight_completeness:     float = 0.25
    weight_consistency:      float = 0.30
    weight_freshness:        float = 0.20
    weight_confidence:       float = 0.15
    weight_coverage:         float = 0.10


# ── Utility functions ─────────────────────────────────────────────────────────

def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def score_to_grade(score: float) -> QualityGrade:
    if score >= QUALITY_SCORE_EXCELLENT: return QualityGrade.A
    if score >= QUALITY_SCORE_GOOD:      return QualityGrade.B
    if score >= QUALITY_SCORE_AVERAGE:   return QualityGrade.C
    if score >= QUALITY_SCORE_POOR:      return QualityGrade.D
    return QualityGrade.F


def hours_since(iso_str: str) -> float:
    """Return hours elapsed since an ISO-format UTC datetime string."""
    try:
        dt = datetime.fromisoformat(iso_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - dt).total_seconds() / 3600.0
    except (ValueError, TypeError):
        return float("inf")
