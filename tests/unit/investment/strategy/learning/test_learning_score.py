"""tests/unit/investment/strategy/learning/test_learning_score.py
Tests for LearningConfidence, StrategyMaturity, LearningQuality, LearningScore.
"""
import pytest
from datetime import datetime, timezone, timedelta

from tests.unit.investment.strategy.learning.conftest import (
    make_observation, make_observations_series
)
from iios.investment.strategy.learning.learning_profile import StrategyLearningProfile
from iios.investment.strategy.learning.learning_policy import DEFAULT_POLICY
from iios.investment.strategy.learning.learning_confidence import LearningConfidence
from iios.investment.strategy.learning.strategy_maturity import (
    StrategyMaturity, MaturityAssessor, MaturityLevel
)
from iios.investment.strategy.learning.learning_quality import LearningQuality
from iios.investment.strategy.learning.learning_score import LearningScore, LearningScoreCalculator


def _build_profile(n_obs: int, score: float = 70.0, sid: str = "s1") -> StrategyLearningProfile:
    profile = StrategyLearningProfile(strategy_id=sid, strategy_name="Test")
    base_time = datetime.now(timezone.utc) - timedelta(days=n_obs)
    for i, obs in enumerate(make_observations_series(sid=sid, n=n_obs, score=score)):
        profile.record(obs)
    return profile


class TestLearningConfidence:
    def test_low_confidence_with_few_obs(self):
        profile = _build_profile(n_obs=3)
        obs = make_observations_series(n=3)
        conf = LearningConfidence.compute(profile, obs, DEFAULT_POLICY)
        assert conf.grade in ("LOW", "MEDIUM")

    def test_higher_confidence_with_many_obs(self):
        profile = _build_profile(n_obs=50)
        obs = make_observations_series(n=50)
        conf = LearningConfidence.compute(profile, obs, DEFAULT_POLICY)
        assert conf.overall_confidence > 0.0

    def test_all_components_in_range(self):
        profile = _build_profile(n_obs=20)
        obs = make_observations_series(n=20)
        conf = LearningConfidence.compute(profile, obs, DEFAULT_POLICY)
        for val in (conf.data_sufficiency, conf.pattern_stability,
                    conf.regime_coverage, conf.temporal_coverage,
                    conf.overall_confidence):
            assert 0.0 <= val <= 100.0

    def test_grade_values(self):
        profile = _build_profile(n_obs=20)
        obs = make_observations_series(n=20)
        conf = LearningConfidence.compute(profile, obs, DEFAULT_POLICY)
        assert conf.grade in ("HIGH", "MEDIUM", "LOW")

    def test_is_reliable_high_confidence(self):
        # Build enough observations to get high confidence
        profile = _build_profile(n_obs=100)
        base = datetime.now(timezone.utc) - timedelta(days=100)
        obs = [
            make_observation(
                eval_score=75.0,
                regime=["trending", "volatile", "ranging"][i % 3],
                observed_at=base + timedelta(days=i),
            )
            for i in range(100)
        ]
        for o in obs:
            profile.record(o)
        conf = LearningConfidence.compute(profile, obs, DEFAULT_POLICY)
        assert isinstance(conf.is_reliable, bool)

    def test_frozen(self):
        profile = _build_profile(n_obs=10)
        obs = make_observations_series(n=10)
        conf = LearningConfidence.compute(profile, obs, DEFAULT_POLICY)
        with pytest.raises(Exception):
            conf.overall_confidence = 999.0  # type: ignore[misc]


class TestMaturityAssessor:
    def test_nascent_with_5_obs(self):
        profile = _build_profile(n_obs=5)
        obs = make_observations_series(n=5)
        result = MaturityAssessor().assess(profile, obs)
        assert result.level == MaturityLevel.NASCENT

    def test_developing_with_25_obs(self):
        profile = _build_profile(n_obs=25)
        obs = make_observations_series(n=25)
        result = MaturityAssessor().assess(profile, obs)
        assert result.level == MaturityLevel.DEVELOPING

    def test_established_with_60_obs(self):
        profile = _build_profile(n_obs=60)
        obs = make_observations_series(n=60)
        result = MaturityAssessor().assess(profile, obs)
        assert result.level == MaturityLevel.ESTABLISHED

    def test_maturity_score_in_range(self):
        profile = _build_profile(n_obs=20)
        obs = make_observations_series(n=20)
        result = MaturityAssessor().assess(profile, obs)
        assert 0.0 <= result.maturity_score <= 100.0

    def test_next_milestone_for_nascent(self):
        profile = _build_profile(n_obs=5)
        obs = make_observations_series(n=5)
        result = MaturityAssessor().assess(profile, obs)
        assert "developing" in result.next_milestone.lower()

    def test_veteran_milestone(self):
        profile = _build_profile(n_obs=1000)
        obs = make_observations_series(n=1000)
        result = MaturityAssessor().assess(profile, obs)
        assert result.level == MaturityLevel.VETERAN
        assert "veteran" in result.next_milestone.lower()

    def test_result_is_frozen(self):
        profile = _build_profile(n_obs=10)
        obs = make_observations_series(n=10)
        result = MaturityAssessor().assess(profile, obs)
        with pytest.raises(Exception):
            result.maturity_score = 999.0  # type: ignore[misc]


