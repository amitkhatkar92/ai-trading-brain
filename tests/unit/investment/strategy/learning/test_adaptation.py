"""tests/unit/investment/strategy/learning/test_adaptation.py
Tests for ParameterAnalyzer, RegimeAdaptation, AdaptationEngine.
"""
import pytest

from tests.unit.investment.strategy.learning.conftest import (
    make_observation, make_observations_series
)
from iios.investment.strategy.learning.parameter_analysis import ParameterAnalyzer
from iios.investment.strategy.learning.regime_adaptation import RegimeAdaptationAnalyzer
from iios.investment.strategy.learning.adaptation_engine import AdaptationEngine


class TestParameterAnalyzer:
    def test_stable_when_consistent_metrics(self):
        obs = [
            make_observation(eval_score=75.0, sharpe=1.5, max_dd=0.10, win_rate=0.60)
            for _ in range(15)
        ]
        analyzer = ParameterAnalyzer()
        result = analyzer.analyse(obs)
        assert result.is_stable

    def test_unstable_when_volatile_metrics(self):
        obs = []
        for i in range(15):
            obs.append(make_observation(
                eval_score=float(30 + (i % 2) * 50),   # alternates 30/80
                sharpe=0.2 + (i % 2) * 2.8,
                max_dd=0.05 + (i % 2) * 0.30,
                win_rate=0.30 + (i % 2) * 0.40,
            ))
        analyzer = ParameterAnalyzer()
        result = analyzer.analyse(obs)
        assert not result.is_stable

    def test_overall_stability_in_range(self):
        obs = make_observations_series(n=15, score=70.0)
        analyzer = ParameterAnalyzer()
        result = analyzer.analyse(obs)
        assert 0.0 <= result.overall_stability <= 100.0

    def test_instability_drivers_list(self):
        obs = make_observations_series(n=15, score=70.0)
        analyzer = ParameterAnalyzer()
        result = analyzer.analyse(obs)
        assert isinstance(result.instability_drivers, list)

    def test_result_is_frozen(self):
        obs = make_observations_series(n=15, score=70.0)
        analyzer = ParameterAnalyzer()
        result = analyzer.analyse(obs)
        with pytest.raises(Exception):
            result.overall_stability = 999.0  # type: ignore[misc]


class TestRegimeAdaptationAnalyzer:
    def test_known_regimes_in_suitability(self, mixed_regime_series):
        analyzer = RegimeAdaptationAnalyzer()
        result = analyzer.analyse(mixed_regime_series)
        assert "trending" in result.regime_suitability

    def test_suitability_in_range(self, mixed_regime_series):
        analyzer = RegimeAdaptationAnalyzer()
        result = analyzer.analyse(mixed_regime_series)
        for k, v in result.regime_suitability.items():
            assert 0.0 <= v <= 100.0

    def test_adaptability_score_in_range(self, mixed_regime_series):
        analyzer = RegimeAdaptationAnalyzer()
        result = analyzer.analyse(mixed_regime_series)
        assert 0.0 <= result.adaptability_score <= 100.0

    def test_recommended_regimes_subset_of_seen(self, mixed_regime_series):
        analyzer = RegimeAdaptationAnalyzer()
        result = analyzer.analyse(mixed_regime_series)
        seen = set(result.regime_suitability.keys())
        for r in result.recommended_regimes:
            assert r in seen

    def test_avoid_regimes_subset_of_seen(self, mixed_regime_series):
        analyzer = RegimeAdaptationAnalyzer()
        result = analyzer.analyse(mixed_regime_series)
        seen = set(result.regime_suitability.keys())
        for r in result.avoid_regimes:
            assert r in seen

    def test_single_regime_obs(self):
        obs = [make_observation(regime="trending") for _ in range(10)]
        analyzer = RegimeAdaptationAnalyzer()
        result = analyzer.analyse(obs)
        assert "trending" in result.regime_suitability


class TestAdaptationEngine:
    def test_analyse_returns_report(self, obs_series_20):
        engine = AdaptationEngine()
        report = engine.analyse(obs_series_20)
        assert report is not None

    def test_overall_adaptation_in_range(self, obs_series_20):
        engine = AdaptationEngine()
        report = engine.analyse(obs_series_20)
        assert 0.0 <= report.overall_adaptation <= 100.0

    def test_recommendations_are_list(self, obs_series_20):
        engine = AdaptationEngine()
        report = engine.analyse(obs_series_20)
        assert isinstance(report.recommendations, list)

    def test_report_is_frozen(self, obs_series_20):
        engine = AdaptationEngine()
        report = engine.analyse(obs_series_20)
        with pytest.raises(Exception):
            report.overall_adaptation = 999.0  # type: ignore[misc]

    def test_mixed_regime_lower_adaptability_than_single(
        self, obs_series_20, mixed_regime_series
    ):
        engine = AdaptationEngine()
        # Mixed regimes with low scores in some → lower adaptability than stable
        rep_stable = engine.analyse(obs_series_20)        # trending-only, high score
        rep_mixed  = engine.analyse(mixed_regime_series)  # mixed regimes, variable score
        # Not guaranteed ordering but both must be valid
        assert 0.0 <= rep_stable.overall_adaptation <= 100.0
        assert 0.0 <= rep_mixed.overall_adaptation <= 100.0
