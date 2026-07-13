"""tests/unit/investment/company/integration/test_health_monitoring.py
Tests for health monitoring: engine health, dependency, coverage, and health monitor.
"""
from __future__ import annotations

import time
import pytest

from iios.investment.company.integration.company_state import EngineStatus
from iios.investment.company.integration.coverage_monitor import CoverageMonitor
from iios.investment.company.integration.dependency_monitor import DependencyMonitor
from iios.investment.company.integration.engine_health import (
    EngineHealthRecord, compute_engine_status,
)
from iios.investment.company.integration.health_monitor import HealthMonitor


# ── EngineHealthRecord ────────────────────────────────────────────────────────

class TestEngineHealthRecord:
    def test_initial_state(self):
        rec = EngineHealthRecord(engine_name="financials")
        assert rec.status == EngineStatus.UNAVAILABLE
        assert rec.update_count == 0
        assert rec.is_available is False

    def test_after_update(self):
        rec = EngineHealthRecord(engine_name="financials")
        rec.record_update(latency_ms=15.0)
        assert rec.status == EngineStatus.HEALTHY
        assert rec.update_count == 1
        assert rec.is_available is True
        assert rec.latency_ms == pytest.approx(15.0)

    def test_error_increments(self):
        rec = EngineHealthRecord(engine_name="earnings")
        rec.record_error()
        assert rec.error_count == 1

    def test_staleness_seconds_infinite_if_never_updated(self):
        rec = EngineHealthRecord(engine_name="x")
        assert rec.staleness_seconds == float("inf")

    def test_staleness_seconds_after_update(self):
        rec = EngineHealthRecord(engine_name="x")
        rec.record_update()
        time.sleep(0.05)
        assert rec.staleness_seconds > 0

    def test_to_dict(self):
        rec = EngineHealthRecord(engine_name="financials")
        rec.record_update(latency_ms=12.0)
        d = rec.to_dict()
        assert d["engine_name"] == "financials"
        assert d["status"] == "healthy"
        assert d["latency_ms"] == pytest.approx(12.0)


class TestComputeEngineStatus:
    def test_fresh(self):
        assert compute_engine_status(60.0) == EngineStatus.HEALTHY

    def test_warn(self):
        assert compute_engine_status(5_000.0) == EngineStatus.DEGRADED

    def test_critical(self):
        assert compute_engine_status(100_000.0) == EngineStatus.STALE


# ── DependencyMonitor ─────────────────────────────────────────────────────────

class TestDependencyMonitor:
    def test_initial_all_unavailable(self):
        dm = DependencyMonitor()
        assert "financials" in dm.unavailable_engines()

    def test_record_update_marks_healthy(self):
        dm = DependencyMonitor()
        dm.record_update("financials", latency_ms=10.0)
        assert "financials" in dm.healthy_engines()
        assert "financials" not in dm.unavailable_engines()

    def test_record_error(self):
        dm = DependencyMonitor()
        dm.record_error("earnings")
        rec = dm.get_health("earnings")
        assert rec.error_count == 1

    def test_get_health_unknown(self):
        dm = DependencyMonitor()
        assert dm.get_health("not_an_engine") is None

    def test_all_health_keys(self):
        dm = DependencyMonitor()
        health = dm.all_health()
        assert "financials" in health

    def test_health_fraction_initially_zero(self):
        dm = DependencyMonitor()
        assert dm.overall_health_fraction() == pytest.approx(0.0)

    def test_health_fraction_after_updates(self):
        from iios.investment.company.integration.company_state import KNOWN_ENGINES
        dm = DependencyMonitor()
        for engine in KNOWN_ENGINES:
            dm.record_update(engine)
        assert dm.overall_health_fraction() == pytest.approx(1.0)

    def test_to_dict(self):
        dm = DependencyMonitor()
        d = dm.to_dict()
        assert isinstance(d, dict)
        assert "financials" in d


