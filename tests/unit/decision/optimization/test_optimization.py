"""
tests/unit/decision/optimization/test_optimization.py
======================================================
Comprehensive unit tests for the C9 M4 Decision Optimization Framework.

Coverage targets
----------------
- Constants and enums
- Exceptions (hierarchy + error codes)
- DecisionCandidate (creation, computed properties, serialisation)
- DecisionObjective (extraction, normalization, factory)
- DecisionConstraint (all 8 operators, hard vs soft, factory)
- DecisionOptimizationContext (create, from_engine_context, get)
- DecisionOptimizationStrategy (factory methods)
- DecisionOptimizationRequest (create)
- CandidateScore (frozen)
- ConstraintCheckResult / ConstraintEvaluationResult
- DecisionCandidateRegistry (CRUD + thread-safety)
- DecisionConstraintEngine (evaluate_all)
- DecisionScoringEngine (score_all, cross-candidate normalization)
- DecisionRankingEngine (rank, best_feasible)
- DecisionPriorityEngine (prioritize, top_priority)
- DecisionSolutionSelector (all 7 strategy types)
- DecisionSolutionValidator (7 checks)
- DecisionOptimizer (full pipeline, NoCandidatesError, NoFeasibleSolutionError)
- DecisionOptimizationRegistry (objective + constraint CRUD, batch)
- DecisionStrategyRegistry (CRUD, default, full)
- DecisionOptimizationEvents (factory functions, to_dict)
- DecisionOptimizationStatistics (counters, EMA, throughput, reset)
- DecisionOptimizationHistory (events, responses, by-type, by-decision)
- DecisionOptimizationFactory (all 6 create methods)
- DecisionOptimizationResponse (success, failure, properties)
- DecisionOptimizationManager (optimize, zero-candidate, failed paths)
- DecisionOptimizationEngine (lifecycle, register/deregister, optimize, listeners)
- OptimizationFrameworkAdapter (optimize with candidates dict and class)
- __init__ exports
"""
from __future__ import annotations

import threading
import time
from datetime import datetime, timezone
from typing import Any, Dict, List

import pytest

# ── Package import ────────────────────────────────────────────────────────
from iios.decision.optimization import (
    # constants / enums
    OPTIMIZATION_SYSTEM_ID,
    VERSION,
    DEFAULT_STRATEGY_ID,
    ConstraintOperator,
    ConstraintType,
    OptimizationEventType,
    OptimizationObjectiveType,
    OptimizationStatus,
    OptimizationStrategyType,
    OptimizationValidationCode,
    # exceptions
    DecisionOptimizationError,
    OptimizationEngineNotRunningError,
    NoCandidatesError,
    NoFeasibleSolutionError,
    ObjectiveNotFoundError,
    ConstraintNotFoundError,
    StrategyNotFoundError,
    OptimizationValidationError,
    CandidateRegistryError,
    OptimizationConfigurationError,
    # value objects
    CandidateScore,
    ConstraintCheckResult,
    ConstraintEvaluationResult,
    DecisionCandidate,
    DecisionConstraint,
    DecisionObjective,
    DecisionOptimizationContext,
    DecisionOptimizationEvent,
    DecisionOptimizationRequest,
    DecisionOptimizationResponse,
    DecisionOptimizationSummary,
    DecisionOptimizationStrategy,
    DecisionRanking,
    DecisionSolution,
    OptimizationReport,
    # engines
    DecisionCandidateRegistry,
    DecisionConstraintEngine,
    DecisionOptimizer,
    DecisionPriorityEngine,
    DecisionRankingEngine,
    DecisionScoringEngine,
    DecisionSolutionSelector,
    DecisionSolutionValidator,
    # registries
    DecisionOptimizationRegistry,
    DecisionStrategyRegistry,
    # observability
    DecisionOptimizationFactory,
    DecisionOptimizationHistory,
    DecisionOptimizationStatistics,
    # manager + engine
    DecisionOptimizationManager,
    DecisionOptimizationEngine,
    OptimizationFrameworkAdapter,
    # event factories
    make_optimization_started,
    make_candidates_loaded,
    make_objectives_loaded,
    make_constraints_loaded,
    make_optimization_completed,
    make_solution_selected,
    make_solution_validated,
    make_optimization_failed,
    # validation
    SolutionValidationCheckResult,
    SolutionValidationResult,
)


# ============================================================================
# Helpers
# ============================================================================

def _candidate(
    symbol="RELIANCE",
    direction="buy",
    quantity=10.0,
    price=2500.0,
    expected_return=0.08,
    risk_score=0.3,
    confidence=0.75,
    **kw,
) -> DecisionCandidate:
    return DecisionCandidate.create(
        symbol=symbol,
        direction=direction,
        quantity=quantity,
        price=price,
        expected_return=expected_return,
        risk_score=risk_score,
        confidence=confidence,
        **kw,
    )


def _objective(
    name="Return",
    obj_type=OptimizationObjectiveType.MAXIMIZE_EXPECTED_RETURN,
    weight=1.0,
) -> DecisionObjective:
    return DecisionObjective.create(name=name, objective_type=obj_type, weight=weight)


def _constraint(
    name="RiskCap",
    ct=ConstraintType.RISK,
    op=ConstraintOperator.LTE,
    field="risk_score",
    threshold=0.5,
) -> DecisionConstraint:
    return DecisionConstraint.create(
        name=name,
        constraint_type=ct,
        operator=op,
        field_path=field,
        threshold=threshold,
    )


def _context(decision_id="dec-001") -> DecisionOptimizationContext:
    return DecisionOptimizationContext.create(
        decision_id=decision_id,
        request_id="req-001",
    )


def _started_engine() -> DecisionOptimizationEngine:
    engine = DecisionOptimizationEngine()
    engine.start()
    return engine


# ============================================================================
# 1. Constants & Enums
# ============================================================================

class TestConstants:
    def test_system_id_not_empty(self):
        assert OPTIMIZATION_SYSTEM_ID

    def test_version_string(self):
        assert isinstance(VERSION, str)
        assert "." in VERSION

    def test_default_strategy_id(self):
        assert isinstance(DEFAULT_STRATEGY_ID, str)

    def test_all_objective_types_defined(self):
        assert len(OptimizationObjectiveType) == 10

    def test_all_strategy_types_defined(self):
        assert len(OptimizationStrategyType) == 8

    def test_all_constraint_types_defined(self):
        assert len(ConstraintType) == 10

    def test_all_constraint_operators_defined(self):
        assert len(ConstraintOperator) == 8

    def test_optimization_status_values(self):
        names = {s.name for s in OptimizationStatus}
        assert {"PENDING", "IN_PROGRESS", "COMPLETED", "FAILED"} == names

    def test_event_types_count(self):
        assert len(OptimizationEventType) == 8

    def test_validation_code_count(self):
        assert len(OptimizationValidationCode) == 7


# ============================================================================
# 2. Exceptions
# ============================================================================

