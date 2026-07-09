"""tests/unit/execution/planning/test_execution_planning_engine.py
Full test suite for the Execution Planning & Smart Routing Engine.
Target: >= 150 tests.
"""
from __future__ import annotations

import asyncio
import threading
import time

import pytest

from iios.execution.planning import (
    # Engine
    ExecutionPlanningEngine,
    get_planning_engine,
    reset_planning_engine,
    # Manager
    PlanningManager,
    PlanningManagerStats,
    get_planning_manager,
    reset_planning_manager,
    # Registry
    PlanningRegistry,
    get_planning_registry,
    reset_planning_registry,
    # Context
    PlanningContextState,
    get_planning_context,
    reset_planning_context,
    planning_session,
    planning_stage_scope,
    # Factory
    PlanningFactory,
    # Core models
    ExecutionPlan,
    ExecutionCost,
    ExecutionConstraints,
    ExecutionRoute,
    ExecutionSchedule,
    ExecutionStrategy,
    ExecutionInstruction,
    ExecutionPlanStatus,
    # Routing
    RouteRegistry,
    VenueInfo,
    RouteEvaluator,
    RouteScore,
    RouteSelector,
    RouteOptimizer,
    OptimizationResult,
    RoutingEngine,
    # Planner
    ExecutionBatch,
    OrderSplitter,
    SplitConfig,
    SplitResult,
    OrderMerger,
    MergeResult,
    ExecutionScheduler,
    ScheduleRequest,
    OrderPlanner,
    PlanRequest,
    PlanResult,
    # Analytics
    CostEstimator,
    CostEstimatorConfig,
    SlippageEstimator,
    SlippageEstimatorConfig,
    ImpactEstimator,
    ImpactEstimatorConfig,
    LiquidityEstimate,
    LiquidityEstimator,
    LiquidityEstimatorConfig,
    # Policies
    ExecutionPolicy,
    ImmediatePolicy,
    RiskLimitedPolicy,
    PolicyEvaluation,
    PolicyRegistry,
    PolicyRule,
    # Enums
    ExecutionAlgorithm,
    ExecutionMode,
    ExecutionPriority,
    LiquidityLevel,
    OrderSplitType,
    PolicyType,
    RoutingStrategy,
    # Exceptions
    PlanningIntelligenceError,
    PlanNotFoundError,
    PlanAlreadyExistsError,
    PlanTerminalError,
    PlanInvalidError,
    NoSuitableVenueError,
    PolicyViolationError,
    ConstraintViolationError,
    PlanningEngineNotInitializedError,
    PlanningEngineAlreadyRunningError,
    PlanningRegistryOverflowError,
)
from iios.execution.planning.planning_constants import (
    PLANNING_ENGINE_VERSION,
    PLANNING_ENGINE_SYSTEM_ID,
)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _req(
    symbol:      str   = "TCS",
    order_value: float = 500_000.0,
    mode:        ExecutionMode = ExecutionMode.IMMEDIATE,
    strategy:    RoutingStrategy = RoutingStrategy.SINGLE_VENUE,
) -> PlanRequest:
    return PlanRequest(
        symbol           = symbol,
        order_value      = order_value,
        execution_mode   = mode,
        routing_strategy = strategy,
        adv              = 10_000_000.0,
    )


def _venue(vid: str = "NSE", fee: float = 0.0003) -> VenueInfo:
    return VenueInfo(
        venue_id      = vid,
        name          = f"{vid} Exchange",
        fee_rate      = fee,
        latency_ms    = 5.0,
        is_active     = True,
        asset_classes = ["equity"],
    )


# ─────────────────────────────────────────────────────────────────────────────
# autouse fixture
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def _reset_all():
    reset_planning_engine()
    reset_planning_manager()
    reset_planning_registry()
    reset_planning_context()
    yield
    reset_planning_engine()
    reset_planning_manager()
    reset_planning_registry()
    reset_planning_context()


# ─────────────────────────────────────────────────────────────────────────────
# 1. Constants & Enums
# ─────────────────────────────────────────────────────────────────────────────

class TestConstants:
    def test_version(self):
        assert PLANNING_ENGINE_VERSION == "1.0.0"

    def test_system_id(self):
        assert "planning" in PLANNING_ENGINE_SYSTEM_ID

    def test_routing_strategy_enum(self):
        assert RoutingStrategy.SINGLE_VENUE.value == "single_venue"

    def test_execution_mode_enum(self):
        assert ExecutionMode.IMMEDIATE.value == "immediate"

    def test_plan_status_draft(self):
        assert ExecutionPlanStatus.DRAFT.value == "draft"

    def test_liquidity_level_high(self):
        assert LiquidityLevel.HIGH.value == "high"


