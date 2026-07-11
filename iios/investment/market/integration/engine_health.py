"""iios/investment/market/integration/engine_health.py
Per-engine health tracking record and updater.
"""
from __future__ import annotations

import time
from typing import Dict, Optional

from iios.investment.market.integration.models import EngineHealthRecord, HealthStatus

_DEFAULT_STALE_THRESHOLD = 5   # bars without update → STALE


class EngineHealthTracker:
    """Maintains EngineHealthRecord for all registered engines."""

    def __init__(self, stale_threshold_bars: int = _DEFAULT_STALE_THRESHOLD) -> None:
        self._records:   Dict[str, EngineHealthRecord] = {}
        self._stale_thr: int = stale_threshold_bars

    def register(self, engine_name: str) -> None:
        if engine_name not in self._records:
            self._records[engine_name] = EngineHealthRecord(
                engine_name=engine_name,
                status=HealthStatus.MISSING,
                last_update_bar=-1,
                last_update_ts=0.0,
            )

    def record_update(
        self, engine_name: str, bar_index: int, ts: Optional[float] = None
    ) -> None:
        ts = ts or time.time()
        rec = self._records.get(engine_name)
        if rec is None:
            self.register(engine_name)
            rec = self._records[engine_name]
        rec.last_update_bar = bar_index
        rec.last_update_ts  = ts
        rec.staleness_bars  = 0
        rec.status          = HealthStatus.HEALTHY

    def record_error(self, engine_name: str, error: str) -> None:
        self.register(engine_name)
        rec = self._records[engine_name]
        rec.error_count += 1
        rec.last_error   = error
        rec.status       = HealthStatus.FAILED

    def advance_bar(self, current_bar: int) -> None:
        """Called each bar; ages records not updated this bar."""
        for rec in self._records.values():
            if rec.last_update_bar < current_bar:
                rec.staleness_bars = current_bar - rec.last_update_bar
                if rec.staleness_bars >= self._stale_thr:
                    rec.status = HealthStatus.STALE
                elif rec.staleness_bars > 0 and rec.status is HealthStatus.HEALTHY:
                    rec.status = HealthStatus.DEGRADED

    def get(self, engine_name: str) -> Optional[EngineHealthRecord]:
        return self._records.get(engine_name)

    def all_records(self) -> Dict[str, EngineHealthRecord]:
        return dict(self._records)

    def healthy_count(self) -> int:
        return sum(1 for r in self._records.values() if r.status is HealthStatus.HEALTHY)

    def degraded_engines(self) -> list:
        return [r.engine_name for r in self._records.values()
                if r.status in (HealthStatus.STALE, HealthStatus.DEGRADED, HealthStatus.FAILED)]
