"""iios/investment/market/integration/coverage_monitor.py
Tracks which engines have provided data and measures coverage completeness.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Dict, List, Set

from iios.investment.market.integration.aggregation_engine import KNOWN_ENGINES


class CoverageMonitor:
    """Tracks per-engine coverage across bars."""

    def __init__(self, expected_engines: List[str] = None) -> None:
        self._expected     = set(expected_engines or KNOWN_ENGINES)
        self._seen:        Dict[str, int] = defaultdict(int)   # engine → bars received
        self._bars_total:  int = 0

    def record(self, engines_received: Set[str]) -> None:
        self._bars_total += 1
        for engine in engines_received:
            self._seen[engine] += 1

    @property
    def total_bars(self) -> int:
        return self._bars_total

    def coverage_rate(self, engine_name: str) -> float:
        """Fraction of bars in which this engine provided data."""
        if self._bars_total == 0:
            return 0.0
        return self._seen.get(engine_name, 0) / self._bars_total

    def overall_coverage(self) -> float:
        """Average coverage rate across all expected engines."""
        if not self._expected or self._bars_total == 0:
            return 0.0
        rates = [self.coverage_rate(e) for e in self._expected]
        return sum(rates) / len(rates)

    def missing_this_bar(self, engines_received: Set[str]) -> Set[str]:
        return self._expected - engines_received

    def coverage_report(self) -> Dict[str, float]:
        return {e: self.coverage_rate(e) for e in self._expected}

    def consistently_missing(self, threshold: float = 0.5) -> List[str]:
        """Engines with coverage rate below threshold."""
        return [e for e in self._expected if self.coverage_rate(e) < threshold]