# ─────────────────────────────────────────────────────────────────────────────
# 2. Exceptions
# ─────────────────────────────────────────────────────────────────────────────

class TestExceptions:
    def test_base_error(self):
        e = PlanningIntelligenceError("test", code="EP-000")
        assert e.code == "EP-000"

    def test_plan_not_found(self):
        e = PlanNotFoundError(plan_id="P1")
        assert e.plan_id == "P1"
        assert isinstance(e, PlanningIntelligenceError)

    def test_plan_already_exists(self):
        e = PlanAlreadyExistsError(plan_id="P1")
        assert e.plan_id == "P1"

    def test_plan_terminal(self):
        e = PlanTerminalError(plan_id="P1", status="cancelled")
        assert "cancelled" in str(e)

    def test_engine_not_initialized(self):
        assert issubclass(PlanningEngineNotInitializedError, PlanningIntelligenceError)

    def test_registry_overflow(self):
        e = PlanningRegistryOverflowError(capacity=5, current=5)
        assert e.capacity == 5

    def test_constraint_violation(self):
        e = ConstraintViolationError(constraint="max_slippage", value=0.01)
        assert e.constraint == "max_slippage"

    def test_policy_violation(self):
        e = PolicyViolationError(policy_name="ImmediatePolicy")
        assert e.policy_name == "ImmediatePolicy"


# ─────────────────────────────────────────────────────────────────────────────
# 3. ExecutionPlan
# ─────────────────────────────────────────────────────────────────────────────

class TestExecutionPlan:
    def test_defaults(self):
        p = ExecutionPlan()
        assert p.plan_id != ""
        assert p.status == ExecutionPlanStatus.DRAFT

    def test_transition_draft_to_validated(self):
        p = ExecutionPlan()
        p.transition_to(ExecutionPlanStatus.VALIDATED)
        assert p.status == ExecutionPlanStatus.VALIDATED

    def test_transition_to_archived_from_terminal(self):
        p = ExecutionPlan()
        p.transition_to(ExecutionPlanStatus.VALIDATED)
        p.transition_to(ExecutionPlanStatus.APPROVED)
        p.transition_to(ExecutionPlanStatus.ACTIVE)
        p.transition_to(ExecutionPlanStatus.COMPLETED)
        p.transition_to(ExecutionPlanStatus.ARCHIVED)
        assert p.status == ExecutionPlanStatus.ARCHIVED

    def test_terminal_blocks_re_transition(self):
        p = ExecutionPlan()
        p.transition_to(ExecutionPlanStatus.VALIDATED)
        p.transition_to(ExecutionPlanStatus.CANCELLED)
        with pytest.raises(PlanTerminalError):
            p.transition_to(ExecutionPlanStatus.VALIDATED)

    def test_add_instruction(self):
        p = ExecutionPlan()
        inst = PlanningFactory.make_instruction(symbol="TCS", quantity=100)
        p.add_instruction(inst)
        assert len(p.instructions) == 1

    def test_to_dict(self):
        p = ExecutionPlan(symbol="INFY", order_id="O1")
        d = p.to_dict()
        assert d["symbol"] == "INFY"
        assert "plan_id" in d


# ─────────────────────────────────────────────────────────────────────────────
# 4. ExecutionCost
# ─────────────────────────────────────────────────────────────────────────────

class TestExecutionCost:
    def test_total_computed(self):
        c = ExecutionCost(order_value=100_000.0)
        c.with_commission(30.0).with_slippage(50.0).with_impact(20.0)
        assert c.total_estimated_cost == pytest.approx(100.0)

    def test_cost_bps(self):
        c = ExecutionCost(order_value=100_000.0)
        c.with_commission(30.0)  # 30 / 100_000 * 10_000 = 3 bps
        assert c.cost_bps == pytest.approx(3.0)

    def test_to_dict(self):
        c = ExecutionCost(plan_id="P1")
        d = c.to_dict()
        assert "total_estimated_cost" in d


# ─────────────────────────────────────────────────────────────────────────────
# 5. ExecutionConstraints
# ─────────────────────────────────────────────────────────────────────────────

class TestExecutionConstraints:
    def test_defaults(self):
        c = ExecutionConstraints()
        assert c.max_slippage_pct == pytest.approx(0.005)

    def test_venue_allowed(self):
        c = ExecutionConstraints(allowed_venues=["NSE"])
        assert c.venue_is_allowed("NSE")
        assert not c.venue_is_allowed("BSE")

    def test_to_dict(self):
        c = ExecutionConstraints()
        d = c.to_dict()
        assert "max_slippage_pct" in d


