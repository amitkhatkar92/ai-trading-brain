"""
iios/observation/collectors/scheduled_collector.py
==================================================
ScheduledCollector — collector with built-in schedule configuration.

The schedule drives when the CollectorScheduler triggers ``run()``.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Optional

from ..models.observation import Observation
from .base_collector      import BaseCollector, CollectorConfig
from .collector_constants import ScheduleType

__all__ = ["ScheduleConfig", "ScheduledCollector"]


@dataclass
class ScheduleConfig:
    """Describes when a collector should be executed."""
    schedule_type:     ScheduleType  = ScheduleType.MANUAL
    interval_s:        float         = 60.0          # for INTERVAL
    cron_expr:         str           = ""             # for CRON  "*/5 * * * *"
    market_hours_only: bool          = False          # for MARKET_HOURS
    event_names:       list[str]     = field(default_factory=list)  # for EVENT
    dependencies:      list[str]     = field(default_factory=list)  # for DEPENDENCY
    timezone:          str           = "Asia/Kolkata"
    jitter_s:          float         = 0.0
    max_missed:        int           = 3
    enabled:           bool          = True

    def next_run_at(self, last_run_at: float) -> float:
        """Compute the next scheduled run time (Unix timestamp)."""
        if self.schedule_type == ScheduleType.MANUAL:
            return float("inf")
        return last_run_at + self.interval_s

    def is_due(self, last_run_at: float) -> bool:
        """Return True if a run is due now."""
        if not self.enabled:
            return False
        if self.schedule_type == ScheduleType.MANUAL:
            return False
        if self.schedule_type == ScheduleType.INTERVAL:
            return time.time() >= self.next_run_at(last_run_at)
        # CRON / MARKET_HOURS / EVENT / DEPENDENCY handled by the Scheduler
        return False


class ScheduledCollector(BaseCollector):
    """
    Collector aware of its own scheduling configuration.

    The ``CollectorScheduler`` checks ``should_run_now()`` each tick.
    """

    def __init__(
        self,
        config:   CollectorConfig,
        schedule: Optional[ScheduleConfig] = None,
    ) -> None:
        super().__init__(config)
        self.schedule      = schedule or ScheduleConfig()
        self._last_run_at  = 0.0
        self._missed_count = 0

    def should_run_now(self) -> bool:
        """Return True if this collector is due for execution."""
        return self.schedule.is_due(self._last_run_at)

    def run(self) -> list[Observation]:
        observations      = super().run()
        self._last_run_at  = time.time()
        self._missed_count = 0
        return observations

    def _do_collect(self) -> Any:
        return []

    def _do_normalise(self, raw: Any) -> list[Observation]:
        return []