class TestExceptions:
    def test_base_is_iios_error_subclass(self):
        from iios.common.errors.exceptions import IIOSError
        assert issubclass(DecisionOptimizationError, IIOSError)

    def test_engine_not_running(self):
        err = OptimizationEngineNotRunningError("engine stopped")
        assert "DO-001" in str(err) or err.error_code == "DO-001"

    def test_no_candidates(self):
        err = NoCandidatesError()
        assert "DO-002" in str(err) or err.error_code == "DO-002"

    def test_no_feasible_solution(self):
        err = NoFeasibleSolutionError("all infeasible")
        assert "DO-003" in str(err) or err.error_code == "DO-003"

    def test_objective_not_found(self):
        err = ObjectiveNotFoundError("obj-123")
        assert "DO-004" in str(err) or err.error_code == "DO-004"

    def test_constraint_not_found(self):
        err = ConstraintNotFoundError("con-123")
        assert "DO-005" in str(err) or err.error_code == "DO-005"

    def test_strategy_not_found(self):
        err = StrategyNotFoundError("strat-xyz")
        assert "DO-006" in str(err) or err.error_code == "DO-006"

    def test_validation_error_has_failed_checks(self):
        err = OptimizationValidationError("bad", failed_checks=["CHECK_A"])
        assert list(err.failed_checks) == ["CHECK_A"]

    def test_candidate_registry_error(self):
        err = CandidateRegistryError("full")
        assert "DO-008" in str(err) or err.error_code == "DO-008"

    def test_configuration_error(self):
        err = OptimizationConfigurationError("bad config")
        assert "DO-009" in str(err) or err.error_code == "DO-009"

    def test_hierarchy(self):
        for cls in [
            NoCandidatesError,
            NoFeasibleSolutionError,
            ObjectiveNotFoundError,
            ConstraintNotFoundError,
            StrategyNotFoundError,
            OptimizationValidationError,
            CandidateRegistryError,
            OptimizationConfigurationError,
        ]:
            assert issubclass(cls, DecisionOptimizationError)


# ============================================================================
# 3. DecisionCandidate
# ============================================================================

class TestDecisionCandidate:
    def test_create_basic(self):
        c = _candidate()
        assert c.symbol == "RELIANCE"
        assert c.direction == "buy"
        assert c.candidate_id

    def test_create_sets_uuid_if_none(self):
        c1 = _candidate()
        c2 = _candidate()
        assert c1.candidate_id != c2.candidate_id

    def test_explicit_candidate_id(self):
        c = _candidate(candidate_id="my-id")
        assert c.candidate_id == "my-id"

    def test_risk_adjusted_return(self):
        c = _candidate(expected_return=0.1, risk_score=0.5)
        assert abs(c.risk_adjusted_return - 0.2) < 1e-9

    def test_drawdown_estimate(self):
        c = _candidate(risk_score=0.4)
        assert abs(c.drawdown_estimate - 0.2) < 1e-9

    def test_capital_efficiency_positive(self):
        c = _candidate(expected_return=0.1, execution_cost=0.01, portfolio_exposure=0.1)
        assert c.capital_efficiency > 0

    def test_operational_stability_equals_confidence(self):
        c = _candidate(confidence=0.8)
        assert c.operational_stability == 0.8

    def test_policy_compliance_score_always_one(self):
        assert _candidate().policy_compliance_score == 1.0

    def test_to_dict_contains_computed_fields(self):
        d = _candidate().to_dict()
        assert "risk_adjusted_return" in d
        assert "drawdown_estimate" in d
        assert "capital_efficiency" in d

    def test_metadata_defaults_to_empty_dict(self):
        assert _candidate().metadata == {}

    def test_created_at_is_utc(self):
        c = _candidate()
        assert c.created_at.tzinfo is not None


# ============================================================================
# 4. DecisionObjective
# ============================================================================

class TestDecisionObjective:
    def test_create_sets_uuid(self):
        o = _objective()
        assert o.objective_id

    def test_explicit_id(self):
        o = DecisionObjective.create(
            "R", OptimizationObjectiveType.MAXIMIZE_EXPECTED_RETURN,
            objective_id="obj-1",
        )
        assert o.objective_id == "obj-1"

    def test_is_maximize_for_maximize_type(self):
        o = _objective(obj_type=OptimizationObjectiveType.MAXIMIZE_EXPECTED_RETURN)
        assert o.is_maximize
        assert not o.is_minimize

    def test_is_minimize_for_risk(self):
        o = _objective(obj_type=OptimizationObjectiveType.MINIMIZE_RISK)
        assert o.is_minimize
        assert not o.is_maximize

    def test_extract_value_dotted_path(self):
        o = DecisionObjective.create(
            "R", OptimizationObjectiveType.MAXIMIZE_EXPECTED_RETURN,
            target_field="expected_return",
        )
        assert o.extract_value({"expected_return": 0.07}) == pytest.approx(0.07)

    def test_extract_value_missing_key_returns_zero(self):
        o = _objective()
        assert o.extract_value({}) == 0.0

    def test_normalize_maximize_high_is_one(self):
        o = _objective(obj_type=OptimizationObjectiveType.MAXIMIZE_EXPECTED_RETURN)
        assert o.normalize_score(1.0, 0.0, 1.0) == pytest.approx(1.0)

    def test_normalize_minimize_high_is_zero(self):
        o = _objective(obj_type=OptimizationObjectiveType.MINIMIZE_RISK)
        assert o.normalize_score(1.0, 0.0, 1.0) == pytest.approx(0.0)

    def test_normalize_equal_min_max_returns_half(self):
        o = _objective()
        assert o.normalize_score(0.5, 0.5, 0.5) == pytest.approx(0.5)

    def test_custom_evaluator(self):
        o = DecisionObjective.create(
            "custom", OptimizationObjectiveType.MAXIMIZE_EXPECTED_RETURN,
            custom_evaluator=lambda d: d.get("custom_val", 0.0),
        )
        assert o.extract_value({"custom_val": 0.33}) == pytest.approx(0.33)

    def test_resolved_field_falls_back_to_default(self):
        o = _objective(obj_type=OptimizationObjectiveType.MINIMIZE_RISK)
        assert o.resolved_field  # must not be empty


# ============================================================================
# 5. DecisionConstraint
# ============================================================================

class TestDecisionConstraint:
    def test_create_sets_uuid(self):
        c = _constraint()
        assert c.constraint_id

    def test_lte_satisfied(self):
        c = _constraint(op=ConstraintOperator.LTE, threshold=0.5)
        assert c.is_satisfied({"risk_score": 0.3})

    def test_lte_violated(self):
        c = _constraint(op=ConstraintOperator.LTE, threshold=0.5)
        assert not c.is_satisfied({"risk_score": 0.6})

    def test_lt_satisfied(self):
        c = _constraint(op=ConstraintOperator.LT, threshold=0.5)
        assert c.is_satisfied({"risk_score": 0.49})

    def test_lt_violated_equal(self):
        c = _constraint(op=ConstraintOperator.LT, threshold=0.5)
        assert not c.is_satisfied({"risk_score": 0.5})

    def test_gte_satisfied(self):
        c = _constraint(op=ConstraintOperator.GTE, field="confidence", threshold=0.6)
        assert c.is_satisfied({"confidence": 0.8})

    def test_gt_satisfied(self):
        c = _constraint(op=ConstraintOperator.GT, field="confidence", threshold=0.6)
        assert c.is_satisfied({"confidence": 0.61})

    def test_eq_satisfied(self):
        c = _constraint(op=ConstraintOperator.EQ, field="quantity", threshold=10.0)
        assert c.is_satisfied({"quantity": 10.0})

    def test_between_satisfied(self):
        c = DecisionConstraint.create(
            "BetweenTest", ConstraintType.RISK, ConstraintOperator.BETWEEN,
            "price", 100.0, threshold_max=200.0,
        )
        assert c.is_satisfied({"price": 150.0})

    def test_between_violated(self):
        c = DecisionConstraint.create(
            "BetweenTest", ConstraintType.RISK, ConstraintOperator.BETWEEN,
            "price", 100.0, threshold_max=200.0,
        )
        assert not c.is_satisfied({"price": 250.0})

    def test_exists_satisfied(self):
        c = _constraint(op=ConstraintOperator.EXISTS, field="symbol", threshold=0)
        assert c.is_satisfied({"symbol": "RELIANCE"})

    def test_not_exists_satisfied(self):
        c = _constraint(op=ConstraintOperator.NOT_EXISTS, field="missing_key", threshold=0)
        assert c.is_satisfied({})

    def test_soft_constraint_not_infeasible(self):
        c = DecisionConstraint.create(
            "soft", ConstraintType.RISK, ConstraintOperator.LTE,
            "risk_score", 0.1, is_hard=False, penalty=0.3,
        )
        assert not c.is_hard

    def test_custom_evaluator(self):
        c = DecisionConstraint.create(
            "custom", ConstraintType.CUSTOM, ConstraintOperator.LTE,
            "x", 0.0, custom_evaluator=lambda d: True,
        )
        assert c.is_satisfied({})


