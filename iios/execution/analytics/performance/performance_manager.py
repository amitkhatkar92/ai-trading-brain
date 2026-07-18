"""
iios/execution/analytics/performance/performance_manager.py
===========================================================
PerformanceManager — orchestrates the full performance analytics cycle.

Workflow per request:
  1. Validate request
  2. Register in registry
  3. Collect data (PerformanceCollector)
  4. Calculate KPIs (PerformanceCalculator)
  5. Aggregate with window (PerformanceAggregator)
  6. Analyse trends if request.include_trends
  7. Compare benchmarks if request.include_benchmarks
  8. Build scorecard if request.include_scorecard
  9. Publish snapshot
 10. Build PerformanceAnalyticsReport
 11. Record stats, history, events
 12. Return PerformanceAnalyticsReport

NO predictive forecasting.  NO alerts.  NO trade execution.

C8 Execution Analytics & Intelligence — Phase 1, Module 3
"""
from __future__ import annotations

import time
import uuid
from typing import Dict, List, Optional

from iios.common.logging.logging_manager import get_logger
from iios.investment.workflow.engine_lifecycle import EngineState, LifecycleAwareMixin

from .constants import (
    MANAGER_SYSTEM_ID,
    WINDOW_SECONDS,
    AggregationWindow,
    KPIType,
    PerformanceDomain,
)
from .exceptions import PerformanceEngineNotRunningError
from .performance_aggregator import PerformanceAggregator
from .performance_benchmark import PerformanceBenchmark
from .performance_calculator import PerformanceCalculator
from .performance_collector import PerformanceCollector
from .performance_context import PerformanceContext
from .performance_events import (
    make_analytics_failed_event,
    make_analytics_published_event,
    make_analytics_started_event,
    make_benchmark_completed_event,
    make_kpi_calculated_event,
    make_report_generated_event,
    make_trend_detected_event,
)
from .performance_history import PerformanceAnalyticsHistory
from .performance_kpi import KPIValue, make_kpi_report
from .performance_registry import PerformanceAnalyticsRegistry
from .performance_request import PerformanceRequest
from .performance_response import (
    BenchmarkReport,
    PerformanceAnalyticsReport,
    PerformanceScorecard,
    PerformanceSnapshot,
    TrendAnalysis,
    make_performance_snapshot,
)
from .performance_scorecard import PerformanceScorecardBuilder
from .performance_statistics import PerformanceAnalyticsStatistics
from .performance_trend_analyzer import PerformanceTrendAnalyzer
from .performance_validation import PerformanceValidator

_log = get_logger(__name__)

_RUNNING = frozenset({EngineState.RUNNING, "running"})


