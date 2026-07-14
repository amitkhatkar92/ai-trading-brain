"""iios/investment/decision/explainability/explainability_constants.py
All enumerations, constants, and thresholds for the Decision Explainability Engine.
"""
from __future__ import annotations

from enum import Enum


class DecisionOutcome(str, Enum):
    """Derived outcome from the combined intelligence assessment."""
    PROCEED            = "proceed"            # low risk + high confidence
    CAUTION            = "caution"            # medium risk or medium confidence
    HALT               = "halt"              # critical risk or execution blocked
    INSUFFICIENT_DATA  = "insufficient_data" # not enough evidence to assess

    @property
    def is_actionable(self) -> bool:
        return self in {DecisionOutcome.PROCEED, DecisionOutcome.CAUTION}

    @property
    def severity(self) -> int:
        return {
            "proceed": 1, "caution": 2,
            "halt": 4, "insufficient_data": 3,
        }[self.value]


class ExplanationLevel(str, Enum):
    """Target audience / detail level for an explanation."""
    EXECUTIVE  = "executive"   # one-page, business language
    ANALYST    = "analyst"     # full factor breakdown
    DEVELOPER  = "developer"   # internal scores + timings
    AUDIT      = "audit"       # complete immutable record


class ExplanationFormat(str, Enum):
    """Output serialization format."""
    JSON     = "json"
    TEXT     = "text"
    MARKDOWN = "markdown"
    DICT     = "dict"


class TraceabilityLevel(str, Enum):
    """Depth of evidence→outcome traceability."""
    FULL    = "full"     # every evidence item traced to outcome
    PARTIAL = "partial"  # most items traced
    MINIMAL = "minimal"  # only aggregate stats traced
    NONE    = "none"     # traceability unavailable


class ExplainabilityGrade(str, Enum):
    A = "A"   # >= 90
    B = "B"   # >= 75
    C = "C"   # >= 60
    D = "D"   # >= 45
    F = "F"   # <  45

    @classmethod
    def from_score(cls, score: float) -> "ExplainabilityGrade":
        if score >= 90.0: return cls.A
        if score >= 75.0: return cls.B
        if score >= 60.0: return cls.C
        if score >= 45.0: return cls.D
        return cls.F


class ExplainabilityStatus(str, Enum):
    INITIALIZING = "initializing"
    READY        = "ready"
    GENERATING   = "generating"
    DEGRADED     = "degraded"
    STOPPED      = "stopped"

    @property
    def is_operational(self) -> bool:
        return self in {
            ExplainabilityStatus.READY,
            ExplainabilityStatus.GENERATING,
            ExplainabilityStatus.DEGRADED,
        }


class FactorSource(str, Enum):
    """Which upstream engine produced this explanation factor."""
    EVIDENCE   = "evidence"
    REASONING  = "reasoning"
    CONFIDENCE = "confidence"
    RISK       = "risk"


class CounterfactualType(str, Enum):
    """Type of counterfactual question."""
    CONFIDENCE_THRESHOLD  = "confidence_threshold"   # min confidence to change outcome
    RISK_THRESHOLD        = "risk_threshold"         # max risk to change outcome
    EVIDENCE_QUALITY      = "evidence_quality"       # min quality to change outcome
    DIMENSION_SENSITIVITY = "dimension_sensitivity"  # sensitivity to one risk dimension


# ── Outcome derivation thresholds ──────────────────────────────────────────────
PROCEED_CONFIDENCE_MIN   = 60.0   # confidence >= this → eligible for PROCEED
PROCEED_RISK_MAX         = 60.0   # risk < this → eligible for PROCEED
CAUTION_CONFIDENCE_MIN   = 30.0   # confidence >= this (but < PROCEED threshold)
INSUFFICIENT_DATA_ITEMS  = 2      # fewer items → INSUFFICIENT_DATA

# ── Transparency thresholds ────────────────────────────────────────────────────
MIN_FACTORS_FOR_FULL_TRANSPARENCY  = 3
MIN_STEPS_FOR_FULL_TRACEABILITY    = 3
FULL_TRACEABILITY_ITEM_MIN         = 5

# ── History ────────────────────────────────────────────────────────────────────
EXPLANATION_HISTORY_WINDOW = 100

# ── Sensitivity perturbation ──────────────────────────────────────────────────
SENSITIVITY_PERTURBATION_STEP = 5.0  # ±5 units when probing sensitivity