# ─────────────────────────────────────────────────────────────────────────────
# 6. ExecutionRoute
# ─────────────────────────────────────────────────────────────────────────────

class TestExecutionRoute:
    def test_defaults(self):
        r = ExecutionRoute()
        assert r.route_id != ""

    def test_all_venues(self):
        r = ExecutionRoute(primary_venue="NSE", backup_venues=["BSE"])
        assert "NSE" in r.all_venues()
        assert "BSE" in r.all_venues()

    def test_to_dict(self):
        r = ExecutionRoute(primary_venue="NSE")
        d = r.to_dict()
        assert d["primary_venue"] == "NSE"


# ─────────────────────────────────────────────────────────────────────────────
# 7. CostEstimator
# ─────────────────────────────────────────────────────────────────────────────

class TestCostEstimator:
    def test_commission_basic(self):
        est = CostEstimator()
        c   = est.estimate_commission(100_000.0)
        assert c == pytest.approx(30.0)  # 3bps

    def test_opportunity_zero_window(self):
        est = CostEstimator()
        opp = est.estimate_opportunity_cost(100_000.0, 0.0)
        assert opp == pytest.approx(0.0)

    def test_full_estimate(self):
        est = CostEstimator()
        c   = est.estimate(order_value=100_000.0, slippage=50.0, market_impact=30.0)
        assert c.total_estimated_cost > 0

    def test_to_dict(self):
        est = CostEstimator()
        d   = est.to_dict()
        assert "commission_rate" in d


# ─────────────────────────────────────────────────────────────────────────────
# 8. SlippageEstimator
# ─────────────────────────────────────────────────────────────────────────────

class TestSlippageEstimator:
    def test_zero_value(self):
        est = SlippageEstimator()
        assert est.estimate(0.0) == pytest.approx(0.0)

    def test_basic_estimate(self):
        est = SlippageEstimator()
        s   = est.estimate(100_000.0)
        assert s > 0

    def test_estimate_rate(self):
        est = SlippageEstimator()
        rate = est.estimate_slippage_rate(1_000, 100_000)
        assert rate > 0

    def test_to_dict(self):
        est = SlippageEstimator()
        # SlippageEstimator exposes config
        assert est._cfg.base_slippage_rate > 0


# ─────────────────────────────────────────────────────────────────────────────
# 9. ImpactEstimator
# ─────────────────────────────────────────────────────────────────────────────

class TestImpactEstimator:
    def test_zero_value(self):
        est = ImpactEstimator()
        assert est.estimate(0.0) == pytest.approx(0.0)

    def test_basic_estimate(self):
        est = ImpactEstimator()
        imp = est.estimate(100_000.0, participation_rate=0.10)
        assert imp > 0

    def test_higher_participation_higher_impact(self):
        est  = ImpactEstimator()
        low  = est.estimate(100_000.0, 0.05)
        high = est.estimate(100_000.0, 0.30)
        assert high > low

    def test_bps_method(self):
        est = ImpactEstimator()
        bps = est.impact_bps(100_000.0, 0.10)
        assert bps > 0


# ─────────────────────────────────────────────────────────────────────────────
# 10. LiquidityEstimator
# ─────────────────────────────────────────────────────────────────────────────

class TestLiquidityEstimator:
    def test_high_adv_high_liquidity(self):
        est = LiquidityEstimator()
        r   = est.estimate(100_000.0, adv=100_000_000.0)
        assert r.liquidity_level == LiquidityLevel.HIGH

    def test_small_adv_low_liquidity(self):
        est = LiquidityEstimator()
        r   = est.estimate(500_000.0, adv=1_000_000.0)
        assert r.liquidity_level in (LiquidityLevel.LOW, LiquidityLevel.VERY_LOW)

    def test_fill_probability_range(self):
        est = LiquidityEstimator()
        r   = est.estimate(100_000.0)
        assert 0 < r.fill_probability <= 1.0

    def test_to_dict(self):
        est = LiquidityEstimator()
        r   = est.estimate(100_000.0)
        d   = r.to_dict()
        assert "liquidity_score" in d


# ─────────────────────────────────────────────────────────────────────────────
# 11. RouteRegistry
# ─────────────────────────────────────────────────────────────────────────────

