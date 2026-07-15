"""tests/unit/investment/portfolio/integration/test_integration_engine.py

Integration tests for PortfolioIntelligenceIntegrationEngine.
"""
from __future__ import annotations

import pytest

from iios.investment.portfolio.integration.integration_types import (
    AggregationStatus, EngineId, REQUIRED_ENGINES, SnapshotStatus,
)
from iios.investment.portfolio.integration.portfolio_intelligence_integration_engine import (
    PortfolioIntelligenceIntegrationEngine,
)
from iios.investment.portfolio.integration.portfolio_snapshot import (
    PortfolioIntelligenceSnapshot,
)


class TestEngineLifecycle:
    def test_start_stop(self, engine):
        assert engine.is_running
        engine.stop()
        assert not engine.is_running

    def test_version(self, engine):
        assert engine.VERSION == "1.0.0"


class TestReceiveAndIntegrate:
    def test_receive_contribution(self, engine):
        c = engine.receive("P-1", EngineId.RISK, {"risk_score": 0.5})
        assert c.engine_id == EngineId.RISK
        assert c.portfolio_id == "P-1"

    def test_integrate_returns_snapshot(self, loaded_engine):
        snap = loaded_engine.integrate("P-HEALTH")
        assert isinstance(snap, PortfolioIntelligenceSnapshot)

    def test_snapshot_portfolio_id(self, loaded_engine):
        snap = loaded_engine.integrate("P-HEALTH")
        assert snap.portfolio_id == "P-HEALTH"

    def test_full_contribution_complete_status(self, loaded_engine):
        snap = loaded_engine.integrate("P-HEALTH")
        assert snap.aggregation_status == AggregationStatus.COMPLETE

    def test_snapshot_published_when_publish_true(self, loaded_engine):
        snap = loaded_engine.integrate("P-HEALTH", publish=True)
        assert snap.status == SnapshotStatus.PUBLISHED
        assert snap.published_at is not None

    def test_snapshot_not_published_when_false(self, loaded_engine):
        snap = loaded_engine.integrate("P-HEALTH", publish=False)
        # Status stays VALIDATED (not PUBLISHED)
        assert snap.status in (SnapshotStatus.VALIDATED, SnapshotStatus.DRAFT)

    def test_partial_integration_not_ready(self, engine):
        engine.receive("P-PART", EngineId.RISK, {"v": 1})
        snap = engine.integrate("P-PART")
        assert not snap.is_ready

    def test_healthy_portfolio_is_ready(self, loaded_engine):
        snap = loaded_engine.integrate("P-HEALTH")
        assert snap.is_ready

    def test_snapshot_is_frozen(self, loaded_engine):
        snap = loaded_engine.integrate("P-HEALTH")
        with pytest.raises((AttributeError, TypeError)):
            snap.quality_score = 0.0  # type: ignore


class TestSnapshotFields:
    def test_construction_fields_populated(self, loaded_engine):
        snap = loaded_engine.integrate("P-HEALTH")
        assert snap.n_positions == 20
        assert snap.construction_quality == 0.82

    def test_allocation_fields_populated(self, loaded_engine):
        snap = loaded_engine.integrate("P-HEALTH")
        assert snap.equity_weight == 0.60
        assert snap.bond_weight   == 0.25

    def test_risk_fields_populated(self, loaded_engine):
        snap = loaded_engine.integrate("P-HEALTH")
        assert snap.risk_budget_utilization == 0.55
        assert snap.is_risk_within_budget is True

    def test_performance_fields_populated(self, loaded_engine):
        snap = loaded_engine.integrate("P-HEALTH")
        assert snap.sharpe_ratio == 0.90

    def test_recommendation_fields_populated(self, loaded_engine):
        snap = loaded_engine.integrate("P-HEALTH")
        assert snap.primary_action == "no_action"


class TestQualityAndConsistency:
    def test_quality_score_range(self, loaded_engine):
        snap = loaded_engine.integrate("P-HEALTH")
        assert 0.0 <= snap.quality_score <= 1.0

    def test_consistency_score_range(self, loaded_engine):
        snap = loaded_engine.integrate("P-HEALTH")
        assert 0.0 <= snap.consistency_score <= 1.0

    def test_healthy_is_consistent(self, loaded_engine):
        snap = loaded_engine.integrate("P-HEALTH")
        assert snap.is_consistent

    def test_conflicted_has_conflicts(self, engine, conflicted_contributions):
        for eid, data in conflicted_contributions.items():
            engine.receive("P-CONF", eid, data)
        snap = engine.integrate("P-CONF")
        assert snap.n_conflicts >= 1

    def test_conflicted_has_unresolved(self, engine, conflicted_contributions):
        for eid, data in conflicted_contributions.items():
            engine.receive("P-CONF2", eid, data)
        snap = engine.integrate("P-CONF2")
        # Critical conflict (aggressive+high risk) → escalated
        assert snap.n_unresolved_conflicts >= 1


