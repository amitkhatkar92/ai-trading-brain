"""test_engine_integration.py — End-to-end PortfolioOptimizationEngine tests."""
import pytest

from iios.investment.portfolio.optimization.portfolio_optimization_engine import (
    PortfolioOptimizationEngine,
    OptimizationIntegrationRefs,
)
from iios.investment.portfolio.optimization.optimization_plan import (
    OptimizationObjective,
    OptimizationRequest,
)
from iios.investment.portfolio.optimization.optimization_policy import (
    BALANCED_OPTIMIZATION_POLICY,
    CONSERVATIVE_OPTIMIZATION_POLICY,
    AGGRESSIVE_OPTIMIZATION_POLICY,
    RISK_PARITY_POLICY,
)
from iios.investment.portfolio.optimization.optimization_types import (
    ObjectiveType,
    OptimizationMethod,
    OptimizationRunStatus,
)


# ---------------------------------------------------------------------------
# Lifecycle tests
# ---------------------------------------------------------------------------

class TestEngineLifecycle:
    def test_start_stop(self):
        e = PortfolioOptimizationEngine()
        assert not e.is_running
        e.start()
        assert e.is_running
        e.stop()
        assert not e.is_running

    def test_double_start_safe(self):
        e = PortfolioOptimizationEngine()
        e.start()
        e.start()   # should not raise
        assert e.is_running
        e.stop()

    def test_health_available_without_runs(self):
        e = PortfolioOptimizationEngine()
        e.start()
        rpt = e.health()
        assert rpt.is_healthy
        e.stop()

    def test_stats_empty_on_start(self):
        e = PortfolioOptimizationEngine()
        e.start()
        snap = e.statistics_snapshot()
        assert snap.total_runs == 0
        e.stop()


# ---------------------------------------------------------------------------
# Portfolio registration
# ---------------------------------------------------------------------------

class TestPortfolioRegistration:
    def test_register_and_check(self):
        e = PortfolioOptimizationEngine()
        e.register_portfolio("P1")
        assert e.is_registered("P1")
        assert not e.is_registered("P_NOPE")

    def test_deregister(self):
        e = PortfolioOptimizationEngine()
        e.register_portfolio("P1")
        e.deregister_portfolio("P1")
        assert not e.is_registered("P1")

    def test_list_portfolios(self):
        e = PortfolioOptimizationEngine()
        e.register_portfolio("A")
        e.register_portfolio("B")
        pids = e.list_portfolios()
        assert "A" in pids and "B" in pids

    def test_portfolio_count(self):
        e = PortfolioOptimizationEngine()
        assert e.portfolio_count() == 0
        e.register_portfolio("X")
        assert e.portfolio_count() == 1


# ---------------------------------------------------------------------------
# Optimization: success path
# ---------------------------------------------------------------------------

class TestOptimizationSuccessPath:
    @pytest.fixture(autouse=True)
    def engine(self):
        self.e = PortfolioOptimizationEngine()
        self.e.start()
        yield
        self.e.stop()

    def test_basic_optimization_succeeds(self, allocation_plan_5, standard_request):
        result = self.e.optimize("P1", allocation_plan_5, standard_request)
        assert result.succeeded
        assert result.has_plan

    def test_plan_has_correct_positions(self, allocation_plan_5, standard_request):
        result = self.e.optimize("P1", allocation_plan_5, standard_request)
        assert result.plan.total_positions == len(allocation_plan_5.allocations)

    def test_weights_sum_to_one(self, allocation_plan_5, standard_request):
        result = self.e.optimize("P1", allocation_plan_5, standard_request)
        total  = sum(p.optimized_weight for p in result.plan.positions)
        assert abs(total - 1.0) < 1e-3

    def test_all_weights_non_negative(self, allocation_plan_5, standard_request):
        result = self.e.optimize("P1", allocation_plan_5, standard_request)
        for p in result.plan.positions:
            assert p.optimized_weight >= -1e-6

    def test_max_weight_respected(self, allocation_plan_5):
        req = OptimizationRequest(
            portfolio_id    = "P2",
            total_capital   = 1_000_000.0,
            method          = OptimizationMethod.EQUAL_WEIGHT,
            max_weight      = 0.25,
        )
        result = self.e.optimize("P2", allocation_plan_5, req)
        for p in result.plan.positions:
            assert p.optimized_weight <= 0.25 + 1e-4

    def test_auto_register(self, allocation_plan_5, standard_request):
        # Portfolio not pre-registered
        assert not self.e.is_registered("AUTO")
        result = self.e.optimize("AUTO", allocation_plan_5, standard_request, auto_register=True)
        assert result.succeeded
        assert self.e.is_registered("AUTO")

    def test_quality_summary_present(self, allocation_plan_5, standard_request):
        result = self.e.optimize("P1", allocation_plan_5, standard_request)
        assert "overall_score" in result.quality_summary
        assert "grade" in result.quality_summary

    def test_validation_summary_present(self, allocation_plan_5, standard_request):
        result = self.e.optimize("P1", allocation_plan_5, standard_request)
        assert "is_valid" in result.validation_summary

    def test_constraint_summary_present(self, allocation_plan_5, standard_request):
        result = self.e.optimize("P1", allocation_plan_5, standard_request)
        assert "is_feasible" in result.constraint_summary


