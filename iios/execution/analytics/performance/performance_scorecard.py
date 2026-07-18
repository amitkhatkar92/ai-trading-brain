"""
iios/execution/analytics/performance/performance_scorecard.py
=============================================================
PerformanceScorecardBuilder — grades KPI values and computes an overall
performance score, returning a PerformanceScorecard.

Grading uses the KPI_BENCHMARKS thresholds and score_to_grade() from
constants.

C8 Execution Analytics & Intelligence — Phase 1, Module 3
"""
from __future__ import annotations

import uuid
from typing import Dict, List, Optional

from iios.common.logging.logging_manager import get_logger
from iios.investment.workflow.engine_lifecycle import EngineState, LifecycleAwareMixin

from .constants import CALC_SYSTEM_ID, AggregationWindow, KPI_BENCHMARKS, KPIType, PerformanceDomain, PerformanceGrade, score_to_grade
from .exceptions import PerformanceEngineNotRunningError
from .performance_kpi import KPIReport, KPIValue
from .performance_response import BenchmarkReport, PerformanceScorecard

_log = get_logger(__name__)

_RUNNING = frozenset({EngineState.RUNNING, "running"})


def _kpi_score(kv: KPIValue) -> float:
    """
    Normalise a KPI value to [0, 1] using its benchmark thresholds.

    When no benchmark is defined, the value itself is clamped to [0, 1].
    """
    threshold = KPI_BENCHMARKS.get(kv.kpi_type)
    if threshold is None:
        return min(1.0, max(0.0, kv.value))
    w = threshold.warning
    c = threshold.critical
    v = kv.value
    hib = threshold.higher_is_better
    if hib:
        if c <= 0:
            return 1.0 if v > 0 else 0.0
        if v >= w:
            return 1.0
        if v >= c:
            return 0.5 + 0.5 * (v - c) / max(w - c, 1e-9)
        return min(0.5, 0.5 * v / c)
    else:
        # Lower is better — invert
        if w <= 0:
            return 1.0 if v <= 0 else 0.0
        if v <= w:
            return 1.0
        if v <= c:
            return 0.5 + 0.5 * (c - v) / max(c - w, 1e-9)
        return max(0.0, 0.5 * (c / v) if v > 0 else 0.0)


class PerformanceScorecardBuilder(LifecycleAwareMixin):
    """
    Builds a PerformanceScorecard from a KPIReport (or BenchmarkReport).

    Thread-safe.  Must be started before use.
    """

    def _on_start(self) -> None:
        _log.info("PerformanceScorecardBuilder started.", system_id=CALC_SYSTEM_ID)

    def _on_stop(self) -> None:
        _log.info("PerformanceScorecardBuilder stopped.", system_id=CALC_SYSTEM_ID)

    def _assert_running(self) -> None:
        if self.lifecycle_state() not in _RUNNING:
            raise PerformanceEngineNotRunningError()

    def build(
        self,
        kpi_report: KPIReport,
    ) -> PerformanceScorecard:
        """
        Grade each KPI and compute an overall domain score.

        Uses benchmark-normalised scores; overall = weighted mean
        (all KPIs weighted equally).
        """
        self._assert_running()
        kpi_scores: Dict[str, float] = {}
        for kv in kpi_report.kpi_values:
            score = _kpi_score(kv)
            kpi_scores[kv.kpi_type.value] = round(score, 6)

        overall = (
            sum(kpi_scores.values()) / len(kpi_scores)
            if kpi_scores else 0.0
        )

        return PerformanceScorecard(
            scorecard_id  = str(uuid.uuid4()),
            domain        = kpi_report.domain,
            window        = kpi_report.window,
            grade         = score_to_grade(overall),
            overall_score = round(overall, 6),
            kpi_scores    = kpi_scores,
        )

    def build_from_benchmark(
        self,
        benchmark_report: BenchmarkReport,
    ) -> PerformanceScorecard:
        """
        Build a scorecard from an existing BenchmarkReport.

        Uses the per-KPI benchmark scores already in the report.
        """
        self._assert_running()
        kpi_scores: Dict[str, float] = {
            c.kpi_type.value: round(c.score, 6) for c in benchmark_report.comparisons
        }
        overall = benchmark_report.overall_score
        return PerformanceScorecard(
            scorecard_id  = str(uuid.uuid4()),
            domain        = benchmark_report.domain,
            window        = benchmark_report.window,
            grade         = score_to_grade(overall),
            overall_score = round(overall, 6),
            kpi_scores    = kpi_scores,
        )
