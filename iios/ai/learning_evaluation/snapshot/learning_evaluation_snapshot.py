"""
learning_evaluation_snapshot.py -- iios.ai.learning_evaluation.snapshot
=========================================================================
Point-in-time frozen snapshots for the A7 Learning & Evaluation Platform.

A7 Learning & Evaluation Platform — Phase 3, Module 7
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from typing import Any, Dict, Tuple


@dataclass(frozen=True)
class EvaluationSessionSnapshot:
    """Immutable snapshot of one EvaluationSession at a point in time."""

    snapshot_id:   str
    session_id:    str
    status:        str
    result_count:  int
    pass_rate:     float
    captured_at:   float

    @classmethod
    def capture(
        cls,
        session_id:   str,
        status:       str,
        result_count: int,
        pass_rate:    float,
    ) -> "EvaluationSessionSnapshot":
        return cls(
            snapshot_id  = str(uuid.uuid4()),
            session_id   = session_id,
            status       = status,
            result_count = result_count,
            pass_rate    = round(pass_rate, 4),
            captured_at  = time.time(),
        )


@dataclass(frozen=True)
class LearningEvaluationFrameworkSnapshot:
    """
    Immutable point-in-time snapshot of the entire A7 platform state.

    ``session_snapshots`` — tuple of :class:`EvaluationSessionSnapshot` objects.
    ``counters``          — frozen key→int stats dict (stored as frozenset of tuples).
    """

    snapshot_id:       str
    is_running:        bool
    active_sessions:   int
    total_sessions:    int
    total_benchmarks:  int
    total_feedback:    int
    total_learning:    int
    session_snapshots: Tuple[EvaluationSessionSnapshot, ...]
    counters:          frozenset              # FrozenSet[Tuple[str, int]]
    captured_at:       float

    @classmethod
    def build(
        cls,
        is_running:        bool,
        active_sessions:   int,
        total_sessions:    int,
        total_benchmarks:  int,
        total_feedback:    int,
        total_learning:    int,
        session_snapshots: Tuple[EvaluationSessionSnapshot, ...] = (),
        counters:          Dict[str, Any] = None,
    ) -> "LearningEvaluationFrameworkSnapshot":
        return cls(
            snapshot_id       = str(uuid.uuid4()),
            is_running        = is_running,
            active_sessions   = active_sessions,
            total_sessions    = total_sessions,
            total_benchmarks  = total_benchmarks,
            total_feedback    = total_feedback,
            total_learning    = total_learning,
            session_snapshots = session_snapshots,
            counters          = frozenset((counters or {}).items()),
            captured_at       = time.time(),
        )
