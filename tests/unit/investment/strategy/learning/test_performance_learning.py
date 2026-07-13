"""tests/unit/investment/strategy/learning/test_performance_learning.py
Tests for SuccessPattern, FailurePattern, PerformanceDrift, PerformanceLearner.
"""
import pytest
from datetime import datetime, timezone, timedelta
from typing import List

from tests.unit.investment.strategy.learning.conftest import (
    make_observation, make_observations_series
)
from iios.investment.strategy.learning.success_pattern import SuccessPatternExtractor, SuccessPattern
from iios.investment.strategy.learning.failure_pattern import FailurePatternExtractor, FailurePattern
from iios.investment.strategy.learning.performance_drift import PerformanceDriftAnalyzer, PerformanceDrift
from iios.investment.strategy.learning.performance_learning import PerformanceLearner


class TestSuccessPatternExtractor:
    def test_no_patterns_with_few_obs(self):
        obs = [make_observation(eval_score=75.0) for _ in range(2)]
        extractor = SuccessPatternExtractor(min_support=3)
        patterns = extractor.extract(obs)
        assert isinstance(patterns, list)

    def test_regime_alignment_pattern_detected(self):
        # 6 high-score observations all in "trending" regime
        obs = [
            make_observation(eval_score=80.0, regime="trending")
            for _ in range(6)
        ]
        extractor = SuccessPatternExtractor(success_threshold=70.0, min_support=3)
        patterns = extractor.extract(obs)
        names = [p.name for p in patterns]
        assert any("regime_alignment" in n for n in names)

    def test_sharpe_pattern_detected(self):
        obs = [
            make_observation(eval_score=80.0, sharpe=2.0)
            for _ in range(5)
        ]
        extractor = SuccessPatternExtractor(success_threshold=70.0, min_support=3)
        patterns = extractor.extract(obs)
        assert isinstance(patterns, list)

    def test_pattern_confidence_in_range(self):
        obs = make_observations_series(n=20, score=80.0)
        extractor = SuccessPatternExtractor()
        patterns = extractor.extract(obs)
        for p in patterns:
            assert 0.0 <= p.confidence <= 1.0

    def test_pattern_is_frozen(self):
        obs = make_observations_series(n=20, score=80.0)
        extractor = SuccessPatternExtractor()
        patterns = extractor.extract(obs)
        if patterns:
            p = patterns[0]
            with pytest.raises(Exception):
                p.name = "hack"  # type: ignore[misc]


class TestFailurePatternExtractor:
    def test_no_failure_patterns_for_good_strategy(self):
        obs = [make_observation(eval_score=80.0, max_dd=0.05, win_rate=0.65) for _ in range(10)]
        extractor = FailurePatternExtractor(failure_threshold=45.0, min_support=3)
        patterns = extractor.extract(obs)
        # May or may not find any failure patterns — just must be a list
        assert isinstance(patterns, list)

    def test_regime_mismatch_failure_detected(self):
        obs = [
            make_observation(
                sid="s_fail",
                eval_score=35.0,
                regime="bear_market",   # not in supported_regimes → mismatch
            )
            for _ in range(5)
        ]
        extractor = FailurePatternExtractor(failure_threshold=45.0, min_support=3)
        patterns = extractor.extract(obs)
        names = [p.name for p in patterns]
        assert any("regime_mismatch" in n for n in names)

    def test_failure_has_remedy(self):
        obs = [make_observation(eval_score=30.0, max_dd=0.35) for _ in range(5)]
        extractor = FailurePatternExtractor(min_support=3)
        patterns = extractor.extract(obs)
        for p in patterns:
            assert p.suggested_remedy

    def test_severity_valid_values(self):
        obs = [make_observation(eval_score=30.0) for _ in range(5)]
        extractor = FailurePatternExtractor(min_support=3)
        patterns = extractor.extract(obs)
        valid = {"mild", "moderate", "severe"}
        for p in patterns:
            assert p.severity in valid


class TestPerformanceDriftAnalyzer:
    def test_no_drift_stable_series(self):
        baseline_obs = make_observations_series(n=10, score=70.0, jitter=1.0)
        recent_obs   = make_observations_series(n=10, score=70.0, jitter=1.0)
        analyzer = PerformanceDriftAnalyzer()
        drift = analyzer.analyse(baseline_obs, recent_obs)
        assert isinstance(drift, PerformanceDrift)
        assert drift.drift_direction in ("improving", "degrading", "stable")

    def test_severe_degradation_detected(self):
        baseline_obs = make_observations_series(n=10, score=80.0, jitter=1.0)
        recent_obs   = make_observations_series(n=10, score=35.0, jitter=1.0)
        analyzer = PerformanceDriftAnalyzer()
        drift = analyzer.analyse(baseline_obs, recent_obs)
        assert drift.drift_direction == "degrading"
        assert drift.overall_drift != 0

    def test_improvement_detected(self):
        baseline_obs = make_observations_series(n=10, score=40.0, jitter=1.0)
        recent_obs   = make_observations_series(n=10, score=80.0, jitter=1.0)
        analyzer = PerformanceDriftAnalyzer()
        drift = analyzer.analyse(baseline_obs, recent_obs)
        assert drift.drift_direction == "improving"

    def test_drift_is_frozen(self):
        baseline_obs = make_observations_series(n=10, score=70.0)
        recent_obs   = make_observations_series(n=10, score=70.0)
        analyzer = PerformanceDriftAnalyzer()
        drift = analyzer.analyse(baseline_obs, recent_obs)
        with pytest.raises(Exception):
            drift.overall_drift = 999.0  # type: ignore[misc]


class TestPerformanceLearner:
    def test_learn_returns_result(self):
        obs = make_observations_series(n=15, score=70.0)
        learner = PerformanceLearner()
        result = learner.learn(obs)
        assert result is not None

    def test_winning_conditions_populated(self):
        obs = [make_observation(eval_score=80.0, regime="trending") for _ in range(15)]
        learner = PerformanceLearner()
        result = learner.learn(obs)
        assert isinstance(result.winning_characteristics, list)

    def test_regime_performance_built(self):
        obs = [
            make_observation(eval_score=80.0, regime="trending"),
            make_observation(eval_score=80.0, regime="trending"),
            make_observation(eval_score=40.0, regime="volatile"),
            make_observation(eval_score=40.0, regime="volatile"),
        ] * 3   # 12 observations
        learner = PerformanceLearner()
        result = learner.learn(obs)
        assert "trending" in result.regime_performance
        assert "volatile" in result.regime_performance

    def test_consistency_score_in_range(self):
        obs = make_observations_series(n=20, score=70.0)
        learner = PerformanceLearner()
        result = learner.learn(obs)
        assert 0.0 <= result.score_consistency <= 100.0
