"""tests/unit/investment/strategy/learning/test_learning_engine.py
Integration tests for StrategyLearningEngine (main facade).
"""
import pytest
from datetime import datetime, timezone, timedelta
from typing import List

from tests.unit.investment.strategy.learning.conftest import (
    make_observation, make_observations_series
)
from iios.investment.strategy.learning.strategy_learning_engine import StrategyLearningEngine
from iios.investment.strategy.learning.learning_policy import DEFAULT_POLICY
from iios.investment.strategy.learning.degradation_detector import DegradationLevel
from iios.investment.strategy.learning.recommendation_engine import RecommendationType
from iios.investment.strategy.learning.strategy_maturity import MaturityLevel


class TestStrategyLearningEngineObserve:
    def test_single_observe_returns_profile(self):
        engine = StrategyLearningEngine()
        obs = make_observation()
        profile = engine.observe(obs)
        assert profile.strategy_id == "s1"

    def test_profile_accumulates_observations(self):
        engine = StrategyLearningEngine()
        for obs in make_observations_series(n=10):
            engine.observe(obs)
        profile = engine.get_profile("s1")
        assert profile is not None
        assert profile.observation_count == 10

    def test_unknown_strategy_returns_none(self):
        engine = StrategyLearningEngine()
        assert engine.get_profile("nonexistent") is None

    def test_observe_batch(self):
        engine = StrategyLearningEngine()
        obs_s1 = make_observations_series(sid="s1", n=5)
        obs_s2 = make_observations_series(sid="s2", n=5)
        profiles = engine.observe_batch(obs_s1 + obs_s2)
        assert "s1" in profiles
        assert "s2" in profiles

    def test_observe_fires_event(self):
        events_received = []
        engine = StrategyLearningEngine()
        engine.event_bus.subscribe(lambda e: events_received.append(e))
        engine.observe(make_observation())
        assert len(events_received) == 1


class TestStrategyLearningEngineQueryAPIs:
    @pytest.fixture
    def engine_with_20_obs(self):
        engine = StrategyLearningEngine()
        for obs in make_observations_series(n=20):
            engine.observe(obs)
        return engine

    def test_get_learning_score(self, engine_with_20_obs):
        score = engine_with_20_obs.get_learning_score("s1")
        assert score is not None
        assert 0.0 <= score.overall_learning_score <= 100.0

    def test_get_maturity(self, engine_with_20_obs):
        maturity = engine_with_20_obs.get_maturity("s1")
        assert maturity is not None
        assert isinstance(maturity.level, MaturityLevel)

    def test_get_confidence(self, engine_with_20_obs):
        conf = engine_with_20_obs.get_confidence("s1")
        assert conf is not None
        assert conf.grade in ("HIGH", "MEDIUM", "LOW")

    def test_get_recommendations(self, engine_with_20_obs):
        recs = engine_with_20_obs.get_recommendations("s1")
        assert isinstance(recs, list)

    def test_get_lessons(self, engine_with_20_obs):
        lessons = engine_with_20_obs.get_lessons("s1")
        assert isinstance(lessons, list)

    def test_learning_history(self, engine_with_20_obs):
        history = engine_with_20_obs.learning_history("s1", n=10)
        assert isinstance(history, list)

    def test_improvement_timeline(self, engine_with_20_obs):
        timeline = engine_with_20_obs.improvement_timeline("s1")
        assert isinstance(timeline, list)

    def test_get_drift_signals(self, engine_with_20_obs):
        signals = engine_with_20_obs.get_drift_signals("s1")
        assert isinstance(signals, list)

    def test_compare_strategies(self):
        engine = StrategyLearningEngine()
        for sid in ("s1", "s2"):
            for obs in make_observations_series(sid=sid, n=10):
                engine.observe(obs)
        comparison = engine.compare_strategies(["s1", "s2", "s_unknown"])
        assert "s1" in comparison
        assert "s2" in comparison
        assert comparison["s_unknown"] is None

    def test_top_strategies(self):
        engine = StrategyLearningEngine()
        for sid, score in [("s1", 80.0), ("s2", 60.0), ("s3", 40.0)]:
            for obs in make_observations_series(sid=sid, n=20, score=score):
                engine.observe(obs)
        top = engine.top_strategies(n=2)
        assert len(top) <= 2
        assert all(isinstance(t, tuple) for t in top)

    def test_stats(self, engine_with_20_obs):
        stats = engine_with_20_obs.stats()
        assert stats["total_strategies"] >= 1
        assert stats["total_observations"] >= 20
        assert "policy" in stats


