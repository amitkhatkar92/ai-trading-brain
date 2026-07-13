"""iios/investment/strategy/lifecycle/execution_monitor.py
Unified execution monitoring facade.

Combines ExecutionTracker + PerformanceTracker to provide per-strategy
and engine-wide health assessments with configurable alert thresholds.
"""
from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Callable, Dict, List, Optional

from iios.investment.strategy.lifecycle.execution_tracker import (
    ExecutionRecord,
    ExecutionTracker,
)
from iios.investment.strategy.lifecycle.performance_tracker import (
    PerformanceMetrics,
    PerformanceTracker,
)

logger = logging.getLogger(__name__)


class HealthStatus(str, Enum):
    HEALTHY  = "healthy"
    DEGRADED = "degraded"
    CRITICAL = "critical"
    UNKNOWN  = "unknown"


@dataclass
class StrategyHealth:
    """Health assessment for a single strategy."""

    strategy_id: str
    health: HealthStatus
    last_execution: Optional[datetime]
    metrics: Optional[PerformanceMetrics]
    alert_reasons: List[str] = field(default_factory=list)
    assessed_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    def to_dict(self) -> dict:
        return {
            "strategy_id": self.strategy_id,
            "health": self.health.value,
            "last_execution": (
                self.last_execution.isoformat() if self.last_execution else None
            ),
            "alert_reasons": self.alert_reasons,
            "assessed_at": self.assessed_at.isoformat(),
            "metrics": self.metrics.to_dict() if self.metrics else None,
        }


@dataclass
class EngineHealthReport:
    """Overall engine health summary."""

    health: HealthStatus
    healthy_strategies: int
    degraded_strategies: int
    critical_strategies: int
    total_strategies: int
    global_metrics: Optional[PerformanceMetrics]
    generated_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    def to_dict(self) -> dict:
        return {
            "health": self.health.value,
            "healthy_strategies": self.healthy_strategies,
            "degraded_strategies": self.degraded_strategies,
            "critical_strategies": self.critical_strategies,
            "total_strategies": self.total_strategies,
            "generated_at": self.generated_at.isoformat(),
            "global_metrics": (
                self.global_metrics.to_dict() if self.global_metrics else None
            ),
        }


class ExecutionMonitor:
    """
    Monitors strategy execution health and fires alert callbacks.

    Thresholds:
      p95_latency_warn_ms  — alert when P95 exceeds this (default 5 000 ms)
      failure_rate_warn    — alert when failure rate exceeds this (default 10 %)
      min_samples          — minimum completed samples before assessment is
                             meaningful (default 5)

    Health levels:
      UNKNOWN   — fewer than min_samples completed executions
      HEALTHY   — all thresholds within bounds
      DEGRADED  — one threshold exceeded at the warning level
      CRITICAL  — one threshold exceeded at 2× the warning level
    """

    def __init__(
        self,
        p95_latency_warn_ms: float = 5_000.0,
        failure_rate_warn: float = 0.10,
        min_samples: int = 5,
    ) -> None:
        self._tracker = ExecutionTracker()
        self._perf = PerformanceTracker(self._tracker)
        self._lock = threading.RLock()
        self._p95_warn = p95_latency_warn_ms
        self._failure_warn = failure_rate_warn
        self._min_samples = min_samples
        self._alert_handlers: List[Callable[[StrategyHealth], None]] = []

    # ── Handler registration ──────────────────────────────────────────────────

    def add_alert_handler(
        self, handler: Callable[[StrategyHealth], None]
    ) -> None:
        with self._lock:
            self._alert_handlers.append(handler)

    # ── Record tracking ───────────────────────────────────────────────────────

    def start_record(
        self,
        strategy_id: str,
        session_id: str = "",
        cycle_id: str = "",
    ) -> ExecutionRecord:
        """Create and return a new RUNNING execution record."""
        return self._tracker.start_record(strategy_id, session_id, cycle_id)

    @property
    def tracker(self) -> ExecutionTracker:
        return self._tracker

    @property
    def performance(self) -> PerformanceTracker:
        return self._perf

    # ── Health assessment ─────────────────────────────────────────────────────

    def assess_strategy(self, strategy_id: str) -> StrategyHealth:
        """Compute and return a health assessment for a single strategy."""
        metrics = self._perf.compute(strategy_id=strategy_id, last_n=100)
        last_rec = self._tracker.last_execution(strategy_id)
        last_time = last_rec.started_at if last_rec else None

        alerts: List[str] = []
        health = HealthStatus.HEALTHY

        if metrics.sample_count < self._min_samples:
            health = HealthStatus.UNKNOWN
        else:
            # Failure rate
            fr = metrics.failure_rate
            if fr > self._failure_warn * 2:
                health = HealthStatus.CRITICAL
                alerts.append(
                    f"Failure rate {fr:.0%} exceeds critical threshold "
                    f"({self._failure_warn * 2:.0%})"
                )
            elif fr > self._failure_warn:
                if health != HealthStatus.CRITICAL:
                    health = HealthStatus.DEGRADED
                alerts.append(
                    f"Failure rate {fr:.0%} exceeds warning threshold "
                    f"({self._failure_warn:.0%})"
                )

            # P95 latency
            if metrics.p95_ms > self._p95_warn * 2:
                health = HealthStatus.CRITICAL
                alerts.append(
                    f"P95 latency {metrics.p95_ms:.0f}ms exceeds critical "
                    f"threshold ({self._p95_warn * 2:.0f}ms)"
                )
            elif metrics.p95_ms > self._p95_warn:
                if health != HealthStatus.CRITICAL:
                    health = HealthStatus.DEGRADED
                alerts.append(
                    f"P95 latency {metrics.p95_ms:.0f}ms exceeds warning "
                    f"threshold ({self._p95_warn:.0f}ms)"
                )

        assessment = StrategyHealth(
            strategy_id=strategy_id,
            health=health,
            last_execution=last_time,
            metrics=metrics,
            alert_reasons=alerts,
        )

        if health in (HealthStatus.DEGRADED, HealthStatus.CRITICAL):
            self._fire_alerts(assessment)

        return assessment

    def engine_health_report(self) -> EngineHealthReport:
        """Generate an overall engine health report across all known strategies."""
        strategy_ids = self._tracker.known_strategy_ids()
        assessments = [self.assess_strategy(sid) for sid in strategy_ids]

        healthy = sum(1 for a in assessments if a.health == HealthStatus.HEALTHY)
        degraded = sum(
            1 for a in assessments if a.health == HealthStatus.DEGRADED
        )
        critical = sum(
            1 for a in assessments if a.health == HealthStatus.CRITICAL
        )

        if critical > 0:
            overall = HealthStatus.CRITICAL
        elif degraded > 0:
            overall = HealthStatus.DEGRADED
        elif assessments:
            overall = HealthStatus.HEALTHY
        else:
            overall = HealthStatus.UNKNOWN

        global_metrics = self._perf.compute(last_n=1_000)

        return EngineHealthReport(
            health=overall,
            healthy_strategies=healthy,
            degraded_strategies=degraded,
            critical_strategies=critical,
            total_strategies=len(assessments),
            global_metrics=global_metrics,
        )

    # ── Internal ──────────────────────────────────────────────────────────────

    def _fire_alerts(self, assessment: StrategyHealth) -> None:
        with self._lock:
            handlers = list(self._alert_handlers)
        for handler in handlers:
            try:
                handler(assessment)
            except Exception:  # noqa: BLE001
                logger.exception("Alert handler raised an exception")