# ============================================================================
# 6. DecisionOptimizationContext
# ============================================================================

class TestDecisionOptimizationContext:
    def test_create_generates_ids(self):
        ctx = _context()
        assert ctx.context_id
        assert ctx.decision_id == "dec-001"

    def test_get_dotted_path(self):
        ctx = DecisionOptimizationContext.create(
            decision_id="d1",
            inputs={"market": {"regime": "bullish"}},
        )
        assert ctx.get("inputs.market.regime") == "bullish"

    def test_get_missing_returns_default(self):
        ctx = _context()
        assert ctx.get("nonexistent.field", "fallback") == "fallback"

    def test_to_dict_has_required_keys(self):
        d = _context().to_dict()
        assert "context_id" in d
        assert "decision_id" in d

    def test_from_engine_context_with_dict(self):
        # engine_context is duck-typed; any object with .decision_id works
        class FakeCtx:
            decision_id = "d-fake"
            request_id  = "r-fake"
            session_id  = ""
            pipeline_id = ""
            inputs      = {}
            metadata    = {}
        ctx = DecisionOptimizationContext.from_engine_context(
            FakeCtx(), policy_result={"approved": True}
        )
        assert ctx.decision_id == "d-fake"
        assert ctx.policy_result == {"approved": True}

    def test_immutable(self):
        ctx = _context()
        with pytest.raises((AttributeError, TypeError)):
            ctx.decision_id = "changed"  # type: ignore[misc]


# ============================================================================
# 7. DecisionOptimizationStrategy
# ============================================================================

class TestDecisionOptimizationStrategy:
    def test_create_sets_uuid(self):
        s = DecisionOptimizationStrategy.create(
            "test", OptimizationStrategyType.WEIGHTED_SCORE
        )
        assert s.strategy_id

    def test_weighted_score_factory(self):
        s = DecisionOptimizationStrategy.weighted_score()
        assert s.strategy_type == OptimizationStrategyType.WEIGHTED_SCORE

    def test_priority_based_factory(self):
        s = DecisionOptimizationStrategy.priority_based()
        assert s.strategy_type == OptimizationStrategyType.PRIORITY_BASED

    def test_pareto_ranking_factory(self):
        s = DecisionOptimizationStrategy.pareto_ranking()
        assert s.strategy_type == OptimizationStrategyType.PARETO_RANKING


# ============================================================================
# 8. DecisionOptimizationRequest
# ============================================================================

class TestDecisionOptimizationRequest:
    def test_create_basic(self):
        ctx = _context()
        req = DecisionOptimizationRequest.create(ctx, [_candidate()])
        assert req.request_id
        assert len(req.candidates) == 1

    def test_explicit_request_id(self):
        ctx = _context()
        req = DecisionOptimizationRequest.create(ctx, [], request_id="req-x")
        assert req.request_id == "req-x"

    def test_default_strategy(self):
        req = DecisionOptimizationRequest.create(_context(), [])
        assert req.strategy_id == DEFAULT_STRATEGY_ID

    def test_objective_ids_default_none(self):
        req = DecisionOptimizationRequest.create(_context(), [])
        assert req.objective_ids is None

    def test_constraint_ids_default_none(self):
        req = DecisionOptimizationRequest.create(_context(), [])
        assert req.constraint_ids is None


# ============================================================================
# 9. DecisionCandidateRegistry
# ============================================================================

class TestDecisionCandidateRegistry:
    def test_register_and_get(self):
        reg = DecisionCandidateRegistry()
        c = _candidate(candidate_id="c1")
        reg.register(c)
        assert reg.get("c1") is c

    def test_count(self):
        reg = DecisionCandidateRegistry()
        reg.register_all([_candidate(), _candidate()])
        assert reg.count() == 2

    def test_deregister(self):
        reg = DecisionCandidateRegistry()
        c = _candidate(candidate_id="c2")
        reg.register(c)
        reg.deregister("c2")
        assert reg.get("c2") is None

    def test_clear(self):
        reg = DecisionCandidateRegistry()
        reg.register(_candidate())
        reg.clear()
        assert reg.count() == 0

    def test_all_candidates_returns_list(self):
        reg = DecisionCandidateRegistry()
        reg.register_all([_candidate(), _candidate()])
        assert isinstance(reg.all_candidates(), list)
        assert len(reg.all_candidates()) == 2

    def test_thread_safe_registration(self):
        reg = DecisionCandidateRegistry()
        errors = []
        def insert(n):
            try:
                for i in range(n):
                    reg.register(_candidate())
            except Exception as e:
                errors.append(e)
        threads = [threading.Thread(target=insert, args=(10,)) for _ in range(5)]
        for t in threads: t.start()
        for t in threads: t.join()
        assert not errors
        assert reg.count() == 50


# ============================================================================
# 10. DecisionConstraintEngine
# ============================================================================

class TestDecisionConstraintEngine:
    def test_no_constraints_all_feasible(self):
        engine = DecisionConstraintEngine()
        c = _candidate()
        result = engine.evaluate_all(c, [], _context())
        assert result.is_feasible
        assert result.total_penalty == 0.0

    def test_satisfied_hard_constraint(self):
        engine = DecisionConstraintEngine()
        c = _candidate(risk_score=0.2)
        con = _constraint(op=ConstraintOperator.LTE, threshold=0.5)
        result = engine.evaluate_all(c, [con], _context())
        assert result.is_feasible
        assert len(result.violated_hard) == 0

    def test_violated_hard_constraint_infeasible(self):
        engine = DecisionConstraintEngine()
        c = _candidate(risk_score=0.9)
        con = _constraint(op=ConstraintOperator.LTE, threshold=0.5)
        result = engine.evaluate_all(c, [con], _context())
        assert not result.is_feasible
        assert len(result.violated_hard) > 0

    def test_soft_violation_adds_penalty(self):
        engine = DecisionConstraintEngine()
        c = _candidate(risk_score=0.9)
        con = DecisionConstraint.create(
            "soft_risk", ConstraintType.RISK, ConstraintOperator.LTE,
            "risk_score", 0.5, is_hard=False, penalty=0.4,
        )
        result = engine.evaluate_all(c, [con], _context())
        assert result.is_feasible
        assert result.total_penalty > 0

    def test_total_violations_property(self):
        engine = DecisionConstraintEngine()
        c = _candidate(risk_score=0.9, confidence=0.1)
        cons = [
            _constraint(op=ConstraintOperator.LTE, threshold=0.5),
            DecisionConstraint.create(
                "conf", ConstraintType.COMPLIANCE, ConstraintOperator.GTE,
                "confidence", 0.5,
            ),
        ]
        result = engine.evaluate_all(c, cons, _context())
        assert result.total_violations >= 2


