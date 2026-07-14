"""tests/unit/investment/decision/confidence/test_historical_confidence.py"""
from __future__ import annotations

import pytest

from iios.investment.decision.confidence.confidence_constants import (
    DriftSeverity,
    TrendDirection,
)
from iios.investment.decision.confidence.confidence_drift import ConfidenceDriftDetector
from iios.investment.decision.confidence.confidence_evolution import (
    ConfidenceEvolutionTracker,
)
from iios.investment.decision.confidence.confidence_trends import ConfidenceTrendAnalyzer
from iios.investment.decision.confidence.historical_confidence import (
    HistoricalConfidenceAnalyzer,
)


# ========================= ConfidenceTrendAnalyzer =======================

class TestConfidenceTrendAnalyzer:
    def test_empty_series(self):
        ta = ConfidenceTrendAnalyzer()
        result = ta.analyze([])
        assert result.sample_count == 0
        assert result.direction == TrendDirection.STABLE

    def test_single_element(self):
        ta = ConfidenceTrendAnalyzer()
        result = ta.analyze([70.0])
        assert result.sample_count == 1
        assert result.slope == 0.0

    def test_improving_trend(self):
        ta = ConfidenceTrendAnalyzer()
        series = [50.0, 55.0, 60.0, 65.0, 70.0, 75.0, 80.0, 85.0, 90.0, 95.0]
        result = ta.analyze(series)
        assert result.slope > 0
        assert result.direction == TrendDirection.IMPROVING

    def test_declining_trend(self):
        ta = ConfidenceTrendAnalyzer()
        series = [90.0, 85.0, 80.0, 75.0, 70.0, 65.0, 60.0, 55.0, 50.0, 45.0]
        result = ta.analyze(series)
        assert result.slope < 0
        assert result.direction == TrendDirection.DECLINING

    def test_stable_trend(self):
        ta = ConfidenceTrendAnalyzer()
        series = [70.0, 71.0, 70.0, 71.0, 70.0, 71.0, 70.0, 71.0, 70.0, 71.0]
        result = ta.analyze(series)
        assert result.direction == TrendDirection.STABLE

    def test_volatile_trend(self):
        ta = ConfidenceTrendAnalyzer()
        series = [20.0, 90.0, 15.0, 85.0, 25.0, 95.0, 10.0, 88.0, 30.0, 92.0]
        result = ta.analyze(series)
        assert result.direction == TrendDirection.VOLATILE

    def test_to_dict(self):
        ta = ConfidenceTrendAnalyzer()
        result = ta.analyze([70.0, 75.0, 80.0])
        d = result.to_dict()
        assert "direction" in d
        assert "slope" in d
        assert "trend_confidence" in d


# ========================= ConfidenceDriftDetector =======================

class TestConfidenceDriftDetector:
    def test_no_drift_stable(self):
        dd = ConfidenceDriftDetector()
        series = [70.0] * 30
        result = dd.detect(series)
        assert result.severity == DriftSeverity.NONE

    def test_severe_drift(self):
        dd = ConfidenceDriftDetector()
        baseline = [80.0] * 30
        drifted  = [80.0] * 25 + [50.0, 50.0, 50.0, 50.0, 50.0]
        result = dd.detect(drifted)
        assert result.severity in {DriftSeverity.MODERATE, DriftSeverity.SEVERE}

    def test_drift_score_range(self):
        dd = ConfidenceDriftDetector()
        series = [70.0] * 10
        result = dd.detect(series)
        assert 0.0 <= result.drift_score <= 100.0

    def test_absolute_drift_computed(self):
        dd = ConfidenceDriftDetector()
        series = [80.0] * 20 + [60.0] * 5
        result = dd.detect(series, baseline_window=20, recent_window=5)
        assert result.absolute_drift < 0   # current < baseline → negative drift

    def test_empty_series(self):
        dd = ConfidenceDriftDetector()
        result = dd.detect([])
        assert result.severity == DriftSeverity.NONE

    def test_to_dict(self):
        dd = ConfidenceDriftDetector()
        result = dd.detect([70.0, 70.0, 70.0])
        d = result.to_dict()
        assert "severity" in d
        assert "drift_score" in d


# ========================= ConfidenceEvolutionTracker ====================

class TestConfidenceEvolutionTracker:
    def test_record_and_evolve(self):
        tracker = ConfidenceEvolutionTracker()
        tracker.record("INFY", 1, 65.0)
        tracker.record("INFY", 2, 70.0)
        tracker.record("INFY", 3, 75.0)
        evol = tracker.evolution("INFY")
        assert evol is not None
        assert evol.delta == pytest.approx(10.0)
        assert evol.record_count == 3

    def test_unknown_subject_returns_none(self):
        tracker = ConfidenceEvolutionTracker()
        assert tracker.evolution("UNKNOWN") is None

    def test_confidence_series(self):
        tracker = ConfidenceEvolutionTracker()
        for v, c in enumerate([60.0, 65.0, 70.0], start=1):
            tracker.record("TCS", v, c)
        series = tracker.confidence_series("TCS")
        assert series == [60.0, 65.0, 70.0]

    def test_known_subjects(self):
        tracker = ConfidenceEvolutionTracker()
        tracker.record("INFY", 1, 70.0)
        tracker.record("TCS",  1, 65.0)
        assert "INFY" in tracker.known_subjects()
        assert "TCS" in tracker.known_subjects()

    def test_to_dict(self):
        tracker = ConfidenceEvolutionTracker()
        tracker.record("INFY", 1, 70.0)
        evol = tracker.evolution("INFY")
        d = evol.to_dict()
        assert "delta" in d
        assert "last_conf" in d


# ========================= HistoricalConfidenceAnalyzer ==================

class TestHistoricalConfidenceAnalyzer:
    def test_no_history_returns_neutral(self):
        ana = HistoricalConfidenceAnalyzer()
        result = ana.analyze("NEW", [], version=1, current=70.0)
        assert result.sample_count == 0
        assert result.stability_score == pytest.approx(50.0)

    def test_stable_history_high_stability(self):
        ana = HistoricalConfidenceAnalyzer()
        series = [70.0] * 20
        result = ana.analyze("INFY", series, version=21, current=70.0)
        assert result.stability_score >= 80.0

    def test_historical_conf_range(self):
        ana = HistoricalConfidenceAnalyzer()
        series = [65.0, 68.0, 70.0, 72.0, 74.0]
        result = ana.analyze("INFY", series, version=6, current=74.0)
        assert 0.0 <= result.historical_conf <= 100.0

    def test_evolution_recorded(self):
        ana = HistoricalConfidenceAnalyzer()
        ana.analyze("INFY", [70.0, 72.0], version=3, current=75.0)
        evol = ana._evol.evolution("INFY")
        assert evol is not None

    def test_to_dict(self):
        ana = HistoricalConfidenceAnalyzer()
        result = ana.analyze("INFY", [70.0], version=2, current=72.0)
        d = result.to_dict()
        assert "stability_score" in d
        assert "historical_conf" in d
        assert "trend" in d