# ---------------------------------------------------------------------------
# Optimization: failure path
# ---------------------------------------------------------------------------

class TestOptimizationFailurePath:
    @pytest.fixture(autouse=True)
    def engine(self):
        self.e = PortfolioOptimizationEngine()
        self.e.start()
        yield
        self.e.stop()

    def test_engine_not_running_fails(self, allocation_plan_5, standard_request):
        stopped = PortfolioOptimizationEngine()
        # Do NOT call start()
        result = stopped.optimize("P1", allocation_plan_5, standard_request)
        assert result.failed

    def test_empty_plan_fails(self, standard_request):
        class _EmptyPlan:
            allocations    = []
            total_capital  = 1_000_000.0
            plan_id        = "empty"
            blueprint_id   = ""
            portfolio_id   = "P_EMPTY"
            version        = 1

        result = self.e.optimize("P_EMPTY", _EmptyPlan(), standard_request)
        assert result.failed

    def test_zero_capital_fails(self):
        class _ZeroPlan:
            allocations   = []
            total_capital = 0.0
            plan_id       = "zero"
            blueprint_id  = ""
            portfolio_id  = "P3"
            version       = 1

        req = OptimizationRequest(
            portfolio_id  = "P3",
            total_capital = 0.0,
        )
        result = self.e.optimize("P3", _ZeroPlan(), req)
        assert result.failed


# ---------------------------------------------------------------------------
# History and query APIs
# ---------------------------------------------------------------------------

class TestQueryAPIs:
    @pytest.fixture(autouse=True)
    def engine(self):
        self.e = PortfolioOptimizationEngine()
        self.e.start()
        yield
        self.e.stop()

    def test_current_optimization_none_before_run(self):
        self.e.register_portfolio("HIST")
        assert self.e.current_optimization("HIST") is None

    def test_current_optimization_after_run(self, allocation_plan_5, standard_request):
        self.e.optimize("H1", allocation_plan_5, standard_request)
        snap = self.e.current_optimization("H1")
        assert snap is not None

    def test_history_grows(self, allocation_plan_5, standard_request):
        for _ in range(3):
            self.e.optimize("H2", allocation_plan_5, standard_request)
        history = self.e.optimization_history("H2", n=10)
        assert len(history) == 3

    def test_quality_score_after_run(self, allocation_plan_5, standard_request):
        self.e.optimize("H3", allocation_plan_5, standard_request)
        score = self.e.quality_score("H3")
        assert score is not None
        assert 0.0 <= score.overall <= 1.0

    def test_stats_accumulate(self, allocation_plan_5, standard_request):
        for _ in range(4):
            self.e.optimize("STATS", allocation_plan_5, standard_request)
        snap = self.e.statistics_snapshot()
        assert snap.total_runs >= 4


# ---------------------------------------------------------------------------
# All optimization methods
# ---------------------------------------------------------------------------