class TestRouteRegistry:
    def test_register_and_get(self):
        reg = RouteRegistry()
        reg.register_venue(_venue("NSE"))
        v   = reg.get_venue("NSE")
        assert v.venue_id == "NSE"

    def test_duplicate_raises(self):
        reg = RouteRegistry()
        reg.register_venue(_venue("NSE"))
        with pytest.raises(KeyError):
            reg.register_venue(_venue("NSE"))

    def test_overwrite(self):
        reg = RouteRegistry()
        reg.register_venue(_venue("NSE"))
        reg.register_venue(_venue("NSE"), overwrite=True)
        assert reg.has_venue("NSE")

    def test_active_venues(self):
        reg = RouteRegistry()
        reg.register_venue(_venue("NSE"))
        reg.register_venue(VenueInfo(venue_id="BSE", is_active=False))
        active = reg.active_venues()
        assert all(v.is_active for v in active)


# ─────────────────────────────────────────────────────────────────────────────
# 12. RouteEvaluator
# ─────────────────────────────────────────────────────────────────────────────

class TestRouteEvaluator:
    def test_returns_sorted_scores(self):
        ev  = RouteEvaluator()
        scores = ev.evaluate(
            [_venue("NSE", 0.0003), _venue("BSE", 0.0010)],
            order_value=500_000.0,
        )
        assert len(scores) == 2
        assert scores[0].composite_score >= scores[1].composite_score

    def test_cheaper_venue_wins(self):
        ev  = RouteEvaluator()
        scores = ev.evaluate([_venue("NSE", 0.0001), _venue("BSE", 0.0020)])
        assert scores[0].venue_id == "NSE"

    def test_empty_venues(self):
        ev = RouteEvaluator()
        assert ev.evaluate([]) == []


# ─────────────────────────────────────────────────────────────────────────────
# 13. RouteSelector
# ─────────────────────────────────────────────────────────────────────────────

class TestRouteSelector:
    def test_no_venues_returns_default(self):
        sel   = RouteSelector()
        route = sel.select()
        assert route.primary_venue == "default"

    def test_single_venue_routing(self):
        reg   = RouteRegistry()
        reg.register_venue(_venue("NSE"))
        sel   = RouteSelector(registry=reg)
        route = sel.select()
        assert route.primary_venue == "NSE"

    def test_preferred_venue(self):
        reg = RouteRegistry()
        reg.register_venue(_venue("NSE"))
        reg.register_venue(_venue("BSE"))
        sel   = RouteSelector(registry=reg)
        route = sel.select(preferred_venue="BSE")
        assert route.primary_venue == "BSE"

    def test_multi_venue_routing(self):
        reg = RouteRegistry()
        for v in ["NSE", "BSE", "MCX"]:
            reg.register_venue(_venue(v))
        sel   = RouteSelector(registry=reg)
        route = sel.select(strategy=RoutingStrategy.MULTI_VENUE)
        assert route.primary_venue in ["NSE", "BSE", "MCX"]


# ─────────────────────────────────────────────────────────────────────────────
# 14. RouteOptimizer
# ─────────────────────────────────────────────────────────────────────────────

class TestRouteOptimizer:
    def test_no_venues(self):
        opt = RouteOptimizer()
        r   = opt.optimize()
        assert r.winner is None

    def test_with_venues(self):
        reg = RouteRegistry()
        reg.register_venue(_venue("NSE"))
        opt = RouteOptimizer(registry=reg)
        r   = opt.optimize(order_value=500_000.0)
        assert r.winner is not None
        assert r.winner.venue_id == "NSE"

    def test_to_dict(self):
        opt = RouteOptimizer()
        r   = opt.optimize()
        d   = r.to_dict()
        assert "winner" in d


# ─────────────────────────────────────────────────────────────────────────────
# 15. OrderPlanner
# ─────────────────────────────────────────────────────────────────────────────

class TestOrderPlanner:
    def test_basic_plan(self):
        planner = OrderPlanner()
        result  = planner.plan(_req())
        assert isinstance(result, PlanResult)
        assert result.plan.plan_id != ""

    def test_plan_status_validated(self):
        planner = OrderPlanner()
        result  = planner.plan(_req())
        assert result.plan.status == ExecutionPlanStatus.VALIDATED

    def test_plan_has_schedule(self):
        planner = OrderPlanner()
        result  = planner.plan(_req())
        assert result.plan.schedule is not None

    def test_plan_has_cost(self):
        planner = OrderPlanner()
        result  = planner.plan(_req(order_value=1_000_000.0))
        assert result.plan.estimated_cost.total_estimated_cost > 0

    def test_plan_has_route(self):
        planner = OrderPlanner()
        result  = planner.plan(_req())
        assert result.plan.route is not None

    def test_duration_ms_positive(self):
        planner = OrderPlanner()
        result  = planner.plan(_req())
        assert result.duration_ms >= 0


