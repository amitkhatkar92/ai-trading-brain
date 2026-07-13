"""iios/investment/company/integration/dependency_monitor.py
Monitors engine-level dependency health and availability.
"""
from __future__ import annotations

import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from iios.investment.company.integration.company_state import (
    EngineStatus, KNOWN_ENGINES,
)
from iios.investment.company.integration.engine_health import EngineHealthRecord


class DependencyMonitor:
    """
    Thread-safe registry of EngineHealthRecord objects for all known upstream engines.

    Responsibilities:
    - Track last-update time and update count per engine
    - Surface engine availability for the health dashboard
    - Provide a dependency-failure list for the integration engine
    """

    def __init__(self) -> None:
        self._lock    = threading.RLock()
        self._engines: Dict[str, EngineHealthRecord] = {
            name: EngineHealthRecord(engine_name=name)
            for name in KNOWN_ENGINES
        }

    def record_update(self, engine_name: str, latency_ms: Optional[float] = None) -> None:
        with self._lock:
            if engine_name not in self._engines:
                self._engines[engine_name] = EngineHealthRecord(engine_name=engine_name)
            self._engines[engine_name].record_update(latency_ms=latency_ms)

    def record_error(self, engine_name: str) -> None:
        with self._lock:
            if engine_name not in self._engines:
                self._engines[engine_name] = EngineHealthRecord(engine_name=engine_name)
            self._engines[engine_name].record_error()

    def get_health(self, engine_name: str) -> Optional[EngineHealthRecord]:
        with self._lock:
            return self._engines.get(engine_name)

    def all_health(self) -> Dict[str, EngineHealthRecord]:
        with self._lock:
            # Refresh status before returning
            for rec in self._engines.values():
                rec.refresh_status()
            return dict(self._engines)

    def unavailable_engines(self) -> List[str]:
        with self._lock:
            return [
                name for name, rec in self._engines.items()
                if rec.status == EngineStatus.UNAVAILABLE
            ]

    def stale_engines(self) -> List[str]:
        with self._lock:
            return [
                name for name, rec in self._engines.items()
                if rec.status == EngineStatus.STALE
            ]

    def healthy_engines(self) -> List[str]:
        with self._lock:
            return [
                name for name, rec in self._engines.items()
                if rec.status == EngineStatus.HEALTHY
            ]

    def to_dict(self) -> Dict[str, Any]:
        return {
            name: rec.to_dict()
            for name, rec in self.all_health().items()
        }

    def overall_health_fraction(self) -> float:
        """Fraction of KNOWN_ENGINES that are currently HEALTHY."""
        with self._lock:
            total = len(KNOWN_ENGINES)
            healthy = sum(
                1 for n in KNOWN_ENGINES
                if n in self._engines and self._engines[n].status == EngineStatus.HEALTHY
            )
            return healthy / total if total > 0 else 0.0
