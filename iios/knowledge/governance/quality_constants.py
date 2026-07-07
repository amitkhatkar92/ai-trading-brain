"""
iios/knowledge/governance/quality_constants.py
===============================================
Quality-specific enumerations and constants for the Knowledge Quality
& Governance Engine.

Governance constants (workflow states, policy types, etc.) live in
governance_constants.py.
"""

from __future__ import annotations

from enum import Enum
from typing import Final

__all__ = [
    "QualityDimension",
    "QualityTier",
    "ViolationSeverity",
    "ViolationType",
    "GOVERNANCE_NAMESPACE",
    "SYSTEM_GOVERNANCE_ACTOR",
    "DEFAULT_MIN_KQI",
    "DEFAULT_MIN_COMPLETENESS",
    "DEFAULT_MIN_CONFIDENCE",
    "AUTO_APPROVE_KQI_THRESHOLD",
    "KQI_POOR_MAX",
    "KQI_FAIR_MAX",
    "KQI_GOOD_MAX",
    "DIMENSION_WEIGHTS",
    "MAX_VIOLATIONS_PER_RECORD",
    "MONITOR_STALENESS_DAYS",
    "GOVERNANCE_SCHEMA_VERSION",
]


class QualityDimension(str, Enum):
    """Quality dimension evaluated during KQI computation."""

    COMPLETENESS = "completeness"   # required fields, content richness
    FRESHNESS    = "freshness"      # age relative to TTL
    CONFIDENCE   = "confidence"     # declared confidence value
    CONSISTENCY  = "consistency"    # version format, status validity
    INTEGRITY    = "integrity"      # checksum, references, deletion state
    PROVENANCE   = "provenance"     # origin, author, source
    COVERAGE     = "coverage"       # tags, domain classification
    GOVERNANCE   = "governance"     # approval and certification state


class QualityTier(str, Enum):
    """Human-readable quality tier derived from KQI range."""

    POOR      = "poor"       # KQI < 0.40  — must not enter knowledge base
    FAIR      = "fair"       # 0.40 ≤ KQI < 0.60 — conditional admission
    GOOD      = "good"       # 0.60 ≤ KQI < 0.80 — acceptable
    EXCELLENT = "excellent"  # KQI ≥ 0.80  — gold-standard


class ViolationSeverity(str, Enum):
    """Severity level of a detected quality violation."""

    CRITICAL = "critical"   # blocks approval
    HIGH     = "high"       # strongly discouraged
    MEDIUM   = "medium"     # should be fixed
    LOW      = "low"        # informational warning
    INFO     = "info"       # observation only


class ViolationType(str, Enum):
    """Category of quality violation."""

    MISSING_FIELD        = "missing_field"
    EMPTY_TITLE          = "empty_title"
    EMPTY_CONTENT        = "empty_content"
    LOW_CONFIDENCE       = "low_confidence"
    LOW_KQI              = "low_kqi"
    EXPIRED_RECORD       = "expired_record"
    BROKEN_REFERENCE     = "broken_reference"
    INVALID_VERSION      = "invalid_version"
    INVALID_STATUS       = "invalid_status"
    MISSING_PROVENANCE   = "missing_provenance"
    MISSING_TAGS         = "missing_tags"
    GENERAL_DOMAIN       = "general_domain"
    UNKNOWN_TYPE         = "unknown_type"
    MISSING_CHECKSUM     = "missing_checksum"
    STALE_KNOWLEDGE      = "stale_knowledge"
    DUPLICATE_DETECTED   = "duplicate_detected"
    ONTOLOGY_VIOLATION   = "ontology_violation"
    RELATIONSHIP_INVALID = "relationship_invalid"
    CERTIFICATION_EXPIRED= "certification_expired"
    POLICY_VIOLATION     = "policy_violation"
    QUALITY_DEGRADED     = "quality_degraded"


# ── Module-level constants ────────────────────────────────────────────────────

GOVERNANCE_NAMESPACE:         Final[str]   = "iios.governance"
SYSTEM_GOVERNANCE_ACTOR:      Final[str]   = "iios:governance"

DEFAULT_MIN_KQI:              Final[float] = 0.60
DEFAULT_MIN_COMPLETENESS:     Final[float] = 0.50
DEFAULT_MIN_CONFIDENCE:       Final[float] = 0.30
AUTO_APPROVE_KQI_THRESHOLD:   Final[float] = 0.75

# KQI tier boundaries
KQI_POOR_MAX:  Final[float] = 0.40
KQI_FAIR_MAX:  Final[float] = 0.60
KQI_GOOD_MAX:  Final[float] = 0.80
# KQI >= KQI_GOOD_MAX → EXCELLENT

# Dimension weights — must sum to 1.0
DIMENSION_WEIGHTS: Final[dict[str, float]] = {
    QualityDimension.COMPLETENESS.value: 0.20,
    QualityDimension.FRESHNESS.value:    0.10,
    QualityDimension.CONFIDENCE.value:   0.15,
    QualityDimension.CONSISTENCY.value:  0.15,
    QualityDimension.INTEGRITY.value:    0.15,
    QualityDimension.PROVENANCE.value:   0.10,
    QualityDimension.COVERAGE.value:     0.05,
    QualityDimension.GOVERNANCE.value:   0.10,
}

MAX_VIOLATIONS_PER_RECORD: Final[int] = 50
MONITOR_STALENESS_DAYS:    Final[int] = 30
GOVERNANCE_SCHEMA_VERSION: Final[str] = "1.0.0"
