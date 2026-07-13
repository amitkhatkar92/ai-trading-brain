"""tests/unit/investment/strategy/learning/test_knowledge_engine.py
Tests for LessonRegistry, BestPractices, FailureLibrary, KnowledgeEngine.
"""
import pytest

from tests.unit.investment.strategy.learning.conftest import (
    make_observation, make_observations_series
)
from iios.investment.strategy.learning.lesson_registry import Lesson, LessonCategory, LessonRegistry
from iios.investment.strategy.learning.best_practices import BestPractice, BestPracticeExtractor
from iios.investment.strategy.learning.failure_library import FailureEntry, FailureLibrary
from iios.investment.strategy.learning.success_pattern import SuccessPatternExtractor
from iios.investment.strategy.learning.failure_pattern import FailurePatternExtractor
from iios.investment.strategy.learning.knowledge_engine import KnowledgeEngine


def _make_lesson(strategy_id="s1", category=LessonCategory.SUCCESS):
    import uuid
    from datetime import datetime, timezone
    return Lesson(
        lesson_id=str(uuid.uuid4()),
        strategy_id=strategy_id,
        category=category,
        title="Test lesson",
        description="Test description",
        evidence=["obs1", "obs2"],
        confidence=0.75,
        support_count=5,
    )


class TestLessonRegistry:
    def test_add_and_retrieve(self):
        registry = LessonRegistry()
        lesson = _make_lesson()
        registry.add(lesson)
        lessons = registry.get("s1")
        assert len(lessons) == 1
        assert lessons[0].lesson_id == lesson.lesson_id

    def test_category_filter(self):
        registry = LessonRegistry()
        registry.add(_make_lesson(category=LessonCategory.SUCCESS))
        registry.add(_make_lesson(category=LessonCategory.FAILURE))
        success = registry.get("s1", LessonCategory.SUCCESS)
        assert len(success) == 1
        assert success[0].category == LessonCategory.SUCCESS

    def test_count(self):
        registry = LessonRegistry()
        for _ in range(3):
            registry.add(_make_lesson())
        assert registry.count("s1") == 3

    def test_deactivate(self):
        registry = LessonRegistry()
        lesson = _make_lesson()
        registry.add(lesson)
        assert registry.deactivate(lesson.lesson_id)
        active = registry.active("s1")
        assert len(active) == 0

    def test_deactivate_missing_returns_false(self):
        registry = LessonRegistry()
        assert not registry.deactivate("non-existent-id")

    def test_unknown_strategy_returns_empty(self):
        registry = LessonRegistry()
        assert registry.get("unknown") == []

    def test_add_all(self):
        registry = LessonRegistry()
        lessons = [_make_lesson() for _ in range(5)]
        registry.add_all(lessons)
        assert registry.count("s1") == 5

    def test_lesson_is_frozen(self):
        lesson = _make_lesson()
        with pytest.raises(Exception):
            lesson.title = "hack"  # type: ignore[misc]


class TestBestPracticeExtractor:
    def test_extract_from_success_patterns(self):
        obs = [
            make_observation(eval_score=80.0, regime="trending")
            for _ in range(8)
        ]
        success_extractor = SuccessPatternExtractor(success_threshold=70.0, min_support=3)
        patterns = success_extractor.extract(obs)
        extractor = BestPracticeExtractor()
        practices = extractor.extract("s1", patterns, obs)
        assert isinstance(practices, list)

    def test_practice_is_frozen(self):
        obs = [make_observation(eval_score=80.0) for _ in range(8)]
        success_extractor = SuccessPatternExtractor(success_threshold=70.0, min_support=3)
        patterns = success_extractor.extract(obs)
        extractor = BestPracticeExtractor()
        practices = extractor.extract("s1", patterns, obs)
        if practices:
            with pytest.raises(Exception):
                practices[0].title = "hack"  # type: ignore[misc]

    def test_practice_to_lesson(self):
        obs = [make_observation(eval_score=80.0) for _ in range(8)]
        success_extractor = SuccessPatternExtractor(success_threshold=70.0, min_support=3)
        patterns = success_extractor.extract(obs)
        extractor = BestPracticeExtractor()
        practices = extractor.extract("s1", patterns, obs)
        for p in practices:
            lesson = p.to_lesson()
            assert lesson.category == LessonCategory.SUCCESS


class TestFailureLibrary:
    def test_catalog_failure_patterns(self):
        obs = [make_observation(
            eval_score=30.0,
            regime="bear_market",   # triggers mismatch
            max_dd=0.40,
        ) for _ in range(6)]
        failure_extractor = FailurePatternExtractor(failure_threshold=45.0, min_support=3)
        patterns = failure_extractor.extract(obs)
        library = FailureLibrary()
        entries = library.catalog(patterns)
        assert isinstance(entries, list)

    def test_resolve_entry(self):
        obs = [make_observation(eval_score=30.0, regime="bear_market") for _ in range(6)]
        failure_extractor = FailurePatternExtractor(failure_threshold=45.0, min_support=3)
        patterns = failure_extractor.extract(obs)
        library = FailureLibrary()
        entries = library.catalog(patterns)
        if entries:
            entry_id = entries[0].entry_id
            assert library.resolve(entry_id)
            still_active = library.get("s1")
            assert all(e.entry_id != entry_id for e in still_active)

    def test_failure_entry_is_frozen(self):
        obs = [make_observation(eval_score=30.0, regime="bear_market") for _ in range(6)]
        failure_extractor = FailurePatternExtractor(min_support=3)
        patterns = failure_extractor.extract(obs)
        library = FailureLibrary()
        entries = library.catalog(patterns)
        if entries:
            with pytest.raises(Exception):
                entries[0].description = "hack"  # type: ignore[misc]


class TestKnowledgeEngine:
    def test_extract_empty_obs(self):
        engine = KnowledgeEngine()
        report = engine.extract([])
        assert report.knowledge_score == 0.0
        assert not report.has_actionable

    def test_extract_returns_report(self, obs_series_20):
        engine = KnowledgeEngine()
        report = engine.extract(obs_series_20)
        assert report is not None
        assert report.strategy_id == "s1"

    def test_knowledge_score_in_range(self, obs_series_20):
        engine = KnowledgeEngine()
        report = engine.extract(obs_series_20)
        assert 0.0 <= report.knowledge_score <= 100.0

    def test_get_lessons_after_extract(self, obs_series_20):
        engine = KnowledgeEngine()
        engine.extract(obs_series_20)
        lessons = engine.get_lessons("s1")
        assert isinstance(lessons, list)

    def test_extract_with_degradation_adds_lesson(self, degraded_obs_series):
        from iios.investment.strategy.learning.degradation_detector import DegradationDetector
        detector = DegradationDetector()
        deg = detector.detect(degraded_obs_series)
        engine = KnowledgeEngine()
        report = engine.extract(degraded_obs_series, degradation_report=deg)
        if deg and deg.is_actionable:
            lessons = engine.get_lessons("s_deg")
            assert len(lessons) > 0
