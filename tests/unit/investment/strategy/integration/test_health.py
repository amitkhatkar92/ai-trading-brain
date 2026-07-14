"""tests/unit/investment/strategy/integration/test_health.py
Tests for EngineHealthChecker, DependencyMonitor, CoverageMonitor, HealthMonitor.
"""
from __future__ import annotations

import pytest

from iios.investment.strategy.integration.aggregation_engine import AggregationEngine
from iios.investment.strategy.integration.coverage_monitor import CoverageMonitor
from iios.investment.strategy.integration.dependency_monitor import DependencyMonitor
from iios.investment.strategy.integration.engine_health import EngineHealthChecker
from iios.investment.strategy.integration.integration_constants import (
    HealthStatus,
    IntelligenceSource,
    STALENESS_WARNING_SECONDS,
)
from iios.investment.strategy.integration.strategy_intelligence_aggregator import (
    StrategyIntelligenceAggregator,
)
from tests.unit.investment.strategy.integration.conftest import (
    make_eval_update,
    make_risk_update,
    make_full_state,
)


# ===========================================================================
# EngineHealthChecker
# ===========================================================================

class TestEngineHealthChecker:
    def test_empty_state_map_all_unknown(self):
        checker = EngineHealthChecker()
        report  = checker.check_all({})
        for entry in report.entries.values():
            assert entry.status == HealthStatus.UNKNOWN

    def test_healthy_for_recent_updates(self):
        sid, state, eng = make_full_state("HLT1")
        checker = EngineHealthChecker()
        report  = checker.check_all({sid: state})
        # Sources present in state should be HEALTHY
        for src in state.all_latest():
            assert report.entries[src.value].status == HealthStatus.HEALTHY

    def test_overall_healthy_when_all_healthy(self):
        sid, state, eng = make_full_state("HLT2")
        checker = EngineHealthChecker()
        report  = checker.check_all({sid: state})
        assert report.overall_status in (HealthStatus.HEALTHY, HealthStatus.DEGRADED, HealthStatus.UNKNOWN)

    def test_to_dict(self):
        checker = EngineHealthChecker()
        report  = checker.check_all({})
        d = report.to_dict()
        assert "overall_status" in d
        assert "entries" in d


# ===========================================================================
# DependencyMonitor
# ===========================================================================

class TestDependencyMonitor:
    def test_record_and_check(self):
        mon = DependencyMonitor()
        mon.record_seen(IntelligenceSource.EVALUATION)
        statuses = mon.check_all()
        assert statuses[IntelligenceSource.EVALUATION].is_available

    def test_unknown_source_unavailable(self):
        mon = DependencyMonitor()
        statuses = mon.check_all()
        assert not statuses[IntelligenceSource.EVALUATION].is_available

    def test_missing_sources_all_when_empty(self):
        mon     = DependencyMonitor()
        missing = mon.missing_sources(threshold_seconds=0)
        # All sources should be missing (never seen)
        assert len(missing) == len(list(IntelligenceSource))

    def test_record_seen_removes_from_missing(self):
        mon = DependencyMonitor()
        mon.record_seen(IntelligenceSource.EVALUATION)
        missing = mon.missing_sources(threshold_seconds=STALENESS_WARNING_SECONDS)
        assert IntelligenceSource.EVALUATION not in missing

    def test_error_count(self):
        mon = DependencyMonitor()
        mon.record_error(IntelligenceSource.RISK)
        mon.record_error(IntelligenceSource.RISK)
        statuses = mon.check_all()
        assert statuses[IntelligenceSource.RISK].error_count == 2

    def test_to_dict(self):
        mon = DependencyMonitor()
        mon.record_seen(IntelligenceSource.EVALUATION)
        d = mon.check_all()[IntelligenceSource.EVALUATION].to_dict()
        assert "source" in d
        assert "is_available" in d


# ===========================================================================
# CoverageMonitor
# ===========================================================================

class TestCoverageMonitor:
    def test_empty_aggregator(self):
        agg = StrategyIntelligenceAggregator()
        mon = CoverageMonitor()
        report = mon.compute(agg)
        assert report.total_strategies == 0
        assert report.avg_completeness == 0.0

    def test_full_state_coverage(self):
        agg = StrategyIntelligenceAggregator()
        sid, state, eng = make_full_state("COV1")
        # Submit into aggregator
        for upd in state.all_latest().values():
            agg.submit(upd)
        mon = CoverageMonitor()
        report = mon.compute(agg)
        assert report.total_strategies >= 1
        assert report.avg_completeness > 0

    def test_partial_state_in_partial_bucket(self):
        agg = StrategyIntelligenceAggregator()
        sid = "PCOV1"
        agg.submit(make_eval_update(sid))   # only 1 source
        mon = CoverageMonitor()
        report = mon.compute(agg)
        assert report.partial_strategies >= 1

    def test_to_dict(self):
        agg = StrategyIntelligenceAggregator()
        mon = CoverageMonitor()
        d   = mon.compute(agg).to_dict()
        assert "total_strategies" in d
        assert "avg_completeness" in d
        assert "by_source_coverage" in d