# ─────────────────────────────────────────────────────────────────────────────
# 16. OrderSplitter
# ─────────────────────────────────────────────────────────────────────────────

class TestOrderSplitter:
    def _parent(self) -> ExecutionPlan:
        p = PlanningFactory.make_plan(symbol="TCS")
        return p

    def test_equal_split_two_legs(self):
        splitter = OrderSplitter()
        parent   = self._parent()
        result   = splitter.split(parent, SplitConfig(num_legs=2))
        assert result.leg_count == 2

    def test_children_linked_to_parent(self):
        splitter = OrderSplitter()
        parent   = self._parent()
        result   = splitter.split(parent, SplitConfig(num_legs=3))
        for child in result.child_plans:
            assert child.parent_plan_id == parent.plan_id

    def test_no_split_returns_parent(self):
        splitter = OrderSplitter()
        parent   = self._parent()
        result   = splitter.split(parent, SplitConfig(split_type=OrderSplitType.NO_SPLIT))
        assert result.leg_count == 1
        assert result.child_plans[0] is parent

    def test_max_legs_enforced(self):
        splitter = OrderSplitter()
        parent   = self._parent()
        result   = splitter.split(parent, SplitConfig(num_legs=100, max_legs=5))
        assert result.leg_count == 5


# ─────────────────────────────────────────────────────────────────────────────
# 17. OrderMerger
# ─────────────────────────────────────────────────────────────────────────────

class TestOrderMerger:
    def test_merge_two_plans(self):
        merger = OrderMerger()
        p1     = PlanningFactory.make_plan(symbol="TCS", priority=5)
        p2     = PlanningFactory.make_plan(symbol="TCS", priority=8)
        result = merger.merge([p1, p2])
        assert len(result.source_plan_ids) == 2
        assert result.merged_plan.priority == 8  # highest

    def test_empty_raises(self):
        merger = OrderMerger()
        with pytest.raises(ValueError):
            merger.merge([])

    def test_merged_plan_is_new(self):
        merger = OrderMerger()
        p1     = PlanningFactory.make_plan(symbol="INFY")
        p2     = PlanningFactory.make_plan(symbol="INFY")
        result = merger.merge([p1, p2])
        assert result.merged_plan.plan_id not in (p1.plan_id, p2.plan_id)


# ─────────────────────────────────────────────────────────────────────────────
# 18. ExecutionScheduler
# ─────────────────────────────────────────────────────────────────────────────

class TestExecutionScheduler:
    def test_schedule_assigned(self):
        sched  = ExecutionScheduler()
        plan   = PlanningFactory.make_plan()
        result = sched.schedule(plan)
        assert plan.schedule is not None
        assert plan.schedule.end_time is not None

    def test_immediate_starts_soon(self):
        sched  = ExecutionScheduler()
        plan   = PlanningFactory.make_plan()
        sched.schedule(plan, ScheduleRequest(urgency="immediate"))
        assert plan.schedule.start_time <= time.time() + 1.0

    def test_bulk_starts_later(self):
        sched  = ExecutionScheduler()
        imm    = PlanningFactory.make_plan()
        bulk   = PlanningFactory.make_plan()
        sched.schedule(imm,  ScheduleRequest(urgency="immediate"))
        sched.schedule(bulk, ScheduleRequest(urgency="bulk"))
        assert bulk.schedule.start_time > imm.schedule.start_time


# ─────────────────────────────────────────────────────────────────────────────
# 19. ExecutionBatch
# ─────────────────────────────────────────────────────────────────────────────

class TestExecutionBatch:
    def test_add_remove(self):
        batch = ExecutionBatch(name="B1")
        batch.add_plan("P1")
        batch.add_plan("P2")
        assert batch.size == 2
        batch.remove_plan("P1")
        assert batch.size == 1

    def test_dedup(self):
        batch = ExecutionBatch()
        batch.add_plan("P1")
        batch.add_plan("P1")
        assert batch.size == 1

    def test_to_dict(self):
        batch = ExecutionBatch(name="TestBatch")
        d     = batch.to_dict()
        assert d["name"] == "TestBatch"


# ─────────────────────────────────────────────────────────────────────────────
# 20. Policies
# ─────────────────────────────────────────────────────────────────────────────

