"""iios/investment/company/integration/health_monitor.py
Orchestrates engine health, dependency, and coverage monitoring.
"""
from __future__ import annotations

import threading
from typing import Any, Dict, List, Optional

from iios.investment.company.integration.company_state import EngineStatus, KNOWN_ENGINES
from iios.investment.company.integration.coverage_monitor import CoverageMonitor
from iios.investment.company.integration.dependency_monitor import DependencyMonitor
from iios.investment.company.integration.engine_health import EngineHealthRecord


class HealthMonitor:
    """
    Single health monitoring facade for the integration engine.

    Combines:
    - DependencyMonitor: per-engine availability and update tracking
    - CoverageMonitor:   per-ticker intelligence coverage
    """

    def __init__(self) -> None:
        self._lock        = threading.RLock()
        self._deps        = DependencyMonitor()
        self._coverage    = CoverageMonitor()

    # ── Event recording ───────────────────────────────────────────────────────

    def on_engine_update(
        self,
        engine_name:     str,
        latency_ms:      Optional[float] = None,
    ) -> None:
        """Call whenever an upstream engine provides a new snapshot."""
        self._deps.record_update(engine_name, latency_ms=latency_ms)

    def on_engine_error(self, engine_name: str) -> None:
        self._deps.record_error(engine_name)

    def on_evaluation(self, ticker: str, available_engines: List[str]) -> None:
        """Call once per integration cycle with the engines that participated."""
        self._coverage.record_engines(ticker, available_engines)

    # ── Engine health queries ─────────────────────────────────────────────────

    def engine_health(self, engine_name: str) -> Optional[EngineHealthRecord]:
        return self._deps.get_health(engine_name)

    def all_engine_health(self) -> Dict[str, EngineHealthRecord]:
        return self._deps.all_health()

    def unavailable_engines(self) -> List[str]:
        return self._deps.unavailable_engines()

    def stale_engines(self) -> List[str]:
        return self._deps.stale_engines()

    def healthy_engines(self) -> List[str]:
        return self._deps.healthy_engines()

    def system_health_fraction(self) -> float:
        """Fraction of KNOWN_ENGINES currently HEALTHY."""
        return self._deps.overall_health_fraction()

    # ── Coverage queries ──────────────────────────────────────────────────────

    def ticker_coverage(self, ticker: str) -> float:
        return self._coverage.coverage_fraction(ticker)

    def missing_engines_for(self, ticker: str) -> List[str]:
        return self._coverage.missing_engines(ticker)

    def system_coverage(self) -> float:
        return self._coverage.system_coverage_fraction()

    def poorly_covered_tickers(self, threshold: float = 0.50) -> List[str]:
        return self._coverage.poorly_covered_tickers(threshold)

    def all_tickers(self) -> List[str]:
        return self._coverage.all_tickers()

    # ── Composite report ──────────────────────────────────────────────────────

    def health_report(self) -> Dict[str, Any]:
        return {
            "system_health_fraction":  round(self.system_health_fraction(), 3),
            "system_coverage_fraction": round(self.system_coverage(), 3),
            "healthy_engines":         self.healthy_engines(),
            "unavailable_engines":     self.unavailable_engines(),
            "stale_engines":           self.stale_engines(),
            "total_tickers_tracked":   len(self.all_tickers()),
            "engine_details":          {
                name: rec.to_dict()
                for name, rec in self.all_engine_health().items()
            },
        }
