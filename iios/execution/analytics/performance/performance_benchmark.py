"""
iios/execution/analytics/performance/performance_benchmark.py
=============================================================
PerformanceBenchmark — compares KPI values against institutional
threshold definitions from KPI_BENCHMARKS.

Returns BenchmarkReport with per-KPI status and normalised scores.

C8 Execution Analytics & Intelligence — Phase 1, Module 3
"""
from __future__ import annotations

import uuid
from typing import Dict, List, Optional

from iios.common.logging.logging_manager import get_logger
from iios.investment.workflow.engine_lifecycle import EngineState, LifecycleAwareMixin

from .constants import CALC_SYSTEM_ID, AggregationWindow, BenchmarkStatus, KPI_BENCHMARKS, KPIType, PerformanceDomain
from .exceptions import PerformanceBenchmarkError, PerformanceEngineNotRunningError
from .performance_kpi import KPIReport, KPIValue
from .performance_response import BenchmarkComparison, BenchmarkReport

_log = get_logger(__name__)

_RUNNING = frozenset({EngineState.RUNNING, "running"})


class PerformanceBenchmark(LifecycleAwareMixin):
    """
    Compares KPI values against institutional benchmarks.

    Thread-safe.  Must be started before use.
    """

    def _on_start(self) -> None:
        _log.info("PerformanceBenchmark started.", system_id=CALC_SYSTEM_ID)

    def _on_stop(self) -> None:
        _log.info("PerformanceBenchmark stopped.", system_id=CALC_SYSTEM_ID)

    def _assert_running(self) -> None:
        if self.lifecycle_state() not in _RUNNING:
            raise PerformanceEngineNotRunningError()

    def compare(
        self,
        kpi_report: KPIReport,
    ) -> BenchmarkReport:
        """
        Compare all KPIs in the report against benchmark thresholds.

        Returns a BenchmarkReport.
        """
        self._assert_running()
        comparisons: List[BenchmarkComparison] = []
        for kv in kpi_report.kpi_values:
            comparison = self._compare_single(kv)
            comparisons.append(comparison)

        overall_score = (
            sum(c.score for c in comparisons) / len(comparisons)
            if comparisons else 0.0
        )

        return BenchmarkReport(
            report_id     = str(uuid.uuid4()),
            domain        = kpi_report.domain,
            window        = kpi_report.window,
            comparisons   = tuple(comparisons),
            overall_score = overall_score,
        )

    def compare_kpi(
        self,
        kv: KPIValue,
    ) -> BenchmarkComparison:
        """Compare a single KPIValue against its benchmark."""
        self._assert_running()
        return self._compare_single(kv)

    # ── Internal ──────────────────────────────────────────────────────────────

    def _compare_single(self, kv: KPIValue) -> BenchmarkComparison:
        threshold = KPI_BENCHMARKS.get(kv.kpi_type)
        if threshold is None:
            return BenchmarkComparison(
                kpi_type           = kv.kpi_type,
                actual_value       = kv.value,
                warning_threshold  = 0.0,
                critical_threshold = 0.0,
                status             = BenchmarkStatus.NO_DATA,
                score              = 0.5,
            )

        w = threshold.warning
        c = threshold.critical
        v = kv.value
        hib = threshold.higher_is_better

        if hib:
            # Higher values are better.  target = warning, critical = floor.
            if v >= w:
                status = BenchmarkStatus.ABOVE_TARGET
                # score: 1.0 at w, rises beyond
                if w > 0:
                    score = min(1.0, v / w)
                else:
                    score = 1.0
            elif v >= c:
                status = BenchmarkStatus.MEETS_TARGET
                # score: linear from 0 (at critical) to 1 (at warning)
                if w > c:
                    score = (v - c) / (w - c)
                else:
                    score = 0.5
            else:
                status = BenchmarkStatus.BELOW_TARGET
                # score: 0.0 at 0, 0.5 at critical
                if c > 0:
                    score = min(0.5, (v / c) * 0.5)
                else:
                    score = 0.0
        else:
            # Lower values are better.  target = warning, critical = ceiling.
            if v <= w:
                status = BenchmarkStatus.ABOVE_TARGET
                if w > 0:
                    score = min(1.0, w / v) if v > 0 else 1.0
                else:
                    score = 1.0
            elif v <= c:
                status = BenchmarkStatus.MEETS_TARGET
                if c > w:
                    score = 1.0 - (v - w) / (c - w)
                else:
                    score = 0.5
            else:
                status = BenchmarkStatus.BELOW_TARGET
                if c > 0:
                    score = max(0.0, 0.5 - ((v - c) / c) * 0.5)
                else:
                    score = 0.0

        score = min(1.0, max(0.0, score))
        return BenchmarkComparison(
            kpi_type           = kv.kpi_type,
            actual_value       = v,
            warning_threshold  = w,
            critical_threshold = c,
            status             = status,
            score              = score,
        )
