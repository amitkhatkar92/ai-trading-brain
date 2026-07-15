"""Tests for benchmark registry, engine, comparison, statistics."""
import pytest
from iios.investment.portfolio.performance.benchmark_registry import (
    Benchmark, BenchmarkRegistry, BENCHMARKS,
)
from iios.investment.portfolio.performance.benchmark_engine import BenchmarkEngine
from iios.investment.portfolio.performance.benchmark_comparison import (
    compare_to_benchmark, BenchmarkComparison,
)
from iios.investment.portfolio.performance.benchmark_statistics import (
    BenchmarkStatistics,
)
from iios.investment.portfolio.performance.performance_types import BenchmarkType


class TestBenchmarkRegistry:
    def test_all_benchmarks_present(self):
        required = ["nifty50", "nifty500", "sensex", "nifty_it",
                    "nifty_bank", "nifty_midcap", "global_equity", "risk_free"]
        for key in required:
            assert key in BENCHMARKS, f"Missing benchmark: {key}"

    def test_benchmark_dataclass(self):
        b = BENCHMARKS["nifty50"]
        assert b.benchmark_id == "nifty50"
        assert b.expected_return > 0.0
        assert b.annual_vol_proxy > 0.0

    def test_benchmark_type(self):
        assert BENCHMARKS["nifty50"].benchmark_type == BenchmarkType.BROAD_MARKET
        assert BENCHMARKS["nifty_it"].benchmark_type == BenchmarkType.SECTOR
        assert BENCHMARKS["global_equity"].benchmark_type == BenchmarkType.GLOBAL
        assert BENCHMARKS["risk_free"].benchmark_type == BenchmarkType.RISK_FREE

    def test_registry_get(self):
        reg = BenchmarkRegistry()
        b = reg.get("nifty50")
        assert b is not None
        assert b.benchmark_id == "nifty50"

    def test_registry_get_missing_returns_none(self):
        reg = BenchmarkRegistry()
        assert reg.get("nonexistent") is None

    def test_registry_get_or_default(self):
        reg = BenchmarkRegistry()
        b = reg.get_or_default("nonexistent")
        assert b.benchmark_id == "nifty50"

    def test_registry_register_custom(self):
        reg = BenchmarkRegistry()
        custom = Benchmark(
            benchmark_id="custom",
            name="My Custom",
            benchmark_type=BenchmarkType.CUSTOM,
            expected_return=0.10,
            annual_vol_proxy=0.15,
        )
        reg.register(custom)
        assert reg.get("custom") == custom

    def test_registry_list_ids(self):
        reg = BenchmarkRegistry()
        ids = reg.list_ids()
        assert "nifty50" in ids
        assert len(ids) >= 8

    def test_benchmark_to_dict(self):
        b = BENCHMARKS["nifty50"]
        d = b.to_dict()
        assert "benchmark_id" in d
        assert "expected_return" in d


class TestBenchmarkComparison:
    def test_compare_outperforms(self, positions_diverse):
        reg = BenchmarkRegistry()
        bmk = reg.get("nifty50")
        # portfolio return > nifty50 expected return
        comp = compare_to_benchmark(positions_diverse, bmk, 0.20, "p1", 1.0)
        assert comp.outperforms is True
        assert comp.active_return > 0.0

    def test_compare_underperforms(self, positions_diverse):
        reg = BenchmarkRegistry()
        bmk = reg.get("nifty50")
        comp = compare_to_benchmark(positions_diverse, bmk, 0.05, "p1", 1.0)
        assert comp.outperforms is False

    def test_alpha_calculation(self, positions_diverse):
        reg = BenchmarkRegistry()
        bmk = reg.get("nifty50")
        comp = compare_to_benchmark(positions_diverse, bmk, 0.18, "p1", 1.0)
        # alpha = R_p - [R_f + beta * (R_m - R_f)]
        assert isinstance(comp.alpha, float)

    def test_beta_range(self, positions_diverse):
        reg = BenchmarkRegistry()
        bmk = reg.get("nifty50")
        comp = compare_to_benchmark(positions_diverse, bmk, 0.12, "p1", 1.0)
        assert 0.0 <= comp.beta <= 3.0

    def test_tracking_error_positive(self, positions_diverse):
        reg = BenchmarkRegistry()
        bmk = reg.get("nifty50")
        comp = compare_to_benchmark(positions_diverse, bmk, 0.12, "p1", 1.0)
        assert comp.tracking_error > 0.0

    def test_information_ratio_zero_when_no_active(self, positions_diverse):
        reg = BenchmarkRegistry()
        bmk = reg.get("nifty50")
        # If active_return is very small the IR should be near zero
        comp = compare_to_benchmark(positions_diverse, bmk,
                                    bmk.expected_return, "p1", 1.0)
        assert abs(comp.active_return) < 0.001

    def test_to_dict(self, positions_diverse):
        reg = BenchmarkRegistry()
        bmk = reg.get("nifty50")
        comp = compare_to_benchmark(positions_diverse, bmk, 0.15, "p1", 1.0)
        d = comp.to_dict()
        assert "alpha" in d
        assert "information_ratio" in d


class TestBenchmarkEngine:
    def test_run_primary(self, positions_diverse):
        engine = BenchmarkEngine()
        comp = engine.run_primary(positions_diverse, 0.15, "p1", "nifty50", 1.0)
        assert isinstance(comp, BenchmarkComparison)
        assert comp.benchmark_id == "nifty50"

    def test_run_all(self, positions_diverse):
        engine = BenchmarkEngine()
        report = engine.run_all(positions_diverse, 0.15, "p1",
                                ["nifty50", "sensex"], 1.0)
        assert len(report.comparisons) == 2
        assert report.primary is not None
        assert report.best_vs in ["nifty50", "sensex"]

    def test_report_to_dict(self, positions_diverse):
        engine = BenchmarkEngine()
        report = engine.run_all(positions_diverse, 0.15, "p1",
                                ["nifty50", "nifty500"], 1.0)
        d = report.to_dict()
        assert "primary" in d
        assert "comparisons" in d


class TestBenchmarkStatistics:
    def test_empty_snapshot(self):
        stats = BenchmarkStatistics()
        snap = stats.snapshot()
        assert snap.total_comparisons == 0

    def test_record_and_snapshot(self, positions_diverse):
        engine = BenchmarkEngine()
        stats = BenchmarkStatistics()
        for _ in range(5):
            comp = engine.run_primary(positions_diverse, 0.15, "p1")
            stats.record(comp)
        snap = stats.snapshot()
        assert snap.total_comparisons == 5
        assert 0.0 <= snap.outperformance_rate <= 1.0

    def test_snapshot_to_dict(self, positions_diverse):
        engine = BenchmarkEngine()
        stats = BenchmarkStatistics()
        comp = engine.run_primary(positions_diverse, 0.15, "p1")
        stats.record(comp)
        d = stats.snapshot().to_dict()
        assert "avg_alpha" in d

    def test_max_comparisons_trimming(self, positions_diverse):
        engine = BenchmarkEngine()
        stats = BenchmarkStatistics(max_comparisons=3)
        for _ in range(10):
            comp = engine.run_primary(positions_diverse, 0.15, "p1")
            stats.record(comp)
        snap = stats.snapshot()
        assert snap.total_comparisons == 3
