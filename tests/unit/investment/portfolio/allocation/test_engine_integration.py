"""test_engine_integration.py — End-to-end PortfolioAllocationEngine tests."""
import pytest
from iios.investment.portfolio.allocation.portfolio_allocation_engine import (
    AllocationIntegrationRefs,
    PortfolioAllocationEngine,
)
from iios.investment.portfolio.allocation.allocation_plan import AllocationRequest
from iios.investment.portfolio.allocation.allocation_types import (
    AllocationMethod,
    AllocationRunStatus,
    CapitalDistributionStatus,
)


# ---------------------------------------------------------------------------
# Basic lifecycle
# ---------------------------------------------------------------------------

class TestEngineLifecycle:
    def test_start_stop(self):
        engine = PortfolioAllocationEngine()
        assert not engine.is_running
        engine.start()
        assert engine.is_running
        engine.stop()
        assert not engine.is_running

    def test_double_start_safe(self):
        engine = PortfolioAllocationEngine()
        engine.start()
        engine.start()  # should not raise
        assert engine.is_running
        engine.stop()

    def test_allocate_fails_when_not_running(self, multi_slot_blueprint, standard_request):
        engine = PortfolioAllocationEngine()
        result = engine.allocate("pf-1", multi_slot_blueprint, standard_request)
        assert result.failed
        assert "not running" in result.errors[0].lower()


# ---------------------------------------------------------------------------
# Portfolio registration
# ---------------------------------------------------------------------------

class TestPortfolioRegistration:
    def test_register_deregister(self):
        engine = PortfolioAllocationEngine()
        engine.register_portfolio("pf-A")
        assert engine.is_registered("pf-A")
        engine.deregister_portfolio("pf-A")
        assert not engine.is_registered("pf-A")

    def test_auto_register(self, multi_slot_blueprint, standard_request):
        engine = PortfolioAllocationEngine()
        engine.start()
        result = engine.allocate("pf-auto", multi_slot_blueprint, standard_request,
                                 auto_register=True)
        assert engine.is_registered("pf-auto")
        engine.stop()

    def test_portfolio_count(self):
        engine = PortfolioAllocationEngine()
        engine.register_portfolio("pf-1")
        engine.register_portfolio("pf-2")
        assert engine.portfolio_count() == 2


# ---------------------------------------------------------------------------
# Allocation runs
# ---------------------------------------------------------------------------

class TestAllocationRun:
    def test_successful_allocation(self, multi_slot_blueprint, standard_request):
        engine = PortfolioAllocationEngine()
        engine.start()
        result = engine.allocate("pf-1", multi_slot_blueprint, standard_request)
        assert result.succeeded
        assert result.has_plan
        assert result.plan.total_positions > 0
        engine.stop()

    def test_plan_capital_within_total(self, multi_slot_blueprint, standard_request):
        engine = PortfolioAllocationEngine()
        engine.start()
        result = engine.allocate("pf-1", multi_slot_blueprint, standard_request)
        plan   = result.plan
        total  = plan.invested_capital + plan.cash_capital
        assert abs(total - plan.total_capital) < 1.0   # within $1 tolerance
        engine.stop()

    def test_single_slot_blueprint(self, single_slot_blueprint, standard_request):
        engine = PortfolioAllocationEngine()
        engine.start()
        result = engine.allocate("pf-1", single_slot_blueprint, standard_request)
        assert result.succeeded
        assert result.plan.total_positions == 1
        engine.stop()

    def test_equal_method(self, multi_slot_blueprint):
        engine = PortfolioAllocationEngine()
        engine.start()
        req = AllocationRequest(
            portfolio_id    = "pf-eq",
            blueprint_id    = "bp-test",
            total_capital   = 1_000_000.0,
            method          = AllocationMethod.EQUAL,
            max_position_weight = 1.0,
            min_trade_size  = 100.0,
        )
        result = engine.allocate("pf-eq", multi_slot_blueprint, req)
        assert result.succeeded
        engine.stop()

    def test_conviction_method(self, multi_slot_blueprint):
        engine = PortfolioAllocationEngine()
        engine.start()
        req = AllocationRequest(
            portfolio_id  = "pf-cv",
            total_capital = 1_000_000.0,
            method        = AllocationMethod.CONVICTION,
            max_position_weight = 1.0,
            min_trade_size= 100.0,
        )
        result = engine.allocate("pf-cv", multi_slot_blueprint, req)
        assert result.succeeded
        engine.stop()

    def test_risk_adjusted_method(self, multi_slot_blueprint):
        engine = PortfolioAllocationEngine()
        engine.start()
        req = AllocationRequest(
            portfolio_id  = "pf-ra",
            total_capital = 1_000_000.0,
            method        = AllocationMethod.RISK_ADJUSTED,
            max_position_weight = 1.0,
            min_trade_size= 100.0,
        )
        result = engine.allocate("pf-ra", multi_slot_blueprint, req)
        assert result.succeeded
        engine.stop()

    def test_composite_method(self, multi_slot_blueprint):
        engine = PortfolioAllocationEngine()
        engine.start()
        req = AllocationRequest(
            portfolio_id  = "pf-co",
            total_capital = 1_000_000.0,
            method        = AllocationMethod.COMPOSITE,
            max_position_weight = 1.0,
            min_trade_size= 100.0,
        )
        result = engine.allocate("pf-co", multi_slot_blueprint, req)
        assert result.succeeded
        engine.stop()


