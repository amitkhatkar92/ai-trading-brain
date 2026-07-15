"""iios/investment/portfolio/performance/benchmark_engine.py

Benchmark engine: coordinates all benchmark analyses.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from iios.investment.portfolio.performance.benchmark_comparison import (
    BenchmarkComparison, compare_to_benchmark,
)
from iios.investment.portfolio.performance.benchmark_registry import (
    Benchmark, BenchmarkRegistry, BENCHMARKS,
)
from iios.investment.portfolio.performance.performance_types import PerformancePosition


@dataclass(frozen=True)
class BenchmarkReport:
    """Multi-benchmark comparison report."""

    report_id:       str                         = field(default_factory=lambda: str(uuid.uuid4()))
    portfolio_id:    str                         = ""
    primary:         Optional[BenchmarkComparison] = None
    comparisons:     tuple                       = field(default_factory=tuple)
    best_vs:         str                         = ""   # id of benchmark where active_return is highest
    worst_vs:        str                         = ""   # id where active_return is lowest

    def to_dict(self) -> Dict[str, Any]:
        return {
            "portfolio_id": self.portfolio_id,
            "primary":      self.primary.to_dict() if self.primary else {},
            "comparisons":  [c.to_dict() for c in self.comparisons],
            "best_vs":      self.best_vs,
            "worst_vs":     self.worst_vs,
        }


class BenchmarkEngine:
    """Runs benchmark analysis against one or more benchmarks."""

    def __init__(self, registry: Optional[BenchmarkRegistry] = None) -> None:
        self._registry = registry or BenchmarkRegistry()

    def run_primary(
        self,
        positions:        List[PerformancePosition],
        portfolio_return: float,
        portfolio_id:     str = "",
        benchmark_id:     str = "nifty50",
        period_years:     float = 1.0,
    ) -> BenchmarkComparison:
        bmk = self._registry.get_or_default(benchmark_id)
        return compare_to_benchmark(
            positions, bmk, portfolio_return, portfolio_id, period_years
        )

    def run_all(
        self,
        positions:        List[PerformancePosition],
        portfolio_return: float,
        portfolio_id:     str = "",
        benchmark_ids:    Optional[List[str]] = None,
        period_years:     float = 1.0,
    ) -> BenchmarkReport:
        if benchmark_ids is None:
            benchmark_ids = ["nifty50", "nifty500", "sensex"]

        comparisons: List[BenchmarkComparison] = []
        for bid in benchmark_ids:
            bmk = self._registry.get_or_default(bid)
            c   = compare_to_benchmark(
                positions, bmk, portfolio_return, portfolio_id, period_years
            )
            comparisons.append(c)

        primary = comparisons[0] if comparisons else None
        best_id = max(comparisons, key=lambda c: c.active_return).benchmark_id if comparisons else ""
        worst_id= min(comparisons, key=lambda c: c.active_return).benchmark_id if comparisons else ""

        return BenchmarkReport(
            portfolio_id = portfolio_id,
            primary      = primary,
            comparisons  = tuple(comparisons),
            best_vs      = best_id,
            worst_vs     = worst_id,
        )
