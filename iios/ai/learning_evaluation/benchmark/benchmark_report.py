"""
benchmark_report.py -- iios.ai.learning_evaluation.benchmark
=============================================================
:class:`BenchmarkReport` — aggregates multiple BenchmarkResult objects for
comparison reporting.

A7 Learning & Evaluation Platform — Phase 3, Module 7
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from ..core.benchmark_result import BenchmarkResult


@dataclass(frozen=True)
class BenchmarkReport:
    """
    Immutable comparison report across one or more :class:`BenchmarkResult` objects.

    ``results`` — ordered list of results (earliest → latest).
    ``generated_at`` — report creation timestamp.
    """

    report_id:    str
    title:        str
    results:      tuple          # Tuple[BenchmarkResult, ...]
    generated_at: float

    @classmethod
    def build(cls, title: str, results: List[BenchmarkResult]) -> "BenchmarkReport":
        return cls(
            report_id    = str(uuid.uuid4()),
            title        = title,
            results      = tuple(results),
            generated_at = time.time(),
        )

    # ── analysis ──────────────────────────────────────────────────────────────

    def best_result(self) -> Optional[BenchmarkResult]:
        """Return the result with the highest weighted score."""
        if not self.results:
            return None
        return max(self.results, key=lambda r: r.weighted_score)

    def worst_result(self) -> Optional[BenchmarkResult]:
        """Return the result with the lowest weighted score."""
        if not self.results:
            return None
        return min(self.results, key=lambda r: r.weighted_score)

    def average_score(self) -> float:
        if not self.results:
            return 0.0
        return sum(r.weighted_score for r in self.results) / len(self.results)

    def pass_rate(self) -> float:
        """Fraction of results that have a success outcome."""
        if not self.results:
            return 0.0
        return sum(1 for r in self.results if r.is_success()) / len(self.results)

    def summary_table(self) -> List[Dict[str, Any]]:
        """Return a list of dicts suitable for tabular display."""
        rows = []
        for r in self.results:
            rows.append({
                "result_id":       r.result_id,
                "benchmark_id":    r.benchmark_id,
                "outcome":         r.outcome.value,
                "weighted_score":  round(r.weighted_score, 4),
                "pass_rate":       round(r.pass_rate(), 4),
                "total_scenarios": r.total_scenarios,
                "passed":          r.passed_scenarios,
                "latency_ms":      round(r.total_latency_ms, 2),
            })
        return rows

    def result_count(self) -> int:
        return len(self.results)
