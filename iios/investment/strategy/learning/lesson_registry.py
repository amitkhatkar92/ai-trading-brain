"""iios/investment/strategy/learning/lesson_registry.py
LessonRegistry — thread-safe store for learned institutional lessons.
"""
from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


class LessonCategory(str, Enum):
    SUCCESS     = "success"
    FAILURE     = "failure"
    REGIME      = "regime"
    EXECUTION   = "execution"
    RISK        = "risk"
    ADAPTATION  = "adaptation"
    GENERAL     = "general"


@dataclass(frozen=True)
class Lesson:
    """A single learned lesson — auditable, versioned, never auto-applied."""
    lesson_id:     str
    strategy_id:   str
    category:      LessonCategory
    title:         str
    description:   str
    evidence:      List[str]          # supporting observations / facts
    confidence:    float              # 0-1
    support_count: int                # number of observations backing this
    is_active:     bool = True
    created_at:    datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at:    datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "lesson_id":     self.lesson_id,
            "strategy_id":   self.strategy_id,
            "category":      self.category.value,
            "title":         self.title,
            "description":   self.description,
            "evidence":      self.evidence,
            "confidence":    round(self.confidence, 3),
            "support_count": self.support_count,
            "is_active":     self.is_active,
            "created_at":    self.created_at.isoformat(),
        }


class LessonRegistry:
    """
    Thread-safe registry of learned lessons.
    Lessons are immutable once created; deactivation is the only state change.
    """

    def __init__(self) -> None:
        self._lessons: Dict[str, List[Lesson]] = {}    # strategy_id → lessons
        self._lock = threading.RLock()

    def add(self, lesson: Lesson) -> None:
        with self._lock:
            self._lessons.setdefault(lesson.strategy_id, []).append(lesson)

    def add_all(self, lessons: List[Lesson]) -> None:
        with self._lock:
            for lesson in lessons:
                self._lessons.setdefault(lesson.strategy_id, []).append(lesson)

    def get(self, strategy_id: str, category: Optional[LessonCategory] = None) -> List[Lesson]:
        with self._lock:
            all_lessons = self._lessons.get(strategy_id, [])
            if category is None:
                return list(all_lessons)
            return [l for l in all_lessons if l.category == category]

    def active(self, strategy_id: str) -> List[Lesson]:
        with self._lock:
            return [l for l in self._lessons.get(strategy_id, []) if l.is_active]

    def count(self, strategy_id: str) -> int:
        with self._lock:
            return len(self._lessons.get(strategy_id, []))

    def all_strategy_ids(self) -> List[str]:
        with self._lock:
            return list(self._lessons.keys())

    def deactivate(self, lesson_id: str) -> bool:
        """Deactivates a lesson (never deletes). Returns True if found."""
        with self._lock:
            for lessons in self._lessons.values():
                for i, lesson in enumerate(lessons):
                    if lesson.lesson_id == lesson_id:
                        # Replace with deactivated copy (frozen dataclass)
                        lessons[i] = Lesson(
                            lesson_id=lesson.lesson_id,
                            strategy_id=lesson.strategy_id,
                            category=lesson.category,
                            title=lesson.title,
                            description=lesson.description,
                            evidence=lesson.evidence,
                            confidence=lesson.confidence,
                            support_count=lesson.support_count,
                            is_active=False,
                            created_at=lesson.created_at,
                            updated_at=datetime.now(timezone.utc),
                        )
                        return True
        return False
