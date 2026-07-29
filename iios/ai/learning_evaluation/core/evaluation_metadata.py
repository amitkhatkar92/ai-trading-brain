"""
evaluation_metadata.py -- iios.ai.learning_evaluation.core
============================================================
:class:`EvaluationType`   — evaluation mode classification.
:class:`EvaluationStatus` — session life-cycle states.
:class:`EvaluationMetadata` — immutable session header.

A7 Learning & Evaluation Platform — Phase 3, Module 7
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from enum import Enum
from typing import FrozenSet, Optional


class EvaluationType(str, Enum):
    """Evaluation execution mode."""
    OFFLINE       = "offline"
    ONLINE        = "online"
    BATCH         = "batch"
    COMPARATIVE   = "comparative"


class EvaluationStatus(str, Enum):
    """Evaluation session life-cycle states."""
    CREATED   = "created"
    RUNNING   = "running"
    COMPLETED = "completed"
    FAILED    = "failed"
    CANCELLED = "cancelled"

    def is_terminal(self) -> bool:
        return self in (EvaluationStatus.COMPLETED, EvaluationStatus.FAILED, EvaluationStatus.CANCELLED)

    def is_active(self) -> bool:
        return self in (EvaluationStatus.CREATED, EvaluationStatus.RUNNING)


@dataclass(frozen=True)
class EvaluationMetadata:
    """
    Immutable session header for one evaluation run.

    Fields
    ------
    session_id       — UUID
    name             — human-readable identifier
    evaluation_type  — :class:`EvaluationType`
    target_id        — agent_id / model_id / workflow_id being evaluated
    created_by       — initiating component or user
    created_at       — wall-clock timestamp
    description      — optional free-text description
    tags             — immutable tag set
    """

    session_id:      str
    name:            str
    evaluation_type: EvaluationType
    target_id:       str
    created_by:      str
    created_at:      float
    description:     str
    tags:            FrozenSet[str]

    @classmethod
    def create(
        cls,
        name:            str,
        evaluation_type: EvaluationType,
        target_id:       str,
        created_by:      str = "system",
        description:     str = "",
        tags:            FrozenSet[str] = frozenset(),
    ) -> "EvaluationMetadata":
        return cls(
            session_id      = str(uuid.uuid4()),
            name            = name,
            evaluation_type = evaluation_type,
            target_id       = target_id,
            created_by      = created_by,
            created_at      = time.time(),
            description     = description,
            tags            = frozenset(tags),
        )