# ---------------------------------------------------------------------------
# Quality, scoring, validation summaries
# ---------------------------------------------------------------------------

class TestAllocationResultSummaries:
    def test_quality_summary_present(self, multi_slot_blueprint, standard_request):
        engine = PortfolioAllocationEngine()
        engine.start()
        result = engine.allocate("pf-1", multi_slot_blueprint, standard_request)
        qs     = result.quality_summary
        assert "overall_score" in qs
        assert "grade" in qs
        engine.stop()

    def test_validation_summary_present(self, multi_slot_blueprint, standard_request):
        engine = PortfolioAllocationEngine()
        engine.start()
        result = engine.allocate("pf-1", multi_slot_blueprint, standard_request)
        vs     = result.validation_summary
        assert "is_valid" in vs
        assert "failures" in vs
        engine.stop()

    def test_exposure_summary_present(self, multi_slot_blueprint, standard_request):
        engine = PortfolioAllocationEngine()
        engine.start()
        result = engine.allocate("pf-1", multi_slot_blueprint, standard_request)
        assert "checks" in result.exposure_summary
        engine.stop()


# ---------------------------------------------------------------------------
# Query APIs
# ---------------------------------------------------------------------------

class TestEngineQueryApis:
    def test_current_allocation_after_run(self, multi_slot_blueprint, standard_request):
        engine = PortfolioAllocationEngine()
        engine.start()
        engine.allocate("pf-1", multi_slot_blueprint, standard_request)
        snap = engine.current_allocation("pf-1")
        assert snap is not None
        assert snap.portfolio_id == "pf-1"
        engine.stop()

    def test_allocation_history_grows(self, multi_slot_blueprint, standard_request):
        engine = PortfolioAllocationEngine()
        engine.start()
        for _ in range(3):
            engine.allocate("pf-1", multi_slot_blueprint, standard_request)
        hist = engine.allocation_history("pf-1", n=10)
        assert len(hist) == 3
        engine.stop()

    def test_quality_score_after_run(self, multi_slot_blueprint, standard_request):
        engine = PortfolioAllocationEngine()
        engine.start()
        engine.allocate("pf-1", multi_slot_blueprint, standard_request)
        score = engine.quality_score("pf-1")
        assert score is not None
        assert 0.0 <= score.overall <= 1.0
        engine.stop()

    def test_statistics_snapshot(self, multi_slot_blueprint, standard_request):
        engine = PortfolioAllocationEngine()
        engine.start()
        engine.allocate("pf-1", multi_slot_blueprint, standard_request)
        snap = engine.statistics_snapshot()
        assert snap.total_runs == 1
        assert snap.success_runs == 1
        engine.stop()

    def test_health_report(self, multi_slot_blueprint, standard_request):
        engine = PortfolioAllocationEngine()
        engine.start()
        engine.allocate("pf-1", multi_slot_blueprint, standard_request)
        h = engine.health()
        assert h.total_runs == 1
        engine.stop()

    def test_list_portfolios(self):
        engine = PortfolioAllocationEngine()
        engine.register_portfolio("pf-A")
        engine.register_portfolio("pf-B")
        pfs = engine.list_portfolios()
        assert "pf-A" in pfs
        assert "pf-B" in pfs


# ---------------------------------------------------------------------------
# Event callback
# ---------------------------------------------------------------------------

class TestEventCallback:
    def test_callback_fires_on_start(self):
        events = []
        engine = PortfolioAllocationEngine(event_callback=lambda e, d: events.append(e))
        engine.start()
        assert "engine_started" in events
        engine.stop()
        assert "engine_stopped" in events

    def test_callback_fires_on_allocation(self, multi_slot_blueprint, standard_request):
        events = []
        engine = PortfolioAllocationEngine(event_callback=lambda e, d: events.append(e))
        engine.start()
        engine.allocate("pf-1", multi_slot_blueprint, standard_request)
        assert "allocation_completed" in events
        engine.stop()

    def test_callback_fires_on_failure(self, multi_slot_blueprint, standard_request):
        events = []
        engine = PortfolioAllocationEngine(event_callback=lambda e, d: events.append(e))
        # Not started → should emit allocation_failed
        engine.allocate("pf-1", multi_slot_blueprint, standard_request)
        assert "allocation_failed" in events


# ---------------------------------------------------------------------------
# Integrations
# ---------------------------------------------------------------------------

class TestIntegrations:
    def test_configure_integrations(self):
        engine = PortfolioAllocationEngine()
        refs   = AllocationIntegrationRefs(decision_intelligence="mock_di")
        engine.configure_integrations(refs)
        assert engine._integrations is not None
        d = refs.to_dict()
        assert d["decision_intelligence"] is True
        assert d["market_intelligence"] is False


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------

class TestDeterminism:
    def test_same_inputs_same_plan(self, multi_slot_blueprint, standard_request):
        engine = PortfolioAllocationEngine()
        engine.start()
        r1 = engine.allocate("pf-1", multi_slot_blueprint, standard_request)
        r2 = engine.allocate("pf-2", multi_slot_blueprint, standard_request)
        # Different plan_ids (uuid) but same allocations
        assert r1.plan.total_positions == r2.plan.total_positions
        for a1, a2 in zip(
            sorted(r1.plan.allocations, key=lambda a: a.symbol),
            sorted(r2.plan.allocations, key=lambda a: a.symbol),
        ):
            assert a1.symbol == a2.symbol
            assert abs(a1.allocated_capital - a2.allocated_capital) < 0.01
        engine.stop()