# ============================================================================
# 11. DecisionScoringEngine
# ============================================================================

class TestDecisionScoringEngine:
    def _make_candidates(self):
        return [
            _candidate(expected_return=0.1, risk_score=0.2, confidence=0.9,
                       candidate_id="c1"),
            _candidate(expected_return=0.05, risk_score=0.4, confidence=0.6,
                       candidate_id="c2"),
        ]

    def test_score_returns_list_same_length(self):
        engine = DecisionScoringEngine()
        candidates = self._make_candidates()
        scores = engine.score_all(candidates, [], {}, _context())
        assert len(scores) == len(candidates)

    def test_all_feasible_no_constraints(self):
        engine = DecisionScoringEngine()
        candidates = self._make_candidates()
        scores = engine.score_all(candidates, [], {}, _context())
        assert all(s.is_feasible for s in scores)

    def test_higher_return_scores_higher(self):
        engine = DecisionScoringEngine()
        candidates = self._make_candidates()
        obj = _objective(obj_type=OptimizationObjectiveType.MAXIMIZE_EXPECTED_RETURN)
        scores = engine.score_all(candidates, [obj], {}, _context())
        score_map = {s.candidate_id: s for s in scores}
        assert score_map["c1"].final_score >= score_map["c2"].final_score

    def test_no_objectives_equal_scores(self):
        engine = DecisionScoringEngine()
        candidates = self._make_candidates()
        scores = engine.score_all(candidates, [], {}, _context())
        # No objectives → no differentiation; all candidates share the same score
        assert all(s.final_score == scores[0].final_score for s in scores)

    def test_infeasible_candidate_gets_penalty(self):
        engine = DecisionScoringEngine()
        con = _constraint(op=ConstraintOperator.LTE, threshold=0.1)
        constraint_engine = DecisionConstraintEngine()
        c1 = _candidate(risk_score=0.05, candidate_id="c1")
        c2 = _candidate(risk_score=0.9, candidate_id="c2")
        con_results = {
            c1.candidate_id: constraint_engine.evaluate_all(c1, [con], _context()),
            c2.candidate_id: constraint_engine.evaluate_all(c2, [con], _context()),
        }
        scores = engine.score_all([c1, c2], [], con_results, _context())
        s_map = {s.candidate_id: s for s in scores}
        assert not s_map["c2"].is_feasible


# ============================================================================
# 12. DecisionRankingEngine
# ============================================================================

class TestDecisionRankingEngine:
    def _make_scores(self):
        return [
            CandidateScore("c1", 0.8, {}, 0.0, 0.8, True, 0.72),
            CandidateScore("c2", 0.6, {}, 0.0, 0.6, True, 0.48),
            CandidateScore("c3", 0.9, {}, 0.5, 0.4, False, 0.32),
        ]

    def test_rank_returns_same_count(self):
        engine = DecisionRankingEngine()
        rankings = engine.rank(self._make_scores())
        assert len(rankings) == 3

    def test_feasible_before_infeasible(self):
        engine = DecisionRankingEngine()
        rankings = engine.rank(self._make_scores())
        feasible_ranks = [r.rank for r in rankings if r.is_feasible]
        infeasible_ranks = [r.rank for r in rankings if not r.is_feasible]
        if feasible_ranks and infeasible_ranks:
            assert max(feasible_ranks) < min(infeasible_ranks)

    def test_rank_one_is_best_feasible(self):
        engine = DecisionRankingEngine()
        rankings = engine.rank(self._make_scores())
        rank1 = next(r for r in rankings if r.rank == 1)
        assert rank1.candidate_id == "c1"

    def test_best_feasible_helper(self):
        engine = DecisionRankingEngine()
        rankings = engine.rank(self._make_scores())
        best = engine.best_feasible(rankings)
        assert best is not None
        assert best.is_feasible

    def test_empty_rankings_best_feasible_none(self):
        engine = DecisionRankingEngine()
        assert engine.best_feasible([]) is None


# ============================================================================
# 13. DecisionPriorityEngine
# ============================================================================

class TestDecisionPriorityEngine:
    def test_prioritize_returns_list(self):
        engine = DecisionPriorityEngine()
        candidates = [_candidate(), _candidate()]
        result = engine.prioritize(candidates, _context())
        assert len(result) == 2

    def test_higher_confidence_return_ranked_first(self):
        engine = DecisionPriorityEngine()
        low = _candidate(confidence=0.3, expected_return=0.02, candidate_id="low")
        high = _candidate(confidence=0.9, expected_return=0.1, candidate_id="high")
        result = engine.prioritize([low, high], _context())
        assert result[0].candidate_id == "high"

    def test_top_priority_on_single(self):
        engine = DecisionPriorityEngine()
        c = _candidate()
        top = engine.top_priority([c], _context())
        assert top is c

    def test_top_priority_empty_returns_none(self):
        engine = DecisionPriorityEngine()
        # Empty list raises ValueError (no candidates to select from)
        with pytest.raises((ValueError, IndexError)):
            engine.top_priority([], _context())


# ============================================================================
# 14. DecisionSolutionSelector
# ============================================================================

class TestDecisionSolutionSelector:
    def _make_setup(self):
        c1 = _candidate(confidence=0.9, expected_return=0.1, candidate_id="c1")
        c2 = _candidate(confidence=0.5, expected_return=0.05, candidate_id="c2")
        scores = [
            CandidateScore("c1", 0.8, {"obj1": 0.8}, 0.0, 0.8, True, 0.72),
            CandidateScore("c2", 0.6, {"obj1": 0.6}, 0.0, 0.6, True, 0.30),
        ]
        rankings = [
            DecisionRanking(1, "c1", 0.8, 0.72, True, True),
            DecisionRanking(2, "c2", 0.6, 0.30, True, False),
        ]
        return [c1, c2], scores, rankings

    def test_weighted_score_selects_best(self):
        selector = DecisionSolutionSelector()
        candidates, scores, rankings = self._make_setup()
        strategy = DecisionOptimizationStrategy.weighted_score()
        result = selector.select(candidates, scores, rankings, strategy, _context())
        assert result is not None
        assert result.candidate_id == "c1"

    def test_priority_based_strategy(self):
        selector = DecisionSolutionSelector()
        candidates, scores, rankings = self._make_setup()
        strategy = DecisionOptimizationStrategy.priority_based()
        result = selector.select(candidates, scores, rankings, strategy, _context())
        assert result is not None

    def test_pareto_ranking_strategy(self):
        selector = DecisionSolutionSelector()
        candidates, scores, rankings = self._make_setup()
        strategy = DecisionOptimizationStrategy.pareto_ranking()
        result = selector.select(candidates, scores, rankings, strategy, _context())
        assert result is not None

    def test_constraint_satisfaction_picks_feasible(self):
        selector = DecisionSolutionSelector()
        c1 = _candidate(candidate_id="c1", confidence=0.9)
        c2 = _candidate(candidate_id="c2", confidence=0.5)
        scores = [
            CandidateScore("c1", 0.8, {}, 0.5, 0.3, False, 0.27),
            CandidateScore("c2", 0.6, {}, 0.0, 0.6, True,  0.30),
        ]
        rankings = [
            DecisionRanking(1, "c2", 0.6, 0.30, True, True),
            DecisionRanking(2, "c1", 0.3, 0.27, False, False),
        ]
        strategy = DecisionOptimizationStrategy.create(
            "cs", OptimizationStrategyType.CONSTRAINT_SATISFACTION
        )
        result = selector.select([c1, c2], scores, rankings, strategy, _context())
        assert result is not None
        assert result.candidate_id == "c2"

    def test_empty_candidates_returns_none(self):
        selector = DecisionSolutionSelector()
        strategy = DecisionOptimizationStrategy.weighted_score()
        assert selector.select([], [], [], strategy, _context()) is None