# ── CoverageMonitor ───────────────────────────────────────────────────────────

class TestCoverageMonitor:
    def test_no_coverage_initially(self):
        cm = CoverageMonitor()
        assert cm.coverage_fraction("X") == pytest.approx(0.0)

    def test_record_engines(self):
        cm = CoverageMonitor()
        cm.record_engines("X", ["financials", "earnings"])
        assert cm.coverage_fraction("X") > 0.0

    def test_missing_engines(self):
        cm = CoverageMonitor()
        cm.record_engines("X", ["financials"])
        missing = cm.missing_engines("X")
        assert "earnings" in missing
        assert "financials" not in missing

    def test_full_coverage(self):
        from iios.investment.company.integration.company_state import SCORED_ENGINES
        cm = CoverageMonitor()
        cm.record_engines("X", list(SCORED_ENGINES))
        assert cm.coverage_fraction("X") == pytest.approx(1.0)

    def test_system_coverage(self):
        cm = CoverageMonitor()
        cm.record_engines("A", ["financials", "earnings"])
        cm.record_engines("B", ["financials"])
        frac = cm.system_coverage_fraction()
        assert 0.0 < frac < 1.0

    def test_poorly_covered_tickers(self):
        cm = CoverageMonitor()
        cm.record_engines("A", ["financials"])          # < 50%
        cm.record_engines("B", ["financials", "earnings",
                                 "business_quality", "valuation",
                                 "growth"])             # ≥ 50%
        poor = cm.poorly_covered_tickers(threshold=0.50)
        assert "A" in poor
        assert "B" not in poor

    def test_eval_count(self):
        cm = CoverageMonitor()
        cm.record_engines("X", ["financials"])
        cm.record_engines("X", ["earnings"])
        assert cm.eval_count("X") == 2

    def test_all_tickers(self):
        cm = CoverageMonitor()
        cm.record_engines("A", ["financials"])
        cm.record_engines("B", ["financials"])
        assert "A" in cm.all_tickers()
        assert "B" in cm.all_tickers()


# ── HealthMonitor ─────────────────────────────────────────────────────────────

class TestHealthMonitor:
    def test_on_engine_update(self):
        hm = HealthMonitor()
        hm.on_engine_update("financials", latency_ms=20.0)
        rec = hm.engine_health("financials")
        assert rec is not None
        assert rec.status == EngineStatus.HEALTHY

    def test_on_engine_error(self):
        hm = HealthMonitor()
        hm.on_engine_error("earnings")
        rec = hm.engine_health("earnings")
        assert rec.error_count == 1

    def test_on_evaluation_coverage(self):
        hm = HealthMonitor()
        hm.on_evaluation("X", ["financials", "earnings"])
        assert hm.ticker_coverage("X") > 0.0

    def test_missing_engines_for(self):
        hm = HealthMonitor()
        hm.on_evaluation("X", ["financials"])
        missing = hm.missing_engines_for("X")
        assert "earnings" in missing

    def test_system_health_fraction_initially_zero(self):
        hm = HealthMonitor()
        assert hm.system_health_fraction() == pytest.approx(0.0)

    def test_system_health_after_updates(self):
        from iios.investment.company.integration.company_state import KNOWN_ENGINES
        hm = HealthMonitor()
        for engine in KNOWN_ENGINES:
            hm.on_engine_update(engine)
        assert hm.system_health_fraction() == pytest.approx(1.0)

    def test_health_report_keys(self):
        hm = HealthMonitor()
        report = hm.health_report()
        assert all(k in report for k in [
            "system_health_fraction", "system_coverage_fraction",
            "healthy_engines", "unavailable_engines", "engine_details",
        ])

    def test_poorly_covered_tickers(self):
        hm = HealthMonitor()
        hm.on_evaluation("X", ["financials"])  # well below 50%
        poor = hm.poorly_covered_tickers()
        assert "X" in poor
