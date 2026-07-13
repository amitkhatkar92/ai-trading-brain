"""iios/investment/strategy/learning/knowledge_engine.py
KnowledgeEngine — extracts and maintains the institutional knowledge base.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from iios.investment.strategy.learning.learning_input import LearningObservation
from iios.investment.strategy.learning.success_pattern import SuccessPattern, SuccessPatternExtractor
from iios.investment.strategy.learning.failure_pattern import FailurePattern, FailurePatternExtractor
from iios.investment.strategy.learning.best_practices import BestPractice, BestPracticeExtractor
from iios.investment.strategy.learning.failure_library import FailureEntry, FailureLibrary
from iios.investment.strategy.learning.lesson_registry import Lesson, LessonRegistry, LessonCategory
from iios.investment.strategy.learning.degradation_detector import DegradationReport
from iios.investment.strategy.learning.drift_detector import DriftSignal
from iios.investment.strategy.learning.learning_statistics import clamp


@dataclass(frozen=True)
class KnowledgeReport:
    """Extracted knowledge snapshot for a strategy at a point in time."""
    strategy_id:      str
    assessed_at:      datetime

    success_patterns: List[SuccessPattern]
    failure_patterns: List[FailurePattern]
    best_practices:   List[BestPractice]
    failure_entries:  List[FailureEntry]
    lessons:          List[Lesson]

    knowledge_score:  float   # 0-100; how much institutional knowledge exists
    has_actionable:   bool    # any failure entries or lessons to act on

    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy_id":         self.strategy_id,
            "assessed_at":         self.assessed_at.isoformat(),
            "success_pattern_count": len(self.success_patterns),
            "failure_pattern_count": len(self.failure_patterns),
            "best_practice_count": len(self.best_practices),
            "lesson_count":        len(self.lessons),
            "knowledge_score":     round(self.knowledge_score, 2),
            "has_actionable":      self.has_actionable,
        }


class KnowledgeEngine:
    """
    Extracts and maintains institutional knowledge from strategy observations.
    All knowledge is accumulated — never auto-applied to strategies.
    """

    def __init__(
        self,
        lesson_registry:   Optional[LessonRegistry] = None,
        failure_library:   Optional[FailureLibrary]  = None,
        success_threshold: float = 70.0,
        failure_threshold: float = 45.0,
        min_support:       int   = 3,
    ) -> None:
        self._registry = lesson_registry or LessonRegistry()
        self._library  = failure_library or FailureLibrary()
        self._success_extractor = SuccessPatternExtractor(
            success_threshold=success_threshold,
            min_support=min_support,
        )
        self._failure_extractor = FailurePatternExtractor(
            failure_threshold=failure_threshold,
            min_support=min_support,
        )
        self._practice_extractor = BestPracticeExtractor()

    def extract(
        self,
        observations:       List[LearningObservation],
        degradation_report: Optional[DegradationReport] = None,
    ) -> KnowledgeReport:
        if not observations:
            sid = "unknown"
            return KnowledgeReport(
                strategy_id=sid,
                assessed_at=datetime.now(timezone.utc),
                success_patterns=[], failure_patterns=[],
                best_practices=[], failure_entries=[], lessons=[],
                knowledge_score=0.0, has_actionable=False,
            )

        sid = observations[0].strategy_id

        # Extract patterns
        success_patterns = self._success_extractor.extract(observations)
        failure_patterns = self._failure_extractor.extract(observations)

        # Extract best practices from success patterns
        best_practices = self._practice_extractor.extract(
            sid, success_patterns, observations
        )

        # Catalog failures
        failure_entries = self._library.catalog(failure_patterns)

        # Build lessons from both sides
        lessons: List[Lesson] = []
        for bp in best_practices:
            lessons.append(bp.to_lesson())
        for fe in failure_entries:
            lessons.append(fe.to_lesson())

        # Add drift-based lessons if degradation present
        if degradation_report and degradation_report.is_actionable:
            drift_lesson = Lesson(
                lesson_id=str(__import__("uuid").uuid4()),
                strategy_id=sid,
                category=LessonCategory.RISK,
                title=f"Active degradation: {degradation_report.level.value}",
                description=(
                    f"Strategy is showing {degradation_report.level.value} degradation "
                    f"(score: {degradation_report.degradation_score:.1f}/100). "
                    f"Significant drifts: {', '.join(degradation_report.significant_drifts) or 'none'}."
                ),
                evidence=degradation_report.significant_drifts,
                confidence=min(degradation_report.degradation_score / 100.0, 1.0),
                support_count=len(degradation_report.drift_signals),
            )
            lessons.append(drift_lesson)

        # Store all lessons
        self._registry.add_all(lessons)

        # Knowledge score
        knowledge_score = self._compute_score(
            success_patterns, failure_patterns, best_practices, lessons
        )

        return KnowledgeReport(
            strategy_id=sid,
            assessed_at=datetime.now(timezone.utc),
            success_patterns=success_patterns,
            failure_patterns=failure_patterns,
            best_practices=best_practices,
            failure_entries=failure_entries,
            lessons=lessons,
            knowledge_score=knowledge_score,
            has_actionable=bool(failure_entries) or (
                bool(degradation_report) and degradation_report.is_actionable  # type: ignore[union-attr]
            ),
        )

    def get_lessons(self, strategy_id: str, category: Optional[LessonCategory] = None) -> List[Lesson]:
        return self._registry.get(strategy_id, category)

    def get_failures(self, strategy_id: str) -> List[FailureEntry]:
        return self._library.get(strategy_id)

    @staticmethod
    def _compute_score(
        success_patterns: List[SuccessPattern],
        failure_patterns: List[FailurePattern],
        best_practices:   List[BestPractice],
        lessons:          List[Lesson],
    ) -> float:
        base = 0.0
        base += min(len(success_patterns) * 15.0, 40.0)
        base += min(len(failure_patterns) * 10.0, 20.0)
        base += min(len(best_practices)   * 12.0, 30.0)
        base += min(len(lessons)          *  2.0, 10.0)
        return clamp(base)