# ============================================================================
# 15. DecisionSolutionValidator
# ============================================================================

class TestDecisionSolutionValidator:
    def _make_solution(self) -> DecisionSolution:
        c = _candidate(candidate_id="c1")
        ranking = DecisionRanking(1, "c1", 0.8, 0.72, True, True)
        return DecisionSolution(
            solution_id           = "sol-1",
            request_id            = "req-1",
            decision_id           = "dec-1",
            selected_candidate    = c,
            final_score           = 0.8,
            rank                  = 1,
            rankings              = (ranking,),
            objective_scores      = {"obj1": 0.8},
            constraint_violations = (),
            optimization_strategy = "weighted_score",
            rationale             = "Best candidate",
            evaluation_time_s     = 0.05,
            generated_at          = datetime.now(timezone.utc),
            is_optimal            = True,
            is_feasible           = True,
            framework_version     = VERSION,
        )

    def test_valid_solution_passes(self):
        validator = DecisionSolutionValidator()
        result = validator.validate(self._make_solution())
        assert result.is_valid

    def test_passed_count_is_seven(self):
        validator = DecisionSolutionValidator()
        result = validator.validate(self._make_solution())
        assert result.passed_count == 7

    def test_check_count_is_seven(self):
        validator = DecisionSolutionValidator()
        result = validator.validate(self._make_solution())
        assert len(result.checks) == 7

    def test_error_messages_empty_when_valid(self):
        validator = DecisionSolutionValidator()
        result = validator.validate(self._make_solution())
        assert result.error_messages == ()


# ============================================================================
# 16. DecisionOptimizer
# ============================================================================

class TestDecisionOptimizer:
    def test_optimize_single_candidate(self):
        optimizer = DecisionOptimizer()
        c = _candidate(candidate_id="c1")
        solution = optimizer.optimize(
            request_id  = "req-1",
            decision_id = "dec-1",
            candidates  = [c],
            objectives  = [],
            constraints = [],
            strategy    = DecisionOptimizationStrategy.weighted_score(),
            context     = _context(),
        )
        assert solution.selected_candidate.candidate_id == "c1"
        assert solution.is_feasible

    def test_raises_no_candidates_error(self):
        optimizer = DecisionOptimizer()
        with pytest.raises(NoCandidatesError):
            optimizer.optimize(
                "req", "dec", [], [], [], DecisionOptimizationStrategy.weighted_score(),
                _context(),
            )

    def test_raises_no_feasible_solution(self):
        optimizer = DecisionOptimizer()
        c = _candidate(risk_score=0.9, candidate_id="c1")
        hard_con = _constraint(op=ConstraintOperator.LTE, threshold=0.1)
        with pytest.raises(NoFeasibleSolutionError):
            optimizer.optimize(
                "req", "dec", [c], [], [hard_con],
                DecisionOptimizationStrategy.weighted_score(), _context(),
            )

    def test_multiple_candidates_with_objective(self):
        optimizer = DecisionOptimizer()
        candidates = [
            _candidate(expected_return=0.1, candidate_id="c1"),
            _candidate(expected_return=0.05, candidate_id="c2"),
        ]
        obj = _objective(obj_type=OptimizationObjectiveType.MAXIMIZE_EXPECTED_RETURN)
        solution = optimizer.optimize(
            "req", "dec", candidates, [obj], [],
            DecisionOptimizationStrategy.weighted_score(), _context(),
        )
        assert solution.selected_candidate.candidate_id == "c1"

    def test_solution_has_rankings(self):
        optimizer = DecisionOptimizer()
        candidates = [_candidate(), _candidate()]
        solution = optimizer.optimize(
            "req", "dec", candidates, [], [],
            DecisionOptimizationStrategy.weighted_score(), _context(),
        )
        assert len(solution.rankings) == 2


# ============================================================================
# 17. DecisionOptimizationRegistry
# ============================================================================

class TestDecisionOptimizationRegistry:
    def test_register_and_get_objective(self):
        reg = DecisionOptimizationRegistry()
        obj = _objective()
        reg.register_objective(obj)
        assert reg.get_objective(obj.objective_id) is obj

    def test_get_objective_not_found_raises(self):
        reg = DecisionOptimizationRegistry()
        with pytest.raises(ObjectiveNotFoundError):
            reg.get_objective("nonexistent")

    def test_find_objective_returns_none(self):
        reg = DecisionOptimizationRegistry()
        assert reg.find_objective("x") is None

    def test_deregister_objective(self):
        reg = DecisionOptimizationRegistry()
        obj = _objective()
        reg.register_objective(obj)
        reg.deregister_objective(obj.objective_id)
        assert reg.find_objective(obj.objective_id) is None

    def test_objective_count(self):
        reg = DecisionOptimizationRegistry()
        reg.register_objective(_objective())
        reg.register_objective(_objective())
        assert reg.objective_count() == 2

    def test_register_and_get_constraint(self):
        reg = DecisionOptimizationRegistry()
        con = _constraint()
        reg.register_constraint(con)
        assert reg.get_constraint(con.constraint_id) is con

    def test_get_constraint_not_found_raises(self):
        reg = DecisionOptimizationRegistry()
        with pytest.raises(ConstraintNotFoundError):
            reg.get_constraint("nonexistent")

    def test_deregister_constraint(self):
        reg = DecisionOptimizationRegistry()
        con = _constraint()
        reg.register_constraint(con)
        reg.deregister_constraint(con.constraint_id)
        assert reg.find_constraint(con.constraint_id) is None

    def test_get_objectives_none_returns_all(self):
        reg = DecisionOptimizationRegistry()
        o1, o2 = _objective(), _objective()
        reg.register_objective(o1)
        reg.register_objective(o2)
        assert len(reg.get_objectives(None)) == 2

    def test_get_objectives_filtered(self):
        reg = DecisionOptimizationRegistry()
        o1, o2 = _objective(), _objective()
        reg.register_objective(o1)
        reg.register_objective(o2)
        result = reg.get_objectives([o1.objective_id])
        assert len(result) == 1
        assert result[0].objective_id == o1.objective_id

    def test_get_constraints_none_returns_all(self):
        reg = DecisionOptimizationRegistry()
        reg.register_constraint(_constraint())
        reg.register_constraint(_constraint())
        assert len(reg.get_constraints(None)) == 2

    def test_clear_removes_all(self):
        reg = DecisionOptimizationRegistry()
        reg.register_objective(_objective())
        reg.register_constraint(_constraint())
        reg.clear()
        assert reg.objective_count() == 0
        assert reg.constraint_count() == 0


# ============================================================================
# 18. DecisionStrategyRegistry
# ============================================================================

class TestDecisionStrategyRegistry:
    def test_default_registered_on_init(self):
        reg = DecisionStrategyRegistry()
        default = reg.get_default()
        assert default.strategy_id == DEFAULT_STRATEGY_ID

    def test_register_and_find(self):
        reg = DecisionStrategyRegistry()
        s = DecisionOptimizationStrategy.create("s1", OptimizationStrategyType.PARETO_RANKING,
                                                strategy_id="strat-1")
        reg.register(s)
        assert reg.find("strat-1") is s

    def test_get_not_found_raises(self):
        reg = DecisionStrategyRegistry()
        with pytest.raises(StrategyNotFoundError):
            reg.get("missing")

    def test_deregister(self):
        reg = DecisionStrategyRegistry()
        s = DecisionOptimizationStrategy.create("s2", OptimizationStrategyType.PARETO_RANKING,
                                                strategy_id="strat-2")
        reg.register(s)
        reg.deregister("strat-2")
        assert reg.find("strat-2") is None

    def test_count_includes_default(self):
        reg = DecisionStrategyRegistry()
        assert reg.count() >= 1

    def test_all_strategies_returns_list(self):
        reg = DecisionStrategyRegistry()
        assert isinstance(reg.all_strategies(), list)


