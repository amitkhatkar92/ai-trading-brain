"""iios/investment/strategy/integration/health_monitor.py
HealthMonitor: background async loop for periodic health/coverage checks.
"""
from __future__ import annotations

import asyncio
import logging
import threading
from dataclasses import dataclass
from typing import Any, Dict, Optional

from iios.investment.strategy.integration.coverage_monitor import CoverageMonitor, CoverageReport
from iios.investment.strategy.integration.dependency_monitor import (
    DependencyMonitor,
    DependencyStatus,
)
from iios.investment.strategy.integration.engine_health import (
    EngineHealthChecker,
    EngineHealthReport,
)
from iios.investment.strategy.integration.integration_constants import IntelligenceSource
from iios.investment.strategy.integration.strategy_intelligence_aggregator import (
    StrategyIntelligenceAggregator,
)

_log = logging.getLogger(__name__)


@dataclass
class HealthMonitorConfig:
    check_interval_seconds: float = 60.0
    stale_threshold_seconds: float = 7_200.0


class HealthMonitor:
    """
    Runs periodic health and coverage checks in a background asyncio task.
    Provides synchronous read accessors for the integration engine facade.
    """

    def __init__(
        self,
        aggregator:   StrategyIntelligenceAggregator,
        config:       Optional[HealthMonitorConfig] = None,
        health_checker: Optional[EngineHealthChecker] = None,
        dep_monitor:   Optional[DependencyMonitor]    = None,
        cov_monitor:   Optional[CoverageMonitor]      = None,
    ) -> None:
        self._aggregator     = aggregator
        self._config         = config or HealthMonitorConfig()
        self._health_checker = health_checker or EngineHealthChecker()
        self._dep_monitor    = dep_monitor    or DependencyMonitor()
        self._cov_monitor    = cov_monitor    or CoverageMonitor()

        self._lock:           threading.RLock            = threading.RLock()
        self._latest_health:  Optional[EngineHealthReport] = None
        self._latest_coverage: Optional[CoverageReport]  = None
        self._running:        bool                        = False
        self._task:           Optional[asyncio.Task]     = None

    # ------------------------------------------------------------------ start/stop

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._task    = asyncio.create_task(self._run_loop())
        _log.info("HealthMonitor started (interval=%.0fs)", self._config.check_interval_seconds)

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        _log.info("HealthMonitor stopped.")

    # ------------------------------------------------------------------ background loop

    async def _run_loop(self) -> None:
        while self._running:
            try:
                await self._tick()
            except Exception as exc:  # pylint: disable=broad-except
                _log.warning("HealthMonitor tick failed: %s", exc)
            await asyncio.sleep(self._config.check_interval_seconds)

    async def _tick(self) -> None:
        state_map = {
            sid: self._aggregator.state(sid)
            for sid in self._aggregator.known_strategies()
        }

        health   = self._health_checker.check_all(state_map)
        coverage = self._cov_monitor.compute(self._aggregator)

        with self._lock:
            self._latest_health   = health
            self._latest_coverage = coverage

    # ------------------------------------------------------------------ accessors

    def get_health(self) -> Optional[EngineHealthReport]:
        with self._lock:
            return self._latest_health

    def get_coverage(self) -> Optional[CoverageReport]:
        with self._lock:
            return self._latest_coverage

    def get_dependency_status(self) -> Dict[IntelligenceSource, DependencyStatus]:
        return self._dep_monitor.check_all()

    def record_seen(self, source: IntelligenceSource) -> None:
        """Call whenever an update from this source arrives."""
        self._dep_monitor.record_seen(source)

    def snapshot_dict(self) -> Dict[str, Any]:
        h  = self.get_health()
        co = self.get_coverage()
        return {
            "health":   h.to_dict() if h else None,
            "coverage": co.to_dict() if co else None,
        }