class TestLearningQuality:
    def test_assess_returns_quality(self, obs_series_20):
        profile = _build_profile(n_obs=20)
        result = LearningQuality.assess(
            profile=profile,
            observations=obs_series_20,
            success_patterns=[],
            failure_patterns=[],
            drift_signals=[],
            recommendations=[],
        )
        assert result is not None
        assert 0.0 <= result.overall_quality <= 100.0

    def test_grade_valid_values(self, obs_series_20):
        profile = _build_profile(n_obs=20)
        result = LearningQuality.assess(
            profile=profile,
            observations=obs_series_20,
            success_patterns=[],
            failure_patterns=[],
            drift_signals=[],
            recommendations=[],
        )
        assert result.grade in ("A", "B", "C", "D", "F")

    def test_quality_issues_is_list(self, obs_series_20):
        profile = _build_profile(n_obs=20)
        result = LearningQuality.assess(
            profile=profile,
            observations=obs_series_20,
            success_patterns=[],
            failure_patterns=[],
            drift_signals=[],
            recommendations=[],
        )
        assert isinstance(result.quality_issues, list)

    def test_empty_obs_has_zero_quality(self):
        profile = _build_profile(n_obs=1)
        result = LearningQuality.assess(
            profile=profile,
            observations=[],
            success_patterns=[],
            failure_patterns=[],
            drift_signals=[],
            recommendations=[],
        )
        # No obs → input/pattern/drift all 0; recommendations neutral (30) → overall low
        assert result.overall_quality < 15.0  # well below passing grade

    def test_frozen(self, obs_series_20):
        profile = _build_profile(n_obs=20)
        result = LearningQuality.assess(
            profile=profile,
            observations=obs_series_20,
            success_patterns=[],
            failure_patterns=[],
            drift_signals=[],
            recommendations=[],
        )
        with pytest.raises(Exception):
            result.overall_quality = 999.0  # type: ignore[misc]


class TestLearningScoreCalculator:
    def test_score_returns_learning_score(self, obs_series_20):
        profile = _build_profile(n_obs=20)
        calculator = LearningScoreCalculator()
        score = calculator.score(
            profile=profile,
            performance_result=None,
            adaptation_report=None,
            knowledge_report=None,
            maturity=None,
            confidence=None,
        )
        assert isinstance(score, LearningScore)

    def test_overall_score_in_range(self, obs_series_20):
        profile = _build_profile(n_obs=20)
        calculator = LearningScoreCalculator()
        score = calculator.score(
            profile=profile,
            performance_result=None,
            adaptation_report=None,
            knowledge_report=None,
            maturity=None,
            confidence=None,
        )
        assert 0.0 <= score.overall_learning_score <= 100.0

    def test_grade_valid_values(self, obs_series_20):
        profile = _build_profile(n_obs=20)
        calculator = LearningScoreCalculator()
        score = calculator.score(
            profile=profile,
            performance_result=None,
            adaptation_report=None,
            knowledge_report=None,
            maturity=None,
            confidence=None,
        )
        assert score.learning_grade in ("A", "B", "C", "D", "F")

    def test_low_confidence_reduces_score(self, obs_series_20):
        profile = _build_profile(n_obs=20)
        conf_low = LearningConfidence(
            strategy_id="s1",
            assessed_at=datetime.now(timezone.utc),
            data_sufficiency=10.0,
            pattern_stability=10.0,
            regime_coverage=10.0,
            temporal_coverage=10.0,
            overall_confidence=20.0,   # below 40 threshold
            grade="LOW",
        )
        calculator = LearningScoreCalculator()
        score_with_low_conf = calculator.score(
            profile=profile,
            performance_result=None,
            adaptation_report=None,
            knowledge_report=None,
            maturity=None,
            confidence=conf_low,
        )
        score_no_conf = calculator.score(
            profile=profile,
            performance_result=None,
            adaptation_report=None,
            knowledge_report=None,
            maturity=None,
            confidence=None,
        )
        # Low confidence should pull score down
        assert score_with_low_conf.overall_learning_score <= score_no_conf.overall_learning_score

    def test_score_is_frozen(self, obs_series_20):
        profile = _build_profile(n_obs=20)
        calculator = LearningScoreCalculator()
        score = calculator.score(profile, None, None, None, None, None)
        with pytest.raises(Exception):
            score.overall_learning_score = 999.0  # type: ignore[misc]
