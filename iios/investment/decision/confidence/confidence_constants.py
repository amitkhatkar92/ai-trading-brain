"""iios/investment/decision/confidence/confidence_constants.py
All enumerations, constants, and thresholds for the Decision Confidence Engine.
"""
from __future__ import annotations

from enum import Enum


class ConfidenceLevel(str, Enum):
    VERY_HIGH = "very_high"   # >= 85
    HIGH      = "high"        # >= 70
    MEDIUM    = "medium"      # >= 50
    LOW       = "low"         # >= 30
    VERY_LOW  = "very_low"    # <  30

    @classmethod
    def from_score(cls, score: float) -> "ConfidenceLevel":
        if score >= 85.0: return cls.VERY_HIGH
        if score >= 70.0: return cls.HIGH
        if score >= 50.0: return cls.MEDIUM
        if score >= 30.0: return cls.LOW
        return cls.VERY_LOW

    @property
    def is_actionable(self) -> bool:
        return self in {ConfidenceLevel.VERY_HIGH, ConfidenceLevel.HIGH, ConfidenceLevel.MEDIUM}

    @property
    def numeric(self) -> int:
        return {"very_high": 5, "high": 4, "medium": 3, "low": 2, "very_low": 1}[self.value]


class ConfidenceDimension(str, Enum):
    EVIDENCE    = "evidence"
    REASONING   = "reasoning"
    SCORING     = "scoring"
    HISTORICAL  = "historical"
    CALIBRATION = "calibration"

    @property
    def default_weight(self) -> float:
        return {
            "evidence":    0.30,
            "reasoning":   0.30,
            "scoring":     0.20,
            "historical":  0.10,
            "calibration": 0.10,
        }[self.value]


class EvidenceConfidenceFactor(str, Enum):
    COVERAGE     = "coverage"
    FRESHNESS    = "freshness"
    RELIABILITY  = "reliability"
    CONSISTENCY  = "consistency"

    @property
    def default_weight(self) -> float:
        return {
            "coverage":    0.30,
            "freshness":   0.25,
            "reliability": 0.30,
            "consistency": 0.15,
        }[self.value]


class ReasoningConfidenceFactor(str, Enum):
    COMPLETENESS        = "completeness"
    CONSISTENCY         = "consistency"
    CONTRADICTION_FREE  = "contradiction_free"
    HYPOTHESIS_STRENGTH = "hypothesis_strength"
    ARGUMENT_QUALITY    = "argument_quality"

    @property
    def default_weight(self) -> float:
        return {
            "completeness":        0.25,
            "consistency":         0.25,
            "contradiction_free":  0.20,
            "hypothesis_strength": 0.15,
            "argument_quality":    0.15,
        }[self.value]


class CalibrationStatus(str, Enum):
    WELL_CALIBRATED      = "well_calibrated"
    PARTIALLY_CALIBRATED = "partially_calibrated"
    POORLY_CALIBRATED    = "poorly_calibrated"
    UNCALIBRATED         = "uncalibrated"
    INSUFFICIENT_DATA    = "insufficient_data"

    @property
    def is_reliable(self) -> bool:
        return self in {CalibrationStatus.WELL_CALIBRATED, CalibrationStatus.PARTIALLY_CALIBRATED}

    @property
    def quality_score(self) -> float:
        return {
            "well_calibrated":      90.0,
            "partially_calibrated": 65.0,
            "poorly_calibrated":    35.0,
            "uncalibrated":         20.0,
            "insufficient_data":    50.0,
        }[self.value]


class ConfidenceEngineStatus(str, Enum):
    INITIALIZING = "initializing"
    READY        = "ready"
    ESTIMATING   = "estimating"
    DEGRADED     = "degraded"
    STOPPED      = "stopped"

    @property
    def is_operational(self) -> bool:
        return self in {
            ConfidenceEngineStatus.READY,
            ConfidenceEngineStatus.ESTIMATING,
            ConfidenceEngineStatus.DEGRADED,
        }


class TrendDirection(str, Enum):
    IMPROVING = "improving"
    STABLE    = "stable"
    DECLINING = "declining"
    VOLATILE  = "volatile"

    @property
    def is_concerning(self) -> bool:
        return self in {TrendDirection.DECLINING, TrendDirection.VOLATILE}


class DriftSeverity(str, Enum):
    NONE     = "none"
    MINOR    = "minor"
    MODERATE = "moderate"
    SEVERE   = "severe"

    @property
    def requires_action(self) -> bool:
        return self in {DriftSeverity.MODERATE, DriftSeverity.SEVERE}


class ConfidenceQualityGrade(str, Enum):
    A = "A"
    B = "B"
    C = "C"
    D = "D"
    F = "F"

    @classmethod
    def from_score(cls, score: float) -> "ConfidenceQualityGrade":
        if score >= 90.0: return cls.A
        if score >= 75.0: return cls.B
        if score >= 60.0: return cls.C
        if score >= 45.0: return cls.D
        return cls.F


# ─── Overall dimension weights (must sum to 1.0) ─────────────────────────────
EVIDENCE_DIM_WEIGHT    = 0.30
REASONING_DIM_WEIGHT   = 0.30
SCORING_DIM_WEIGHT     = 0.20
HISTORICAL_DIM_WEIGHT  = 0.10
CALIBRATION_DIM_WEIGHT = 0.10

# ─── Confidence thresholds ───────────────────────────────────────────────────
HIGH_CONFIDENCE_THRESHOLD   = 70.0
MEDIUM_CONFIDENCE_THRESHOLD = 50.0
LOW_CONFIDENCE_THRESHOLD    = 30.0

# ─── Calibration ─────────────────────────────────────────────────────────────
MIN_CALIBRATION_SAMPLES         = 20
CALIBRATION_BUCKET_COUNT        = 10
CALIBRATION_TOLERANCE           = 0.05   # ±5 % accuracy tolerance

# ─── History / trend ─────────────────────────────────────────────────────────
HISTORY_WINDOW_SIZE      = 100
TREND_WINDOW_SIZE        = 10
DRIFT_THRESHOLD_MINOR    = 5.0
DRIFT_THRESHOLD_MODERATE = 10.0
DRIFT_THRESHOLD_SEVERE   = 20.0

# ─── Evidence confidence ─────────────────────────────────────────────────────
MIN_SOURCE_TYPES_FOR_COVERAGE   = 2
IDEAL_SOURCE_TYPES_FOR_COVERAGE = 5
FRESHNESS_DECAY_HALF_LIFE_HOURS = 24.0

# ─── Reasoning confidence ────────────────────────────────────────────────────
EXPECTED_REASONING_STEPS        = 9
STRONG_HYPOTHESIS_SUPPORT_SCORE = 0.55

# ─── Performance ─────────────────────────────────────────────────────────────
DEFAULT_CONFIDENCE_TIMEOUT_SECS = 10.0
CACHE_TTL_SECONDS               = 300
