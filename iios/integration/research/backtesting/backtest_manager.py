"""backtest_manager.py — High-level coordinator for backtest lifecycle."""
from __future__ import annotations

import logging
import time
from typing import Any, Optional

from iios.integration.research.backtesting.backtest_constants import (
    BacktestEventType,
    BacktestStatus,
)
from iios.integration.research.backtesting.backtest_exceptions import (
    BacktestNotFoundError,
    BacktestStateError,
    BacktestValidationError,
)
from iios.integration.research.backtesting.backtest_registry import BacktestRegistry
from iios.integration.research.backtesting.core.backtest import Backtest
from iios.integration.research.backtesting.core.backtest_configuration import BacktestConfiguration
from iios.integration.research.backtesting.core.backtest_history import BacktestHistory, BacktestHistoryEntry
from iios.integration.research.backtesting.core.backtest_request import BacktestRequest
from iios.integration.research.backtesting.core.backtest_result import BacktestResult
from iios.integration.research.backtesting.core.backtest_statistics import BacktestStatistics
from iios.integration.research.backtesting.engine.market_simulator import BarEvent
from iios.integration.research.backtesting.engine.simulation_engine import BacktestStrategy, SimulationEngine
from iios.integration.research.backtesting.metrics.performance_engine import PerformanceEngine
from iios.integration.research.backtesting.reporting.report_generator import ReportGenerator
from iios.integration.research.backtesting.validation.validation_engine import ValidationEngine, ValidationResult

_log = logging.getLogger(__name__)