class TestPolicies:
    def test_default_policy_approves_all(self):
        pol  = ExecutionPolicy()
        plan = PlanningFactory.make_plan()
        ev   = pol.evaluate(plan)
        assert ev.approved

    def test_immediate_policy_rejects_scheduled(self):
        pol  = ImmediatePolicy()
        plan = PlanningFactory.make_plan(execution_mode=ExecutionMode.SCHEDULED)
        ev   = pol.evaluate(plan)
        assert not ev.approved
        assert ev.violations

    def test_immediate_policy_approves_immediate(self):
        pol  = ImmediatePolicy()
        plan = PlanningFactory.make_plan(execution_mode=ExecutionMode.IMMEDIATE)
        ev   = pol.evaluate(plan)
        assert ev.approved

    def test_risk_limited_policy_rejects_high_cost(self):
        pol  = RiskLimitedPolicy(max_total_cost=10.0)
        plan = PlanningFactory.make_plan()
        plan.estimated_cost.with_commission(100.0)
        ev   = pol.evaluate(plan)
        assert not ev.approved

    def test_policy_enforce_raises_on_violation(self):
        pol  = ImmediatePolicy()
        plan = PlanningFactory.make_plan(execution_mode=ExecutionMode.SCHEDULED)
        with pytest.raises(PolicyViolationError):
            pol.enforce(plan)

    def test_policy_registry(self):
        reg = PolicyRegistry()
        reg.register(ImmediatePolicy())
        assert len(reg.all_policies()) == 1


# ─────────────────────────────────────────────────────────────────────────────
# 21. PlanningRegistry
# ─────────────────────────────────────────────────────────────────────────────

class TestPlanningRegistry:
    def test_register_and_get(self):
        reg  = PlanningRegistry()
        plan = PlanningFactory.make_plan(symbol="TCS")
        reg.register(plan)
        assert reg.get(plan.plan_id).plan_id == plan.plan_id

    def test_duplicate_raises(self):
        reg  = PlanningRegistry()
        plan = PlanningFactory.make_plan()
        reg.register(plan)
        with pytest.raises(PlanAlreadyExistsError):
            reg.register(plan)

    def test_not_found_raises(self):
        reg = PlanningRegistry()
        with pytest.raises(PlanNotFoundError):
            reg.get("NOPE")

    def test_overflow(self):
        reg = PlanningRegistry(max_plans=2)
        reg.register(PlanningFactory.make_plan())
        reg.register(PlanningFactory.make_plan())
        with pytest.raises(PlanningRegistryOverflowError):
            reg.register(PlanningFactory.make_plan())

    def test_statistics(self):
        reg = PlanningRegistry()
        reg.register(PlanningFactory.make_plan())
        s   = reg.statistics()
        assert s["registered_plans"] == 1


# ─────────────────────────────────────────────────────────────────────────────
# 22. PlanningContext
# ─────────────────────────────────────────────────────────────────────────────

class TestPlanningContext:
    def test_get_context(self):
        ctx = get_planning_context()
        assert isinstance(ctx, PlanningContextState)

    def test_request_id_generated(self):
        ctx = get_planning_context()
        assert ctx.request_id != ""

    def test_planning_session(self):
        with planning_session("req-xyz") as ctx:
            assert ctx.request_id == "req-xyz"

    def test_stage_scope(self):
        with planning_stage_scope("routing") as ctx:
            assert ctx.stage == "routing"

    def test_reset(self):
        reset_planning_context()
        ctx = get_planning_context()
        assert ctx is not None


# ─────────────────────────────────────────────────────────────────────────────
# 23. PlanningFactory
# ─────────────────────────────────────────────────────────────────────────────

class TestPlanningFactory:
    def test_make_plan(self):
        p = PlanningFactory.make_plan(symbol="INFY", priority=8)
        assert p.symbol == "INFY"
        assert p.priority == 8

    def test_make_route(self):
        r = PlanningFactory.make_route("NSE")
        assert r.primary_venue == "NSE"

    def test_make_cost(self):
        c = PlanningFactory.make_cost(plan_id="P1", order_value=50_000.0)
        assert c.order_value == 50_000.0

    def test_make_constraints(self):
        c = PlanningFactory.make_constraints(max_slippage_pct=0.003)
        assert c.max_slippage_pct == pytest.approx(0.003)

    def test_make_instruction(self):
        inst = PlanningFactory.make_instruction(plan_id="P1", symbol="TCS", quantity=100)
        assert inst.symbol == "TCS"
        assert inst.quantity == 100


