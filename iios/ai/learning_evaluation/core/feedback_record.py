"""
feedback_record.py -- iios.ai.learning_evaluation.core
========================================================
:class:`FeedbackType`      — feedback classification.
:class:`FeedbackSentiment` — sentiment polarity.
:class:`FeedbackRecord`    — immutable feedback unit.

A7 Learning & Evaluation Platform — Phase 3, Module 7
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from enum import Enum
from typing import Any, FrozenSet, Optional, Tuple


class FeedbackType(str, Enum):
    """Classification of a feedback submission."""
    RATING      = "rating"
    CORRECTION  = "correction"
    SUGGESTION  = "suggestion"
    REPORT      = "report"
    ENDORSEMENT = "endorsement"


class FeedbackSentiment(str, Enum):
    """Polarity of the feedback."""
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL  = "neutral"


@dataclass(frozen=True)
class FeedbackRecord:
    """
    Immutable feedback record submitted by a human operator or automated system.

    ``target_id``  — agent_id, model_id, or session_id the feedback targets.
    ``content``    — feedback text or structured data.
    ``rating``     — 0.0–5.0 numeric rating (None if not applicable).
    """

    feedback_id:  str
    target_id:    str
    submitted_by: str
    feedback_type: FeedbackType
    sentiment:    FeedbackSentiment
    content:      Any
    rating:       Optional[float]    # 0.0–5.0
    submitted_at: float
    metadata:     FrozenSet[Tuple[str, Any]]

    @classmethod
    def create(
        cls,
        target_id:     str,
        submitted_by:  str,
        feedback_type: FeedbackType,
        content:       Any,
        sentiment:     FeedbackSentiment = FeedbackSentiment.NEUTRAL,
        rating:        Optional[float]   = None,
        **metadata: Any,
    ) -> "FeedbackRecord":
        clamped = None
        if rating is not None:
            clamped = max(0.0, min(5.0, rating))
        return cls(
            feedback_id   = str(uuid.uuid4()),
            target_id     = target_id,
            submitted_by  = submitted_by,
            feedback_type = feedback_type,
            sentiment     = sentiment,
            content       = content,
            rating        = clamped,
            submitted_at  = time.time(),
            metadata      = frozenset(metadata.items()),
        )
