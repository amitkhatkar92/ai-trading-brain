"""
learning_record.py -- iios.ai.learning_evaluation.core
========================================================
:class:`LearningCategory` — category of a learning event.
:class:`LearningRecord`   — immutable record of one learning observation.

A7 Learning & Evaluation Platform — Phase 3, Module 7
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from enum import Enum
from typing import Any, FrozenSet, Optional, Tuple


class LearningCategory(str, Enum):
    """Classification of a learning observation."""
    ACCURACY    = "accuracy"
    BEHAVIOR    = "behavior"
    PERFORMANCE = "performance"
    FEEDBACK    = "feedback"
    CORRECTION  = "correction"
    ANOMALY     = "anomaly"


@dataclass(frozen=True)
class LearningRecord:
    """
    Immutable record of one learning observation.

    ``source_id``    — agent_id, model_id, or session_id that generated this record.
    ``observation``  — free-form observation data.
    ``signal``       — numeric learning signal (positive = good, negative = bad).
    ``metadata``     — additional key→value context.
    """

    record_id:   str
    source_id:   str
    category:    LearningCategory
    observation: Any
    signal:      float
    recorded_at: float
    metadata:    FrozenSet[Tuple[str, Any]]
    session_id:  Optional[str]

    @classmethod
    def create(
        cls,
        source_id:   str,
        category:    LearningCategory,
        observation: Any,
        signal:      float          = 0.0,
        session_id:  Optional[str]  = None,
        **metadata: Any,
    ) -> "LearningRecord":
        return cls(
            record_id   = str(uuid.uuid4()),
            source_id   = source_id,
            category    = category,
            observation = observation,
            signal      = signal,
            recorded_at = time.time(),
            metadata    = frozenset(metadata.items()),
            session_id  = session_id,
        )

    def get_meta(self, key: str, default: Any = None) -> Any:
        for k, v in self.metadata:
            if k == key:
                return v
        return default