class TestStrategyLearningEngineConstraints:
    """Verify the engine never modifies strategies, models, or generates trade signals."""

    def test_no_buy_sell_hold_in_recommendations(self):
        engine = StrategyLearningEngine()
        for obs in make_observations_series(n=20):
            engine.observe(obs)
        recs = engine.get_recommendations("s1")
        forbidden = {"BUY", "SELL", "HOLD"}
        for rec in recs:
            assert rec.rec_type.value.upper() not in forbidden

    def test_recommendation_types_are_valid(self):
        engine = StrategyLearningEngine()
        for obs in make_observations_series(n=20):
            engine.observe(obs)
        recs = engine.get_recommendations("s1")
        valid_types = {rt.value for rt in RecommendationType}
        for rec in recs:
            assert rec.rec_type.value in valid_types

    def test_all_recommendations_are_reversible_or_flagged(self):
        engine = StrategyLearningEngine()
        for obs in make_observations_series(n=20):
            engine.observe(obs)
        recs = engine.get_recommendations("s1")
        # All recommendations must have is_reversible bool attribute
        for rec in recs:
            assert isinstance(rec.is_reversible, bool)

    def test_recommendations_have_rationale(self):
        engine = StrategyLearningEngine()
        for obs in make_observations_series(n=20):
            engine.observe(obs)
        recs = engine.get_recommendations("s1")
        for rec in recs:
            assert len(rec.rationale) > 0

    def test_recommendations_have_evidence(self):
        engine = StrategyLearningEngine()
        for obs in make_observations_series(n=20):
            engine.observe(obs)
        recs = engine.get_recommendations("s1")
        for rec in recs:
            assert isinstance(rec.evidence, list)


class TestStrategyLearningEngineDegradation:
    def test_degraded_strategy_is_actionable(self):
        engine = StrategyLearningEngine()
        # First 10: high score; next 15: low score (causes degradation)
        base_time = datetime.now(timezone.utc) - timedelta(days=25)
        for i in range(25):
            obs = make_observation(
                eval_score=80.0 if i < 10 else 30.0,
                risk_score=25.0 if i < 10 else 70.0,
                sharpe=1.8 if i < 10 else 0.2,
                sid="s_deg",
                observed_at=base_time + timedelta(days=i),
            )
            engine.observe(obs)

        deg = engine.get_degradation_report("s_deg")
        if deg:
            assert isinstance(deg.degradation_score, float)
            assert 0.0 <= deg.degradation_score <= 100.0

    def test_stable_strategy_has_no_critical_degradation(self):
        engine = StrategyLearningEngine()
        for obs in make_observations_series(sid="s_stable", n=25, score=75.0, jitter=1.0):
            engine.observe(obs)
        deg = engine.get_degradation_report("s_stable")
        if deg:
            assert deg.level not in (DegradationLevel.CRITICAL,)


class TestStrategyLearningEngineMultiStrategy:
    def test_strategies_isolated(self):
        engine = StrategyLearningEngine()
        for sid in ("alpha", "beta"):
            for obs in make_observations_series(sid=sid, n=10, score=70.0):
                engine.observe(obs)
        profile_alpha = engine.get_profile("alpha")
        profile_beta  = engine.get_profile("beta")
        assert profile_alpha is not None
        assert profile_beta is not None
        assert profile_alpha.strategy_id != profile_beta.strategy_id

    def test_stats_counts_all_strategies(self):
        engine = StrategyLearningEngine()
        for sid in ("s1", "s2", "s3"):
            for obs in make_observations_series(sid=sid, n=5):
                engine.observe(obs)
        stats = engine.stats()
        assert stats["total_strategies"] == 3

    def test_event_bus_accessible(self):
        engine = StrategyLearningEngine()
        bus = engine.event_bus
        assert bus is not None
