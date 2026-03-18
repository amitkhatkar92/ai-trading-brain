"""
System Monitor
==============
Tracks the operational health of the entire AI Trading Brain system.

Monitors:
  • Layer latency        — how long each layer took (ms)
  • Cycle cadence        — whether cycles run on schedule
  • Agent health         — agent-level error counts
  • Broker API health    — last API call latency vs alert threshold
  • Data feed lag        — age of last received data vs threshold
  • Task queue backlog   — whether async workers are falling behind
  • Memory usage         — strategy memory entry counts
  • Error rate           — fraction of cycles that produced errors

Emits structured HealthReport after every cycle.
Logs CRITICAL alerts when thresholds are breached.

Alert thresholds
  LAYER_LATENCY_WARN_MS   = 2000   (2 seconds per layer)
  LAYER_LATENCY_CRIT_MS   = 5000   (5 seconds → critical)
  BROKER_LATENCY_WARN_MS  = 3000   (broker API > 3 sec → execution suspended)
  DATA_LAG_WARN_S         = 300    (5 min stale feed)
  QUEUE_BACKLOG_WARN       = 50    (task queue > 50 pending)
  ERROR_RATE_WARN          = 0.20  (20% error rate over last 10 cycles)
"""

from __future__ import annotations
import collections
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from typing import Deque, Generator, Optional

from utils import get_logger

log = get_logger(__name__)

# ── Thresholds ────────────────────────────────────────────────────────────
LAYER_LATENCY_WARN_MS  = 2_000
LAYER_LATENCY_CRIT_MS  = 5_000
BROKER_LATENCY_WARN_MS = 3_000
DATA_LAG_WARN_S        = 300
QUEUE_BACKLOG_WARN     = 50
ERROR_RATE_WARN        = 0.20
HISTORY_WINDOW         = 10     # cycles to keep for error-rate calculation

# Per-layer WARN overrides — for layers that make external network calls
# and are expected to be slower than the default 2 000 ms threshold.
LAYER_LATENCY_WARN_OVERRIDES: dict = {
    "GlobalIntelligence": 5_000,   # first call fetches 13 yfinance symbols (~3-4s cold)
}
LAYER_LATENCY_CRIT_OVERRIDES: dict = {
    "GlobalIntelligence": 12_000,  # only CRITICAL if truly hung (>12s)
}


@dataclass
class LayerTiming:
    name:       str
    duration_ms: float
    status:     str    # "OK" | "WARN" | "CRITICAL"


@dataclass
class HealthReport:
    timestamp:       datetime
    cycle_id:        int
    layer_timings:   list[LayerTiming] = field(default_factory=list)
    total_cycle_ms:  float = 0.0
    agent_errors:    dict[str, int] = field(default_factory=dict)
    broker_latency_ms: float = 0.0
    data_lag_s:      float = 0.0
    queue_backlog:   int   = 0
    alerts:          list[str] = field(default_factory=list)
    healthy:         bool  = True

    def summary(self) -> str:
        status = "HEALTHY ✅" if self.healthy else "DEGRADED ⚠️"
        slowest = max(self.layer_timings, key=lambda t: t.duration_ms,
                      default=None)
        slowest_str = (f" | Slowest={slowest.name}({slowest.duration_ms:.0f}ms)"
                       if slowest else "")
        alerts_str  = f" | {len(self.alerts)} ALERT(S)" if self.alerts else ""
        return (f"[SystemMonitor] {status} | Cycle #{self.cycle_id} | "
                f"Total={self.total_cycle_ms:.0f}ms{slowest_str}{alerts_str}")


