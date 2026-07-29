"""
benchmark_result.py -- iios.ai.learning_evaluation.core
=========================================================
:class:`BenchmarkOutcome` — high-level benchmark result.
:class:`ScenarioResult`   — per-scenario outcome.
:class:`BenchmarkResult`  — aggregate benchmark result.

A7 Learning & Evaluation Platform — Phase 3, Module 7
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from enum import Enum
from typing import FrozenSet, List, Optional, Tuple


class BenchmarkOutcome(str, Enum):
    """Aggregate benchmark result."""
    PASSED = "passed"
    FAILED = "failed"
    PARTIAL = "partial"
    ERROR   = "error"

    def is_success(self) -> bool:
        return self in (BenchmarkOutcome.PASSED, BenchmarkOutcome.PARTIAL)


@dataclass(frozen=True)
class ScenarioResult:
    """Immutable result for one scenario within a benchmark run."""

    scenario_id:  str
    scenario_name: str
    passed:       bool
    score:        float          # 0.0–1.0
    latency_ms:   float
    notes:        str

    @classmethod
    def create(
        cls,
        scenario_id:   str,
        scenario_name: str,
        score:         float,
        latency_ms:    float = 0.0,
        pass_threshold: float = 0.6,
        notes:         str   = "",
    ) -> "ScenarioResult":
        return cls(
            scenario_id   = scenario_id,
            scenario_name = scenario_name,
            passed        = score >= pass_threshold,
            score         = max(0.0, min(1.0, score)),
            latency_ms    = latency_ms,
            notes         = notes,
        )


@dataclass(frozen=True)
class BenchmarkResult:
    """
    Immutable aggregate result of one :class:`BenchmarkSuite` run.

    ``scenario_results`` — frozenset of :class:`ScenarioResult` objects.
    ``metric_scores``    — frozenset of ``(metric_name, score)`` tuples.
    ``weighted_score``   — 0.0–1.0 weighted aggregate.
    """

    result_id:        str
    benchmark_id:     str
    outcome:          BenchmarkOutcome
    scenario_results: FrozenSet[ScenarioResult]
    metric_scores:    FrozenSet[Tuple[str, float]]
    weighted_score:   float
    total_scenarios:  int
    passed_scenarios: int
    total_latency_ms: float
    completed_at:     float
    notes:            str

    @classmethod
    def build(
        cls,
        benchmark_id:     str,
        scenario_results: FrozenSet[ScenarioResult],
        metric_scores:    FrozenSet[Tuple[str, float]] = frozenset(),
        notes:            str = "",
        pass_threshold:   float = 0.6,
    ) -> "BenchmarkResult":
        sr_list       = list(scenario_results)
        total         = len(sr_list)
        passed        = sum(1 for s in sr_list if s.passed)
        total_lat     = sum(s.latency_ms for s in sr_list)
        weighted      = (sum(s.score for s in sr_list) / total) if total else 0.0
        if total == 0:
            outcome = BenchmarkOutcome.ERROR
        elif weighted >= pass_threshold and passed == total:
            outcome = BenchmarkOutcome.PASSED
        elif passed > 0:
            outcome = BenchmarkOutcome.PARTIAL
        else:
            outcome = BenchmarkOutcome.FAILED

        return cls(
            result_id        = str(uuid.uuid4()),
            benchmark_id     = benchmark_id,
            outcome          = outcome,
            scenario_results = frozenset(scenario_results),
            metric_scores    = frozenset(metric_scores),
            weighted_score   = round(weighted, 6),
            total_scenarios  = total,
            passed_scenarios = passed,
            total_latency_ms = total_lat,
            completed_at     = time.time(),
            notes            = notes,
        )

    def pass_rate(self) -> float:
        return (self.passed_scenarios / self.total_scenarios) if self.total_scenarios else 0.0

    def is_success(self) -> bool:
        return self.outcome.is_success()
