"""tests/unit/investment/decision/confidence/test_overall_confidence.py"""
from __future__ import annotations

import pytest

from iios.investment.decision.confidence.confidence_constants import (
    CalibrationStatus,
    ConfidenceDimension,
    ConfidenceLevel,
    ConfidenceQualityGrade,
)
from iios.investment.decision.confidence.confidence_health import ConfidenceHealthMonitor
from iios.investment.decision.confidence.confidence_quality import (
    ConfidenceQualityEvaluator,
)
from iios.investment.decision.confidence.confidence_score import (
    ConfidenceScore,
    compute_confidence_score,
)
from iios.investment.decision.confidence.confidence_statistics import (
    ConfidenceStatisticsTracker,
)
from iios.investment.decision.confidence.confidence_validator import ConfidenceValidator
from iios.investment.decision.confidence.decision_confidence import (
    DecisionConfidence,
    build_decision_confidence,
)
from iios.investment.decision.confidence.overall_confidence import (
    OverallConfidenceEstimator,
)


# ========================= ConfidenceScore ===============================

class TestConfidenceScore:
    def test_all_max(self):
        cs = compute_confidence_score(100, 100, 100, 100, 100)
        assert cs.overall == pytest.approx(100.0)

    def test_all_zero(self):
        cs = compute_confidence_score(0, 0, 0, 0, 0)
        assert cs.overall == 0.0

    def test_grade_a(self):
        cs = compute_confidence_score(95, 95, 95, 95, 95)
        assert cs.grade == ConfidenceQualityGrade.A

    def test_grade_f(self):
        cs = compute_confidence_score(10, 10, 10, 10, 10)
        assert cs.grade == ConfidenceQualityGrade.F

    def test_level_very_high(self):
        cs = compute_confidence_score(90, 90, 90, 90, 90)
        assert cs.level == ConfidenceLevel.VERY_HIGH

    def test_to_dict_keys(self):
        cs = compute_confidence_score(80, 80, 80, 80, 80)
        d = cs.to_dict()
        for k in ("overall", "evidence", "reasoning", "scoring", "historical",
                  "calibration", "level", "grade", "computed_at"):
            assert k in d

    def test_dimension_weights_sum(self):
        total = sum(dim.default_weight for dim in ConfidenceDimension)
        assert total == pytest.approx(1.0)


# ========================= DecisionConfidence ============================

class TestDecisionConfidence:
    def _build(self, ev=70.0, re=70.0, sc=70.0, hi=70.0, ca=70.0, scoring=True):
        return build_decision_confidence(
            decision_id="D1",
            subject_id="INFY",
            subject_type="equity",
            evidence_confidence=ev,
            reasoning_confidence=re,
            scoring_confidence=sc,
            historical_confidence=hi,
            calibration_quality=ca,
            scoring_available=scoring,
            version=1,
        )

    def test_builds_correctly(self):
        dc = self._build()
        assert isinstance(dc, DecisionConfidence)

    def test_overall_in_range(self):
        dc = self._build()
        assert 0.0 <= dc.overall_confidence <= 100.0

    def test_confidence_level_from_overall(self):
        dc = self._build(ev=90, re=90, sc=90, hi=90, ca=90)
        assert dc.confidence_level == ConfidenceLevel.VERY_HIGH

    def test_scoring_unavailable_redistributes(self):
        dc_with = self._build(scoring=True)
        dc_without = self._build(sc=0.0, scoring=False)
        # Without scoring, weights redistribute; both should be valid
        assert 0.0 <= dc_without.overall_confidence <= 100.0

    def test_uncertainty_computed(self):
        dc = self._build(ev=90, re=30, sc=70, hi=50, ca=60)
        assert dc.uncertainty > 0.0

    def test_immutable(self):
        dc = self._build()
        with pytest.raises(Exception):
            dc.overall_confidence = 999.0  # type: ignore

    def test_dimension_score_accessor(self):
        dc = self._build(ev=80.0)
        assert dc.dimension_score(ConfidenceDimension.EVIDENCE) == pytest.approx(80.0, abs=0.01)

    def test_to_dict(self):
        dc = self._build()
        d = dc.to_dict()
        assert "overall_confidence" in d
        assert "confidence_level" in d
        assert "uncertainty" in d


# ========================= OverallConfidenceEstimator ====================

class TestOverallConfidenceEstimator:
    def test_estimate_returns_result(
        self, rich_evidence_snapshot, rich_reasoning_snapshot,
    ):
        from iios.investment.decision.confidence.evidence_confidence import EvidenceConfidenceEstimator
        from iios.investment.decision.confidence.reasoning_confidence import ReasoningConfidenceEstimator
        from iios.investment.decision.confidence.historical_confidence import HistoricalConfidenceAnalyzer
        from iios.investment.decision.confidence.calibration_engine import CalibrationEngine

        ev_result  = EvidenceConfidenceEstimator().estimate(rich_evidence_snapshot)
        re_result  = ReasoningConfidenceEstimator().estimate(rich_reasoning_snapshot)
        hi_result  = HistoricalConfidenceAnalyzer().analyze("INFY", [], 1, ev_result.overall)
        cal_result = CalibrationEngine().calibrate(ev_result.overall)

        ov = OverallConfidenceEstimator().estimate(
            decision_id="D1",
            subject_id="INFY",
            subject_type="equity",
            version=1,
            evidence_result=ev_result,
            reasoning_result=re_result,
            historical_result=hi_result,
            calibration_result=cal_result,
            scoring_confidence=0.0,
            scoring_available=False,
        )
        assert 0.0 <= ov.decision_confidence.overall_confidence <= 100.0