class TestAllMethods:
    @pytest.fixture(autouse=True)
    def engine(self):
        self.e = PortfolioOptimizationEngine()
        self.e.start()
        yield
        self.e.stop()

    @pytest.mark.parametrize("method", [
        OptimizationMethod.EQUAL_WEIGHT,
        OptimizationMethod.MINIMUM_VARIANCE,
        OptimizationMethod.MAXIMUM_SHARPE,
        OptimizationMethod.MAXIMUM_SORTINO,
        OptimizationMethod.MAXIMUM_CALMAR,
        OptimizationMethod.RISK_PARITY,
        OptimizationMethod.EQUAL_RISK_CONTRIBUTION,
        OptimizationMethod.MAXIMUM_DIVERSIFICATION,
        OptimizationMethod.BLACK_LITTERMAN,
        OptimizationMethod.HIERARCHICAL_RISK_PARITY,
        OptimizationMethod.MEAN_VARIANCE,
        OptimizationMethod.MAXIMUM_UTILITY,
        OptimizationMethod.MINIMUM_TURNOVER,
    ])
    def test_method_produces_valid_result(self, allocation_plan_5, method):
        req = OptimizationRequest(
            portfolio_id  = f"P_{method.value}",
            total_capital = 1_000_000.0,
            method        = method,
            max_weight    = 0.50,
        )
        result = self.e.optimize(f"P_{method.value}", allocation_plan_5, req)
        assert result.succeeded, f"{method.value} failed: {result.errors}"
        assert result.plan.total_positions > 0


# ---------------------------------------------------------------------------
# Policies
# ---------------------------------------------------------------------------

class TestPolicies:
    def test_conservative_policy(self, allocation_plan_5, standard_request):
        e = PortfolioOptimizationEngine(policy=CONSERVATIVE_OPTIMIZATION_POLICY)
        e.start()
        result = e.optimize("CP", allocation_plan_5, standard_request)
        assert result.succeeded
        e.stop()

    def test_aggressive_policy(self, allocation_plan_5, standard_request):
        e = PortfolioOptimizationEngine(policy=AGGRESSIVE_OPTIMIZATION_POLICY)
        e.start()
        result = e.optimize("AP", allocation_plan_5, standard_request)
        assert result.succeeded
        e.stop()

    def test_risk_parity_policy(self, allocation_plan_5):
        e = PortfolioOptimizationEngine(policy=RISK_PARITY_POLICY)
        e.start()
        req = OptimizationRequest(
            portfolio_id  = "RP",
            total_capital = 1_000_000.0,
            method        = OptimizationMethod.RISK_PARITY,
        )
        result = e.optimize("RP", allocation_plan_5, req)
        assert result.succeeded
        e.stop()


# ---------------------------------------------------------------------------
# Events
# ---------------------------------------------------------------------------

class TestEventCallback:
    def test_events_emitted(self, allocation_plan_5, standard_request):
        events = []
        e = PortfolioOptimizationEngine(event_callback=lambda ev, d: events.append(ev))
        e.start()
        e.optimize("EV1", allocation_plan_5, standard_request)
        e.stop()
        assert "engine_started" in events
        assert "optimization_completed" in events
        assert "engine_stopped" in events

    def test_failed_event_on_failure(self, standard_request):
        events = []
        e = PortfolioOptimizationEngine(event_callback=lambda ev, d: events.append(ev))
        e.start()

        class _Bad:
            allocations = []
            total_capital = 1_000_000.0
            plan_id = ""
            blueprint_id = ""
            portfolio_id = ""
            version = 1

        e.optimize("BAD", _Bad(), standard_request)
        assert "optimization_failed" in events
        e.stop()


# ---------------------------------------------------------------------------
# Integration refs
# ---------------------------------------------------------------------------

class TestIntegrationRefs:
    def test_configure_integrations(self):
        e    = PortfolioOptimizationEngine()
        refs = OptimizationIntegrationRefs(decision_intelligence=object())
        e.configure_integrations(refs)
        assert e._integrations is refs

    def test_to_dict_has_all_keys(self):
        refs = OptimizationIntegrationRefs()
        d = refs.to_dict()
        assert "decision_intelligence" in d
        assert "allocation_engine" in d