class BacktestManager:
    """
    High-level coordinator.

    Typical usage::

        manager = BacktestManager(registry, sim_engine, perf_engine, ...)
        backtest = manager.submit(request)
        result   = await manager.run(backtest.backtest_id, strategy, bars_data)
    """

    def __init__(
        self,
        registry:         BacktestRegistry,
        sim_engine:       SimulationEngine,
        perf_engine:      PerformanceEngine,
        report_generator: ReportGenerator,
        validation_engine: ValidationEngine,
        history:          BacktestHistory,
    ) -> None:
        self._registry  = registry
        self._sim       = sim_engine
        self._perf      = perf_engine
        self._report    = report_generator
        self._val       = validation_engine
        self._history   = history
        self._results:  dict[str, BacktestResult]    = {}
        self._stats_map: dict[str, BacktestStatistics] = {}

    # ── Backtest lifecycle ────────────────────────────────────────────────────

    def submit(self, request: BacktestRequest) -> Backtest:
        """
        Validate a request and register a new Backtest (PENDING state).
        """
        errors = request.validate()
        if errors:
            raise BacktestValidationError("; ".join(errors))

        backtest = Backtest(
            strategy_id   = request.strategy_id,
            strategy_name = request.strategy_name,
            configuration = request.configuration,
            request_id    = request.request_id,
            tags          = list(request.tags),
        )
        self._registry.register(backtest)
        self._record(backtest.backtest_id, BacktestEventType.BACKTEST_CREATED,
                     "Backtest submitted")
        _log.info("[BacktestManager] submitted backtest=%s strategy=%s",
                  backtest.backtest_id, request.strategy_id)
        return backtest

    async def run(
        self,
        backtest_id: str,
        strategy:    BacktestStrategy,
        bars_data:   dict[str, list[BarEvent]],
        *,
        risk_free_rate:    float                    = 0.06,
        benchmark_returns: Optional[list[float]]   = None,
    ) -> BacktestResult:
        """
        Execute the simulation, compute metrics, generate report.

        Returns the populated BacktestResult.
        """
        backtest = self._registry.get(backtest_id)
        self._transition(backtest, BacktestStatus.RUNNING)
        self._record(backtest_id, BacktestEventType.BACKTEST_STARTED, "Simulation started")

        result = await self._sim.run(
            backtest_id = backtest_id,
            config      = backtest.configuration,
            strategy    = strategy,
            bars_data   = bars_data,
        )

        if result.is_success:
            # Compute metrics
            stats = self._perf.compute(result, risk_free_rate, benchmark_returns)
            self._stats_map[backtest_id] = stats

            # Generate report
            self._report.generate(backtest, result, stats,
                                  benchmark_returns=benchmark_returns)

            self._transition(backtest, BacktestStatus.COMPLETED)
            backtest.result_id   = result.result_id
            backtest.completed_at = time.time()
            self._registry.update(backtest)
            self._record(backtest_id, BacktestEventType.BACKTEST_COMPLETED,
                         f"Completed  trades={result.trade_count}")
        else:
            self._transition(backtest, BacktestStatus.FAILED)
            backtest.error_message = result.error
            self._registry.update(backtest)
            self._record(backtest_id, BacktestEventType.BACKTEST_FAILED,
                         result.error or "Unknown error")

        self._results[backtest_id] = result
        return result

    def validate(self, backtest_id: str, **kwargs) -> ValidationResult:
        """Run validation passes on a completed backtest."""
        result = self.get_result(backtest_id)
        return self._val.validate(result, **kwargs)

    def cancel(self, backtest_id: str) -> None:
        """Cancel a PENDING backtest."""
        backtest = self._registry.get(backtest_id)
        if backtest.status not in (BacktestStatus.PENDING, BacktestStatus.RUNNING):
            raise BacktestStateError(
                f"Cannot cancel backtest in status {backtest.status.value!r}"
            )
        self._transition(backtest, BacktestStatus.CANCELLED)
        self._registry.update(backtest)
        self._record(backtest_id, BacktestEventType.BACKTEST_CANCELLED, "Cancelled")

    def archive(self, backtest_id: str) -> None:
        """Archive a terminal backtest."""
        backtest = self._registry.get(backtest_id)
        if not backtest.is_terminal():
            raise BacktestStateError(
                f"Cannot archive non-terminal backtest (status={backtest.status.value!r})"
            )
        self._transition(backtest, BacktestStatus.ARCHIVED)
        self._registry.update(backtest)
        self._record(backtest_id, BacktestEventType.BACKTEST_ARCHIVED, "Archived")

    # ── Accessors ─────────────────────────────────────────────────────────────

    def get_backtest(self, backtest_id: str) -> Backtest:
        return self._registry.get(backtest_id)

    def get_result(self, backtest_id: str) -> BacktestResult:
        if backtest_id not in self._results:
            raise BacktestNotFoundError(f"No result for backtest {backtest_id!r}")
        return self._results[backtest_id]

    def get_statistics(self, backtest_id: str) -> Optional[BacktestStatistics]:
        return self._stats_map.get(backtest_id)

    def list_backtests(self, status: Optional[BacktestStatus] = None) -> list[Backtest]:
        if status is not None:
            return self._registry.find_by_status(status)
        return self._registry.all_backtests()

    def compare(self, backtest_ids: list[str]) -> dict[str, Any]:
        results = [self.get_result(bid) for bid in backtest_ids if bid in self._results]
        from iios.integration.research.backtesting.reporting.comparison_report import ComparisonReport
        return ComparisonReport().build(results)

    def stats(self) -> dict[str, Any]:
        from iios.integration.research.backtesting.core.backtest_statistics import BacktestStatistics
        return {
            "registry":  self._registry.stats(),
            "results":   len(self._results),
            "sim_stats": self._sim.stats(),
        }

    # ── Internals ─────────────────────────────────────────────────────────────

    def _transition(self, backtest: Backtest, status: BacktestStatus) -> None:
        if status == BacktestStatus.RUNNING:
            backtest.started_at = time.time()
        backtest.status = status
        backtest.touch()

    def _record(self, entity_id: str, event: BacktestEventType, desc: str) -> None:
        self._history.append(BacktestHistoryEntry(
            entity_type = "backtest",
            entity_id   = entity_id,
            event_type  = event,
            description = desc,
        ))
