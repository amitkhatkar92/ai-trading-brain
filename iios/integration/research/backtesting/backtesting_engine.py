"""backtesting_engine.py — Singleton facade for the Strategy Backtesting Framework."""
from __future__ import annotations

import logging
import threading
import time
from typing import Any, Optional

from iios.integration.research.backtesting.backtest_constants import (
    BACKTESTING_ENGINE_VERSION,
    BacktestEngineStatus,
    BacktestStatus,
)
from iios.integration.research.backtesting.backtest_exceptions import (
    BacktestEngineAlreadyRunningError,
    BacktestEngineInitializationError,
    BacktestEngineNotRunningError,
)
from iios.integration.research.backtesting.backtest_factory import BacktestFactory
from iios.integration.research.backtesting.backtest_manager import BacktestManager
from iios.integration.research.backtesting.core.backtest import Backtest
from iios.integration.research.backtesting.core.backtest_result import BacktestResult
from iios.integration.research.backtesting.core.backtest_statistics import BacktestStatistics
from iios.integration.research.backtesting.core.backtest_request import BacktestRequest
from iios.integration.research.backtesting.engine.market_simulator import BarEvent
from iios.integration.research.backtesting.engine.simulation_engine import BacktestStrategy
from iios.integration.research.backtesting.validation.validation_engine import ValidationResult

_log = logging.getLogger(__name__)


class BacktestingEngine:
    """
    Singleton facade for the complete Strategy Backtesting Framework.

    Provides a single stable API surface that hides all internal complexity.

    Usage::

        engine = get_backtesting_engine(auto_start=True)
        backtest = engine.submit(request)
        result   = await engine.run(backtest.backtest_id, strategy, bars_data)
        report   = result.report
    """

    def __init__(self) -> None:
        self._status: BacktestEngineStatus = BacktestEngineStatus.STOPPED
        self._started_at: Optional[float]  = None
        self._manager: Optional[BacktestManager] = None

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    async def start(self) -> None:
        if self._status == BacktestEngineStatus.RUNNING:
            raise BacktestEngineAlreadyRunningError("BacktestingEngine is already running")
        self._status = BacktestEngineStatus.INITIALIZING
        try:
            self._manager = BacktestManager(
                registry         = BacktestFactory.create_registry(),
                sim_engine       = BacktestFactory.create_simulation_engine(),
                perf_engine      = BacktestFactory.create_performance_engine(),
                report_generator = BacktestFactory.create_report_generator(),
                validation_engine = BacktestFactory.create_validation_engine(),
                history          = BacktestFactory.create_history(),
            )
            self._status     = BacktestEngineStatus.RUNNING
            self._started_at = time.time()
            _log.info("[BacktestingEngine] started  version=%s", BACKTESTING_ENGINE_VERSION)
        except Exception as exc:
            self._status = BacktestEngineStatus.ERROR
            raise BacktestEngineInitializationError(f"Init failed: {exc}") from exc

    async def stop(self) -> None:
        self._status  = BacktestEngineStatus.STOPPED
        self._manager = None
        _log.info("[BacktestingEngine] stopped")

    def is_running(self) -> bool:
        return self._status == BacktestEngineStatus.RUNNING

    def status(self) -> BacktestEngineStatus:
        return self._status

    def uptime_sec(self) -> float:
        if self._started_at is None:
            return 0.0
        return time.time() - self._started_at

    # ── Submission ────────────────────────────────────────────────────────────

    def submit(self, request: BacktestRequest) -> Backtest:
        self._assert_running()
        return self._manager.submit(request)  # type: ignore[union-attr]

    # ── Execution ─────────────────────────────────────────────────────────────

    async def run(
        self,
        backtest_id:       str,
        strategy:          BacktestStrategy,
        bars_data:         dict[str, list[BarEvent]],
        *,
        risk_free_rate:    float                  = 0.06,
        benchmark_returns: Optional[list[float]] = None,
    ) -> BacktestResult:
        self._assert_running()
        return await self._manager.run(  # type: ignore[union-attr]
            backtest_id,
            strategy,
            bars_data,
            risk_free_rate    = risk_free_rate,
            benchmark_returns = benchmark_returns,
        )

    # ── Retrieval ─────────────────────────────────────────────────────────────

    def get_backtest(self, backtest_id: str) -> Backtest:
        self._assert_running()
        return self._manager.get_backtest(backtest_id)  # type: ignore[union-attr]

    def get_result(self, backtest_id: str) -> BacktestResult:
        self._assert_running()
        return self._manager.get_result(backtest_id)  # type: ignore[union-attr]

    def get_statistics(self, backtest_id: str) -> Optional[BacktestStatistics]:
        self._assert_running()
        return self._manager.get_statistics(backtest_id)  # type: ignore[union-attr]

    def list_backtests(self, status: Optional[BacktestStatus] = None) -> list[Backtest]:
        self._assert_running()
        return self._manager.list_backtests(status)  # type: ignore[union-attr]

    # ── Validation ────────────────────────────────────────────────────────────

    def validate(self, backtest_id: str, **kwargs) -> ValidationResult:
        self._assert_running()
        return self._manager.validate(backtest_id, **kwargs)  # type: ignore[union-attr]

    # ── Workflow helpers ──────────────────────────────────────────────────────

    def cancel(self, backtest_id: str) -> None:
        self._assert_running()
        self._manager.cancel(backtest_id)  # type: ignore[union-attr]

    def archive(self, backtest_id: str) -> None:
        self._assert_running()
        self._manager.archive(backtest_id)  # type: ignore[union-attr]

    def compare(self, backtest_ids: list[str]) -> dict[str, Any]:
        self._assert_running()
        return self._manager.compare(backtest_ids)  # type: ignore[union-attr]

    # ── Statistics ────────────────────────────────────────────────────────────

    def stats(self) -> dict[str, Any]:
        base = {
            "version":    BACKTESTING_ENGINE_VERSION,
            "status":     self._status.value,
            "uptime_sec": self.uptime_sec(),
        }
        if self._manager:
            base.update(self._manager.stats())
        return base

    # ── Guard ─────────────────────────────────────────────────────────────────

    def _assert_running(self) -> None:
        if not self.is_running():
            raise BacktestEngineNotRunningError(
                "BacktestingEngine is not running. Call await engine.start() first."
            )


# ── Singleton ─────────────────────────────────────────────────────────────────

_instance: Optional[BacktestingEngine] = None
_lock      = threading.Lock()


def get_backtesting_engine(auto_start: bool = False) -> BacktestingEngine:
    """Return (or lazily create) the process-wide BacktestingEngine singleton."""
    global _instance
    with _lock:
        if _instance is None:
            _instance = BacktestingEngine()
            if auto_start:
                import asyncio
                asyncio.run(_instance.start())
    return _instance


def reset_backtesting_engine() -> None:
    """Replace the singleton — use only in tests."""
    global _instance
    with _lock:
        _instance = None
