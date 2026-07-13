"""iios/investment/company/integration/company_state.py
Enumerations and shared constants for the Company Intelligence Integration layer.
"""
from __future__ import annotations

from enum import Enum


# ── Completeness ──────────────────────────────────────────────────────────────

class IntelligenceCompleteness(Enum):
    """Reflects how many upstream engines have provided data (out of 8)."""
    COMPLETE      = "complete"       # ≥ 8 engines
    SUBSTANTIAL   = "substantial"    # 6 – 7 engines
    PARTIAL       = "partial"        # 4 – 5 engines
    MINIMAL       = "minimal"        # 2 – 3 engines
    INSUFFICIENT  = "insufficient"   # 0 – 1 engines


# ── Validation ────────────────────────────────────────────────────────────────

class ValidationStatus(Enum):
    PASSED  = "passed"
    WARNING = "warning"
    FAILED  = "failed"


# ── Conflicts ─────────────────────────────────────────────────────────────────

class ConflictSeverity(Enum):
    CRITICAL = "critical"
    HIGH     = "high"
    MEDIUM   = "medium"
    LOW      = "low"
    INFO     = "info"


class ConflictStatus(Enum):
    DETECTED  = "detected"
    RESOLVED  = "resolved"
    ESCALATED = "escalated"
    DISMISSED = "dismissed"


class ConflictType(Enum):
    SCORE_DIVERGENCE      = "score_divergence"       # Engine scores diverge widely
    SIGNAL_CONFLICT       = "signal_conflict"        # Opposite directional signals
    TREND_CONFLICT        = "trend_conflict"         # Contradictory trends
    FUNDAMENTAL_CONFLICT  = "fundamental_conflict"   # Metric contradiction
    RISK_CONFLICT         = "risk_conflict"          # Risk levels disagree


class ResolutionStrategy(Enum):
    HIGHER_CONFIDENCE     = "higher_confidence"   # Trust the more confident engine
    CONSERVATIVE          = "conservative"        # Use the more cautious value
    LATEST_UPDATE         = "latest_update"       # Trust most recently updated engine
    AVERAGE               = "average"             # Use average of conflicting values
    ESCALATE              = "escalate"            # No deterministic resolution


# ── Engine health ─────────────────────────────────────────────────────────────

class EngineStatus(Enum):
    HEALTHY     = "healthy"
    DEGRADED    = "degraded"    # Slow or intermittent
    STALE       = "stale"       # Data is old
    UNAVAILABLE = "unavailable" # No data received


# ── Constants ─────────────────────────────────────────────────────────────────

# All known upstream engine keys (registration order matters for display)
KNOWN_ENGINES: tuple = (
    "profile",
    "financials",
    "earnings",
    "business_quality",
    "valuation",
    "growth",
    "management",
    "ownership",
    "opportunity",
)

# Engines counted toward completeness score (profile is supplementary)
SCORED_ENGINES: tuple = (
    "financials",
    "earnings",
    "business_quality",
    "valuation",
    "growth",
    "management",
    "ownership",
    "opportunity",
)

# Staleness thresholds (seconds)
STALE_WARN_SECONDS = 3_600    #  1 hour — data freshness warning
STALE_CRIT_SECONDS = 86_400   # 24 hours — data is considered stale

# Overall score weight map — must sum to 1.0; only for SCORED_ENGINES
ENGINE_WEIGHTS: dict = {
    "financials":       0.20,
    "earnings":         0.18,
    "business_quality": 0.18,
    "valuation":        0.14,
    "growth":           0.12,
    "management":       0.10,
    "ownership":        0.06,
    "opportunity":      0.02,
}

# Score divergence thresholds (points, 0-100 scale)
DIVERGENCE_WARN_THRESHOLD  = 35.0
DIVERGENCE_CRIT_THRESHOLD  = 55.0

# Completeness fractions (of SCORED_ENGINES)
COMPLETENESS_BANDS: dict = {
    IntelligenceCompleteness.COMPLETE:    8 / 8,
    IntelligenceCompleteness.SUBSTANTIAL: 6 / 8,
    IntelligenceCompleteness.PARTIAL:     4 / 8,
    IntelligenceCompleteness.MINIMAL:     2 / 8,
}

# Overall intelligence score → grade
GRADE_THRESHOLDS: dict = {
    "A+": 90, "A": 82, "B+": 74, "B": 65,
    "C+": 56, "C": 47, "D": 35,
}  # below D → F


def score_to_grade(score: float) -> str:
    """Convert 0-100 score to letter grade."""
    for grade, threshold in GRADE_THRESHOLDS.items():
        if score >= threshold:
            return grade
    return "F"


def completeness_from_fraction(fraction: float) -> IntelligenceCompleteness:
    """Map engine fraction to IntelligenceCompleteness enum."""
    for level, threshold in COMPLETENESS_BANDS.items():
        if fraction >= threshold:
            return level
    return IntelligenceCompleteness.INSUFFICIENT
