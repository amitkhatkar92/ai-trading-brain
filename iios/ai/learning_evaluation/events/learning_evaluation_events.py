"""
learning_evaluation_events.py -- iios.ai.learning_evaluation.events
=====================================================================
Event types and concrete event dataclasses for the A7 Learning &
Evaluation Platform.

A7 Learning & Evaluation Platform — Phase 3, Module 7
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from enum import Enum
from typing import Any, FrozenSet, Optional, Tuple


class LearningEvaluationEventType(str, Enum):
    """All event types emitted by the A7 platform."""
    EVALUATION_SESSION_CREATED   = "evaluation_session_created"
    EVALUATION_SESSION_STARTED   = "evaluation_session_started"
    EVALUATION_SESSION_COMPLETED = "evaluation_session_completed"
    EVALUATION_SESSION_FAILED    = "evaluation_session_failed"
    EVALUATION_SESSION_CANCELLED = "evaluation_session_cancelled"
    EVALUATION_RESULT_ADDED      = "evaluation_result_added"
    BENCHMARK_STARTED            = "benchmark_started"
    BENCHMARK_COMPLETED          = "benchmark_completed"
    LEARNING_RECORDED            = "learning_recorded"
    FEEDBACK_RECEIVED            = "feedback_received"
    QUALITY_ASSESSED             = "quality_assessed"
    IMPROVEMENT_SUGGESTED        = "improvement_suggested"
    METRICS_CAPTURED             = "metrics_captured"


@dataclass(frozen=True)
class LearningEvaluationEvent:
    """Base immutable event for the A7 platform."""

    event_id:   str
    event_type: LearningEvaluationEventType
    source_id:  str                              # agent / component that emitted
    occurred_at: float
    metadata:   FrozenSet[Tuple[str, Any]]

    @classmethod
    def _base_fields(
        cls,
        event_type: LearningEvaluationEventType,
        source_id:  str,
        **metadata: Any,
    ) -> dict:
        return {
            "event_id":   str(uuid.uuid4()),
            "event_type": event_type,
            "source_id":  source_id,
            "occurred_at": time.time(),
            "metadata":   frozenset(metadata.items()),
        }


# ── Evaluation events ─────────────────────────────────────────────────────────

@dataclass(frozen=True)
class EvaluationSessionCreatedEvent(LearningEvaluationEvent):
    session_id: str

    @classmethod
    def create(cls, source_id: str, session_id: str, **meta: Any) -> "EvaluationSessionCreatedEvent":
        return cls(
            **LearningEvaluationEvent._base_fields(
                LearningEvaluationEventType.EVALUATION_SESSION_CREATED, source_id, **meta
            ),
            session_id = session_id,
        )


@dataclass(frozen=True)
class EvaluationSessionCompletedEvent(LearningEvaluationEvent):
    session_id: str
    result_count: int
    pass_rate: float

    @classmethod
    def create(
        cls, source_id: str, session_id: str, result_count: int, pass_rate: float, **meta: Any
    ) -> "EvaluationSessionCompletedEvent":
        return cls(
            **LearningEvaluationEvent._base_fields(
                LearningEvaluationEventType.EVALUATION_SESSION_COMPLETED, source_id, **meta
            ),
            session_id   = session_id,
            result_count = result_count,
            pass_rate    = pass_rate,
        )


@dataclass(frozen=True)
class EvaluationSessionFailedEvent(LearningEvaluationEvent):
    session_id: str
    reason: str

    @classmethod
    def create(cls, source_id: str, session_id: str, reason: str, **meta: Any) -> "EvaluationSessionFailedEvent":
        return cls(
            **LearningEvaluationEvent._base_fields(
                LearningEvaluationEventType.EVALUATION_SESSION_FAILED, source_id, **meta
            ),
            session_id = session_id,
            reason     = reason,
        )


@dataclass(frozen=True)
class EvaluationResultAddedEvent(LearningEvaluationEvent):
    session_id: str
    result_id: str
    passed: bool

    @classmethod
    def create(
        cls, source_id: str, session_id: str, result_id: str, passed: bool, **meta: Any
    ) -> "EvaluationResultAddedEvent":
        return cls(
            **LearningEvaluationEvent._base_fields(
                LearningEvaluationEventType.EVALUATION_RESULT_ADDED, source_id, **meta
            ),
            session_id = session_id,
            result_id  = result_id,
            passed     = passed,
        )


# ── Benchmark events ──────────────────────────────────────────────────────────

@dataclass(frozen=True)
class BenchmarkStartedEvent(LearningEvaluationEvent):
    benchmark_id: str
    suite_id: Optional[str]

    @classmethod
    def create(
        cls, source_id: str, benchmark_id: str, suite_id: Optional[str] = None, **meta: Any
    ) -> "BenchmarkStartedEvent":
        return cls(
            **LearningEvaluationEvent._base_fields(
                LearningEvaluationEventType.BENCHMARK_STARTED, source_id, **meta
            ),
            benchmark_id = benchmark_id,
            suite_id     = suite_id,
        )


@dataclass(frozen=True)
class BenchmarkCompletedEvent(LearningEvaluationEvent):
    benchmark_id: str
    weighted_score: float
    passed: bool

    @classmethod
    def create(
        cls, source_id: str, benchmark_id: str, weighted_score: float, passed: bool, **meta: Any
    ) -> "BenchmarkCompletedEvent":
        return cls(
            **LearningEvaluationEvent._base_fields(
                LearningEvaluationEventType.BENCHMARK_COMPLETED, source_id, **meta
            ),
            benchmark_id   = benchmark_id,
            weighted_score = weighted_score,
            passed         = passed,
        )


# ── Learning / feedback events ────────────────────────────────────────────────

@dataclass(frozen=True)
class LearningRecordedEvent(LearningEvaluationEvent):
    record_id: str
    category: str

    @classmethod
    def create(cls, source_id: str, record_id: str, category: str, **meta: Any) -> "LearningRecordedEvent":
        return cls(
            **LearningEvaluationEvent._base_fields(
                LearningEvaluationEventType.LEARNING_RECORDED, source_id, **meta
            ),
            record_id = record_id,
            category  = category,
        )


@dataclass(frozen=True)
class FeedbackReceivedEvent(LearningEvaluationEvent):
    feedback_id: str
    target_id: str
    sentiment: str

    @classmethod
    def create(
        cls, source_id: str, feedback_id: str, target_id: str, sentiment: str, **meta: Any
    ) -> "FeedbackReceivedEvent":
        return cls(
            **LearningEvaluationEvent._base_fields(
                LearningEvaluationEventType.FEEDBACK_RECEIVED, source_id, **meta
            ),
            feedback_id = feedback_id,
            target_id   = target_id,
            sentiment   = sentiment,
        )


@dataclass(frozen=True)
class QualityAssessedEvent(LearningEvaluationEvent):
    target_id: str
    grade: str
    aggregate: float

    @classmethod
    def create(
        cls, source_id: str, target_id: str, grade: str, aggregate: float, **meta: Any
    ) -> "QualityAssessedEvent":
        return cls(
            **LearningEvaluationEvent._base_fields(
                LearningEvaluationEventType.QUALITY_ASSESSED, source_id, **meta
            ),
            target_id = target_id,
            grade     = grade,
            aggregate = aggregate,
        )


@dataclass(frozen=True)
class ImprovementSuggestedEvent(LearningEvaluationEvent):
    recommendation_id: str
    target_id: str
    priority: str

    @classmethod
    def create(
        cls, source_id: str, recommendation_id: str, target_id: str, priority: str, **meta: Any
    ) -> "ImprovementSuggestedEvent":
        return cls(
            **LearningEvaluationEvent._base_fields(
                LearningEvaluationEventType.IMPROVEMENT_SUGGESTED, source_id, **meta
            ),
            recommendation_id = recommendation_id,
            target_id         = target_id,
            priority          = priority,
        )