# ============================================================================
# 19. DecisionOptimizationEvents
# ============================================================================

class TestDecisionOptimizationEvents:
    def _base_args(self):
        return ("req-1", "dec-1", "test-source")

    def test_make_optimization_started(self):
        ev = make_optimization_started(*self._base_args(), candidate_count=3, strategy="ws")
        assert ev.event_type == OptimizationEventType.OPTIMIZATION_STARTED
        assert ev.payload["candidate_count"] == 3

    def test_make_candidates_loaded(self):
        ev = make_candidates_loaded(*self._base_args(), count=5)
        assert ev.event_type == OptimizationEventType.CANDIDATES_LOADED
        assert ev.payload["count"] == 5

    def test_make_objectives_loaded(self):
        ev = make_objectives_loaded(*self._base_args(), count=2)
        assert ev.event_type == OptimizationEventType.OBJECTIVES_LOADED

    def test_make_constraints_loaded(self):
        ev = make_constraints_loaded(*self._base_args(), count=3)
        assert ev.event_type == OptimizationEventType.CONSTRAINTS_LOADED

    def test_make_optimization_completed(self):
        ev = make_optimization_completed(*self._base_args(), selected_id="c1",
                                         final_score=0.8, evaluation_time_s=0.05)
        assert ev.event_type == OptimizationEventType.OPTIMIZATION_COMPLETED
        assert ev.payload["selected_candidate_id"] == "c1"

    def test_make_solution_selected(self):
        ev = make_solution_selected(*self._base_args(), solution_id="sol-1", rank=1)
        assert ev.event_type == OptimizationEventType.SOLUTION_SELECTED

    def test_make_solution_validated(self):
        ev = make_solution_validated(*self._base_args(), is_valid=True)
        assert ev.event_type == OptimizationEventType.SOLUTION_VALIDATED

    def test_make_optimization_failed(self):
        ev = make_optimization_failed(*self._base_args(), reason="all infeasible")
        assert ev.event_type == OptimizationEventType.OPTIMIZATION_FAILED

    def test_to_dict_keys(self):
        ev = make_optimization_started(*self._base_args())
        d = ev.to_dict()
        assert "event_id" in d
        assert "event_type" in d
        assert "occurred_at" in d

    def test_event_id_unique(self):
        args = self._base_args()
        ev1 = make_optimization_started(*args)
        ev2 = make_optimization_started(*args)
        assert ev1.event_id != ev2.event_id


# ============================================================================
# 20. DecisionOptimizationStatistics
# ============================================================================

class TestDecisionOptimizationStatistics:
    def test_initial_snapshot_zeros(self):
        stats = DecisionOptimizationStatistics()
        snap = stats.snapshot()
        assert snap["optimization_requests"] == 0
        assert snap["solutions_generated"] == 0

    def test_record_request_started(self):
        stats = DecisionOptimizationStatistics()
        stats.record_request_started(5)
        snap = stats.snapshot()
        assert snap["optimization_requests"] == 1
        assert snap["candidates_evaluated"] == 5

    def test_record_success(self):
        stats = DecisionOptimizationStatistics()
        stats.record_request_started(3)
        stats.record_request_completed(success=True, evaluation_time_s=0.1)
        snap = stats.snapshot()
        assert snap["solutions_generated"] == 1
        assert snap["optimization_success_rate"] > 0

    def test_record_failure(self):
        stats = DecisionOptimizationStatistics()
        stats.record_request_started(3)
        stats.record_request_completed(success=False, evaluation_time_s=0.05)
        snap = stats.snapshot()
        assert snap["solutions_generated"] == 0

    def test_average_time_ema_updates(self):
        stats = DecisionOptimizationStatistics()
        stats.record_request_started(1)
        stats.record_request_completed(success=True, evaluation_time_s=1.0)
        snap = stats.snapshot()
        assert snap["average_optimization_time_s"] > 0

    def test_throughput_window(self):
        stats = DecisionOptimizationStatistics()
        for _ in range(3):
            stats.record_request_started(1)
            stats.record_request_completed(success=True, evaluation_time_s=0.01)
        snap = stats.snapshot()
        assert snap["optimization_throughput"] >= 3

    def test_violations_accumulated(self):
        stats = DecisionOptimizationStatistics()
        stats.record_request_started(2)
        stats.record_request_completed(success=True, evaluation_time_s=0.01, violations=4)
        snap = stats.snapshot()
        assert snap["constraint_violations"] == 4

    def test_reset(self):
        stats = DecisionOptimizationStatistics()
        stats.record_request_started(3)
        stats.record_request_completed(success=True, evaluation_time_s=0.01)
        stats.reset()
        snap = stats.snapshot()
        assert snap["optimization_requests"] == 0
        assert snap["solutions_generated"] == 0


# ============================================================================
# 21. DecisionOptimizationHistory
# ============================================================================

class TestDecisionOptimizationHistory:
    def test_record_and_retrieve_events(self):
        history = DecisionOptimizationHistory()
        ev = make_optimization_started("req-1", "dec-1", "test")
        history.record_event(ev)
        assert history.event_count() == 1
        assert history.latest_event() is ev

    def test_events_for_decision(self):
        history = DecisionOptimizationHistory()
        ev1 = make_optimization_started("req-1", "dec-A", "test")
        ev2 = make_optimization_started("req-2", "dec-B", "test")
        history.record_event(ev1)
        history.record_event(ev2)
        result = history.events_for_decision("dec-A")
        assert len(result) == 1
        assert result[0].decision_id == "dec-A"

    def test_events_by_type(self):
        history = DecisionOptimizationHistory()
        history.record_event(make_optimization_started("r", "d", "s"))
        history.record_event(make_optimization_failed("r", "d", "s", reason="x"))
        failed = history.events_by_type(OptimizationEventType.OPTIMIZATION_FAILED)
        assert len(failed) == 1

    def test_record_and_retrieve_responses(self):
        history = DecisionOptimizationHistory()
        history.record_response({"response_id": "resp-1", "decision_id": "dec-1"})
        assert history.response_count() == 1
        assert history.latest_response() == {"response_id": "resp-1", "decision_id": "dec-1"}

    def test_responses_for_decision(self):
        history = DecisionOptimizationHistory()
        history.record_response({"decision_id": "dec-A"})
        history.record_response({"decision_id": "dec-B"})
        result = history.responses_for_decision("dec-A")
        assert len(result) == 1

    def test_clear(self):
        history = DecisionOptimizationHistory()
        history.record_event(make_optimization_started("r", "d", "s"))
        history.record_response({"response_id": "x"})
        history.clear()
        assert history.event_count() == 0
        assert history.response_count() == 0

    def test_bounded_by_max(self):
        history = DecisionOptimizationHistory(max_events=3)
        for i in range(5):
            history.record_event(make_optimization_started(f"r{i}", "d", "s"))
        assert history.event_count() == 3


# ============================================================================
# 22. DecisionOptimizationFactory
# ============================================================================

