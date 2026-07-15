"""iios/investment/portfolio/performance/benchmark_registry.py

Built-in benchmark definitions for IIOS.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from iios.investment.portfolio.performance.performance_types import (
    BENCHMARK_NIFTY50_RETURN, BENCHMARK_NIFTY500_RETURN,
    BENCHMARK_SENSEX_RETURN, BENCHMARK_NIFTY_IT_RETURN,
    BENCHMARK_NIFTY_BANK_RETURN, BENCHMARK_NIFTY_MIDCAP_RETURN,
    BENCHMARK_GLOBAL_RETURN, RISK_FREE_RATE_ANNUAL, BenchmarkType,
)


@dataclass(frozen=True)
class Benchmark:
    """A benchmark definition for performance comparison."""

    benchmark_id:       str
    name:               str
    benchmark_type:     BenchmarkType
    expected_return:    float   # annual expected return proxy
    annual_vol_proxy:   float   # annual vol proxy for TE computation
    description:        str     = ""
    currency:           str     = "INR"
    country:            str     = "IN"
    is_default:         bool    = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "benchmark_id":    self.benchmark_id,
            "name":            self.name,
            "benchmark_type":  self.benchmark_type.value,
            "expected_return": round(self.expected_return, 4),
            "annual_vol_proxy":round(self.annual_vol_proxy, 4),
        }


BENCHMARKS: Dict[str, Benchmark] = {
    "nifty50": Benchmark(
        benchmark_id    = "nifty50",
        name            = "NIFTY 50",
        benchmark_type  = BenchmarkType.BROAD_MARKET,
        expected_return = BENCHMARK_NIFTY50_RETURN,
        annual_vol_proxy= 0.16,
        description     = "NSE NIFTY 50 Large Cap Index",
        is_default      = True,
    ),
    "nifty500": Benchmark(
        benchmark_id    = "nifty500",
        name            = "NIFTY 500",
        benchmark_type  = BenchmarkType.BROAD_MARKET,
        expected_return = BENCHMARK_NIFTY500_RETURN,
        annual_vol_proxy= 0.18,
        description     = "NSE NIFTY 500 Broad Market Index",
    ),
    "sensex": Benchmark(
        benchmark_id    = "sensex",
        name            = "BSE SENSEX",
        benchmark_type  = BenchmarkType.BROAD_MARKET,
        expected_return = BENCHMARK_SENSEX_RETURN,
        annual_vol_proxy= 0.16,
        description     = "Bombay Stock Exchange SENSEX 30",
    ),
    "nifty_it": Benchmark(
        benchmark_id    = "nifty_it",
        name            = "NIFTY IT",
        benchmark_type  = BenchmarkType.SECTOR,
        expected_return = BENCHMARK_NIFTY_IT_RETURN,
        annual_vol_proxy= 0.22,
        description     = "NIFTY IT Sector Index",
    ),
    "nifty_bank": Benchmark(
        benchmark_id    = "nifty_bank",
        name            = "NIFTY BANK",
        benchmark_type  = BenchmarkType.SECTOR,
        expected_return = BENCHMARK_NIFTY_BANK_RETURN,
        annual_vol_proxy= 0.20,
        description     = "NIFTY Bank Sector Index",
    ),
    "nifty_midcap": Benchmark(
        benchmark_id    = "nifty_midcap",
        name            = "NIFTY MIDCAP 100",
        benchmark_type  = BenchmarkType.BROAD_MARKET,
        expected_return = BENCHMARK_NIFTY_MIDCAP_RETURN,
        annual_vol_proxy= 0.20,
        description     = "NIFTY MIDCAP 100 Index",
    ),
    "global_equity": Benchmark(
        benchmark_id    = "global_equity",
        name            = "Global Equity",
        benchmark_type  = BenchmarkType.GLOBAL,
        expected_return = BENCHMARK_GLOBAL_RETURN,
        annual_vol_proxy= 0.15,
        description     = "Global equity market proxy",
        currency        = "USD",
        country         = "US",
    ),
    "risk_free": Benchmark(
        benchmark_id    = "risk_free",
        name            = "Risk-Free Rate",
        benchmark_type  = BenchmarkType.RISK_FREE,
        expected_return = RISK_FREE_RATE_ANNUAL,
        annual_vol_proxy= 0.01,
        description     = "Indian 10Y Government Securities",
    ),
}


class BenchmarkRegistry:
    """Registry for built-in and custom benchmarks."""

    def __init__(self) -> None:
        self._store: Dict[str, Benchmark] = dict(BENCHMARKS)

    def get(self, benchmark_id: str) -> Optional[Benchmark]:
        return self._store.get(benchmark_id)

    def get_or_default(self, benchmark_id: str = "nifty50") -> Benchmark:
        return self._store.get(benchmark_id, BENCHMARKS["nifty50"])

    def register(self, benchmark: Benchmark) -> None:
        self._store[benchmark.benchmark_id] = benchmark

    def list_ids(self):
        return list(self._store.keys())

    def all(self) -> Dict[str, Benchmark]:
        return dict(self._store)