class SystemMonitor:
    """
    Collects timing and health metrics throughout each trading cycle.

    Usage (in orchestrator)::
        monitor = SystemMonitor()

        with monitor.time_layer("MarketIntelligence"):
            snapshot = self._run_market_intelligence(bias)

        report = monitor.finalize_cycle()
    """

    def __init__(self) -> None:
        self._cycle_id:     int = 0
        self._layer_timings: list[LayerTiming] = []
        self._cycle_start:  Optional[float] = None
        self._agent_errors: dict[str, int] = collections.defaultdict(int)
        self._broker_latency_ms: float = 0.0
        self._data_lag_s:    float = 0.0
        self._queue_backlog: int   = 0
        self._cycle_had_error: Deque[bool] = collections.deque(maxlen=HISTORY_WINDOW)
        self._cycle_abort_flag: bool = False   # set True when a layer hits CRITICAL

        log.info("[SystemMonitor] Initialised. Tracking layer latency, "
                 "errors, broker health, data lag.")

    # ── Cycle lifecycle ───────────────────────────────────────────────────
    def start_cycle(self) -> None:
        self._cycle_id      += 1
        self._cycle_start    = time.perf_counter()
        self._layer_timings  = []
        self._cycle_abort_flag = False   # reset every cycle
        log.debug("[SystemMonitor] Cycle #%d started.", self._cycle_id)

    @contextmanager
    def time_layer(self, layer_name: str) -> Generator[None, None, None]:
        """Context manager — wraps a layer call and records timing."""
        t0 = time.perf_counter()
        try:
            yield
        finally:
            ms = (time.perf_counter() - t0) * 1000
            warn_ms = LAYER_LATENCY_WARN_OVERRIDES.get(layer_name, LAYER_LATENCY_WARN_MS)
            crit_ms = LAYER_LATENCY_CRIT_OVERRIDES.get(layer_name, LAYER_LATENCY_CRIT_MS)
            if ms >= crit_ms:
                status = "CRITICAL"
                self._cycle_abort_flag = True   # ← enforce: abort rest of cycle
                log.error("[SystemMonitor] CRITICAL latency: %s took %.0f ms "
                          "(≥%.0f ms) — cycle will be aborted.", layer_name, ms,
                          crit_ms)
            elif ms >= warn_ms:
                status = "WARN"
                log.warning("[SystemMonitor] SLOW layer: %s took %.0f ms",
                            layer_name, ms)
            else:
                status = "OK"
                log.debug("[SystemMonitor] %s: %.0f ms", layer_name, ms)
            self._layer_timings.append(LayerTiming(
                name=layer_name, duration_ms=round(ms, 1), status=status,
            ))

    def should_abort_cycle(self) -> bool:
        """
        Returns True if any layer in the current cycle exceeded LAYER_LATENCY_CRIT_MS.
        The orchestrator should check this after each layer and bail out early if True.
        """
        return self._cycle_abort_flag

    def finalize_cycle(self, had_error: bool = False) -> HealthReport:
        """Call at end of cycle to produce and log a HealthReport."""
        total_ms = 0.0
        if self._cycle_start is not None:
            total_ms = (time.perf_counter() - self._cycle_start) * 1000

        self._cycle_had_error.append(had_error)
        alerts = self._collect_alerts(total_ms)
        healthy = len([a for a in alerts if "CRITICAL" in a or "HALT" in a]) == 0

        report = HealthReport(
            timestamp       = datetime.now(),
            cycle_id        = self._cycle_id,
            layer_timings   = list(self._layer_timings),
            total_cycle_ms  = round(total_ms, 1),
            agent_errors    = dict(self._agent_errors),
            broker_latency_ms = self._broker_latency_ms,
            data_lag_s      = self._data_lag_s,
            queue_backlog   = self._queue_backlog,
            alerts          = alerts,
            healthy         = healthy,
        )
        log.info(report.summary())
        for alert in alerts:
            log.warning("[SystemMonitor] ALERT: %s", alert)
        return report

    # ── Update methods (called by orchestrator or agents) ─────────────────
    def record_agent_error(self, agent_name: str) -> None:
        self._agent_errors[agent_name] += 1
        log.warning("[SystemMonitor] Agent error recorded: %s (total=%d)",
                    agent_name, self._agent_errors[agent_name])

    def record_broker_latency(self, latency_ms: float) -> None:
        self._broker_latency_ms = latency_ms
        if latency_ms >= BROKER_LATENCY_WARN_MS:
            log.error("[SystemMonitor] Broker latency=%.0f ms ≥ %.0f ms — "
                      "execution suspended!", latency_ms, BROKER_LATENCY_WARN_MS)

    def record_data_lag(self, lag_seconds: float) -> None:
        self._data_lag_s = lag_seconds
        if lag_seconds >= DATA_LAG_WARN_S:
            log.warning("[SystemMonitor] Data feed lag=%.0fs — stale signals "
                        "possible", lag_seconds)

    def record_queue_backlog(self, backlog: int) -> None:
        self._queue_backlog = backlog
        if backlog >= QUEUE_BACKLOG_WARN:
            log.warning("[SystemMonitor] Task queue backlog=%d — system may "
                        "be overloaded", backlog)

    def print_cycle_table(self, report: HealthReport) -> None:
        """Print a formatted timing table for the cycle."""
        border = "═" * 60
        log.info(border)
        log.info("  SYSTEM HEALTH REPORT  |  Cycle #%d  |  %s",
                 report.cycle_id,
                 report.timestamp.strftime("%H:%M:%S"))
        log.info("─" * 60)
        log.info("  %-32s %10s  %s", "Layer", "Time(ms)", "Status")
        log.info("  " + "─" * 56)
        for t in report.layer_timings:
            flag = "⚠️" if t.status == "WARN" else ("🛑" if t.status == "CRITICAL" else "✅")
            log.info("  %-32s %10.0f  %s %s",
                     t.name, t.duration_ms, flag, t.status)
        log.info("  " + "─" * 56)
        log.info("  %-32s %10.0f  ms total", "FULL CYCLE", report.total_cycle_ms)
        if report.alerts:
            log.info("─" * 60)
            for a in report.alerts:
                log.info("  ⚠️  %s", a)
        log.info(border)

    # ── Private ───────────────────────────────────────────────────────────
    def _collect_alerts(self, total_ms: float) -> list[str]:
        alerts = []

        # Slow layers
        for t in self._layer_timings:
            if t.status == "CRITICAL":
                alerts.append(f"CRITICAL latency: {t.name} took {t.duration_ms:.0f}ms")
            elif t.status == "WARN":
                alerts.append(f"Slow layer: {t.name} took {t.duration_ms:.0f}ms")

        # Broker latency
        if self._broker_latency_ms >= BROKER_LATENCY_WARN_MS:
            alerts.append(f"CRITICAL Broker API latency={self._broker_latency_ms:.0f}ms — "
                          f"HALT execution")

        # Data lag
        if self._data_lag_s >= DATA_LAG_WARN_S:
            alerts.append(f"Stale data feed: lag={self._data_lag_s:.0f}s")

        # Queue backlog
        if self._queue_backlog >= QUEUE_BACKLOG_WARN:
            alerts.append(f"Task queue backlog={self._queue_backlog} — system overload")

        # Error rate
        if len(self._cycle_had_error) >= 5:
            error_rate = sum(self._cycle_had_error) / len(self._cycle_had_error)
            if error_rate >= ERROR_RATE_WARN:
                alerts.append(f"High error rate: {error_rate:.0%} of last "
                               f"{len(self._cycle_had_error)} cycles had errors")

        return alerts
