"""
learning_manager.py -- iios.ai.learning_evaluation.learning
=============================================================
:class:`LearningManager` — combines FeedbackCollector + LearningHistory and
generates :class:`ImprovementRecommendation` objects.

A7 Learning & Evaluation Platform — Phase 3, Module 7
"""
from __future__ import annotations

from typing import Any, List, Optional

from ..core.feedback_record             import FeedbackRecord, FeedbackSentiment, FeedbackType
from ..core.improvement_recommendation  import (
    ImprovementRecommendation,
    Priority,
    RecommendationType,
)
from ..core.learning_record             import LearningCategory, LearningRecord
from .feedback_collector                import FeedbackCollector
from .learning_history                  import LearningHistory


class LearningManager:
    """
    High-level façade that unifies :class:`FeedbackCollector` and
    :class:`LearningHistory` and provides recommendation generation.
    """

    def __init__(
        self,
        feedback_collector: Optional[FeedbackCollector] = None,
        learning_history:   Optional[LearningHistory]   = None,
    ) -> None:
        self._feedback = feedback_collector or FeedbackCollector()
        self._history  = learning_history   or LearningHistory()

    # ── properties ────────────────────────────────────────────────────────────

    @property
    def feedback_collector(self) -> FeedbackCollector:
        return self._feedback

    @property
    def learning_history(self) -> LearningHistory:
        return self._history

    # ── learning recording ────────────────────────────────────────────────────

    def record_learning(
        self,
        source_id:   str,
        category:    LearningCategory,
        observation: Any,
        signal:      float          = 0.0,
        session_id:  Optional[str]  = None,
        **metadata:  Any,
    ) -> LearningRecord:
        record = LearningRecord.create(
            source_id   = source_id,
            category    = category,
            observation = observation,
            signal      = signal,
            session_id  = session_id,
            **metadata,
        )
        self._history.add(record)
        return record

    # ── feedback submission ───────────────────────────────────────────────────

    def submit_feedback(
        self,
        target_id:     str,
        submitted_by:  str,
        feedback_type: FeedbackType,
        content:       Any,
        sentiment:     FeedbackSentiment = FeedbackSentiment.NEUTRAL,
        rating:        Optional[float]   = None,
        **metadata:    Any,
    ) -> FeedbackRecord:
        record = FeedbackRecord.create(
            target_id     = target_id,
            submitted_by  = submitted_by,
            feedback_type = feedback_type,
            content       = content,
            sentiment     = sentiment,
            rating        = rating,
            **metadata,
        )
        self._feedback.collect(record)
        return record

    # ── recommendation generation ─────────────────────────────────────────────

    def generate_recommendations(
        self,
        source_id: str,
    ) -> List[ImprovementRecommendation]:
        """
        Generate :class:`ImprovementRecommendation` objects for a given source
        based on its learning history and feedback.

        Heuristics:
        - Avg signal < 0.3  → parameter tune (HIGH)
        - Negative-sentiment feedback rate > 50% → prompt improve (MEDIUM)
        - Average rating < 2.5 → model swap suggestion (HIGH)
        - Anomaly records present → monitoring recommendation (LOW)
        """
        recs: List[ImprovementRecommendation] = []

        avg_signal = self._history.average_signal(source_id)
        if avg_signal is not None and avg_signal < 0.3:
            recs.append(
                ImprovementRecommendation.create(
                    source_id           = source_id,
                    recommendation_type = RecommendationType.PARAMETER_TUNE,
                    priority            = Priority.HIGH,
                    title               = "Low learning signal — tune parameters",
                    rationale           = f"Average learning signal {avg_signal:.3f} < 0.3",
                    expected_gain       = 0.15,
                )
            )

        fb_records  = self._feedback.get_feedback(source_id)
        if fb_records:
            neg_count   = sum(1 for r in fb_records if r.sentiment == FeedbackSentiment.NEGATIVE)
            neg_rate    = neg_count / len(fb_records)
            if neg_rate > 0.5:
                recs.append(
                    ImprovementRecommendation.create(
                        source_id           = source_id,
                        recommendation_type = RecommendationType.PROMPT_IMPROVE,
                        priority            = Priority.MEDIUM,
                        title               = "High negative feedback rate — improve prompts",
                        rationale           = f"Negative sentiment rate {neg_rate:.1%}",
                        expected_gain       = 0.10,
                    )
                )
            avg_rating = self._feedback.average_rating(source_id)
            if avg_rating is not None and avg_rating < 2.5:
                recs.append(
                    ImprovementRecommendation.create(
                        source_id           = source_id,
                        recommendation_type = RecommendationType.MODEL_SWAP,
                        priority            = Priority.HIGH,
                        title               = "Low average rating — consider model swap",
                        rationale           = f"Average rating {avg_rating:.2f} < 2.5",
                        expected_gain       = 0.20,
                    )
                )

        anomalies = self._history.get(source_id, category=LearningCategory.ANOMALY)
        if anomalies:
            recs.append(
                ImprovementRecommendation.create(
                    source_id           = source_id,
                    recommendation_type = RecommendationType.MONITORING,
                    priority            = Priority.LOW,
                    title               = f"Anomalies detected ({len(anomalies)}) — add monitoring",
                    rationale           = "Anomaly records indicate unexpected behaviour",
                    expected_gain       = 0.05,
                )
            )

        return recs
