"""iios/investment/company/integration/coverage_monitor.py
Tracks per-ticker and system-wide intelligence coverage.
"""
from __future__ import annotations

import threading
from collections import defaultdict
from typing import Any, Dict, List, Optional

from iios.investment.company.integration.company_state import SCORED_ENGINES


class CoverageMonitor:
    """
    Tracks which engines have provided intelligence for which tickers,
    and reports coverage gaps at both ticker and system levels.
    """

    def __init__(self) -> None:
        self._lock    = threading.RLock()
        # ticker → set of engine names that have provided data
        self._coverage: Dict[str, set] = defaultdict(set)
        # ticker → evaluation count
        self._eval_counts: Dict[str, int] = defaultdict(int)

    def record_engines(self, ticker: str, available: List[str]) -> None:
        """Record which engines provided data for *ticker* in this cycle."""
        with self._lock:
            self._coverage[ticker].update(available)
            self._eval_counts[ticker] += 1

    def covered_engines(self, ticker: str) -> List[str]:
        """Engines that have ever provided data for *ticker*."""
        with self._lock:
            return list(self._coverage.get(ticker, set()))

    def missing_engines(self, ticker: str) -> List[str]:
        """SCORED_ENGINES that have never provided data for *ticker*."""
        with self._lock:
            covered = self._coverage.get(ticker, set())
            return [e for e in SCORED_ENGINES if e not in covered]

    def coverage_fraction(self, ticker: str) -> float:
        """Fraction of SCORED_ENGINES ever covered for *ticker*."""
        with self._lock:
            covered = self._coverage.get(ticker, set())
            scored_covered = sum(1 for e in SCORED_ENGINES if e in covered)
            return scored_covered / len(SCORED_ENGINES)

    def eval_count(self, ticker: str) -> int:
        with self._lock:
            return self._eval_counts.get(ticker, 0)

    def all_tickers(self) -> List[str]:
        with self._lock:
            return list(self._coverage.keys())

    def system_coverage_fraction(self) -> float:
        """Average coverage fraction across all tickers (0-1)."""
        with self._lock:
            if not self._coverage:
                return 0.0
            fractions = []
            for ticker in self._coverage:
                covered = self._coverage[ticker]
                scored = sum(1 for e in SCORED_ENGINES if e in covered)
                fractions.append(scored / len(SCORED_ENGINES))
            return sum(fractions) / len(fractions)

    def poorly_covered_tickers(self, threshold: float = 0.50) -> List[str]:
        """Tickers with coverage fraction below *threshold*."""
        with self._lock:
            result = []
            for ticker, engines in self._coverage.items():
                scored = sum(1 for e in SCORED_ENGINES if e in engines)
                if scored / len(SCORED_ENGINES) < threshold:
                    result.append(ticker)
            return result

    def to_dict(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "total_tickers":          len(self._coverage),
                "system_coverage":        round(self.system_coverage_fraction(), 3),
                "per_ticker": {
                    t: {
                        "covered":    sorted(list(self._coverage[t])),
                        "missing":    [e for e in SCORED_ENGINES if e not in self._coverage[t]],
                        "fraction":   round(
                            sum(1 for e in SCORED_ENGINES if e in self._coverage[t])
                            / len(SCORED_ENGINES), 3
                        ),
                    }
                    for t in self._coverage
                },
            }