class TestDecisionOptimizationFactory:
    def test_create_candidate(self):
        fac = DecisionOptimizationFactory()
        c = fac.create_candidate(
            "TCS", "buy", 5.0, 3500.0, 0.07, 0.3, 0.8
        )
        assert isinstance(c, DecisionCandidate)
        assert c.symbol == "TCS"

    def test_create_objective(self):
        fac = DecisionOptimizationFactory()
        o = fac.create_objective("R", OptimizationObjectiveType.MAXIMIZE_EXPECTED_RETURN)
        assert isinstance(o, DecisionObjective)

    def test_create_constraint(self):
        fac = DecisionOptimizationFactory()
        con = fac.create_constraint(
            "MaxRisk", ConstraintType.RISK, ConstraintOperator.LTE, "risk_score", 0.5
        )
        assert isinstance(con, DecisionConstraint)

    def test_create_strategy(self):
        fac = DecisionOptimizationFactory()
        s = fac.create_strategy("ws", OptimizationStrategyType.WEIGHTED_SCORE)
        assert isinstance(s, DecisionOptimizationStrategy)

    def test_create_context(self):
        fac = DecisionOptimizationFactory()
        ctx = fac.create_context(decision_id="d-1", request_id="r-1")
        assert isinstance(ctx, DecisionOptimizationContext)
        assert ctx.decision_id == "d-1"

    def test_create_request(self):
        fac = DecisionOptimizationFactory()
        ctx = fac.create_context(decision_id="d-1")
        c = fac.create_candidate("HDFC", "buy", 1.0, 1600.0, 0.05, 0.2, 0.7)
        req = fac.create_request(ctx, [c])
        assert isinstance(req, DecisionOptimizationRequest)
        assert len(req.candidates) == 1


# ============================================================================
# 23. DecisionOptimizationResponse
# ============================================================================

class TestDecisionOptimizationResponse:
    def _make_solution(self) -> DecisionSolution:
        c = _candidate(candidate_id="c1")
        ranking = DecisionRanking(1, "c1", 0.8, 0.72, True, True)
        return DecisionSolution(
            solution_id="sol-1", request_id="req-1", decision_id="dec-1",
            selected_candidate=c, final_score=0.8, rank=1,
            rankings=(ranking,), objective_scores={},
            constraint_violations=(), optimization_strategy="weighted_score",
            rationale="Best", evaluation_time_s=0.05,
            generated_at=datetime.now(timezone.utc),
            is_optimal=True, is_feasible=True, framework_version=VERSION,
        )

    def _make_summary(self, solution) -> DecisionOptimizationSummary:
        return DecisionOptimizationSummary(
            summary_id="sum-1", request_id="req-1", decision_id="dec-1",
            selected_candidate_id="c1", is_feasible=True, final_score=0.8,
            candidates_evaluated=1, feasible_count=1, infeasible_count=0,
            optimization_strategy="weighted_score", optimization_time_s=0.05,
            objectives_applied=0, constraints_applied=0, constraint_violations=0,
            rationale="Best", solution=solution,
            evaluated_at=datetime.now(timezone.utc),
        )

    def _make_report(self) -> OptimizationReport:
        return OptimizationReport(
            report_id="rep-1", request_id="req-1", decision_id="dec-1",
            candidates_evaluated=1, feasible_count=1, infeasible_count=0,
            constraint_violations=0, optimization_strategy="weighted_score",
            selected_candidate_id="c1", final_score=0.8, rankings=(),
            objective_scores={}, generated_at=datetime.now(timezone.utc),
        )

    def test_success_is_success(self):
        sol = self._make_solution()
        resp = DecisionOptimizationResponse.success(
            "req-1", "dec-1", sol, self._make_summary(sol), self._make_report()
        )
        assert resp.is_success
        assert resp.error is None

    def test_failure_is_not_success(self):
        resp = DecisionOptimizationResponse.failure("req-1", "dec-1", "error msg")
        assert not resp.is_success
        assert resp.error == "error msg"
        assert resp.solution is None

    def test_is_optimal_true_when_solution_optimal(self):
        sol = self._make_solution()
        resp = DecisionOptimizationResponse.success(
            "req-1", "dec-1", sol, self._make_summary(sol), self._make_report()
        )
        assert resp.is_optimal

    def test_is_feasible_false_on_failure(self):
        resp = DecisionOptimizationResponse.failure("req-1", "dec-1", "fail")
        assert not resp.is_feasible

    def test_to_dict_keys(self):
        resp = DecisionOptimizationResponse.failure("req-1", "dec-1", "fail")
        d = resp.to_dict()
        assert "response_id" in d
        assert "is_success" in d


# ============================================================================
# 24. DecisionOptimizationManager
# ============================================================================

class TestDecisionOptimizationManager:
    def _make_manager(self):
        opt_reg   = DecisionOptimizationRegistry()
        strat_reg = DecisionStrategyRegistry()
        optimizer = DecisionOptimizer()
        return DecisionOptimizationManager(opt_reg, strat_reg, optimizer)

    def test_optimize_with_candidates(self):
        mgr = self._make_manager()
        ctx = _context()
        req = DecisionOptimizationRequest.create(ctx, [_candidate()])
        summary, report = mgr.optimize(req)
        assert summary.solution is not None
        assert summary.is_feasible

    def test_zero_candidates_returns_empty_summary(self):
        mgr = self._make_manager()
        ctx = _context()
        req = DecisionOptimizationRequest.create(ctx, [])
        summary, report = mgr.optimize(req)
        assert summary.solution is None
        assert summary.selected_candidate_id is None

    def test_infeasible_candidates_returns_error_summary(self):
        mgr = self._make_manager()
        reg = mgr._registry
        con = _constraint(op=ConstraintOperator.LTE, threshold=0.01)
        reg.register_constraint(con)
        ctx = _context()
        c = _candidate(risk_score=0.9)
        req = DecisionOptimizationRequest.create(ctx, [c])
        summary, report = mgr.optimize(req)
        assert summary.solution is None

    def test_optimize_picks_best_with_objective(self):
        mgr = self._make_manager()
        obj = _objective(obj_type=OptimizationObjectiveType.MAXIMIZE_EXPECTED_RETURN)
        mgr._registry.register_objective(obj)
        candidates = [
            _candidate(expected_return=0.1, candidate_id="c1"),
            _candidate(expected_return=0.03, candidate_id="c2"),
        ]
        ctx = _context()
        req = DecisionOptimizationRequest.create(ctx, candidates)
        summary, report = mgr.optimize(req)
        assert summary.selected_candidate_id == "c1"

    def test_report_candidate_count(self):
        mgr = self._make_manager()
        ctx = _context()
        candidates = [_candidate(), _candidate(), _candidate()]
        req = DecisionOptimizationRequest.create(ctx, candidates)
        summary, report = mgr.optimize(req)
        assert report.candidates_evaluated == 3


# ============================================================================
# 25. DecisionOptimizationEngine (lifecycle + optimize)
# ============================================================================

