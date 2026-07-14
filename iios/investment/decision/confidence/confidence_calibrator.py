"""iios/investment/decision/confidence/confidence_calibrator.py
ConfidenceCalibrator — maintains calibration records and adjusts raw confidence.
Calibration maps raw scores to historical accuracy using bucketed statistics.
"""
from __future__ import annotations

import statistics
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from iios.investment.decision.confidence.confidence_constants import (
    CALIBRATION_BUCKET_COUNT,
    CALIBRATION_TOLERANCE,
    CalibrationStatus,
    MIN_CALIBRATION_SAMPLES,
)


@dataclass(frozen=True)
class CalibrationRecord:
    """One historical (confidence, outcome) pair."""
    decision_id:    str
    raw_confidence: float    # 0–100
    was_correct:    bool     # did the decision prove correct?
    recorded_at:    datetime

    def to_dict(self) -> Dict[str, Any]:
        return {
            "decision_id":    self.decision_id,
            "raw_confidence": round(self.raw_confidence, 2),
            "was_correct":    self.was_correct,
            "recorded_at":    self.recorded_at.isoformat(),
        }


@dataclass(frozen=True)
class CalibrationBucket:
    """Accuracy statistics for one confidence bucket."""
    bucket_min:    float
    bucket_max:    float
    sample_count:  int
    accuracy:      float     # 0–1 fraction correct
    calibration_error: float  # |accuracy - expected_accuracy|

    def to_dict(self) -> Dict[str, Any]:
        return {
            "range":             f"{self.bucket_min:.0f}–{self.bucket_max:.0f}",
            "sample_count":      self.sample_count,
            "accuracy":          round(self.accuracy, 4),
            "calibration_error": round(self.calibration_error, 4),
        }


class ConfidenceCalibrator:
    """
    Thread-safe calibration store.
    Accepts historical feedback and adjusts a raw confidence score.
    When fewer than MIN_CALIBRATION_SAMPLES records exist, the raw score
    is returned unchanged with INSUFFICIENT_DATA status.
    """

    def __init__(
        self,
        n_buckets:     int = CALIBRATION_BUCKET_COUNT,
        min_samples:   int = MIN_CALIBRATION_SAMPLES,
    ) -> None:
        self._n_buckets  = n_buckets
        self._min_samples = min_samples
        self._lock        = threading.RLock()
        self._records: List[CalibrationRecord] = []
        self._bucket_width = 100.0 / n_buckets

    # ── write ──────────────────────────────────────────────────────────────

    def record_outcome(
        self,
        decision_id:    str,
        raw_confidence: float,
        was_correct:    bool,
    ) -> None:
        with self._lock:
            self._records.append(CalibrationRecord(
                decision_id=decision_id,
                raw_confidence=raw_confidence,
                was_correct=was_correct,
                recorded_at=datetime.now(timezone.utc),
            ))

    # ── calibration ────────────────────────────────────────────────────────

    def calibrate(self, raw_confidence: float) -> Tuple[float, CalibrationStatus]:
        """
        Returns (calibrated_confidence, CalibrationStatus).
        The calibrated confidence is adjusted toward historical accuracy.
        """
        with self._lock:
            n = len(self._records)

        if n < self._min_samples:
            return raw_confidence, CalibrationStatus.INSUFFICIENT_DATA

        buckets = self._compute_buckets()
        bucket = self._find_bucket(raw_confidence, buckets)

        if bucket is None or bucket.sample_count < 5:
            return raw_confidence, CalibrationStatus.PARTIALLY_CALIBRATED

        # Blend raw with historical accuracy (Platt scaling approximation)
        # calibrated = raw * α + bucket.accuracy * 100 * (1 - α)
        alpha = 0.6   # trust raw 60 %, history 40 %
        calibrated = raw_confidence * alpha + bucket.accuracy * 100.0 * (1.0 - alpha)
        calibrated = max(0.0, min(100.0, calibrated))

        # Status based on mean calibration error
        mean_error = statistics.mean(b.calibration_error for b in buckets if b.sample_count > 0)
        if mean_error < CALIBRATION_TOLERANCE:
            status = CalibrationStatus.WELL_CALIBRATED
        elif mean_error < CALIBRATION_TOLERANCE * 3:
            status = CalibrationStatus.PARTIALLY_CALIBRATED
        else:
            status = CalibrationStatus.POORLY_CALIBRATED

        return round(calibrated, 4), status

    # ── inspection ─────────────────────────────────────────────────────────

    def buckets(self) -> List[CalibrationBucket]:
        with self._lock:
            return self._compute_buckets()

    def record_count(self) -> int:
        with self._lock:
            return len(self._records)

    # ── private ────────────────────────────────────────────────────────────

    def _compute_buckets(self) -> List[CalibrationBucket]:
        """Partition records into n_buckets and compute accuracy per bucket."""
        width = self._bucket_width
        result: List[CalibrationBucket] = []
        records = self._records   # already under lock when called internally

        for i in range(self._n_buckets):
            lo = i * width
            hi = lo + width
            bucket_recs = [r for r in records if lo <= r.raw_confidence < hi]
            if not bucket_recs:
                result.append(CalibrationBucket(
                    bucket_min=lo, bucket_max=hi, sample_count=0,
                    accuracy=0.0, calibration_error=0.0,
                ))
                continue
            n_correct = sum(1 for r in bucket_recs if r.was_correct)
            accuracy  = n_correct / len(bucket_recs)
            expected  = (lo + width / 2) / 100.0
            err       = abs(accuracy - expected)
            result.append(CalibrationBucket(
                bucket_min=lo,
                bucket_max=hi,
                sample_count=len(bucket_recs),
                accuracy=round(accuracy, 4),
                calibration_error=round(err, 4),
            ))
        return result

    def _find_bucket(
        self,
        score:   float,
        buckets: List[CalibrationBucket],
    ) -> Optional[CalibrationBucket]:
        for b in buckets:
            if b.bucket_min <= score < b.bucket_max:
                return b
        return buckets[-1] if buckets else None
