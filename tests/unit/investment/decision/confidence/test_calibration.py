"""tests/unit/investment/decision/confidence/test_calibration.py"""
from __future__ import annotations

import pytest

from iios.investment.decision.confidence.calibration_engine import (
    CalibrationEngine,
    CalibrationResult,
)
from iios.investment.decision.confidence.calibration_statistics import (
    CalibrationStatisticsTracker,
)
from iios.investment.decision.confidence.confidence_calibrator import (
    CalibrationRecord,
    ConfidenceCalibrator,
)
from iios.investment.decision.confidence.confidence_constants import (
    MIN_CALIBRATION_SAMPLES,
    CalibrationStatus,
)
from iios.investment.decision.confidence.confidence_validator import ConfidenceValidator


# ========================= ConfidenceCalibrator ==========================

class TestConfidenceCalibrator:
    def test_insufficient_data_when_no_records(self):
        cal = ConfidenceCalibrator()
        score, status = cal.calibrate(70.0)
        assert score == 70.0   # raw returned unchanged
        assert status == CalibrationStatus.INSUFFICIENT_DATA

    def test_calibrate_with_records(self):
        cal = ConfidenceCalibrator(min_samples=5)
        for i in range(10):
            cal.record_outcome(f"D{i}", 70.0, i % 2 == 0)
        score, status = cal.calibrate(70.0)
        assert 0.0 <= score <= 100.0
        assert status != CalibrationStatus.INSUFFICIENT_DATA

    def test_buckets_populated(self):
        cal = ConfidenceCalibrator(min_samples=5)
        for i in range(10):
            cal.record_outcome(f"D{i}", float(i * 10), True)
        buckets = cal.buckets()
        assert len(buckets) == 10   # CALIBRATION_BUCKET_COUNT default

    def test_record_count(self):
        cal = ConfidenceCalibrator()
        cal.record_outcome("D1", 60.0, True)
        cal.record_outcome("D2", 80.0, False)
        assert cal.record_count() == 2

    def test_calibration_score_range(self):
        cal = ConfidenceCalibrator(min_samples=5)
        for i in range(20):
            cal.record_outcome(f"D{i}", 75.0, i % 3 == 0)
        score, _ = cal.calibrate(75.0)
        assert 0.0 <= score <= 100.0

    def test_calibration_record_is_immutable(self):
        record = CalibrationRecord(
            decision_id="D1",
            raw_confidence=70.0,
            was_correct=True,
            recorded_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
        )
        with pytest.raises(Exception):
            record.was_correct = False  # type: ignore


# ========================= CalibrationEngine =============================

class TestCalibrationEngine:
    def test_returns_result(self):
        engine = CalibrationEngine()
        result = engine.calibrate(60.0)
        assert isinstance(result, CalibrationResult)

    def test_insufficient_data_status(self):
        engine = CalibrationEngine()
        result = engine.calibrate(60.0)
        assert result.status == CalibrationStatus.INSUFFICIENT_DATA

    def test_quality_score_from_status(self):
        engine = CalibrationEngine()
        result = engine.calibrate(60.0)
        expected_quality = result.status.quality_score
        assert result.quality_score == expected_quality

    def test_record_outcome(self):
        engine = CalibrationEngine()
        engine.record_outcome("D1", 70.0, True)
        assert engine.calibrator.record_count() == 1

    def test_to_dict(self):
        engine = CalibrationEngine()
        result = engine.calibrate(80.0)
        d = result.to_dict()
        assert "calibrated_conf" in d
        assert "status" in d
        assert "quality_score" in d

    def test_adjustment_zero_when_raw_returned(self):
        engine = CalibrationEngine()
        result = engine.calibrate(75.0)
        # No records → calibrated == raw → adjustment == 0
        assert result.adjustment == 0.0


# ========================= CalibrationStatisticsTracker ==================

class TestCalibrationStatisticsTracker:
    def test_empty(self):
        tracker = CalibrationStatisticsTracker()
        stats = tracker.summary()
        assert stats.total_calibrations == 0

    def test_record_and_summary(self):
        tracker = CalibrationStatisticsTracker()
        tracker.record(70.0, 68.0, CalibrationStatus.PARTIALLY_CALIBRATED)
        tracker.record(80.0, 79.0, CalibrationStatus.WELL_CALIBRATED)
        stats = tracker.summary()
        assert stats.total_calibrations == 2
        assert stats.well_calibrated == 1
        assert stats.partially_calibrated == 1

    def test_avg_adjustment(self):
        tracker = CalibrationStatisticsTracker()
        tracker.record(70.0, 65.0, CalibrationStatus.PARTIALLY_CALIBRATED)
        stats = tracker.summary()
        assert abs(stats.avg_adjustment - 5.0) < 0.01

    def test_reset(self):
        tracker = CalibrationStatisticsTracker()
        tracker.record(70.0, 70.0, CalibrationStatus.WELL_CALIBRATED)
        tracker.reset()
        stats = tracker.summary()
        assert stats.total_calibrations == 0

    def test_to_dict(self):
        tracker = CalibrationStatisticsTracker()
        tracker.record(60.0, 60.0, CalibrationStatus.INSUFFICIENT_DATA)
        d = tracker.summary().to_dict()
        assert "reliability_rate" in d
        assert "total_calibrations" in d