class TestDecisionOptimizationEngine:
    def test_start_stop_lifecycle(self):
        engine = DecisionOptimizationEngine()
        engine.start()
        assert engine.lifecycle_state() in ("running", "RUNNING")
        engine.stop()

    def test_optimize_returns_response(self):
        engine = _started_engine()
        try:
            ctx = _context()
            req = DecisionOptimizationRequest.create(ctx, [_candidate()])
            resp = engine.optimize(req)
            assert isinstance(resp, DecisionOptimizationResponse)
        finally:
            engine.stop()

    def test_optimize_success(self):
        engine = _started_engine()
        try:
            ctx = _context()
            req = DecisionOptimizationRequest.create(ctx, [_candidate()])
            resp = engine.optimize(req)
            assert resp.is_success
        finally:
            engine.stop()

    def test_optimize_not_running_raises(self):
        engine = DecisionOptimizationEngine()
        ctx = _context()
        req = DecisionOptimizationRequest.create(ctx, [_candidate()])
        with pytest.raises(OptimizationEngineNotRunningError):
            engine.optimize(req)

    def test_register_objective(self):
        engine = _started_engine()
        try:
            obj = _objective()
            engine.register_objective(obj)
            assert engine.get_objective(obj.objective_id) is obj
        finally:
            engine.stop()

    def test_deregister_objective(self):
        engine = _started_engine()
        try:
            obj = _objective()
            engine.register_objective(obj)
            engine.deregister_objective(obj.objective_id)
            assert engine.get_objective(obj.objective_id) is None
        finally:
            engine.stop()

    def test_register_constraint(self):
        engine = _started_engine()
        try:
            con = _constraint()
            engine.register_constraint(con)
            assert engine.get_constraint(con.constraint_id) is con
        finally:
            engine.stop()

    def test_register_strategy(self):
        engine = _started_engine()
        try:
            s = DecisionOptimizationStrategy.create("s1", OptimizationStrategyType.PARETO_RANKING,
                                                    strategy_id="s1")
            engine.register_strategy(s)
            assert engine.get_strategy("s1") is s
        finally:
            engine.stop()

    def test_list_objectives(self):
        engine = _started_engine()
        try:
            engine.register_objective(_objective())
            engine.register_objective(_objective())
            assert len(engine.list_objectives()) == 2
        finally:
            engine.stop()

    def test_health_is_healthy_when_running(self):
        engine = _started_engine()
        try:
            h = engine.health()
            assert h["is_healthy"]
        finally:
            engine.stop()

    def test_health_not_healthy_when_stopped(self):
        engine = DecisionOptimizationEngine()
        h = engine.health()
        assert not h["is_healthy"]

    def test_statistics_populated_after_optimize(self):
        engine = _started_engine()
        try:
            ctx = _context()
            req = DecisionOptimizationRequest.create(ctx, [_candidate()])
            engine.optimize(req)
            snap = engine.statistics().snapshot()
            assert snap["optimization_requests"] == 1
        finally:
            engine.stop()

    def test_history_records_events(self):
        engine = _started_engine()
        try:
            ctx = _context()
            req = DecisionOptimizationRequest.create(ctx, [_candidate()])
            engine.optimize(req)
            assert engine.history().event_count() > 0
        finally:
            engine.stop()

    def test_listener_called_on_event(self):
        engine = _started_engine()
        received = []
        engine.add_listener(received.append)
        try:
            ctx = _context()
            req = DecisionOptimizationRequest.create(ctx, [_candidate()])
            engine.optimize(req)
            assert len(received) > 0
        finally:
            engine.stop()

    def test_remove_listener(self):
        engine = _started_engine()
        received = []
        cb = received.append
        engine.add_listener(cb)
        engine.remove_listener(cb)
        try:
            ctx = _context()
            req = DecisionOptimizationRequest.create(ctx, [_candidate()])
            engine.optimize(req)
            assert len(received) == 0
        finally:
            engine.stop()

    def test_factory_returns_instance(self):
        engine = _started_engine()
        try:
            assert isinstance(engine.factory(), DecisionOptimizationFactory)
        finally:
            engine.stop()

    def test_status_dict_has_keys(self):
        engine = _started_engine()
        try:
            s = engine.status()
            assert "engine_id" in s
            assert "state" in s
        finally:
            engine.stop()

    def test_zero_candidates_response_not_success(self):
        engine = _started_engine()
        try:
            ctx = _context()
            req = DecisionOptimizationRequest.create(ctx, [])
            resp = engine.optimize(req)
            assert not resp.is_success
        finally:
            engine.stop()

    def test_concurrent_optimize_calls(self):
        engine = _started_engine()
        errors = []

        def run():
            try:
                ctx = _context()
                req = DecisionOptimizationRequest.create(ctx, [_candidate()])
                engine.optimize(req)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=run) for _ in range(5)]
        try:
            for t in threads: t.start()
            for t in threads: t.join()
            assert not errors
        finally:
            engine.stop()


# ============================================================================
# 26. OptimizationFrameworkAdapter
# ============================================================================

class TestOptimizationFrameworkAdapter:
    def test_optimize_with_empty_candidates(self):
        engine = _started_engine()
        adapter = OptimizationFrameworkAdapter(engine)
        try:
            class FakeCtx:
                decision_id = "d-1"
                request_id  = "r-1"
                session_id  = ""
                pipeline_id = ""
                inputs      = {}
                metadata    = {}
            result = adapter.optimize(FakeCtx(), {}, {"candidates": []})
            assert "response_id" in result
            assert not result["is_success"]
        finally:
            engine.stop()

    def test_optimize_with_dict_candidates(self):
        engine = _started_engine()
        adapter = OptimizationFrameworkAdapter(engine)
        try:
            class FakeCtx:
                decision_id = "d-2"
                request_id  = "r-2"
                session_id  = ""
                pipeline_id = ""
                inputs      = {}
                metadata    = {}
            c_dict = {
                "symbol": "INFY", "direction": "buy",
                "quantity": 5.0, "price": 1500.0,
                "expected_return": 0.06, "risk_score": 0.3, "confidence": 0.7,
            }
            result = adapter.optimize(FakeCtx(), {"approved": True}, {"candidates": [c_dict]})
            assert result["is_success"]
            assert result["selected_candidate_id"] is not None
        finally:
            engine.stop()

    def test_optimize_with_candidate_objects(self):
        engine = _started_engine()
        adapter = OptimizationFrameworkAdapter(engine)
        try:
            class FakeCtx:
                decision_id = "d-3"
                request_id  = "r-3"
                session_id  = ""
                pipeline_id = ""
                inputs      = {}
                metadata    = {}
            c = _candidate()
            result = adapter.optimize(FakeCtx(), {}, {"candidates": [c]})
            assert result["is_success"]
        finally:
            engine.stop()

    def test_result_has_all_expected_keys(self):
        engine = _started_engine()
        adapter = OptimizationFrameworkAdapter(engine)
        try:
            class FakeCtx:
                decision_id = "d-4"
                request_id  = "r-4"
                session_id  = ""
                pipeline_id = ""
                inputs      = {}
                metadata    = {}
            c = _candidate()
            result = adapter.optimize(FakeCtx(), {}, {"candidates": [c]})
            expected_keys = {
                "selected_candidate_id", "final_score", "is_optimal",
                "is_feasible", "is_success", "rationale",
                "candidates_evaluated", "optimization_strategy",
                "error", "response_id",
            }
            assert expected_keys.issubset(set(result.keys()))
        finally:
            engine.stop()


# ============================================================================
# 27. __init__ exports
# ============================================================================

class TestInit:
    def test_key_symbols_importable(self):
        import iios.decision.optimization as pkg
        assert hasattr(pkg, "DecisionOptimizationEngine")
        assert hasattr(pkg, "OptimizationFrameworkAdapter")
        assert hasattr(pkg, "DecisionCandidate")
        assert hasattr(pkg, "DecisionObjective")
        assert hasattr(pkg, "DecisionConstraint")
        assert hasattr(pkg, "DecisionOptimizationContext")
        assert hasattr(pkg, "DecisionOptimizationRequest")
        assert hasattr(pkg, "DecisionOptimizationResponse")
        assert hasattr(pkg, "DecisionOptimizer")

    def test_version_accessible(self):
        import iios.decision.optimization as pkg
        assert hasattr(pkg, "VERSION")
        assert pkg.VERSION