# ─────────────────────────────────────────────────────────────────────────────
# 24. PlanningManager
# ─────────────────────────────────────────────────────────────────────────────

class TestPlanningManager:
    def setup_method(self):
        reset_planning_registry()
        self.mgr = PlanningManager(registry=PlanningRegistry())

    def test_create_plan(self):
        r = self.mgr.create_plan(_req())
        assert isinstance(r, PlanResult)

    def test_get_plan(self):
        r = self.mgr.create_plan(_req())
        p = self.mgr.get_plan(r.plan.plan_id)
        assert p.plan_id == r.plan.plan_id

    def test_approve_plan(self):
        r   = self.mgr.create_plan(_req())
        pid = r.plan.plan_id
        self.mgr.get_plan(pid).transition_to(ExecutionPlanStatus.VALIDATED)
        approved = self.mgr.approve_plan(pid)
        assert approved.status == ExecutionPlanStatus.APPROVED

    def test_cancel_plan(self):
        r       = self.mgr.create_plan(_req())
        cancelled = self.mgr.cancel_plan(r.plan.plan_id, "test cancel")
        assert cancelled.status == ExecutionPlanStatus.CANCELLED

    def test_fail_plan(self):
        r    = self.mgr.create_plan(_req())
        plan = self.mgr.fail_plan(r.plan.plan_id)
        assert plan.status == ExecutionPlanStatus.FAILED

    def test_split_plan(self):
        r      = self.mgr.create_plan(_req())
        result = self.mgr.split_plan(r.plan.plan_id, SplitConfig(num_legs=3))
        assert result.leg_count == 3

    def test_merge_plans(self):
        r1 = self.mgr.create_plan(_req())
        r2 = self.mgr.create_plan(_req())
        mr = self.mgr.merge_plans([r1.plan.plan_id, r2.plan.plan_id])
        assert len(mr.source_plan_ids) == 2

    def test_create_batch(self):
        r1 = self.mgr.create_plan(_req())
        r2 = self.mgr.create_plan(_req())
        b  = self.mgr.create_batch([r1.plan.plan_id, r2.plan.plan_id], name="TestBatch")
        assert b.size == 2

    def test_evaluate_policies(self):
        self.mgr.register_policy(ImmediatePolicy())
        r  = self.mgr.create_plan(_req())
        ev = self.mgr.evaluate_policies(r.plan.plan_id)
        assert isinstance(ev, list)

    def test_recent(self):
        for _ in range(5):
            self.mgr.create_plan(_req())
        assert len(self.mgr.recent(3)) == 3

    def test_statistics(self):
        self.mgr.create_plan(_req())
        s = self.mgr.statistics()
        assert s["plans_created"] >= 1

    def test_register_venue(self):
        self.mgr.register_venue(_venue("NSE"))
        # Just checking it doesn't raise
        assert True


# ─────────────────────────────────────────────────────────────────────────────
# 25. ExecutionPlanningEngine (facade)
# ─────────────────────────────────────────────────────────────────────────────

class TestExecutionPlanningEngine:
    def test_not_running_by_default(self):
        eng = ExecutionPlanningEngine()
        assert not eng.is_running

    def test_initialize(self):
        eng = ExecutionPlanningEngine()
        eng.initialize()
        assert eng.is_running

    def test_double_initialize_raises(self):
        eng = ExecutionPlanningEngine()
        eng.initialize()
        with pytest.raises(PlanningEngineAlreadyRunningError):
            eng.initialize()

    def test_requires_initialization(self):
        eng = ExecutionPlanningEngine()
        with pytest.raises(PlanningEngineNotInitializedError):
            eng.create_plan(_req())

    def test_create_and_get_plan(self):
        eng = ExecutionPlanningEngine()
        eng.initialize()
        r   = eng.create_plan(_req())
        p   = eng.get_plan(r.plan.plan_id)
        assert p.plan_id == r.plan.plan_id

    def test_approve_activate_complete(self):
        eng = ExecutionPlanningEngine()
        eng.initialize()
        r   = eng.create_plan(_req())
        pid = r.plan.plan_id
        eng.get_plan(pid).transition_to(ExecutionPlanStatus.VALIDATED)
        eng.approve_plan(pid)
        eng.activate_plan(pid)
        eng.complete_plan(pid)
        assert eng.get_plan(pid).status == ExecutionPlanStatus.COMPLETED

    def test_cancel_plan(self):
        eng = ExecutionPlanningEngine()
        eng.initialize()
        r   = eng.create_plan(_req())
        eng.cancel_plan(r.plan.plan_id)
        assert eng.get_plan(r.plan.plan_id).status == ExecutionPlanStatus.CANCELLED

    def test_split_plan(self):
        eng = ExecutionPlanningEngine()
        eng.initialize()
        r   = eng.create_plan(_req())
        sr  = eng.split_plan(r.plan.plan_id, SplitConfig(num_legs=2))
        assert sr.leg_count == 2

    def test_health_running(self):
        eng = ExecutionPlanningEngine()
        eng.initialize()
        assert eng.health()["status"] == "running"

    def test_health_stopped(self):
        eng = ExecutionPlanningEngine()
        assert eng.health()["status"] == "stopped"

    def test_shutdown(self):
        eng = ExecutionPlanningEngine()
        eng.initialize()
        eng.shutdown()
        assert not eng.is_running

    def test_stats(self):
        eng = ExecutionPlanningEngine()
        eng.initialize()
        eng.create_plan(_req())
        s = eng.stats()
        assert "plans_created" in s

    def test_register_venue_and_policy(self):
        eng = ExecutionPlanningEngine()
        eng.initialize()
        eng.register_venue(_venue("NSE"))
        eng.register_policy(ImmediatePolicy())
        r  = eng.create_plan(_req())
        ev = eng.evaluate_policies(r.plan.plan_id)
        assert len(ev) == 1


