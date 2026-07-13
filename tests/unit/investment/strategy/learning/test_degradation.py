"""tests/unit/investment/strategy/learning/test_degradation.py
Tests for DegradationStatistics, DriftDetector, PerformanceMonitor, DegradationDetector.
"""
import pytest
from datetime import datetime, timezone, timedelta

from tests.unit.investment.strategy.learning.conftest import (
    make_observation, make_observations_series
)
from iios.investment.strategy.learning.degradation_statistics import (
    degradation_score, improvement_score, rolling_z_scores, cumulative_drift,
    max_drawdown_from_scores, drift_acceleration, signal_to_noise_ratio,
    is_statistically_significant,
)
from iios.investment.strategy.learning.drift_detector import DriftDetector, DriftType, DriftSignal
from iios.investment.strategy.learning.performance_monitor import StrategyPerformanceMonitor
from iios.investment.strategy.learning.degradation_detector import (
    DegradationDetector, DegradationLevel, DegradationReport
)


class TestDegradationStatistics:
    def test_zero_change_score(self):
        assert degradation_score(70.0, 70.0) == 0.0

    def test_full_ceiling_score(self):
        # 40% drop, ceiling 0.40 → 100
        assert degradation_score(100.0, 60.0, ceiling=0.40) == 100.0

    def test_partial_degradation(self):
        ds = degradation_score(100.0, 80.0, ceiling=0.40)
        assert 0 < ds < 100

    def test_improvement_score_positive(self):
        s = improvement_score(70.0, 80.0)
        assert s > 0

    def test_improvement_score_no_drop(self):
        s = improvement_score(80.0, 70.0)
        assert s == 0.0

    def test_rolling_z_scores_length(self):
        vals = list(range(20))
        zs = rolling_z_scores([float(v) for v in vals], window=5)
        assert len(zs) == len(vals)

    def test_cumulative_drift_increasing(self):
        vals = [1.0, 2.0, 3.0, 4.0, 5.0]
        cd = cumulative_drift(vals)
        assert cd > 0

    def test_cumulative_drift_flat(self):
        vals = [5.0, 5.0, 5.0]
        assert cumulative_drift(vals) == 0.0

    def test_max_drawdown_no_drawdown(self):
        scores = [70.0, 75.0, 80.0, 85.0]
        assert max_drawdown_from_scores(scores) == 0.0

    def test_max_drawdown_with_dip(self):
        scores = [100.0, 80.0, 60.0, 90.0]
        dd = max_drawdown_from_scores(scores)
        assert pytest.approx(dd, rel=1e-3) == 0.40   # 60/100 - 1

    def test_signal_to_noise_ratio_uniform(self):
        # All same values → std=0 → snr=0
        snr = signal_to_noise_ratio([50.0, 50.0, 50.0])
        assert snr == 0.0

    def test_is_statistically_significant_large_diff(self):
        baseline = [70.0] * 10
        current  = [30.0] * 10
        assert is_statistically_significant(baseline, current, threshold_z=1.65)

    def test_is_statistically_significant_no_diff(self):
        vals = [70.0] * 10
        assert not is_statistically_significant(vals, vals)


