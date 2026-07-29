"""
benchmark_metadata.py -- iios.ai.learning_evaluation.core
===========================================================
:class:`BenchmarkType`     — benchmark classification.
:class:`BenchmarkStatus`   — benchmark life-cycle states.
:class:`BenchmarkMetadata` — immutable benchmark header.

A7 Learning & Evaluation Platform — Phase 3, Module 7
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from enum import Enum
from typing import FrozenSet, Optional


class BenchmarkType(str, Enum):
    """Classification of what is being benchmarked."""
    AGENT            = "agent"
    MODEL            = "model"
    WORKFLOW         = "workflow"
    HISTORICAL_REPLAY = "historical_replay"


class BenchmarkStatus(str, Enum):
    """Benchmark life-cycle states."""
    CREATED   = "created"
    RUNNING   = "running"
    COMPLETED = "completed"
    FAILED    = "failed"
    CANCELLED = "cancelled"

    def is_terminal(self) -> bool:
        return self in (BenchmarkStatus.COMPLETED, BenchmarkStatus.FAILED, BenchmarkStatus.CANCELLED)

    def is_active(self) -> bool:
        return self in (BenchmarkStatus.CREATED, BenchmarkStatus.RUNNING)


@dataclass(frozen=True)
class BenchmarkMetadata:
    """Immutable header for one benchmark run."""

    benchmark_id:   str
    name:           str
    benchmark_type: BenchmarkType
    target_id:      str
    suite_id:       Optional[str]    # owning BenchmarkSuite id (None = standalone)
    created_by:     str
    created_at:     float
    description:    str
    tags:           FrozenSet[str]

    @classmethod
    def create(
        cls,
        name:           str,
        benchmark_type: BenchmarkType,
        target_id:      str,
        suite_id:       Optional[str]   = None,
        created_by:     str             = "system",
        description:    str             = "",
        tags:           FrozenSet[str]  = frozenset(),
    ) -> "BenchmarkMetadata":
        return cls(
            benchmark_id   = str(uuid.uuid4()),
            name           = name,
            benchmark_type = benchmark_type,
            target_id      = target_id,
            suite_id       = suite_id,
            created_by     = created_by,
            created_at     = time.time(),
            description    = description,
            tags           = frozenset(tags),
        )
