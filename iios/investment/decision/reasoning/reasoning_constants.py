"""iios/investment/decision/reasoning/reasoning_constants.py
All enumerations, constants, and thresholds for the Decision Reasoning Engine.
"""
from __future__ import annotations
from enum import Enum


class ReasoningStepType(str, Enum):
    EVIDENCE_REVIEW         = "evidence_review"
    CONTEXT_ANALYSIS        = "context_analysis"
    SIGNAL_INTERPRETATION   = "signal_interpretation"
    RELATIONSHIP_MAPPING    = "relationship_mapping"
    HYPOTHESIS_FORMATION    = "hypothesis_formation"
    ARGUMENT_EVALUATION     = "argument_evaluation"
    CROSS_VALIDATION        = "cross_validation"
    INTERMEDIATE_CONCLUSION = "intermediate_conclusion"
    FINAL_REASONING         = "final_reasoning"


class SignalDirection(str, Enum):
    POSITIVE = "positive"   # evidence signal is favorable for the hypothesis
    NEGATIVE = "negative"   # evidence signal is unfavorable
    NEUTRAL  = "neutral"    # evidence signal is ambiguous or balanced


class HypothesisType(str, Enum):
    BULLISH     = "bullish"
    BEARISH     = "bearish"
    NEUTRAL     = "neutral"
    ALTERNATIVE = "alternative"

    @property
    def is_directional(self) -> bool:
        return self in {HypothesisType.BULLISH, HypothesisType.BEARISH}


class HypothesisStatus(str, Enum):
    PROPOSED     = "proposed"
    SUPPORTED    = "supported"
    REJECTED     = "rejected"
    INCONCLUSIVE = "inconclusive"

    @property
    def is_active(self) -> bool:
        return self in {HypothesisStatus.PROPOSED, HypothesisStatus.SUPPORTED,
                        HypothesisStatus.INCONCLUSIVE}


class ArgumentType(str, Enum):
    SUPPORTING = "supporting"
    OPPOSING   = "opposing"
    NEUTRAL    = "neutral"


class ArgumentStrengthLevel(str, Enum):
    STRONG     = "strong"
    MODERATE   = "moderate"
    WEAK       = "weak"
    NEGLIGIBLE = "negligible"

    @property
    def numeric(self) -> float:
        return {"strong": 1.0, "moderate": 0.65, "weak": 0.35, "negligible": 0.1}[self.value]

    @classmethod
    def from_score(cls, score: float) -> "ArgumentStrengthLevel":
        if score >= 0.70:
            return cls.STRONG
        if score >= 0.45:
            return cls.MODERATE
        if score >= 0.20:
            return cls.WEAK
        return cls.NEGLIGIBLE


class RelationshipType(str, Enum):
    CORROBORATING  = "corroborating"
    CONTRADICTING  = "contradicting"
    COMPLEMENTARY  = "complementary"
    NEUTRAL        = "neutral"


class LogicValidationStatus(str, Enum):
    VALID           = "valid"
    VALID_WITH_GAPS = "valid_with_gaps"
    CONTRADICTORY   = "contradictory"
    INSUFFICIENT    = "insufficient"

    @property
    def is_usable(self) -> bool:
        return self in {LogicValidationStatus.VALID, LogicValidationStatus.VALID_WITH_GAPS}


class ReasoningStatus(str, Enum):
    PENDING       = "pending"
    INTERPRETING  = "interpreting"
    HYPOTHESIZING = "hypothesizing"
    ARGUING       = "arguing"
    CONCLUDING    = "concluding"
    COMPLETE      = "complete"
    FAILED        = "failed"

    @property
    def is_terminal(self) -> bool:
        return self in {ReasoningStatus.COMPLETE, ReasoningStatus.FAILED}


class ReasoningEngineStatus(str, Enum):
    INITIALIZING = "initializing"
    READY        = "ready"
    REASONING    = "reasoning"
    DEGRADED     = "degraded"
    STOPPED      = "stopped"

    @property
    def is_operational(self) -> bool:
        return self in {ReasoningEngineStatus.READY, ReasoningEngineStatus.REASONING}


class ReasoningQualityDimension(str, Enum):
    COMPLETENESS      = "completeness"
    CONSISTENCY       = "consistency"
    TRANSPARENCY      = "transparency"
    EVIDENCE_COVERAGE = "evidence_coverage"
    CHAIN_DEPTH       = "chain_depth"

    @property
    def default_weight(self) -> float:
        return {
            "completeness": 0.25,
            "consistency":  0.25,
            "transparency": 0.20,
            "evidence_coverage": 0.20,
            "chain_depth": 0.10,
        }[self.value]


# ---------------------------------------------------------------------------
# Thresholds
# ---------------------------------------------------------------------------
MIN_EVIDENCE_FOR_REASONING      = 1
MIN_SIGNALS_FOR_HYPOTHESIS      = 1
BULLISH_SIGNAL_THRESHOLD        = 0.55   # >55% positive signals → bullish hypothesis primary
BEARISH_SIGNAL_THRESHOLD        = 0.55   # >55% negative signals → bearish hypothesis primary
STRONG_ARGUMENT_EVIDENCE_COUNT  = 3      # ≥3 supporting items → STRONG argument
DEFAULT_REASONING_TIMEOUT_SECS  = 15.0
REASONING_CACHE_SIZE            = 500