class PerformanceManager(LifecycleAwareMixin):
    """
    Orchestrates the full performance analytics lifecycle.

    Holds references to all sub-components and coordinates them in order.
    Thread-safe.  Must be started before use.
    """

    def __init__(self) -> None:
        super().__init__()
        self._validator   = PerformanceValidator()
        self._registry    = PerformanceAnalyticsRegistry()
        self._collector   = PerformanceCollector()
        self._calculator  = PerformanceCalculator()
        self._aggregator  = PerformanceAggregator()
        self._trend       = PerformanceTrendAnalyzer()
        self._benchmark   = PerformanceBenchmark()
        self._scorecard   = PerformanceScorecardBuilder()
        self._stats       = PerformanceAnalyticsStatistics()
        self._history     = PerformanceAnalyticsHistory()

    def _on_start(self) -> None:
        for component in (
            self._registry, self._collector, self._calculator,
            self._aggregator, self._trend, self._benchmark,
            self._scorecard,
        ):
            component.start()
        _log.info("PerformanceManager started.", system_id=MANAGER_SYSTEM_ID)

    def _on_stop(self) -> None:
        for component in (
            self._registry, self._collector, self._calculator,
            self._aggregator, self._trend, self._benchmark,
            self._scorecard,
        ):
            try:
                component.stop()
            except Exception:
                pass
        _log.info("PerformanceManager stopped.", system_id=MANAGER_SYSTEM_ID)

    def _assert_running(self) -> None:
        if self.lifecycle_state() not in _RUNNING:
            raise PerformanceEngineNotRunningError()

    # ── Public API ────────────────────────────────────────────────────────────

    def process(
        self,
        request: PerformanceRequest,
        context: Optional[PerformanceContext] = None,
    ) -> PerformanceAnalyticsReport:
        """
        Execute the full analytics cycle for the given request.

        If context is None, an empty context is synthesised from the request.
        """
        self._assert_running()
        t0 = time.perf_counter()
        start_event = make_analytics_started_event(request.request_id)
        self._history.add_event(start_event)

        try:
            # 1. Validate
            self._validator.validate_and_raise(request, context)

            # 2. Register
            self._registry.register(request)

            # 3. Build context if not provided
            if context is None:
                from .performance_context import make_performance_context
                context = make_performance_context(
                    request_id = request.request_id,
                    domain     = request.domain,
                    window     = request.window,
                )

            # 4. Collect
            t_calc = time.perf_counter()
            collected = self._collector.collect(context)

            # 5. Calculate KPIs
            kpi_types = list(request.kpi_types) if request.kpi_types else None
            raw_kpis  = self._calculator.calculate(
                collected, request.domain, request.window, kpi_types
            )
            calc_ms = (time.perf_counter() - t_calc) * 1_000.0

            kpi_event = make_kpi_calculated_event(
                request.request_id, len(raw_kpis), request.domain.value
            )
            self._history.add_event(kpi_event)

            # 6. Aggregate
            agg_kpis = self._aggregator.aggregate(
                raw_kpis, request.window, request.domain
            )

            # Build KPIReport
            kpi_report = make_kpi_report(
                list(agg_kpis.values()), request.domain, request.window,
                report_id = str(uuid.uuid4()),
            )
            self._history.add_kpi_report(kpi_report)

            # 7. Trends
            trends: List[TrendAnalysis] = []
            if request.include_trends and context.has_historical_data:
                window_s = WINDOW_SECONDS.get(request.window, 0.0)
                trends   = self._trend.analyze_all(
                    context.historical_kpi_data, request.domain, window_s
                )
                for t in trends:
                    self._history.add_trend(t)
                trend_event = make_trend_detected_event(request.request_id, len(trends))
                self._history.add_event(trend_event)

            # 8. Benchmark
            benchmark_report: Optional[BenchmarkReport] = None
            if request.include_benchmarks and kpi_report.kpi_count > 0:
                benchmark_report = self._benchmark.compare(kpi_report)
                self._history.add_benchmark(benchmark_report)
                bm_event = make_benchmark_completed_event(
                    request.request_id,
                    benchmark_report.overall_score,
                    request.domain.value,
                )
                self._history.add_event(bm_event)

            # 9. Scorecard
            scorecard: Optional[PerformanceScorecard] = None
            if request.include_scorecard:
                if benchmark_report is not None:
                    scorecard = self._scorecard.build_from_benchmark(benchmark_report)
                elif kpi_report.kpi_count > 0:
                    scorecard = self._scorecard.build(kpi_report)
                if scorecard is not None:
                    self._history.add_scorecard(scorecard)

            # 10. Snapshot
            snapshot = make_performance_snapshot(
                request.domain,
                request.window,
                list(agg_kpis.values()),
            )

            # 11. Build report
            processing_ms = (time.perf_counter() - t0) * 1_000.0
            report = PerformanceAnalyticsReport(
                report_id        = str(uuid.uuid4()),
                request_id       = request.request_id,
                domain           = request.domain,
                window           = request.window,
                kpi_report       = kpi_report,
                snapshot         = snapshot,
                trends           = tuple(trends),
                benchmark_report = benchmark_report,
                scorecard        = scorecard,
                processing_ms    = processing_ms,
            )

            # 12. Stats, history, events
            self._stats.record_cycle(
                kpi_count      = kpi_report.kpi_count,
                processing_ms  = processing_ms,
                calculation_ms = calc_ms,
                had_trends     = len(trends) > 0,
                had_benchmarks = benchmark_report is not None,
                had_scorecard  = scorecard is not None,
            )
            self._history.add_report(report)

            rpt_event = make_report_generated_event(
                request.request_id, report.report_id, processing_ms
            )
            pub_event = make_analytics_published_event(
                request.request_id, report.report_id
            )
            self._history.add_event(rpt_event)
            self._history.add_event(pub_event)

            self._registry.complete(request.request_id)
            return report

        except Exception as exc:
            self._stats.record_failure()
            fail_event = make_analytics_failed_event(request.request_id, str(exc))
            self._history.add_event(fail_event)
            self._registry.complete(request.request_id)
            processing_ms = (time.perf_counter() - t0) * 1_000.0
            _log.error(
                "Performance analytics cycle failed.",
                request_id = request.request_id,
                error      = str(exc),
            )
            # Return an error report (never raise to caller)
            empty_kpi_report = make_kpi_report(
                [], request.domain, request.window,
                report_id = str(uuid.uuid4()),
            )
            empty_snapshot = make_performance_snapshot(
                request.domain, request.window, []
            )
            return PerformanceAnalyticsReport(
                report_id     = str(uuid.uuid4()),
                request_id    = request.request_id,
                domain        = request.domain,
                window        = request.window,
                kpi_report    = empty_kpi_report,
                snapshot      = empty_snapshot,
                error_message = str(exc),
                processing_ms = processing_ms,
            )

    @property
    def statistics(self) -> PerformanceAnalyticsStatistics:
        return self._stats

    @property
    def history(self) -> PerformanceAnalyticsHistory:
        return self._history

    @property
    def registry(self) -> PerformanceAnalyticsRegistry:
        return self._registry
