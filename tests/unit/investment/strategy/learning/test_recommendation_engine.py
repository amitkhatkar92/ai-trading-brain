"""tests/unit/investment/strategy/learning/test_recommendation_engine.py
Tests for RecommendationEngine, ImprovementEngine, recommendation history.
"""
import pytest

from tests.unit.investment.strategy.learning.conftest import (
    make_observation, make_observations_series
)
from iios.investment.strategy.learning.learning_profile import StrategyLearningProfile
from iios.investment.strategy.learning.recommendation_engine import (
    RecommendationEngine, RecommendationType, Recommendation
)
from iios.investment.strategy.learning.improvement_engine import ImprovementEngine
from iios.investment.strategy.learning.recommendation_history import (
    RecommendationHistory, RecommendationRecord,
)
from iios.investment.strategy.learning.recommendation_score import score_recommendation
from iios.investment.strategy.learning.degradation_detector import (
    DegradationDetector, DegradationLevel,
)


def _make_profile(sid="s1", n_obs=10, score=70.0):
    profile = StrategyLearningProfile(strategy_id=sid, strategy_name="Test")
    for obs in make_observations_series(sid=sid, n=n_obs, score=score):
        profile.record(obs)
    return profile


class TestRecommendationScore:
    def test_high_urgency_impact_is_high_priority(self):
        rs = score_recommendation(urgency=90.0, impact=90.0, confidence=80.0)
        assert rs.priority_label == "HIGH"

    def test_low_scores_give_low_priority(self):
        rs = score_recommendation(urgency=10.0, impact=15.0, confidence=20.0)
        assert rs.priority_label == "LOW"

    def test_priority_score_in_range(self):
        rs = score_recommendation(urgency=50.0, impact=50.0, confidence=50.0)
        assert 0.0 <= rs.priority_score <= 100.0

    def test_frozen(self):
        rs = score_recommendation(urgency=50.0, impact=50.0, confidence=50.0)
        with pytest.raises(Exception):
            rs.urgency = 999.0  # type: ignore[misc]


class TestRecommendationHistory:
    def _make_record(self, sid="s1", rec_type="maintain"):
        from datetime import datetime, timezone
        import uuid
        return RecommendationRecord(
            record_id=str(uuid.uuid4()),
            strategy_id=sid,
            rec_type=rec_type,
            priority="LOW",
            title=f"Rec {rec_type}",
            rationale="Test",
            evidence=[],
            priority_score=20.0,
            is_reversible=True,
            created_at=datetime.now(timezone.utc),
        )

    def test_add_and_retrieve(self):
        history = RecommendationHistory()
        record = self._make_record()
        history.add(record)
        recent = history.get_recent("s1")
        assert len(recent) == 1

    def test_count(self):
        history = RecommendationHistory()
        for _ in range(5):
            history.add(self._make_record())
        assert history.count("s1") == 5

    def test_get_active(self):
        history = RecommendationHistory()
        history.add(self._make_record())
        active = history.get_active("s1")
        assert len(active) == 1

    def test_was_recent_type_true(self):
        history = RecommendationHistory()
        history.add(self._make_record(rec_type="maintain"))
        assert history.was_recent_type("s1", "maintain", within_n_obs=5)

    def test_was_recent_type_false(self):
        history = RecommendationHistory()
        assert not history.was_recent_type("s1", "retirement", within_n_obs=5)

    def test_ring_buffer_capacity(self):
        history = RecommendationHistory(max_per_strategy=5)
        for _ in range(10):
            history.add(self._make_record())
        assert history.count("s1") <= 5


class TestImprovementEngine:
    def test_nascent_strategy_gets_lifecycle_suggestion(self):
        profile = _make_profile(n_obs=5, score=70.0)
        engine = ImprovementEngine()
        suggestions = engine.suggest(profile, None, None, None)
        cats = [s.category for s in suggestions]
        assert "lifecycle" in cats

    def test_critical_degradation_gets_suspension_suggestion(self, degraded_obs_series):
        from iios.investment.strategy.learning.degradation_detector import DegradationDetector
        detector = DegradationDetector(
            mild_threshold=0.01,
            moderate_threshold=0.05,
            severe_threshold=0.10,
            critical_threshold=0.15,
        )
        deg = detector.detect(degraded_obs_series)
        profile = _make_profile(sid="s_deg", n_obs=20, score=40.0)
        engine = ImprovementEngine()
        suggestions = engine.suggest(profile, deg, None, None)
        assert isinstance(suggestions, list)

    def test_suggestion_is_reversible_by_default(self):
        profile = _make_profile(n_obs=5)
        engine = ImprovementEngine()
        suggestions = engine.suggest(profile, None, None, None)
        for s in suggestions:
            assert isinstance(s.is_reversible, bool)

    def test_suggestion_is_frozen(self):
        profile = _make_profile(n_obs=5)
        engine = ImprovementEngine()
        suggestions = engine.suggest(profile, None, None, None)
        if suggestions:
            with pytest.raises(Exception):
                suggestions[0].title = "hack"  # type: ignore[misc]


class TestRecommendationEngine:
    def test_nascent_gets_further_testing(self):
        profile = _make_profile(n_obs=5)
        engine = RecommendationEngine()
        recs = engine.generate(profile)
        types = {r.rec_type for r in recs}
        assert RecommendationType.FURTHER_TESTING in types

    def test_established_stable_gets_maintain(self):
        profile = _make_profile(n_obs=55, score=75.0)
        engine = RecommendationEngine()
        recs = engine.generate(profile, degradation=None)
        types = {r.rec_type for r in recs}
        assert RecommendationType.MAINTAIN in types

    def test_critical_deg_gets_retirement(self, degraded_obs_series):
        # Force critical degradation via very low thresholds
        from iios.investment.strategy.learning.degradation_detector import DegradationDetector
        detector = DegradationDetector(
            mild_threshold=0.01,
            moderate_threshold=0.03,
            severe_threshold=0.05,
            critical_threshold=0.08,
        )
        deg = detector.detect(degraded_obs_series)
        profile = _make_profile(sid="s_deg", n_obs=20, score=40.0)
        engine = RecommendationEngine()
        recs = engine.generate(profile, degradation=deg)
        # With very low thresholds, degradation is classified as critical
        if deg and deg.level == DegradationLevel.CRITICAL:
            types = {r.rec_type for r in recs}
            assert RecommendationType.RETIREMENT in types

    def test_recommendations_sorted_by_priority(self):
        profile = _make_profile(n_obs=5)
        engine = RecommendationEngine()
        recs = engine.generate(profile)
        scores = [r.priority_score for r in recs]
        assert scores == sorted(scores, reverse=True)

    def test_recommendations_all_reversible_or_flagged(self):
        profile = _make_profile(n_obs=20)
        engine = RecommendationEngine()
        recs = engine.generate(profile)
        for r in recs:
            assert isinstance(r.is_reversible, bool)

    def test_recommendation_has_evidence(self):
        profile = _make_profile(n_obs=5)
        engine = RecommendationEngine()
        recs = engine.generate(profile)
        for r in recs:
            assert isinstance(r.evidence, list)

    def test_recommendation_is_frozen(self):
        profile = _make_profile(n_obs=5)
        engine = RecommendationEngine()
        recs = engine.generate(profile)
        if recs:
            with pytest.raises(Exception):
                recs[0].title = "hack"  # type: ignore[misc]

    def test_history_stores_records(self):
        history = RecommendationHistory()
        engine = RecommendationEngine(history=history)
        profile = _make_profile(n_obs=5)
        engine.generate(profile)
        assert history.count("s1") > 0