# ========================= ConfidenceValidator ===========================

class TestConfidenceValidator:
    def test_valid_snapshot(self, rich_evidence_snapshot, rich_reasoning_snapshot):
        from iios.investment.decision.confidence.decision_confidence_engine import DecisionConfidenceEngine
        engine = DecisionConfidenceEngine()
        engine.start()
        snap = engine.estimate_sync(rich_evidence_snapshot, rich_reasoning_snapshot)
        v = ConfidenceValidator()
        result = v.validate(snap)
        assert isinstance(result.is_valid, bool)

    def test_to_dict(self, rich_evidence_snapshot, rich_reasoning_snapshot):
        from iios.investment.decision.confidence.decision_confidence_engine import DecisionConfidenceEngine
        engine = DecisionConfidenceEngine()
        engine.start()
        snap = engine.estimate_sync(rich_evidence_snapshot, rich_reasoning_snapshot)
        result = ConfidenceValidator().validate(snap)
        d = result.to_dict()
        assert "is_valid" in d
        assert "issues" in d
        assert "warnings" in d


# ========================= ConfidenceQualityEvaluator ====================

class TestConfidenceQualityEvaluator:
    def test_evaluate_returns_report(self, rich_evidence_snapshot, rich_reasoning_snapshot):
        from iios.investment.decision.confidence.decision_confidence_engine import DecisionConfidenceEngine
        engine = DecisionConfidenceEngine()
        engine.start()
        snap = engine.estimate_sync(rich_evidence_snapshot, rich_reasoning_snapshot)
        qe = ConfidenceQualityEvaluator()
        report = qe.evaluate(snap)
        assert 0.0 <= report.overall_quality <= 100.0

    def test_grade_set(self, rich_evidence_snapshot, rich_reasoning_snapshot):
        from iios.investment.decision.confidence.decision_confidence_engine import DecisionConfidenceEngine
        engine = DecisionConfidenceEngine()
        engine.start()
        snap = engine.estimate_sync(rich_evidence_snapshot, rich_reasoning_snapshot)
        report = ConfidenceQualityEvaluator().evaluate(snap)
        assert report.grade in list(ConfidenceQualityGrade)

    def test_to_dict(self, rich_evidence_snapshot, rich_reasoning_snapshot):
        from iios.investment.decision.confidence.decision_confidence_engine import DecisionConfidenceEngine
        engine = DecisionConfidenceEngine()
        engine.start()
        snap = engine.estimate_sync(rich_evidence_snapshot, rich_reasoning_snapshot)
        report = ConfidenceQualityEvaluator().evaluate(snap)
        d = report.to_dict()
        assert "overall_quality" in d
        assert "grade" in d


# ========================= ConfidenceHealthMonitor =======================

class TestConfidenceHealthMonitor:
    def test_empty(self):
        hm = ConfidenceHealthMonitor()
        r = hm.report()
        assert r.total_runs == 0
        assert r.success_rate == 0.0

    def test_record_success(self):
        hm = ConfidenceHealthMonitor()
        hm.record_success(75.0, 100.0)
        r = hm.report()
        assert r.total_runs == 1
        assert r.successful_runs == 1
        assert r.avg_confidence == pytest.approx(75.0)

    def test_record_failure(self):
        hm = ConfidenceHealthMonitor()
        hm.record_failure()
        assert hm.report().failed_runs == 1

    def test_reset(self):
        hm = ConfidenceHealthMonitor()
        hm.record_success(80.0, 50.0)
        hm.reset()
        assert hm.report().total_runs == 0

    def test_grade_distribution_populated(self):
        hm = ConfidenceHealthMonitor()
        hm.record_success(90.0, 50.0)
        r = hm.report()
        assert "A" in r.grade_distribution

    def test_to_dict(self):
        hm = ConfidenceHealthMonitor()
        d = hm.report().to_dict()
        assert "success_rate" in d
        assert "grade_distribution" in d


# ========================= ConfidenceStatisticsTracker ==================

class TestConfidenceStatisticsTracker:
    def test_empty(self):
        tracker = ConfidenceStatisticsTracker()
        stats = tracker.summary()
        assert stats.total_estimations == 0

    def test_record_and_summary(self):
        tracker = ConfidenceStatisticsTracker()
        tracker.record_success(
            overall_confidence=75.0, duration_ms=80.0,
            evidence_confidence=70.0, reasoning_confidence=80.0,
        )
        tracker.record_success(
            overall_confidence=85.0, duration_ms=90.0,
            evidence_confidence=80.0, reasoning_confidence=90.0,
        )
        stats = tracker.summary()
        assert stats.total_estimations == 2
        assert stats.successful == 2
        assert stats.avg_confidence == pytest.approx(80.0)

    def test_record_failure(self):
        tracker = ConfidenceStatisticsTracker()
        tracker.record_failure()
        assert tracker.summary().failed == 1

    def test_high_confidence_pct(self):
        tracker = ConfidenceStatisticsTracker()
        tracker.record_success(80.0, 50.0, 75.0, 85.0)  # >= 70 → counts
        tracker.record_success(40.0, 50.0, 35.0, 45.0)  # < 70 → doesn't count
        stats = tracker.summary()
        assert stats.high_confidence_pct == pytest.approx(0.5)