class TestQueryAPIs:
    def test_current_snapshot(self, loaded_engine):
        loaded_engine.integrate("P-HEALTH")
        snap = loaded_engine.current_snapshot("P-HEALTH")
        assert snap is not None
        assert snap.portfolio_id == "P-HEALTH"

    def test_snapshot_history(self, loaded_engine):
        for _ in range(3):
            loaded_engine.integrate("P-HEALTH")
        history = loaded_engine.snapshot_history("P-HEALTH", n=5)
        assert len(history) >= 1

    def test_portfolio_state(self, loaded_engine):
        loaded_engine.integrate("P-HEALTH")
        state = loaded_engine.portfolio_state("P-HEALTH")
        assert state is not None
        assert state.is_ready

    def test_portfolio_summary(self, loaded_engine):
        loaded_engine.integrate("P-HEALTH")
        summary = loaded_engine.portfolio_summary("P-HEALTH")
        assert summary is not None
        assert len(summary.headline) > 0

    def test_validation_report(self, loaded_engine):
        report = loaded_engine.validation_report("P-HEALTH")
        assert report is not None
        assert hasattr(report, "is_consistent")

    def test_conflict_report(self, loaded_engine):
        report = loaded_engine.conflict_report("P-HEALTH")
        assert report is not None
        assert hasattr(report, "n_detected")

    def test_quality_report(self, loaded_engine):
        loaded_engine.integrate("P-HEALTH")
        report = loaded_engine.quality_report("P-HEALTH")
        assert report is not None
        assert 0.0 <= report.overall_score <= 1.0

    def test_coverage_report(self, loaded_engine):
        report = loaded_engine.coverage_report("P-HEALTH")
        assert report.is_full_coverage

    def test_health_report(self, loaded_engine):
        loaded_engine.integrate("P-HEALTH")
        report = loaded_engine.health()
        assert report is not None
        assert report.total_integrations >= 1

    def test_statistics(self, loaded_engine):
        loaded_engine.integrate("P-HEALTH")
        stats = loaded_engine.statistics()
        assert stats.total_runs >= 1

    def test_all_portfolio_ids(self, loaded_engine):
        loaded_engine.integrate("P-HEALTH")
        pids = loaded_engine.all_portfolio_ids()
        assert "P-HEALTH" in pids

    def test_search_snapshots(self, loaded_engine):
        loaded_engine.integrate("P-HEALTH")
        results = loaded_engine.search_snapshots(portfolio_id="P-HEALTH", min_quality=0.0)
        assert len(results) >= 1

    def test_quality_trend(self, loaded_engine):
        for _ in range(3):
            loaded_engine.integrate("P-HEALTH")
        trend = loaded_engine.quality_trend("P-HEALTH")
        assert isinstance(trend, list)

    def test_no_snapshot_returns_none(self, engine):
        assert engine.current_snapshot("NONEXISTENT") is None
        assert engine.portfolio_state("NONEXISTENT") is None
        assert engine.portfolio_summary("NONEXISTENT") is None
        assert engine.quality_report("NONEXISTENT") is None


class TestEventCallback:
    def test_callback_invoked(self, healthy_contributions):
        events = []
        def callback(event_type, data):
            events.append((event_type, data))
        e = PortfolioIntelligenceIntegrationEngine(event_callback=callback)
        e.start()
        for eid, data in healthy_contributions.items():
            e.receive("P-CB", eid, data)
        e.integrate("P-CB")
        assert len(events) >= 1
        assert events[0][0] == "snapshot_published"

    def test_callback_receives_snapshot(self, healthy_contributions):
        snaps = []
        def callback(event_type, data):
            if event_type == "snapshot_published":
                snaps.append(data)
        e = PortfolioIntelligenceIntegrationEngine(event_callback=callback)
        e.start()
        for eid, data in healthy_contributions.items():
            e.receive("P-CB2", eid, data)
        e.integrate("P-CB2")
        assert all(isinstance(s, PortfolioIntelligenceSnapshot) for s in snaps)


class TestDeterminism:
    def test_same_inputs_same_outputs(
        self, healthy_contributions
    ):
        """Same contributions should produce same field values."""
        e1 = PortfolioIntelligenceIntegrationEngine()
        e1.start()
        for eid, data in healthy_contributions.items():
            e1.receive("P-D1", eid, data)
        snap1 = e1.integrate("P-D1", publish=False)

        e2 = PortfolioIntelligenceIntegrationEngine()
        e2.start()
        for eid, data in healthy_contributions.items():
            e2.receive("P-D2", eid, data)
        snap2 = e2.integrate("P-D2", publish=False)

        assert snap1.equity_weight == snap2.equity_weight
        assert snap1.sharpe_ratio  == snap2.sharpe_ratio
        assert snap1.primary_action == snap2.primary_action
        assert snap1.n_conflicts    == snap2.n_conflicts