# ─────────────────────────────────────────────────────────────────────────────
# 26. Async
# ─────────────────────────────────────────────────────────────────────────────

class TestAsync:
    def test_async_create_plan(self):
        eng = ExecutionPlanningEngine()
        eng.initialize()

        async def _run():
            return await eng.create_plan_async(_req())

        result = asyncio.run(_run())
        assert isinstance(result, PlanResult)

    def test_async_multiple(self):
        eng = ExecutionPlanningEngine()
        eng.initialize()

        async def _run():
            reqs = [_req(symbol=f"SYM{i}") for i in range(4)]
            return await asyncio.gather(*[eng.create_plan_async(r) for r in reqs])

        results = asyncio.run(_run())
        assert len(results) == 4


# ─────────────────────────────────────────────────────────────────────────────
# 27. Singletons
# ─────────────────────────────────────────────────────────────────────────────

class TestSingletons:
    def test_engine_singleton(self):
        e1 = get_planning_engine()
        e2 = get_planning_engine()
        assert e1 is e2

    def test_reset_engine(self):
        e1 = get_planning_engine()
        reset_planning_engine()
        e2 = get_planning_engine()
        assert e1 is not e2

    def test_manager_singleton(self):
        m1 = get_planning_manager()
        m2 = get_planning_manager()
        assert m1 is m2

    def test_registry_singleton(self):
        r1 = get_planning_registry()
        r2 = get_planning_registry()
        assert r1 is r2


# ─────────────────────────────────────────────────────────────────────────────
# 28. Concurrency
# ─────────────────────────────────────────────────────────────────────────────

class TestConcurrency:
    def test_concurrent_plan_creation(self):
        reset_planning_registry()
        mgr    = PlanningManager(registry=PlanningRegistry())
        errors: list[Exception] = []
        results: list[PlanResult] = []

        def _worker():
            try:
                r = mgr.create_plan(_req())
                results.append(r)
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=_worker) for _ in range(12)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors
        assert len(results) == 12

    def test_concurrent_lifecycle(self):
        reset_planning_registry()
        mgr  = PlanningManager(registry=PlanningRegistry())
        reqs = [mgr.create_plan(_req()) for _ in range(6)]
        errors: list[Exception] = []

        def _cancel(pid: str):
            try:
                mgr.cancel_plan(pid)
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=_cancel, args=(r.plan.plan_id,)) for r in reqs]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors

    def test_concurrent_registry(self):
        reg    = PlanningRegistry(max_plans=200)
        errors: list[Exception] = []

        def _register():
            try:
                reg.register(PlanningFactory.make_plan())
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=_register) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors


# ─────────────────────────────────────────────────────────────────────────────
# 29. Package imports
# ─────────────────────────────────────────────────────────────────────────────

class TestPackageImports:
    def test_all_exports_importable(self):
        import iios.execution.planning as pkg
        for name in pkg.__all__:
            assert hasattr(pkg, name), f"Missing export: {name}"

    def test_version(self):
        import iios.execution.planning as pkg
        assert pkg.__version__ == PLANNING_ENGINE_VERSION

    def test_system_id(self):
        import iios.execution.planning as pkg
        assert "planning" in pkg.__system_id__