class TestDriftDetector:
    def test_no_drift_stable(self):
        baseline = make_observations_series(n=10, score=70.0, jitter=1.0)
        recent   = make_observations_series(n=10, score=70.0, jitter=1.0)
        detector = DriftDetector()
        signals  = detector.detect(baseline, recent)
        assert isinstance(signals, list)
        # Stable series — significant drifts should be minimal
        significant = [s for s in signals if s.is_significant]
        assert len(significant) == 0

    def test_performance_drift_detected_on_degradation(self):
        baseline = make_observations_series(n=10, score=80.0, jitter=0.5)
        recent   = make_observations_series(n=10, score=30.0, jitter=0.5)
        detector = DriftDetector(mild_threshold=0.05)
        signals  = detector.detect(baseline, recent)
        types    = {s.drift_type for s in signals}
        assert DriftType.PERFORMANCE in types

    def test_drift_signal_magnitude_in_range(self):
        baseline = make_observations_series(n=10, score=80.0)
        recent   = make_observations_series(n=10, score=30.0)
        detector = DriftDetector()
        signals  = detector.detect(baseline, recent)
        for s in signals:
            assert 0.0 <= s.magnitude <= 100.0

    def test_drift_signal_is_frozen(self):
        baseline = make_observations_series(n=10, score=70.0)
        recent   = make_observations_series(n=10, score=50.0)
        detector = DriftDetector()
        signals  = detector.detect(baseline, recent)
        if signals:
            with pytest.raises(Exception):
                signals[0].magnitude = 999.0  # type: ignore[misc]

    def test_empty_windows(self):
        detector = DriftDetector()
        signals  = detector.detect([], [])
        assert signals == []


class TestStrategyPerformanceMonitor:
    def test_observe_and_rolling_mean(self):
        monitor = StrategyPerformanceMonitor(window=5)
        for i in range(5):
            monitor.observe(make_observation(eval_score=70.0))
        mean = monitor.rolling_mean_score("s1")
        assert pytest.approx(mean, rel=1e-3) == 70.0

    def test_is_improving(self):
        monitor = StrategyPerformanceMonitor()
        base_time = datetime.now(timezone.utc) - timedelta(days=10)
        for i in range(10):
            obs = make_observation(
                eval_score=float(50 + i * 3),
                observed_at=base_time + timedelta(days=i),
            )
            monitor.observe(obs)
        assert monitor.is_improving("s1")

    def test_is_declining(self):
        monitor = StrategyPerformanceMonitor()
        base_time = datetime.now(timezone.utc) - timedelta(days=10)
        for i in range(10):
            obs = make_observation(
                eval_score=float(80 - i * 4),
                observed_at=base_time + timedelta(days=i),
            )
            monitor.observe(obs)
        assert monitor.is_declining("s1")

    def test_recent_min_max(self):
        monitor = StrategyPerformanceMonitor(window=5)
        for score in [60.0, 70.0, 80.0, 50.0, 65.0]:
            monitor.observe(make_observation(eval_score=score))
        assert monitor.recent_min_score("s1") == 50.0
        assert monitor.recent_max_score("s1") == 80.0

    def test_unknown_strategy(self):
        monitor = StrategyPerformanceMonitor()
        assert monitor.rolling_mean_score("unknown") == 0.0


class TestDegradationDetector:
    def test_returns_none_with_insufficient_obs(self):
        obs = make_observations_series(n=5, score=70.0)
        detector = DegradationDetector()
        result = detector.detect(obs)
        assert result is None

    def test_no_degradation_stable(self, obs_series_20):
        detector = DegradationDetector()
        report = detector.detect(obs_series_20)
        if report:
            assert report.level in (DegradationLevel.NONE, DegradationLevel.MILD)

    def test_severe_degradation_detected(self, degraded_obs_series):
        detector = DegradationDetector()
        report = detector.detect(degraded_obs_series)
        assert report is not None
        assert report.level in (
            DegradationLevel.MODERATE,
            DegradationLevel.SEVERE,
            DegradationLevel.CRITICAL,
        )
        assert report.is_actionable

    def test_report_is_frozen(self, degraded_obs_series):
        detector = DegradationDetector()
        report   = detector.detect(degraded_obs_series)
        if report:
            with pytest.raises(Exception):
                report.degradation_score = 999.0  # type: ignore[misc]

    def test_level_none_not_actionable(self, obs_series_20):
        detector = DegradationDetector()
        report   = detector.detect(obs_series_20)
        if report and report.level == DegradationLevel.NONE:
            assert not report.is_actionable

    def test_degradation_score_in_range(self, degraded_obs_series):
        detector = DegradationDetector()
        report   = detector.detect(degraded_obs_series)
        if report:
            assert 0.0 <= report.degradation_score <= 100.0
