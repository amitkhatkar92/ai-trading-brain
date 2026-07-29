"""
improvement_recommendation.py -- iios.ai.learning_evaluation.core
===================================================================
:class:`RecommendationType`       — recommendation category.
:class:`Priority`                 — recommendation priority level.
:class:`ImprovementRecommendation` — immutable improvement suggestion.

A7 Learning & Evaluation Platform — Phase 3, Module 7
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from enum import Enum
from typing import Any, FrozenSet, Optional, Tuple


class RecommendationType(str, Enum):
    """Category of improvement recommendation."""
    PARAMETER_TUNE  = "parameter_tune"
    PROMPT_IMPROVE  = "prompt_improve"
    MODEL_SWAP      = "model_swap"
    STRATEGY_ADJUST = "strategy_adjust"
    DATA_QUALITY    = "data_quality"
    ARCHITECTURE    = "architecture"
    MONITORING      = "monitoring"


class Priority(str, Enum):
    """Recommendation urgency level."""
    LOW      = "low"
    MEDIUM   = "medium"
    HIGH     = "high"
    CRITICAL = "critical"

    def score(self) -> int:
        return {"low": 1, "medium": 2, "high": 3, "critical": 4}[self.value]


@dataclass(frozen=True)
class ImprovementRecommendation:
    """
    Immutable improvement recommendation generated from learning data or quality assessments.

    ``source_id``     — agent/model/session that triggered this recommendation.
    ``rationale``     — human-readable explanation.
    ``expected_gain`` — estimated improvement (0.0–1.0).
    ``evidence``      — supporting evidence references.
    """

    recommendation_id: str
    source_id:         str
    recommendation_type: RecommendationType
    priority:          Priority
    title:             str
    rationale:         str
    expected_gain:     float
    evidence:          FrozenSet[str]
    created_at:        float
    metadata:          FrozenSet[Tuple[str, Any]]

    @classmethod
    def create(
        cls,
        source_id:            str,
        recommendation_type:  RecommendationType,
        priority:             Priority,
        title:                str,
        rationale:            str               = "",
        expected_gain:        float             = 0.0,
        evidence:             FrozenSet[str]    = frozenset(),
        **metadata: Any,
    ) -> "ImprovementRecommendation":
        return cls(
            recommendation_id   = str(uuid.uuid4()),
            source_id           = source_id,
            recommendation_type = recommendation_type,
            priority            = priority,
            title               = title,
            rationale           = rationale,
            expected_gain       = max(0.0, min(1.0, expected_gain)),
            evidence            = frozenset(evidence),
            created_at          = time.time(),
            metadata            = frozenset(metadata.items()),
        )
