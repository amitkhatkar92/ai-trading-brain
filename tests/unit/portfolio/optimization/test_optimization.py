"""
test_optimization.py — tests for iios.portfolio.optimization
=============================================================
Comprehensive unit tests for the Portfolio Optimization Framework.

C10 Portfolio Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

import threading
import time
import uuid
from typing import Any, Dict, List

import pytest

from iios.portfolio.optimization import (
    AllocationCapability,
    AllocationPlan,
    CandidateStatus,
    ConstraintResult,
    ConstraintType,
    ObjectiveResult,
    OptimizationContext,
    OptimizationEventType,
    OptimizationObjective,
    OptimizationStatisticsSnapshot,
    OptimizationStrategyType,
    PortfolioCandidate,
    PortfolioCandidateRegistry,
    PortfolioConstraint,
    PortfolioConstraintEngine,
    PortfolioOptimizationCandidateError,
    PortfolioOptimizationCapacityError,
    PortfolioOptimizationConfigurationError,
    PortfolioOptimizationConstraintError,
    PortfolioOptimizationEngine,
    PortfolioOptimizationError,
    PortfolioOptimizationFactory,
    PortfolioOptimizationHistory,
    PortfolioOptimizationNotFoundError,
    PortfolioOptimizationNotRunningError,
    PortfolioOptimizationRegistry,
    PortfolioOptimizationRequest,
    PortfolioOptimizationResponse,
    PortfolioOptimizationSolutionError,
    PortfolioOptimizationStatistics,
    PortfolioOptimizationStrategy,
    PortfolioOptimizationStrategyError,
    PortfolioOptimizationSummary,
    PortfolioOptimizationValidationError,
    PortfolioObjective,
    PortfolioOptimizer,
    PortfolioSolution,
    PortfolioSolutionSelector,
    PortfolioSolutionValidator,
    PortfolioStrategyRegistry,
    RebalancingCapability,
    RebalancingPlan,
    ScoringMethod,
    SolutionValidationResult,
    StrategyStatus,
    VERSION,
    make_allocation_generated,
    make_candidates_loaded,
    make_constraints_loaded,
    make_objectives_loaded,
    make_optimization_completed,
    make_optimization_failed,
    make_optimization_started,
    make_portfolio_selected,
    make_rebalancing_generated,
    make_solution_validated,
)
from iios.portfolio.optimization.portfolio_allocation_engine import PortfolioAllocationEngine
from iios.portfolio.optimization.portfolio_priority_engine import PortfolioPriorityEngine
from iios.portfolio.optimization.portfolio_ranking_engine import PortfolioRankingEngine
from iios.portfolio.optimization.portfolio_rebalancing_engine import PortfolioRebalancingEngine
from iios.portfolio.optimization.portfolio_scoring_engine import PortfolioScoringEngine


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _candidate(portfolio_id: str = "P1", inputs: Dict = None) -> PortfolioCandidate:
    return PortfolioCandidate(portfolio_id=portfolio_id, inputs=inputs or {})


def _objective(
    score_value: float = 0.8,
    name: str = "test_obj",
    weight: float = 1.0,
) -> PortfolioObjective:
    return PortfolioObjective(
        OptimizationObjective.MAXIMIZE_RISK_ADJUSTED_RETURN,
        name,
        lambda c, i: score_value,
        weight=weight,
    )


def _constraint(
    satisfied: bool = True,
    name: str = "test_con",
    is_hard: bool = True,
) -> PortfolioConstraint:
    return PortfolioConstraint(
        ConstraintType.CAPITAL,
        name,
        lambda c, i: satisfied,
        is_hard=is_hard,
        penalty=0.3,
    )


def _strategy(
    name: str = "default",
    objectives: list = None,
    constraints: list = None,
) -> PortfolioOptimizationStrategy:
    return PortfolioOptimizationStrategy(
        name=name,
        objectives=objectives or [_objective()],
        constraints=constraints or [],
        is_default=(name == "default"),
    )


def _solution(
    score: float = 0.7,
    is_feasible: bool = True,
    objectives_evaluated: int = 1,
    constraints_violated: int = 0,
    optimization_id: str = "opt1",
    candidate_id: str = "",
    portfolio_id: str = "P1",
) -> PortfolioSolution:
    return PortfolioSolution(
        solution_id           = str(uuid.uuid4()),
        optimization_id       = optimization_id,
        candidate_id          = candidate_id or str(uuid.uuid4()),
        portfolio_id          = portfolio_id,
        strategy_name         = "default",
        objectives_evaluated  = objectives_evaluated,
        constraints_satisfied = 1,
        constraints_violated  = constraints_violated,
        allocation_plan       = None,
        rebalancing_plan      = None,
        score                 = score,
        is_feasible           = is_feasible,
        reason                = "test",
        constraint_violations = [],
        objective_scores      = {},
        evaluated_at          = time.time(),
    )


# ===========================================================================
# 1. Constants and enumerations
# ===========================================================================

class TestConstants:
    def test_optimization_system_id(self):
        from iios.portfolio.optimization.constants import OPTIMIZATION_SYSTEM_ID
        assert OPTIMIZATION_SYSTEM_ID == "iios:portfolio:optimization"

    def test_version(self):
        assert VERSION == "1.0.0"

    def test_optimization_objective_count(self):
        assert len(OptimizationObjective) == 10

    def test_strategy_type_count(self):
        assert len(OptimizationStrategyType) == 12

    def test_constraint_type_count(self):
        assert len(ConstraintType) == 12

    def test_allocation_capability_count(self):
        assert len(AllocationCapability) == 8

    def test_rebalancing_capability_count(self):
        assert len(RebalancingCapability) == 6

    def test_scoring_method_count(self):
        assert len(ScoringMethod) == 4

    def test_optimization_event_type_count(self):
        assert len(OptimizationEventType) == 10

    def test_candidate_status_count(self):
        assert len(CandidateStatus) == 5

    def test_strategy_status_count(self):
        assert len(StrategyStatus) == 4

    def test_enum_values_are_strings(self):
        for obj in OptimizationObjective:
            assert isinstance(obj.value, str)

    def test_allocation_capability_values(self):
        assert AllocationCapability.CAPITAL.value == "capital_allocation"
        assert AllocationCapability.ASSET.value   == "asset_allocation"

    def test_rebalancing_capability_values(self):
        assert RebalancingCapability.THRESHOLD.value == "threshold_rebalancing"
        assert RebalancingCapability.PERIODIC.value  == "periodic_rebalancing"


# ===========================================================================
# 2. Exceptions
# ===========================================================================

class TestExceptions:
    def test_base_error_is_iios_error(self):
        from iios.common.errors.exceptions import IIOSError
        err = PortfolioOptimizationError("test")
        assert isinstance(err, IIOSError)
        assert err.error_code == "PO-000"  # type: ignore[attr-defined]

    def test_not_running_error(self):
        err = PortfolioOptimizationNotRunningError()
        assert "PO-001" in str(err) or err.error_code == "PO-001"  # type: ignore[attr-defined]

    def test_not_found_error_fields(self):
        err = PortfolioOptimizationNotFoundError("abc123", item_type="strategy")
        assert err.item_id   == "abc123"
        assert err.item_type == "strategy"

    def test_configuration_error_field(self):
        err = PortfolioOptimizationConfigurationError("bad config", field="max_candidates")
        assert err.field == "max_candidates"

    def test_validation_error_failed_checks(self):
        err = PortfolioOptimizationValidationError("v", failed_checks=("a", "b"))
        assert err.failed_checks == ("a", "b")

    def test_solution_error_optimization_id(self):
        err = PortfolioOptimizationSolutionError("no sol", optimization_id="op1")
        assert err.optimization_id == "op1"

    def test_constraint_error_name(self):
        err = PortfolioOptimizationConstraintError("err", constraint_name="max_exposure")
        assert err.constraint_name == "max_exposure"

    def test_strategy_error_id(self):
        err = PortfolioOptimizationStrategyError("err", strategy_id="strat1")
        assert err.strategy_id == "strat1"

    def test_capacity_error_limit(self):
        err = PortfolioOptimizationCapacityError(100, resource="candidate registry")
        assert err.limit    == 100
        assert err.resource == "candidate registry"

    def test_candidate_error_id(self):
        err = PortfolioOptimizationCandidateError("err", candidate_id="cand1")
        assert err.candidate_id == "cand1"

    def test_exception_hierarchy(self):
        for exc_cls in [
            PortfolioOptimizationNotRunningError,
            PortfolioOptimizationNotFoundError,
            PortfolioOptimizationCapacityError,
        ]:
            assert issubclass(exc_cls, PortfolioOptimizationError)


# ===========================================================================
# 3. PortfolioCandidate
# ===========================================================================

class TestPortfolioCandidate:
    def test_auto_id(self):
        c = PortfolioCandidate(portfolio_id="P1")
        assert len(c.candidate_id) == 36

    def test_explicit_id(self):
        c = PortfolioCandidate("my-id", "P1")
        assert c.candidate_id == "my-id"

    def test_default_status_approved(self):
        c = PortfolioCandidate(portfolio_id="P1")
        assert c.status == CandidateStatus.APPROVED
        assert c.is_approved

    def test_set_score_clamps(self):
        c = _candidate()
        c.set_score(1.5)
        assert c.score == 1.0
        c.set_score(-0.1)
        assert c.score == 0.0

    def test_set_rank(self):
        c = _candidate()
        c.set_rank(3)
        assert c.rank == 3

    def test_select(self):
        c = _candidate()
        c.select()
        assert c.status == CandidateStatus.SELECTED
        assert c.is_selected

    def test_reject(self):
        c = _candidate()
        c.reject()
        assert c.status == CandidateStatus.REJECTED

    def test_discard(self):
        c = _candidate()
        c.discard()
        assert c.status == CandidateStatus.DISCARDED

    def test_inputs_copy(self):
        data = {"k": "v"}
        c = PortfolioCandidate(portfolio_id="P1", inputs=data)
        data["k"] = "changed"
        assert c.inputs["k"] == "v"

    def test_to_dict(self):
        c = _candidate("P2")
        d = c.to_dict()
        assert d["portfolio_id"] == "P2"
        assert "candidate_id" in d
        assert "status" in d

    def test_evaluated_at_set_on_score(self):
        c = _candidate()
        assert c.evaluated_at is None
        c.set_score(0.5)
        assert c.evaluated_at is not None

    def test_repr(self):
        c = _candidate()
        assert "PortfolioCandidate" in repr(c)


# ===========================================================================
# 4. PortfolioObjective
# ===========================================================================

class TestPortfolioObjective:
    def test_score_in_range(self):
        obj = _objective(0.75)
        result = obj.score(_candidate(), {})
        assert 0.0 <= result.score <= 1.0
        assert result.score == 0.75

    def test_score_clamped_high(self):
        obj = _objective(2.0)
        result = obj.score(_candidate(), {})
        assert result.score == 1.0

    def test_score_clamped_low(self):
        obj = _objective(-0.5)
        result = obj.score(_candidate(), {})
        assert result.score == 0.0

    def test_exception_in_fn_returns_zero(self):
        def bad_fn(c, i):
            raise RuntimeError("oops")
        obj = PortfolioObjective(
            OptimizationObjective.MAXIMIZE_DIVERSIFICATION,
            "bad", bad_fn,
        )
        result = obj.score(_candidate(), {})
        assert result.score == 0.0
        assert "exception" in result.message

    def test_objective_result_fields(self):
        obj = _objective(0.6, name="risk_obj", weight=2.0)
        result = obj.score(_candidate(), {})
        assert result.objective_name == "risk_obj"
        assert result.weight         == 2.0
        assert result.objective_type == OptimizationObjective.MAXIMIZE_RISK_ADJUSTED_RETURN

    def test_requires_non_empty_name(self):
        with pytest.raises(ValueError):
            PortfolioObjective(
                OptimizationObjective.MAXIMIZE_DIVERSIFICATION, "",
                lambda c, i: 0.5,
            )

    def test_requires_callable(self):
        with pytest.raises(TypeError):
            PortfolioObjective(
                OptimizationObjective.MAXIMIZE_DIVERSIFICATION, "test", "not_callable"
            )

    def test_negative_weight_raises(self):
        with pytest.raises(ValueError):
            PortfolioObjective(
                OptimizationObjective.MAXIMIZE_DIVERSIFICATION, "test",
                lambda c, i: 0.5, weight=-1.0,
            )

    def test_to_dict(self):
        obj    = _objective(0.5, "o1")
        result = obj.score(_candidate(), {})
        d      = result.to_dict()
        assert "objective_name" in d
        assert "score" in d

    def test_repr(self):
        assert "PortfolioObjective" in repr(_objective())


# ===========================================================================
# 5. PortfolioConstraint
# ===========================================================================

class TestPortfolioConstraint:
    def test_satisfied(self):
        con    = _constraint(True)
        result = con.evaluate(_candidate(), {})
        assert result.satisfied
        assert result.penalty == 0.0

    def test_violated_hard(self):
        con    = _constraint(False, is_hard=True)
        result = con.evaluate(_candidate(), {})
        assert not result.satisfied
        assert result.is_hard
        assert result.penalty == 0.0  # hard constraints don't carry a soft penalty

    def test_violated_soft(self):
        con = PortfolioConstraint(
            ConstraintType.RISK, "soft_con",
            lambda c, i: False,
            is_hard=False, penalty=0.4,
        )
        result = con.evaluate(_candidate(), {})
        assert not result.satisfied
        assert not result.is_hard
        assert result.penalty == 0.4

    def test_exception_treated_as_violated(self):
        def bad_fn(c, i):
            raise RuntimeError("fail")
        con    = PortfolioConstraint(ConstraintType.CASH, "bad", bad_fn, is_hard=False)
        result = con.evaluate(_candidate(), {})
        assert not result.satisfied

    def test_requires_non_empty_name(self):
        with pytest.raises(ValueError):
            PortfolioConstraint(ConstraintType.RISK, "", lambda c, i: True)

    def test_requires_callable(self):
        with pytest.raises(TypeError):
            PortfolioConstraint(ConstraintType.RISK, "con", "not_callable")

    def test_to_dict(self):
        con    = _constraint()
        result = con.evaluate(_candidate(), {})
        d      = result.to_dict()
        assert "constraint_name" in d
        assert "satisfied" in d

    def test_repr(self):
        assert "PortfolioConstraint" in repr(_constraint())


# ===========================================================================
# 6. AllocationPlan
# ===========================================================================

class TestAllocationPlan:
    def test_allocation_plan_frozen(self):
        plan = AllocationPlan(
            plan_id="p1", candidate_id="c1", portfolio_id="P1",
            allocation_type=AllocationCapability.CAPITAL,
            allocations={"equity": 0.6, "bonds": 0.4},
            total=1.0,
            generated_at=time.time(),
            metadata={},
        )
        with pytest.raises((AttributeError, TypeError)):
            plan.total = 2.0  # type: ignore[misc]

    def test_allocation_plan_to_dict(self):
        plan = AllocationPlan(
            plan_id="p1", candidate_id="c1", portfolio_id="P1",
            allocation_type=AllocationCapability.ASSET,
            allocations={"NIFTY": 0.5, "GOLD": 0.5},
            total=1.0,
            generated_at=time.time(),
            metadata={},
        )
        d = plan.to_dict()
        assert d["allocation_type"] == "asset_allocation"
        assert d["asset_count"] == 2


# ===========================================================================
# 7. RebalancingPlan
# ===========================================================================

class TestRebalancingPlan:
    def test_rebalancing_plan_frozen(self):
        plan = RebalancingPlan(
            plan_id="r1", candidate_id="c1", portfolio_id="P1",
            rebalancing_type=RebalancingCapability.THRESHOLD,
            actions=({"asset": "NIFTY", "current": 0.4, "target": 0.5, "delta": 0.1},),
            trigger="threshold",
            generated_at=time.time(),
            metadata={},
        )
        with pytest.raises((AttributeError, TypeError)):
            plan.trigger = "changed"  # type: ignore[misc]

    def test_rebalancing_plan_to_dict(self):
        plan = RebalancingPlan(
            plan_id="r1", candidate_id="c1", portfolio_id="P1",
            rebalancing_type=RebalancingCapability.PERIODIC,
            actions=(),
            trigger="periodic",
            generated_at=time.time(),
            metadata={},
        )
        d = plan.to_dict()
        assert d["rebalancing_type"] == "periodic_rebalancing"
        assert d["action_count"] == 0


# ===========================================================================
# 8. PortfolioSolution
# ===========================================================================

class TestPortfolioSolution:
    def test_solution_mutable_rank(self):
        s = _solution()
        s.rank = 3
        assert s.rank == 3

    def test_solution_mutable_is_selected(self):
        s = _solution()
        s.is_selected = True
        assert s.is_selected

    def test_solution_to_dict(self):
        s = _solution(score=0.8)
        d = s.to_dict()
        assert d["score"] == 0.8
        assert "solution_id" in d
        assert "is_feasible" in d

    def test_solution_default_rank_zero(self):
        s = _solution()
        assert s.rank == 0
        assert not s.is_selected


# ===========================================================================
# 9. PortfolioOptimizationSummary
# ===========================================================================

class TestOptimizationSummary:
    def _make_summary(self, selected: bool = True) -> PortfolioOptimizationSummary:
        return PortfolioOptimizationSummary(
            optimization_id        = "opt1",
            portfolio_id           = "P1",
            strategy_name          = "default",
            total_candidates       = 3,
            feasible_candidates    = 2,
            infeasible_candidates  = 1,
            selected_candidate_id  = "c1" if selected else "",
            selected_solution_id   = "s1" if selected else "",
            best_score             = 0.9,
            avg_score              = 0.75,
            objectives_evaluated   = 2,
            constraints_evaluated  = 4,
            constraints_violated   = 1,
            elapsed_s              = 0.05,
            evaluated_at           = time.time(),
        )

    def test_has_selection(self):
        assert self._make_summary(True).has_selection
        assert not self._make_summary(False).has_selection

    def test_to_dict(self):
        d = self._make_summary().to_dict()
        assert d["total_candidates"] == 3
        assert d["feasible_candidates"] == 2


# ===========================================================================
# 10. OptimizationContext
# ===========================================================================

class TestOptimizationContext:
    def test_create_auto_ids(self):
        ctx = OptimizationContext.create("P1")
        assert ctx.portfolio_id == "P1"
        assert len(ctx.context_id) == 36
        assert len(ctx.optimization_id) == 36

    def test_create_with_strategy(self):
        ctx = OptimizationContext.create("P1", strategy_name="mvp")
        assert ctx.strategy_name == "mvp"

    def test_create_with_objectives(self):
        objs = [OptimizationObjective.MAXIMIZE_DIVERSIFICATION]
        ctx  = OptimizationContext.create("P1", objectives=objs)
        assert OptimizationObjective.MAXIMIZE_DIVERSIFICATION in ctx.objectives

    def test_frozen(self):
        ctx = OptimizationContext.create("P1")
        with pytest.raises((AttributeError, TypeError)):
            ctx.portfolio_id = "P2"  # type: ignore[misc]

    def test_to_dict(self):
        ctx = OptimizationContext.create("P1")
        d   = ctx.to_dict()
        assert d["portfolio_id"] == "P1"


# ===========================================================================
# 11. PortfolioOptimizationRequest
# ===========================================================================

class TestOptimizationRequest:
    def test_create_basic(self):
        req = PortfolioOptimizationRequest.create("P1")
        assert req.portfolio_id == "P1"
        assert req.strategy_name == "default"
        assert req.candidate_count == 0

    def test_create_with_candidates(self):
        cands = [_candidate("P1") for _ in range(3)]
        req   = PortfolioOptimizationRequest.create("P1", candidates=cands)
        assert req.candidate_count == 3

    def test_frozen(self):
        req = PortfolioOptimizationRequest.create("P1")
        with pytest.raises((AttributeError, TypeError)):
            req.portfolio_id = "P2"  # type: ignore[misc]

    def test_with_candidates_returns_new(self):
        req  = PortfolioOptimizationRequest.create("P1")
        req2 = req.with_candidates([_candidate("P1")])
        assert req.candidate_count  == 0
        assert req2.candidate_count == 1
        assert req2.request_id      == req.request_id

    def test_with_inputs_returns_new(self):
        req  = PortfolioOptimizationRequest.create("P1")
        req2 = req.with_inputs({"k": "v"})
        assert req.inputs    == {}
        assert req2.inputs   == {"k": "v"}

    def test_to_dict(self):
        req = PortfolioOptimizationRequest.create("P1")
        d   = req.to_dict()
        assert d["portfolio_id"] == "P1"


# ===========================================================================
# 12. PortfolioOptimizationResponse
# ===========================================================================

class TestOptimizationResponse:
    def _summary(self):
        return PortfolioOptimizationSummary(
            optimization_id="opt1", portfolio_id="P1", strategy_name="default",
            total_candidates=1, feasible_candidates=1, infeasible_candidates=0,
            selected_candidate_id="c1", selected_solution_id="s1",
            best_score=0.8, avg_score=0.8,
            objectives_evaluated=1, constraints_evaluated=0, constraints_violated=0,
            elapsed_s=0.01, evaluated_at=time.time(),
        )

    def test_create_success(self):
        sol  = _solution()
        resp = PortfolioOptimizationResponse.create_success(
            "req1", "P1", "opt1", sol, [sol], self._summary()
        )
        assert resp.is_success
        assert not resp.is_failure
        assert resp.has_solution

    def test_create_failure(self):
        resp = PortfolioOptimizationResponse.create_failure(
            "req1", "P1", "opt1", "no candidates"
        )
        assert resp.is_failure
        assert not resp.is_success
        assert not resp.has_solution
        assert resp.error_message == "no candidates"

    def test_success_to_dict(self):
        sol  = _solution()
        resp = PortfolioOptimizationResponse.create_success(
            "req1", "P1", "opt1", sol, [sol], self._summary()
        )
        d = resp.to_dict()
        assert d["is_success"]
        assert d["total_solutions"] == 1

    def test_failure_to_dict(self):
        resp = PortfolioOptimizationResponse.create_failure(
            "req1", "P1", "opt1", "error"
        )
        d = resp.to_dict()
        assert d["is_failure"]

    def test_frozen(self):
        resp = PortfolioOptimizationResponse.create_failure(
            "req1", "P1", "opt1", "err"
        )
        with pytest.raises((AttributeError, TypeError)):
            resp.is_error = False  # type: ignore[misc]


# ===========================================================================
# 13. PortfolioCandidateRegistry
# ===========================================================================

class TestCandidateRegistry:
    def test_register_and_get(self):
        reg  = PortfolioCandidateRegistry()
        cand = _candidate("P1")
        reg.register(cand)
        assert reg.get(cand.candidate_id) is cand

    def test_capacity_error(self):
        reg = PortfolioCandidateRegistry(max_candidates=2)
        reg.register(_candidate("P1"))
        reg.register(_candidate("P1"))
        with pytest.raises(PortfolioOptimizationCapacityError):
            reg.register(_candidate("P1"))

    def test_remove(self):
        reg  = PortfolioCandidateRegistry()
        cand = _candidate("P1")
        reg.register(cand)
        reg.remove(cand.candidate_id)
        assert reg.get(cand.candidate_id) is None

    def test_remove_not_found(self):
        reg = PortfolioCandidateRegistry()
        with pytest.raises(PortfolioOptimizationNotFoundError):
            reg.remove("nonexistent")

    def test_approved(self):
        reg  = PortfolioCandidateRegistry()
        c1   = _candidate("P1")
        c2   = _candidate("P1")
        c2.reject()
        reg.register(c1)
        reg.register(c2)
        assert len(reg.approved()) == 1

    def test_for_portfolio(self):
        reg = PortfolioCandidateRegistry()
        c1  = _candidate("PA")
        c2  = _candidate("PB")
        reg.register(c1)
        reg.register(c2)
        assert len(reg.for_portfolio("PA")) == 1

    def test_contains(self):
        reg  = PortfolioCandidateRegistry()
        cand = _candidate("P1")
        reg.register(cand)
        assert cand.candidate_id in reg

    def test_update_existing(self):
        reg  = PortfolioCandidateRegistry(max_candidates=1)
        cand = _candidate("P1")
        reg.register(cand)
        # Re-registering same id should not raise
        reg.register(cand)
        assert reg.count == 1


# ===========================================================================
# 14. PortfolioOptimizationStrategy
# ===========================================================================

class TestOptimizationStrategy:
    def test_basic_creation(self):
        s = _strategy("mvp")
        assert s.name == "mvp"
        assert s.is_active

    def test_requires_non_empty_name(self):
        with pytest.raises(ValueError):
            PortfolioOptimizationStrategy(name="")

    def test_lifecycle(self):
        s = _strategy()
        s.deactivate()
        assert s.status == StrategyStatus.INACTIVE
        assert not s.is_active
        s.activate()
        assert s.is_active
        s.deprecate()
        assert s.status == StrategyStatus.DEPRECATED

    def test_objectives_and_constraints(self):
        s = _strategy(objectives=[_objective()], constraints=[_constraint()])
        assert len(s.objectives)  == 1
        assert len(s.constraints) == 1

    def test_to_dict(self):
        s = _strategy()
        d = s.to_dict()
        assert "strategy_id" in d
        assert d["is_active"]

    def test_repr(self):
        assert "PortfolioOptimizationStrategy" in repr(_strategy())


# ===========================================================================
# 15. PortfolioStrategyRegistry
# ===========================================================================

class TestStrategyRegistry:
    def test_register_and_get(self):
        reg = PortfolioStrategyRegistry()
        s   = _strategy("my_strat")
        reg.register(s)
        assert reg.get(s.strategy_id) is s

    def test_get_by_name(self):
        reg = PortfolioStrategyRegistry()
        s   = _strategy("named_strat")
        reg.register(s)
        assert reg.get_by_name("named_strat") is s

    def test_capacity_error(self):
        reg = PortfolioStrategyRegistry(max_strategies=1)
        reg.register(_strategy("s1"))
        with pytest.raises(PortfolioOptimizationCapacityError):
            reg.register(_strategy("s2"))

    def test_remove(self):
        reg = PortfolioStrategyRegistry()
        s   = _strategy()
        reg.register(s)
        reg.remove(s.strategy_id)
        assert reg.get(s.strategy_id) is None

    def test_default_strategy(self):
        reg = PortfolioStrategyRegistry()
        s   = _strategy("default")
        s2  = PortfolioOptimizationStrategy(name="default", is_default=True)
        reg.register(s2)
        assert reg.default_strategy() is s2

    def test_resolve_fallback(self):
        reg = PortfolioStrategyRegistry()
        s   = PortfolioOptimizationStrategy(name="default", is_default=True)
        reg.register(s)
        assert reg.resolve("nonexistent") is s

    def test_all_active(self):
        reg = PortfolioStrategyRegistry()
        s1  = _strategy("s1")
        s2  = _strategy("s2")
        s2.deactivate()
        reg.register(s1)
        reg.register(s2)
        active = reg.all_active()
        assert s1 in active
        assert s2 not in active

    def test_contains(self):
        reg = PortfolioStrategyRegistry()
        s   = _strategy()
        reg.register(s)
        assert s.strategy_id in reg


# ===========================================================================
# 16. PortfolioConstraintEngine
# ===========================================================================

class TestConstraintEngine:
    def test_evaluate_all_satisfied(self):
        eng     = PortfolioConstraintEngine()
        cands   = _candidate()
        cons    = [_constraint(True, "c1"), _constraint(True, "c2")]
        results = eng.evaluate(cands, cons, {})
        assert len(results) == 2
        assert eng.is_feasible(results)

    def test_hard_violation_infeasible(self):
        eng     = PortfolioConstraintEngine()
        cands   = _candidate()
        cons    = [_constraint(False, "c1", is_hard=True)]
        results = eng.evaluate(cands, cons, {})
        assert not eng.is_feasible(results)

    def test_soft_violation_still_feasible(self):
        eng     = PortfolioConstraintEngine()
        cands   = _candidate()
        cons    = [_constraint(False, "c1", is_hard=False)]
        results = eng.evaluate(cands, cons, {})
        assert eng.is_feasible(results)

    def test_violated_names(self):
        eng     = PortfolioConstraintEngine()
        cands   = _candidate()
        cons    = [_constraint(False, "bad_con")]
        results = eng.evaluate(cands, cons, {})
        assert "bad_con" in eng.violated_names(results)

    def test_counts(self):
        eng     = PortfolioConstraintEngine()
        cands   = _candidate()
        cons    = [_constraint(True, "ok"), _constraint(False, "bad")]
        results = eng.evaluate(cands, cons, {})
        assert eng.satisfied_count(results) == 1
        assert eng.violated_count(results)  == 1

    def test_total_penalty_soft(self):
        eng  = PortfolioConstraintEngine()
        cand = _candidate()
        con  = PortfolioConstraint(
            ConstraintType.RISK, "soft",
            lambda c, i: False, is_hard=False, penalty=0.3,
        )
        results = eng.evaluate(cand, [con], {})
        assert abs(eng.total_penalty(results) - 0.3) < 1e-9


# ===========================================================================
# 17. PortfolioAllocationEngine
# ===========================================================================

class TestAllocationEngine:
    def test_default_allocation(self):
        eng  = PortfolioAllocationEngine()
        cand = _candidate()
        plan = eng.generate(cand, _strategy(), {})
        assert plan.allocations == {"PORTFOLIO": 1.0}

    def test_explicit_allocation_from_inputs(self):
        eng   = PortfolioAllocationEngine()
        cand  = _candidate(inputs={"capital_allocation": {"equity": 0.6, "bonds": 0.4}})
        plan  = eng.generate(cand, _strategy(), {}, AllocationCapability.CAPITAL)
        assert plan.allocations["equity"] == pytest.approx(0.6)

    def test_equal_weight_from_position_snapshot(self):
        eng   = PortfolioAllocationEngine()
        cand  = _candidate()
        plan  = eng.generate(
            cand, _strategy(), {"position_snapshot": {"A": 100, "B": 100}},
            AllocationCapability.ASSET
        )
        assert plan.allocations["A"] == pytest.approx(0.5)
        assert plan.allocations["B"] == pytest.approx(0.5)

    def test_all_capabilities_produce_plan(self):
        eng  = PortfolioAllocationEngine()
        cand = _candidate()
        for cap in AllocationCapability:
            plan = eng.generate(cand, _strategy(), {}, cap)
            assert plan.allocation_type == cap
            assert len(plan.allocations) > 0

    def test_plan_has_candidate_and_portfolio_id(self):
        eng  = PortfolioAllocationEngine()
        cand = PortfolioCandidate("cid1", "PF1")
        plan = eng.generate(cand, _strategy(), {})
        assert plan.candidate_id == "cid1"
        assert plan.portfolio_id == "PF1"


# ===========================================================================
# 18. PortfolioRebalancingEngine
# ===========================================================================

class TestRebalancingEngine:
    def test_default_empty_actions(self):
        eng  = PortfolioRebalancingEngine()
        cand = _candidate()
        plan = eng.generate(cand, _strategy(), {})
        assert plan.actions == ()

    def test_explicit_actions_from_inputs(self):
        actions = [{"asset": "A", "current": 0.4, "target": 0.5, "delta": 0.1}]
        eng     = PortfolioRebalancingEngine()
        cand    = _candidate()
        plan    = eng.generate(
            cand, _strategy(), {"threshold_rebalancing": actions},
            RebalancingCapability.THRESHOLD
        )
        assert len(plan.actions) == 1

    def test_delta_from_snapshot(self):
        eng   = PortfolioRebalancingEngine()
        cand  = _candidate()
        inputs = {
            "position_snapshot":  {"A": 0.4, "B": 0.6},
            "target_allocation":  {"A": 0.5, "B": 0.5},
        }
        plan = eng.generate(cand, _strategy(), inputs)
        assert len(plan.actions) == 2

    def test_all_capabilities_produce_plan(self):
        eng  = PortfolioRebalancingEngine()
        cand = _candidate()
        for cap in RebalancingCapability:
            plan = eng.generate(cand, _strategy(), {}, cap)
            assert plan.rebalancing_type == cap


# ===========================================================================
# 19. PortfolioScoringEngine
# ===========================================================================

class TestScoringEngine:
    def test_weighted_score(self):
        eng  = PortfolioScoringEngine()
        cand = _candidate()
        objs = [_objective(0.8, weight=2.0), _objective(0.4, "o2", weight=1.0)]
        s    = eng.score(cand, objs, [], {})
        assert abs(s - (0.8*2 + 0.4*1) / 3.0) < 1e-6

    def test_hard_constraint_veto(self):
        eng  = PortfolioScoringEngine()
        cand = _candidate()
        objs = [_objective(0.9)]
        viol = ConstraintResult("c1", ConstraintType.CAPITAL, False, True, 0.0)
        s    = eng.score(cand, objs, [viol], {})
        assert s == 0.0

    def test_soft_constraint_penalty(self):
        eng  = PortfolioScoringEngine()
        cand = _candidate()
        objs = [_objective(1.0)]
        soft = ConstraintResult("c1", ConstraintType.RISK, False, False, 0.2)
        s    = eng.score(cand, objs, [soft], {}, ScoringMethod.COMPOSITE)
        assert s == pytest.approx(0.8)

    def test_no_objectives_returns_neutral(self):
        eng = PortfolioScoringEngine()
        s   = eng.score(_candidate(), [], [], {})
        assert s == 0.5

    def test_normalized_method(self):
        eng  = PortfolioScoringEngine()
        cand = _candidate()
        objs = [_objective(0.6), _objective(0.4, "o2")]
        s    = eng.score(cand, objs, [], {}, ScoringMethod.NORMALIZED)
        assert abs(s - 0.5) < 1e-6

    def test_pareto_method(self):
        eng  = PortfolioScoringEngine()
        cand = _candidate()
        objs = [_objective(0.9), _objective(0.3, "o2")]
        s    = eng.score(cand, objs, [], {}, ScoringMethod.PARETO)
        assert s == pytest.approx(0.3)

    def test_objective_results_list(self):
        eng  = PortfolioScoringEngine()
        cand = _candidate()
        objs = [_objective(0.7, "a"), _objective(0.5, "b")]
        r    = eng.objective_results(cand, objs, {})
        assert len(r) == 2
        assert {rr.objective_name for rr in r} == {"a", "b"}


# ===========================================================================
# 20. PortfolioRankingEngine
# ===========================================================================

class TestRankingEngine:
    def test_feasible_before_infeasible(self):
        eng  = PortfolioRankingEngine()
        s1   = _solution(0.3, is_feasible=False)
        s2   = _solution(0.7, is_feasible=True)
        ranked = eng.rank([s1, s2])
        assert ranked[0] is s2

    def test_higher_score_ranks_first(self):
        eng    = PortfolioRankingEngine()
        s1     = _solution(0.5)
        s2     = _solution(0.9)
        ranked = eng.rank([s1, s2])
        assert ranked[0] is s2
        assert ranked[0].rank == 1

    def test_ranks_assigned(self):
        eng    = PortfolioRankingEngine()
        sols   = [_solution(0.5), _solution(0.8), _solution(0.3)]
        ranked = eng.rank(sols)
        assert [s.rank for s in ranked] == [1, 2, 3]

    def test_empty_list(self):
        eng = PortfolioRankingEngine()
        assert eng.rank([]) == []


# ===========================================================================
# 21. PortfolioPriorityEngine
# ===========================================================================

class TestPriorityEngine:
    def test_single_solution_unchanged(self):
        eng = PortfolioPriorityEngine()
        sol = _solution()
        res = eng.apply_priority([sol])
        assert res[0] is sol

    def test_feasible_first(self):
        eng = PortfolioPriorityEngine()
        s1  = _solution(0.8, is_feasible=False)
        s2  = _solution(0.6, is_feasible=True)
        res = eng.apply_priority([s1, s2])
        assert res[0] is s2

    def test_fewer_violations_wins_tie(self):
        eng = PortfolioPriorityEngine()
        s1  = _solution(0.8, is_feasible=True, constraints_violated=2)
        s2  = _solution(0.8, is_feasible=True, constraints_violated=0)
        res = eng.apply_priority([s1, s2])
        assert res[0] is s2

    def test_more_objectives_wins_deep_tie(self):
        eng = PortfolioPriorityEngine()
        s1  = _solution(0.8, is_feasible=True, objectives_evaluated=1, constraints_violated=0)
        s2  = _solution(0.8, is_feasible=True, objectives_evaluated=5, constraints_violated=0)
        res = eng.apply_priority([s1, s2])
        assert res[0] is s2


# ===========================================================================
# 22. PortfolioSolutionSelector
# ===========================================================================

class TestSolutionSelector:
    def test_selects_top_feasible(self):
        sel = PortfolioSolutionSelector()
        s1  = _solution(0.9, is_feasible=True)
        s2  = _solution(0.6, is_feasible=True)
        res = sel.select([s1, s2])
        assert res is s1
        assert res.is_selected

    def test_skips_infeasible(self):
        sel = PortfolioSolutionSelector()
        s1  = _solution(0.9, is_feasible=False)
        s2  = _solution(0.6, is_feasible=True)
        res = sel.select([s1, s2])
        assert res is s2

    def test_no_feasible_returns_none(self):
        sel = PortfolioSolutionSelector()
        s1  = _solution(is_feasible=False)
        assert sel.select([s1]) is None

    def test_empty_returns_none(self):
        sel = PortfolioSolutionSelector()
        assert sel.select([]) is None


# ===========================================================================
# 23. PortfolioSolutionValidator
# ===========================================================================

class TestSolutionValidator:
    def test_valid_solution(self):
        val = PortfolioSolutionValidator()
        s   = _solution(score=0.7)
        s.rank = 1
        res = val.validate(s)
        assert res.is_valid
        assert len(res.failed_checks) == 0

    def test_invalid_empty_solution_id(self):
        val = PortfolioSolutionValidator()
        s   = _solution()
        s.solution_id = ""
        res = val.validate(s)
        assert not res.is_valid
        assert "solution_id_non_empty" in res.failed_checks

    def test_invalid_score_out_of_range(self):
        val = PortfolioSolutionValidator()
        s   = _solution()
        s.score = 2.0
        res = val.validate(s)
        assert not res.is_valid
        assert "score_in_range" in res.failed_checks

    def test_selected_with_zero_score_invalid(self):
        val = PortfolioSolutionValidator()
        s   = _solution(score=0.0, is_feasible=True)
        s.is_selected = True
        res = val.validate(s)
        assert not res.is_valid

    def test_to_dict(self):
        val = PortfolioSolutionValidator()
        s   = _solution()
        s.rank = 1
        d   = val.validate(s).to_dict()
        assert "is_valid" in d
        assert "failed_checks" in d


# ===========================================================================
# 24. PortfolioOptimizer (pipeline)
# ===========================================================================

class TestPortfolioOptimizer:
    def test_single_candidate_selected(self):
        opt   = PortfolioOptimizer()
        cand  = _candidate("P1")
        strat = _strategy()
        sols, selected = opt.optimize("opt1", [cand], strat, {})
        assert len(sols) == 1
        assert selected is not None
        assert selected.is_selected

    def test_multiple_candidates_ranked(self):
        opt   = PortfolioOptimizer()
        cands = [_candidate() for _ in range(5)]
        strat = _strategy()
        sols, _ = opt.optimize("opt1", cands, strat, {})
        assert len(sols) == 5
        assert sols[0].rank == 1

    def test_no_candidates_returns_empty(self):
        opt   = PortfolioOptimizer()
        strat = _strategy()
        sols, selected = opt.optimize("opt1", [], strat, {})
        assert sols == []
        assert selected is None

    def test_hard_constraint_makes_infeasible(self):
        opt   = PortfolioOptimizer()
        cand  = _candidate("P1")
        strat = _strategy(
            constraints=[PortfolioConstraint(
                ConstraintType.CAPITAL, "block_all",
                lambda c, i: False, is_hard=True,
            )]
        )
        sols, selected = opt.optimize("opt1", [cand], strat, {})
        assert selected is None
        assert not sols[0].is_feasible

    def test_solutions_have_allocation_plans(self):
        opt   = PortfolioOptimizer()
        cand  = _candidate("P1")
        strat = _strategy()
        sols, _ = opt.optimize("opt1", [cand], strat, {})
        assert sols[0].allocation_plan is not None

    def test_solutions_have_rebalancing_plans(self):
        opt   = PortfolioOptimizer()
        cand  = _candidate("P1")
        strat = _strategy()
        sols, _ = opt.optimize("opt1", [cand], strat, {})
        assert sols[0].rebalancing_plan is not None


# ===========================================================================
# 25. Events (10 factories)
# ===========================================================================

class TestEvents:
    def test_make_optimization_started(self):
        ev = make_optimization_started("opt1", "P1", 5)
        assert ev.event_type == OptimizationEventType.OPTIMIZATION_STARTED
        assert ev.payload["candidate_count"] == 5

    def test_make_candidates_loaded(self):
        ev = make_candidates_loaded("opt1", "P1", 3)
        assert ev.event_type == OptimizationEventType.CANDIDATES_LOADED
        assert ev.payload["count"] == 3

    def test_make_objectives_loaded(self):
        ev = make_objectives_loaded("opt1", "P1", 4)
        assert ev.event_type == OptimizationEventType.OBJECTIVES_LOADED
        assert ev.payload["count"] == 4

    def test_make_constraints_loaded(self):
        ev = make_constraints_loaded("opt1", "P1", 2)
        assert ev.event_type == OptimizationEventType.CONSTRAINTS_LOADED

    def test_make_allocation_generated(self):
        ev = make_allocation_generated("opt1", "P1", "cand1")
        assert ev.event_type == OptimizationEventType.ALLOCATION_GENERATED
        assert ev.payload["candidate_id"] == "cand1"

    def test_make_rebalancing_generated(self):
        ev = make_rebalancing_generated("opt1", "P1", "cand1")
        assert ev.event_type == OptimizationEventType.REBALANCING_GENERATED

    def test_make_optimization_completed(self):
        ev = make_optimization_completed("opt1", "P1", 0.5, "cand1")
        assert ev.event_type == OptimizationEventType.OPTIMIZATION_COMPLETED
        assert ev.payload["elapsed_s"] == pytest.approx(0.5)

    def test_make_portfolio_selected(self):
        ev = make_portfolio_selected("opt1", "P1", "cand1", 0.88)
        assert ev.event_type == OptimizationEventType.PORTFOLIO_SELECTED
        assert ev.payload["score"] == pytest.approx(0.88)

    def test_make_solution_validated(self):
        ev = make_solution_validated("opt1", "P1", is_valid=True)
        assert ev.event_type == OptimizationEventType.SOLUTION_VALIDATED
        assert ev.payload["is_valid"] is True

    def test_make_optimization_failed(self):
        ev = make_optimization_failed("opt1", "P1", "no feasible solution")
        assert ev.event_type == OptimizationEventType.OPTIMIZATION_FAILED
        assert "no feasible" in ev.payload["reason"]

    def test_event_immutable(self):
        ev = make_optimization_started("opt1", "P1")
        with pytest.raises((AttributeError, TypeError)):
            ev.event_type = OptimizationEventType.OPTIMIZATION_FAILED  # type: ignore

    def test_event_to_dict(self):
        ev = make_portfolio_selected("opt1", "P1", "c1")
        d  = ev.to_dict()
        assert "event_type" in d
        assert "payload" in d


# ===========================================================================
# 26. PortfolioOptimizationStatistics
# ===========================================================================

class TestStatistics:
    def test_initial_zeros(self):
        stats = PortfolioOptimizationStatistics()
        snap  = stats.snapshot()
        assert snap.total_optimizations == 0
        assert snap.successful == 0
        assert snap.failed == 0

    def test_record_request(self):
        stats = PortfolioOptimizationStatistics()
        stats.record_request()
        stats.record_request()
        assert stats.snapshot().total_requests == 2

    def test_record_optimization(self):
        stats = PortfolioOptimizationStatistics()
        stats.record_optimization_started(candidate_count=3)
        snap = stats.snapshot()
        assert snap.total_optimizations == 1
        assert snap.total_candidates    == 3

    def test_record_success(self):
        stats = PortfolioOptimizationStatistics()
        stats.record_optimization_started()
        stats.record_success(solution_count=2, selected=True)
        snap = stats.snapshot()
        assert snap.successful       == 1
        assert snap.total_solutions  == 2
        assert snap.total_selected   == 1

    def test_record_failure(self):
        stats = PortfolioOptimizationStatistics()
        stats.record_optimization_started()
        stats.record_failure()
        assert stats.snapshot().failed == 1

    def test_success_rate(self):
        stats = PortfolioOptimizationStatistics()
        stats.record_optimization_started()
        stats.record_success()
        snap = stats.snapshot()
        assert snap.to_dict()["success_rate"] == pytest.approx(1.0)

    def test_reset(self):
        stats = PortfolioOptimizationStatistics()
        stats.record_optimization_started()
        stats.record_success()
        stats.reset()
        snap = stats.snapshot()
        assert snap.total_optimizations == 0

    def test_snapshot_is_frozen(self):
        stats = PortfolioOptimizationStatistics()
        snap  = stats.snapshot()
        with pytest.raises((AttributeError, TypeError)):
            snap.successful = 99  # type: ignore[misc]


# ===========================================================================
# 27. PortfolioOptimizationHistory
# ===========================================================================

class TestHistory:
    def test_record_events(self):
        h  = PortfolioOptimizationHistory(max_events=5)
        ev = make_optimization_started("opt1", "P1")
        h.record_event(ev)
        assert h.recent_events(5) == [ev]

    def test_bounded_events(self):
        h = PortfolioOptimizationHistory(max_events=3)
        for i in range(5):
            h.record_event(make_optimization_started(f"opt{i}", "P1"))
        assert len(h.recent_events(10)) == 3

    def test_record_request_response(self):
        h    = PortfolioOptimizationHistory()
        req  = PortfolioOptimizationRequest.create("P1")
        resp = PortfolioOptimizationResponse.create_failure("r1", "P1", "o1", "err")
        h.record_request(req)
        h.record_response(resp)
        assert len(h.recent_requests(1)) == 1
        assert len(h.recent_responses(1)) == 1

    def test_summary(self):
        h = PortfolioOptimizationHistory()
        h.record_event(make_optimization_started("o1", "P1"))
        s = h.summary()
        assert s["event_count"]    == 1
        assert s["request_count"]  == 0
        assert s["response_count"] == 0

    def test_clear(self):
        h = PortfolioOptimizationHistory()
        h.record_event(make_optimization_started("o1", "P1"))
        h.clear()
        assert h.summary()["event_count"] == 0


# ===========================================================================
# 28. PortfolioOptimizationRegistry
# ===========================================================================

class TestOptimizationRegistry:
    def _resp(self, oid: str = "opt1") -> PortfolioOptimizationResponse:
        return PortfolioOptimizationResponse.create_failure("r1", "P1", oid, "err")

    def test_register_and_get(self):
        reg  = PortfolioOptimizationRegistry()
        resp = self._resp("opt1")
        reg.register(resp)
        assert reg.get("opt1") is resp

    def test_capacity_error(self):
        reg = PortfolioOptimizationRegistry(max_optimizations=1)
        reg.register(self._resp("opt1"))
        with pytest.raises(PortfolioOptimizationCapacityError):
            reg.register(self._resp("opt2"))

    def test_remove(self):
        reg  = PortfolioOptimizationRegistry()
        resp = self._resp()
        reg.register(resp)
        reg.remove("opt1")
        assert reg.get("opt1") is None

    def test_for_portfolio(self):
        reg  = PortfolioOptimizationRegistry()
        r1   = PortfolioOptimizationResponse.create_failure("r1", "PA", "opt1", "e")
        r2   = PortfolioOptimizationResponse.create_failure("r2", "PB", "opt2", "e")
        reg.register(r1)
        reg.register(r2)
        assert len(reg.for_portfolio("PA")) == 1

    def test_get_or_raise(self):
        reg = PortfolioOptimizationRegistry()
        with pytest.raises(PortfolioOptimizationNotFoundError):
            reg.get_or_raise("nonexistent")


# ===========================================================================
# 29. PortfolioOptimizationFactory
# ===========================================================================

class TestFactory:
    def test_create_request(self):
        req = PortfolioOptimizationFactory.create_request("P1")
        assert req.portfolio_id == "P1"

    def test_create_candidate(self):
        cand = PortfolioOptimizationFactory.create_candidate("P1")
        assert cand.portfolio_id == "P1"

    def test_create_strategy(self):
        s = PortfolioOptimizationFactory.create_strategy("my_strat")
        assert s.name == "my_strat"

    def test_create_default_strategy(self):
        s = PortfolioOptimizationFactory.create_default_strategy()
        assert s.is_default
        assert s.name == "default"

    def test_create_objective(self):
        obj = PortfolioOptimizationFactory.create_objective(
            OptimizationObjective.MAXIMIZE_LIQUIDITY,
            "liq_obj",
            lambda c, i: 0.9,
        )
        assert obj.name == "liq_obj"
        result = obj.score(_candidate(), {})
        assert result.score == pytest.approx(0.9)

    def test_create_constraint(self):
        con = PortfolioOptimizationFactory.create_constraint(
            ConstraintType.LIQUIDITY,
            "liq_con",
            lambda c, i: True,
            is_hard=False,
        )
        assert not con.is_hard
        result = con.evaluate(_candidate(), {})
        assert result.satisfied


# ===========================================================================
# 30. PortfolioOptimizationEngine (primary interface)
# ===========================================================================

class TestOptimizationEngine:
    def _started_engine(self) -> PortfolioOptimizationEngine:
        engine = PortfolioOptimizationEngine()
        engine.start()
        return engine

    def test_guard_before_start(self):
        engine = PortfolioOptimizationEngine()
        with pytest.raises(PortfolioOptimizationNotRunningError):
            engine.optimize("P1")

    def test_start_stop(self):
        engine = self._started_engine()
        assert engine.lifecycle_state().value == "running"
        engine.stop()

    def test_optimize_basic(self):
        engine = self._started_engine()
        cands  = [_candidate("P1") for _ in range(3)]
        resp   = engine.optimize("P1", candidates=cands)
        assert resp.is_success
        engine.stop()

    def test_optimize_no_candidates(self):
        engine = self._started_engine()
        resp   = engine.optimize("P1")  # no candidates, empty registry
        assert resp.is_failure
        engine.stop()

    def test_register_strategy(self):
        engine = self._started_engine()
        strat  = _strategy("custom_strat")
        engine.register_strategy(strat)
        found = engine.get_strategy(strat.strategy_id)
        assert found is strat
        engine.stop()

    def test_list_strategies(self):
        engine = self._started_engine()
        strats = engine.list_strategies()
        # At minimum the default strategy is registered
        assert len(strats) >= 1
        engine.stop()

    def test_register_candidate(self):
        engine = self._started_engine()
        cand   = _candidate("P1")
        engine.register_candidate(cand)
        assert engine.get_candidate(cand.candidate_id) is cand
        engine.stop()

    def test_submit_request(self):
        engine = self._started_engine()
        req    = PortfolioOptimizationRequest.create(
            "P1", candidates=[_candidate("P1")]
        )
        resp   = engine.submit(req)
        assert resp.request_id == req.request_id
        engine.stop()

    def test_validate_valid_request(self):
        engine  = self._started_engine()
        req     = PortfolioOptimizationRequest.create(
            "P1", candidates=[_candidate("P1")]
        )
        result  = engine.validate(req)
        assert result["is_valid"]
        engine.stop()

    def test_status(self):
        engine = self._started_engine()
        status = engine.status()
        assert status.lifecycle_state == "running"
        assert status.is_healthy
        assert status.registered_strategies >= 1
        engine.stop()

    def test_statistics(self):
        engine = self._started_engine()
        engine.optimize("P1", candidates=[_candidate("P1")])
        stats  = engine.statistics()
        assert stats["total_optimizations"] >= 1
        engine.stop()

    def test_health(self):
        engine = self._started_engine()
        h      = engine.health()
        assert h["is_healthy"] is True
        engine.stop()

    def test_history(self):
        engine = self._started_engine()
        engine.optimize("P1", candidates=[_candidate("P1")])
        h      = engine.history()
        assert "event_count" in h
        engine.stop()

    def test_event_listener_receives_event(self):
        engine = self._started_engine()
        events = []
        engine.add_listener(events.append)
        engine.optimize("P1", candidates=[_candidate("P1")])
        assert len(events) > 0
        engine.stop()

    def test_remove_listener(self):
        engine = self._started_engine()
        events = []
        engine.add_listener(events.append)
        engine.remove_listener(events.append)
        engine.optimize("P1", candidates=[_candidate("P1")])
        assert len(events) == 0
        engine.stop()

    def test_guard_after_stop(self):
        engine = self._started_engine()
        engine.stop()
        with pytest.raises(PortfolioOptimizationNotRunningError):
            engine.optimize("P1")

    def test_status_to_dict(self):
        engine = self._started_engine()
        d      = engine.status().to_dict()
        assert "lifecycle_state" in d
        assert "framework_version" in d
        engine.stop()


# ===========================================================================
# 31. Integration — full pipeline
# ===========================================================================

class TestIntegration:
    def test_end_to_end_success(self):
        engine = PortfolioOptimizationEngine()
        engine.start()

        # Custom strategy with objectives and constraints
        strat = PortfolioOptimizationStrategy(
            name       = "institutional",
            objectives = [
                PortfolioObjective(
                    OptimizationObjective.MAXIMIZE_RISK_ADJUSTED_RETURN,
                    "sharpe", lambda c, i: 0.85,
                ),
                PortfolioObjective(
                    OptimizationObjective.MINIMIZE_DRAWDOWN,
                    "drawdown", lambda c, i: 0.70, weight=0.5,
                ),
            ],
            constraints = [
                PortfolioConstraint(
                    ConstraintType.EXPOSURE, "max_exposure",
                    lambda c, i: True, is_hard=True,
                ),
            ],
            scoring_method = ScoringMethod.WEIGHTED,
        )
        engine.register_strategy(strat)

        candidates = [
            PortfolioCandidate(
                portfolio_id = "PF1",
                inputs = {"position_snapshot": {"NIFTY": 0.5, "BANKNIFTY": 0.5}},
            )
            for _ in range(4)
        ]

        resp = engine.optimize(
            "PF1",
            candidates    = candidates,
            strategy_name = "institutional",
            inputs        = {"market_regime": "bull"},
        )

        assert resp.is_success
        assert resp.selected_solution is not None
        assert resp.selected_solution.is_selected
        assert resp.summary.total_candidates == 4
        assert resp.summary.feasible_candidates == 4
        engine.stop()

    def test_all_infeasible_returns_failure(self):
        engine = PortfolioOptimizationEngine()
        engine.start()

        blocking_strat = PortfolioOptimizationStrategy(
            name        = "blocking",
            objectives  = [_objective()],
            constraints = [
                PortfolioConstraint(
                    ConstraintType.CAPITAL, "block_all",
                    lambda c, i: False, is_hard=True,
                ),
            ],
        )
        engine.register_strategy(blocking_strat)

        resp = engine.optimize(
            "P1",
            candidates    = [_candidate("P1"), _candidate("P1")],
            strategy_name = "blocking",
        )

        assert not resp.is_failure   # pipeline ran without error
        assert resp.selected_solution is None
        assert resp.summary.feasible_candidates == 0
        engine.stop()

    def test_response_stored_in_registry(self):
        engine = PortfolioOptimizationEngine()
        engine.start()

        cands = [_candidate("P1")]
        resp  = engine.optimize("P1", candidates=cands)
        found = engine._opt_registry.get(resp.optimization_id)
        assert found is resp
        engine.stop()

    def test_multiple_optimizations_accumulate_stats(self):
        engine = PortfolioOptimizationEngine()
        engine.start()

        for _ in range(5):
            engine.optimize("P1", candidates=[_candidate("P1")])

        stats = engine.statistics()
        assert stats["total_optimizations"] >= 5
        engine.stop()


# ===========================================================================
# 32. Thread-safety
# ===========================================================================

class TestThreadSafety:
    def test_concurrent_optimizations(self):
        engine = PortfolioOptimizationEngine()
        engine.start()

        errors  = []
        results = []

        def run():
            try:
                resp = engine.optimize(
                    "P1", candidates=[_candidate("P1") for _ in range(2)]
                )
                results.append(resp)
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=run) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == []
        assert len(results) == 10
        engine.stop()

    def test_concurrent_registry_writes(self):
        reg    = PortfolioCandidateRegistry(max_candidates=1000)
        errors = []

        def add():
            try:
                reg.register(_candidate("P1"))
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=add) for _ in range(50)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == []
        assert reg.count == 50

    def test_concurrent_strategy_registry(self):
        reg    = PortfolioStrategyRegistry(max_strategies=1000)
        errors = []

        def add():
            try:
                s = PortfolioOptimizationStrategy(name=str(uuid.uuid4()))
                reg.register(s)
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=add) for _ in range(50)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == []
        assert reg.count == 50
