"""tests/unit/decision_optimization/test_optimization_engine.py"""
from __future__ import annotations

import asyncio
import threading

import pytest

from iios.decision_optimization import (
    # Constants
    AlgorithmType, ConstraintType, ObjectiveAggregation, ObjectiveType,
    OptimizationMode, OptimizationStatus,
    OPTIMIZATION_ENGINE_VERSION,
    # Exceptions
    AlgorithmNotFoundError, CandidateNotFoundError,
    ConstraintAlreadyExistsError, ConstraintNotFoundError,
    EngineAlreadyRunningError, EngineNotInitializedError,
    InfeasibleSolutionError, InsufficientCandidatesError,
    ObjectiveAlreadyExistsError, ObjectiveNotFoundError,
    OptimizationEngineError, OptimizationNotFoundError,
    RegistryOverflowError,
    # Context
    Candidate, optimization_session, opt_stage_scope, reset_optimization_context,
    # Objectives
    Objective, ScoreObjective, PayloadObjective, CompositeObjective, FunctionObjective,
    ObjectiveManager, ObjectiveRegistry, ObjectiveResult, ObjectiveScore,
    build_objective_result, get_objective_registry, reset_objective_registry,
    # Constraints
    OptimizationConstraint, ConstraintCheckResult,
    ThresholdConstraint, BoundedConstraint, PredicateConstraint,
    ConstraintSolver, ConstraintReport, build_constraint_report,
    ConstraintOptimizer, get_constraint_optimizer, reset_constraint_optimizer,
    # Algorithms
    OptimizationAlgorithm, OptimizationSolution,
    GreedyOptimizer, WeightedSumOptimizer,
    ConstraintSatisfactionOptimizer, MultiObjectiveOptimizer,
    AlgorithmExecutor, AlgorithmRegistry,
    get_algorithm_registry, reset_algorithm_registry, AlgorithmSelector,
    # Simulation
    SimulationEngine, Scenario, ScenarioOptimizer,
    SensitivityAnalyzer, RobustnessEvaluator,
    # Registry
    OptimizationRegistry, get_optimization_registry, reset_optimization_registry,
    # Manager / Engine
    OptimizationRequest, OptimizationResult,
    OptimizationManager, get_optimization_manager, reset_optimization_manager,
    OptimizationFactory,
    DecisionOptimizationEngine,
    get_decision_optimization_engine, reset_decision_optimization_engine,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _cand(name: str = "A", score: float = 0.5, **payload) -> Candidate:
    return Candidate(name=name, payload=payload, evaluation_score=score)


def _score_obj(oid: str, weight: float = 1.0, obj_type: ObjectiveType = ObjectiveType.MAXIMIZE) -> ScoreObjective:
    return ScoreObjective(objective_id=oid, name=oid, objective_type=obj_type, weight=weight)


def _payload_obj(oid: str, key: str, weight: float = 1.0) -> PayloadObjective:
    return PayloadObjective(objective_id=oid, name=oid, key=key, weight=weight)


def _threshold(cid: str, threshold: float, hard: bool = True) -> ThresholdConstraint:
    ctype = ConstraintType.HARD if hard else ConstraintType.SOFT
    return ThresholdConstraint(constraint_id=cid, name=cid, threshold=threshold, constraint_type=ctype)


@pytest.fixture(autouse=True)
def _reset_all():
    reset_decision_optimization_engine()
    reset_optimization_manager()
    reset_optimization_registry()
    reset_objective_registry()
    reset_constraint_optimizer()
    reset_algorithm_registry()
    reset_optimization_context()
    yield
    reset_decision_optimization_engine()
    reset_optimization_manager()
    reset_optimization_registry()
    reset_objective_registry()
    reset_constraint_optimizer()
    reset_algorithm_registry()
    reset_optimization_context()


# ═══════════════════════════════════════════════════════════════════════════════
# TestConstants
# ═══════════════════════════════════════════════════════════════════════════════

class TestConstants:
    def test_objective_type_values(self):
        assert ObjectiveType.MAXIMIZE.value == "maximize"
        assert ObjectiveType.MINIMIZE.value == "minimize"
        assert ObjectiveType.TARGET.value   == "target"

    def test_constraint_type_values(self):
        assert ConstraintType.HARD.value       == "hard"
        assert ConstraintType.SOFT.value       == "soft"
        assert ConstraintType.COMPLIANCE.value == "compliance"

    def test_optimization_status_values(self):
        assert OptimizationStatus.OPTIMAL.value    == "optimal"
        assert OptimizationStatus.INFEASIBLE.value == "infeasible"

    def test_algorithm_type_values(self):
        assert AlgorithmType.GREEDY.value          == "greedy"
        assert AlgorithmType.MULTI_OBJECTIVE.value == "multi_objective"

    def test_optimization_mode_values(self):
        assert OptimizationMode.STRICT.value  == "strict"
        assert OptimizationMode.LENIENT.value == "lenient"

    def test_version(self):
        assert OPTIMIZATION_ENGINE_VERSION == "1.0.0"


# ═══════════════════════════════════════════════════════════════════════════════
# TestExceptions
# ═══════════════════════════════════════════════════════════════════════════════

class TestExceptions:
    def test_base_exception(self):
        e = OptimizationEngineError("test", "OE-999")
        assert "OE-999" in str(e)

    def test_objective_not_found(self):
        e = ObjectiveNotFoundError("o1")
        assert "o1" in str(e)
        assert e.code == "OE-021"

    def test_constraint_not_found(self):
        e = ConstraintNotFoundError("c1")
        assert e.code == "OE-031"

    def test_algorithm_not_found(self):
        e = AlgorithmNotFoundError("alg1")
        assert e.code == "OE-041"

    def test_infeasible_solution(self):
        e = InfeasibleSolutionError()
        assert "OE-034" in str(e)

    def test_engine_not_initialized(self):
        e = EngineNotInitializedError()
        assert "OE-061" in str(e)

    def test_engine_already_running(self):
        e = EngineAlreadyRunningError()
        assert "OE-062" in str(e)

    def test_insufficient_candidates(self):
        e = InsufficientCandidatesError(0)
        assert "OE-082" in str(e)

    def test_registry_overflow(self):
        e = RegistryOverflowError(1000)
        assert "1000" in str(e)

    def test_hierarchy(self):
        assert issubclass(ObjectiveNotFoundError,  OptimizationEngineError)
        assert issubclass(EngineNotInitializedError, OptimizationEngineError)
        assert issubclass(InfeasibleSolutionError,   OptimizationEngineError)


# ═══════════════════════════════════════════════════════════════════════════════
# TestCandidate
# ═══════════════════════════════════════════════════════════════════════════════

class TestCandidate:
    def test_defaults(self):
        c = Candidate()
        assert c.candidate_id
        assert c.evaluation_score == 0.0
        assert c.payload == {}

    def test_get_key(self):
        c = _cand("A", score=0.8, risk=0.3)
        assert c.get("risk") == pytest.approx(0.3)
        assert c.get("missing", -1) == -1

    def test_to_dict(self):
        c = _cand("A", score=0.7)
        d = c.to_dict()
        assert d["name"] == "A"
        assert "evaluation_score" in d

    def test_unique_ids(self):
        c1 = Candidate()
        c2 = Candidate()
        assert c1.candidate_id != c2.candidate_id


# ═══════════════════════════════════════════════════════════════════════════════
# TestOptimizationContextScope
# ═══════════════════════════════════════════════════════════════════════════════

class TestOptimizationContextScope:
    def test_session(self):
        with optimization_session("src", OptimizationMode.AUDIT) as ctx:
            assert ctx.source_id == "src"
            assert ctx.mode == OptimizationMode.AUDIT

    def test_stage_scope(self):
        with optimization_session() as ctx:
            assert ctx.current_stage == ""
            with opt_stage_scope("algo"):
                assert ctx.current_stage == "algo"
            assert ctx.current_stage == ""

    def test_diagnostics(self):
        with optimization_session() as ctx:
            ctx.add_diagnostic("WARNING", "note")
            ctx.add_diagnostic("ERROR", "fail")
            assert len(ctx.warnings()) == 1
            assert len(ctx.errors()) == 1

    def test_elapsed(self):
        import time
        with optimization_session() as ctx:
            time.sleep(0.01)
            assert ctx.elapsed_ms() > 0


# ═══════════════════════════════════════════════════════════════════════════════
# TestScoreObjective
# ═══════════════════════════════════════════════════════════════════════════════

class TestScoreObjective:
    def test_evaluate_returns_score(self):
        obj = _score_obj("o1")
        c   = _cand("A", score=0.75)
        assert obj.evaluate(c) == pytest.approx(0.75)

    def test_maximize_effective_positive(self):
        obj = _score_obj("o1", obj_type=ObjectiveType.MAXIMIZE)
        c   = _cand(score=0.8)
        assert obj.effective_score(c) == pytest.approx(0.8)

    def test_minimize_effective_negated(self):
        obj = _score_obj("o1", obj_type=ObjectiveType.MINIMIZE)
        c   = _cand(score=0.8)
        assert obj.effective_score(c) == pytest.approx(-0.8)

    def test_to_dict(self):
        obj = _score_obj("o1")
        d   = obj.to_dict()
        assert d["objective_id"] == "o1"
        assert d["objective_type"] == "maximize"


# ═══════════════════════════════════════════════════════════════════════════════
# TestPayloadObjective
# ═══════════════════════════════════════════════════════════════════════════════

class TestPayloadObjective:
    def test_evaluate_key(self):
        obj = _payload_obj("o1", "score")
        c   = Candidate(name="A", payload={"score": 0.9})
        # PayloadObjective reads from c.payload["score"]
        assert obj.evaluate(c) == pytest.approx(0.9)

    def test_missing_key_returns_zero(self):
        obj = _payload_obj("o1", "absent")
        c   = _cand("A")
        assert obj.evaluate(c) == pytest.approx(0.0)

    def test_target_effective_score(self):
        obj = PayloadObjective("o1", "o1", "v", objective_type=ObjectiveType.TARGET, target_value=5.0)
        c   = Candidate(payload={"v": 6.0})
        # -|6 - 5| = -1
        assert obj.effective_score(c) == pytest.approx(-1.0)


# ═══════════════════════════════════════════════════════════════════════════════
# TestCompositeObjective
# ═══════════════════════════════════════════════════════════════════════════════

class TestCompositeObjective:
    def test_weighted_average(self):
        o1   = FunctionObjective("o1", "o1", lambda _: 1.0)
        o2   = FunctionObjective("o2", "o2", lambda _: 0.0)
        comp = CompositeObjective("c", "c", [o1, o2], sub_weights=[1.0, 1.0])
        # effective_score on sub = evaluate (MAXIMIZE by default)
        assert comp.evaluate(_cand()) == pytest.approx(0.5)

    def test_empty_returns_zero(self):
        comp = CompositeObjective("c", "c", [])
        assert comp.evaluate(_cand()) == 0.0

    def test_to_dict(self):
        comp = CompositeObjective("c", "c", [_score_obj("o1")])
        d    = comp.to_dict()
        assert d["objective_id"] == "c"


# ═══════════════════════════════════════════════════════════════════════════════
# TestFunctionObjective
# ═══════════════════════════════════════════════════════════════════════════════

class TestFunctionObjective:
    def test_evaluate(self):
        obj = FunctionObjective("o1", "o1", lambda c: c.evaluation_score * 2)
        c   = _cand(score=0.5)
        assert obj.evaluate(c) == pytest.approx(1.0)

    def test_exception_returns_zero(self):
        obj = FunctionObjective("o1", "o1", lambda _: 1 / 0)  # noqa: ZeroDivisionError
        assert obj.evaluate(_cand()) == 0.0


# ═══════════════════════════════════════════════════════════════════════════════
# TestObjectiveRegistry
# ═══════════════════════════════════════════════════════════════════════════════

class TestObjectiveRegistry:
    def test_register_and_get(self):
        reg = get_objective_registry()
        o   = _score_obj("o1")
        reg.register(o)
        assert reg.get("o1") is o

    def test_duplicate_raises(self):
        reg = get_objective_registry()
        reg.register(_score_obj("o2"))
        with pytest.raises(ObjectiveAlreadyExistsError):
            reg.register(_score_obj("o2"))

    def test_overwrite(self):
        reg = get_objective_registry()
        o1  = _score_obj("o3")
        o2  = _score_obj("o3")
        reg.register(o1)
        reg.register(o2, overwrite=True)
        assert reg.get("o3") is o2

    def test_not_found(self):
        reg = get_objective_registry()
        with pytest.raises(ObjectiveNotFoundError):
            reg.get("ghost")

    def test_singleton(self):
        r1 = get_objective_registry()
        r2 = get_objective_registry()
        assert r1 is r2


# ═══════════════════════════════════════════════════════════════════════════════
# TestObjectiveResult
# ═══════════════════════════════════════════════════════════════════════════════

class TestObjectiveResult:
    def test_build_result(self):
        cands = [_cand("A", score=0.9), _cand("B", score=0.3)]
        objs  = [_score_obj("o1")]
        res   = build_objective_result(cands, objs)
        assert res.candidate_count == 2
        assert res.objective_count == 1

    def test_composite_scores(self):
        cands  = [_cand("A", score=0.8)]
        objs   = [_score_obj("o1", weight=1.0)]
        res    = build_objective_result(cands, objs)
        scores = list(res.composite_scores.values())
        assert scores[0] == pytest.approx(0.8)

    def test_to_dict(self):
        res = build_objective_result([], [])
        d   = res.to_dict()
        assert "result_id" in d


# ═══════════════════════════════════════════════════════════════════════════════
# TestConstraintChecker
# ═══════════════════════════════════════════════════════════════════════════════

class TestConstraintChecker:
    def test_threshold_pass(self):
        c     = _threshold("t1", 0.5)
        cand  = _cand(score=0.7)
        res   = c.check(cand)
        assert res.satisfied

    def test_threshold_fail(self):
        c     = _threshold("t1", 0.5)
        cand  = _cand(score=0.3)
        res   = c.check(cand)
        assert not res.satisfied
        assert res.is_hard

    def test_bounded_pass(self):
        c    = BoundedConstraint("b1", "b1", "v", 0.0, 1.0)
        cand = Candidate(payload={"v": 0.5})
        assert c.check(cand).satisfied

    def test_bounded_fail(self):
        c    = BoundedConstraint("b1", "b1", "v", 0.0, 1.0)
        cand = Candidate(payload={"v": 2.0})
        assert not c.check(cand).satisfied

    def test_predicate_pass(self):
        c    = PredicateConstraint("p1", "p1", lambda _: True)
        cand = _cand()
        assert c.check(cand).satisfied

    def test_predicate_fail(self):
        c    = PredicateConstraint("p1", "p1", lambda _: False)
        cand = _cand()
        assert not c.check(cand).satisfied

    def test_predicate_exception_fails(self):
        c    = PredicateConstraint("p1", "p1", lambda _: 1 / 0)  # noqa: ZeroDivisionError
        cand = _cand()
        assert not c.check(cand).satisfied

    def test_soft_constraint_not_hard(self):
        c = _threshold("t1", 0.5, hard=False)
        assert not c.is_hard

    def test_check_result_to_dict(self):
        r = ConstraintCheckResult("c1", satisfied=True)
        d = r.to_dict()
        assert d["satisfied"]


# ═══════════════════════════════════════════════════════════════════════════════
# TestConstraintSolver
# ═══════════════════════════════════════════════════════════════════════════════

class TestConstraintSolver:
    def test_all_pass(self):
        solver = ConstraintSolver()
        cands  = [_cand(score=0.8)]
        cons   = [_threshold("t1", 0.5)]
        r      = solver.solve(cands, cons)
        assert r[cands[0].candidate_id][0].satisfied

    def test_hard_violation(self):
        solver = ConstraintSolver()
        cands  = [_cand(score=0.2)]
        cons   = [_threshold("t1", 0.5)]
        assert not solver.is_feasible(cands[0], cons)

    def test_soft_penalty(self):
        solver = ConstraintSolver()
        cand   = _cand(score=0.2)
        c_soft = _threshold("t1", 0.5, hard=False)
        penalty = solver.soft_penalty(cand, [c_soft])
        assert penalty > 0

    def test_is_feasible_no_hard(self):
        solver = ConstraintSolver()
        cand   = _cand(score=0.2)
        # Only soft constraints → always feasible
        assert solver.is_feasible(cand, [_threshold("t1", 0.9, hard=False)])


# ═══════════════════════════════════════════════════════════════════════════════
# TestConstraintReport
# ═══════════════════════════════════════════════════════════════════════════════

class TestConstraintReport:
    def test_build_feasible(self):
        cands   = [_cand(score=0.8), _cand(score=0.3)]
        cons    = [_threshold("t1", 0.5)]
        solver  = ConstraintSolver()
        results = solver.solve(cands, cons)
        report  = build_constraint_report(cands, cons, results)
        assert len(report.feasible_ids) == 1
        assert len(report.infeasible_ids) == 1

    def test_build_all_feasible(self):
        cands   = [_cand(score=0.9)]
        results = ConstraintSolver().solve(cands, [])
        report  = build_constraint_report(cands, [], results)
        assert len(report.feasible_ids) == 1

    def test_to_dict(self):
        report = build_constraint_report([], [], {})
        d      = report.to_dict()
        assert "report_id" in d


# ═══════════════════════════════════════════════════════════════════════════════
# TestConstraintOptimizer
# ═══════════════════════════════════════════════════════════════════════════════

class TestConstraintOptimizer:
    def test_filter_feasible(self):
        opt   = ConstraintOptimizer()
        cands = [_cand(score=0.9), _cand(score=0.1)]
        con   = _threshold("t1", 0.5)
        feas  = opt.filter_feasible(cands, [con])
        assert len(feas) == 1

    def test_filter_all_infeasible(self):
        opt   = ConstraintOptimizer()
        cands = [_cand(score=0.1), _cand(score=0.2)]
        con   = _threshold("t1", 0.9)
        feas  = opt.filter_feasible(cands, [con])
        assert feas == []

    def test_solve_and_report(self):
        opt    = ConstraintOptimizer()
        cands  = [_cand(score=0.8)]
        report = opt.solve_and_report(cands, [_threshold("t1", 0.5)])
        assert isinstance(report, ConstraintReport)

    def test_registry_singleton(self):
        o1 = get_constraint_optimizer()
        o2 = get_constraint_optimizer()
        assert o1 is o2


# ═══════════════════════════════════════════════════════════════════════════════
# TestGreedyOptimizer
# ═══════════════════════════════════════════════════════════════════════════════

class TestGreedyOptimizer:
    def test_selects_best(self):
        alg    = GreedyOptimizer()
        cands  = [_cand("A", score=0.9), _cand("B", score=0.3)]
        sol    = alg.optimize(cands, [_score_obj("o1")], [])
        assert sol.optimal_id == cands[0].candidate_id
        assert sol.status == OptimizationStatus.OPTIMAL

    def test_empty_candidates(self):
        alg = GreedyOptimizer()
        sol = alg.optimize([], [], [])
        assert sol.status == OptimizationStatus.EMPTY

    def test_infeasible_all_blocked(self):
        alg   = GreedyOptimizer()
        cands = [_cand(score=0.1), _cand(score=0.2)]
        con   = _threshold("t1", 0.9)
        sol   = alg.optimize(cands, [], [con])
        assert sol.status == OptimizationStatus.INFEASIBLE

    def test_with_minimize_objective(self):
        alg   = GreedyOptimizer()
        # A has lower score → better for MINIMIZE
        cands = [_cand("A", score=0.2), _cand("B", score=0.8)]
        obj   = _score_obj("o1", obj_type=ObjectiveType.MINIMIZE)
        sol   = alg.optimize(cands, [obj], [])
        assert sol.optimal_id == cands[0].candidate_id  # lower score → higher effective

    def test_to_dict(self):
        alg = GreedyOptimizer()
        d   = alg.to_dict()
        assert d["algorithm_id"] == "greedy"


# ═══════════════════════════════════════════════════════════════════════════════
# TestWeightedSumOptimizer
# ═══════════════════════════════════════════════════════════════════════════════

class TestWeightedSumOptimizer:
    def test_selects_best(self):
        alg    = WeightedSumOptimizer()
        cands  = [_cand("A", score=0.9), _cand("B", score=0.1)]
        sol    = alg.optimize(cands, [_score_obj("o1")], [])
        assert sol.optimal_id == cands[0].candidate_id

    def test_weighted_objectives(self):
        alg   = WeightedSumOptimizer()
        # A is high on o1 (payload v=10), B is low
        cands = [
            Candidate(name="A", payload={"v": 10.0}, evaluation_score=0.5),
            Candidate(name="B", payload={"v": 1.0},  evaluation_score=0.5),
        ]
        obj   = _payload_obj("o1", "v", weight=2.0)
        sol   = alg.optimize(cands, [obj], [])
        assert sol.optimal_id == cands[0].candidate_id

    def test_no_objectives_fallback(self):
        alg   = WeightedSumOptimizer()
        cands = [_cand("A", score=0.9), _cand("B", score=0.3)]
        sol   = alg.optimize(cands, [], [])
        assert sol.optimal_id == cands[0].candidate_id

    def test_algorithm_id(self):
        assert WeightedSumOptimizer().algorithm_id == "weighted_sum"


# ═══════════════════════════════════════════════════════════════════════════════
# TestConstraintSatisfactionOptimizer
# ═══════════════════════════════════════════════════════════════════════════════

class TestConstraintSatisfactionOptimizer:
    def test_picks_least_violated_when_all_infeasible(self):
        alg   = ConstraintSatisfactionOptimizer()
        # Both fail the hard constraint, but A is closer
        cands = [_cand("A", score=0.4), _cand("B", score=0.1)]
        con   = _threshold("t1", 0.5)
        sol   = alg.optimize(cands, [_score_obj("o1")], [con])
        # Status should still be INFEASIBLE but optimal_id is set
        assert sol.status == OptimizationStatus.INFEASIBLE
        assert sol.optimal_id is not None

    def test_finds_feasible(self):
        alg   = ConstraintSatisfactionOptimizer()
        cands = [_cand("A", score=0.9), _cand("B", score=0.1)]
        con   = _threshold("t1", 0.5)
        sol   = alg.optimize(cands, [_score_obj("o1")], [con])
        assert sol.optimal_id == cands[0].candidate_id
        assert sol.status == OptimizationStatus.OPTIMAL

    def test_algorithm_id(self):
        assert ConstraintSatisfactionOptimizer().algorithm_id == "constraint"


# ═══════════════════════════════════════════════════════════════════════════════
# TestMultiObjectiveOptimizer
# ═══════════════════════════════════════════════════════════════════════════════

class TestMultiObjectiveOptimizer:
    def test_selects_pareto_optimal(self):
        alg   = MultiObjectiveOptimizer()
        # A dominates B on both objectives
        cands = [
            Candidate(name="A", payload={"x": 0.9, "y": 0.9}, evaluation_score=0.9),
            Candidate(name="B", payload={"x": 0.3, "y": 0.3}, evaluation_score=0.3),
        ]
        objs  = [_payload_obj("o1", "x"), _payload_obj("o2", "y")]
        sol   = alg.optimize(cands, objs, [])
        assert sol.optimal_id == cands[0].candidate_id
        assert cands[0].candidate_id in sol.pareto_frontier

    def test_tradeoff_both_on_frontier(self):
        alg   = MultiObjectiveOptimizer()
        # Neither dominates the other (trade-off)
        cands = [
            Candidate(name="A", payload={"x": 0.9, "y": 0.1}, evaluation_score=0.5),
            Candidate(name="B", payload={"x": 0.1, "y": 0.9}, evaluation_score=0.5),
        ]
        objs  = [_payload_obj("o1", "x"), _payload_obj("o2", "y")]
        sol   = alg.optimize(cands, objs, [])
        assert len(sol.pareto_frontier) == 2

    def test_algorithm_id(self):
        assert MultiObjectiveOptimizer().algorithm_id == "multi_objective"


# ═══════════════════════════════════════════════════════════════════════════════
# TestAlgorithmRegistry
# ═══════════════════════════════════════════════════════════════════════════════

class TestAlgorithmRegistry:
    def test_builtin_registered(self):
        reg = get_algorithm_registry()
        assert reg.has("greedy")
        assert reg.has("weighted_sum")
        assert reg.has("constraint")
        assert reg.has("multi_objective")

    def test_get_greedy(self):
        reg = get_algorithm_registry()
        alg = reg.get("greedy")
        assert alg.algorithm_id == "greedy"

    def test_custom_registration(self):
        reg = get_algorithm_registry()

        class CustomAlg(OptimizationAlgorithm):
            @property
            def algorithm_id(self) -> str: return "custom_test"
            @property
            def name(self) -> str: return "Custom"
            def optimize(self, candidates, objectives, constraints, **kwargs):
                return OptimizationSolution()

        reg.register(CustomAlg())
        assert reg.has("custom_test")

    def test_not_found_raises(self):
        reg = get_algorithm_registry()
        with pytest.raises(AlgorithmNotFoundError):
            reg.get("nonexistent")

    def test_singleton(self):
        r1 = get_algorithm_registry()
        r2 = get_algorithm_registry()
        assert r1 is r2


# ═══════════════════════════════════════════════════════════════════════════════
# TestAlgorithmSelector
# ═══════════════════════════════════════════════════════════════════════════════

class TestAlgorithmSelector:
    def test_select_by_type(self):
        sel = AlgorithmSelector()
        alg = sel.select(AlgorithmType.GREEDY)
        assert alg.algorithm_id == "greedy"

    def test_select_multi_objective(self):
        sel = AlgorithmSelector()
        alg = sel.select(AlgorithmType.MULTI_OBJECTIVE)
        assert alg.algorithm_id == "multi_objective"

    def test_select_by_id(self):
        sel = AlgorithmSelector()
        alg = sel.select(AlgorithmType.GREEDY, algorithm_id="weighted_sum")
        assert alg.algorithm_id == "weighted_sum"


# ═══════════════════════════════════════════════════════════════════════════════
# TestAlgorithmExecutor
# ═══════════════════════════════════════════════════════════════════════════════

class TestAlgorithmExecutor:
    def test_execute_greedy(self):
        exe  = AlgorithmExecutor()
        cands = [_cand("A", score=0.8), _cand("B", score=0.4)]
        sol  = exe.execute(cands, [_score_obj("o1")], [])
        assert sol.optimal_id == cands[0].candidate_id

    def test_execute_handles_error(self):
        exe = AlgorithmExecutor()

        class BrokenAlg(OptimizationAlgorithm):
            @property
            def algorithm_id(self) -> str: return "broken"
            @property
            def name(self) -> str: return "Broken"
            def optimize(self, *args, **kwargs):
                raise RuntimeError("deliberate error")

        get_algorithm_registry().register(BrokenAlg())
        sol = exe.execute([_cand()], [], [], algorithm_id="broken")
        assert sol.status == OptimizationStatus.ERROR

    def test_execute_parallel(self):
        exe     = AlgorithmExecutor()
        batches = [[_cand("A", score=0.9)], [_cand("B", score=0.3)]]
        sols    = exe.execute_parallel(batches, [_score_obj("o1")], [])
        assert len(sols) == 2
        assert sols[0].optimal_id == batches[0][0].candidate_id

    def test_execute_empty_candidates(self):
        exe = AlgorithmExecutor()
        sol = exe.execute([], [], [])
        assert sol.status == OptimizationStatus.EMPTY


# ═══════════════════════════════════════════════════════════════════════════════
# TestSimulationEngine
# ═══════════════════════════════════════════════════════════════════════════════

class TestSimulationEngine:
    def test_what_if_perturb(self):
        eng   = SimulationEngine()
        cands = [_cand("A", score=0.3)]
        cid   = cands[0].candidate_id
        sol   = eng.run_what_if(
            cands, [_score_obj("o1")], [],
            perturbation={cid: {"evaluation_score": 0.9}},
        )
        assert sol.optimal_id == cid

    def test_what_if_global(self):
        eng   = SimulationEngine()
        cands = [_cand("A"), _cand("B")]
        sol   = eng.run_what_if(cands, [], [], perturbation={"*": {"note": "test"}})
        # Both candidates get the global patch → no error
        assert sol.status != OptimizationStatus.ERROR

    def test_run_scenario_multiple(self):
        eng   = SimulationEngine()
        cands = [_cand("A", score=0.7)]
        sc1   = {}
        sc2   = {"*": {"tag": "stress"}}
        sols  = eng.run_scenario(cands, [], [], [sc1, sc2])
        assert len(sols) == 2

    def test_original_not_mutated(self):
        eng  = SimulationEngine()
        orig = _cand("A", score=0.5)
        eng.run_what_if(
            [orig], [], [],
            perturbation={orig.candidate_id: {"evaluation_score": 0.9}},
        )
        assert orig.evaluation_score == pytest.approx(0.5)  # unchanged

    def test_empty_perturbation(self):
        eng  = SimulationEngine()
        cand = _cand("A", score=0.6)
        sol  = eng.run_what_if([cand], [_score_obj("o1")], [], perturbation={})
        assert sol.optimal_id == cand.candidate_id


# ═══════════════════════════════════════════════════════════════════════════════
# TestScenarioOptimizer
# ═══════════════════════════════════════════════════════════════════════════════

class TestScenarioOptimizer:
    def test_optimize_scenarios(self):
        opt   = ScenarioOptimizer()
        cands = [_cand("A", score=0.8)]
        scs   = [Scenario(name="base"), Scenario(name="stress")]
        res   = opt.optimize_scenarios(cands, [], [], scs)
        assert len(res) == 2

    def test_compare_results(self):
        opt = ScenarioOptimizer()
        cands = [_cand("A", score=0.9)]
        scs   = [Scenario(name="s1")]
        results = opt.optimize_scenarios(cands, [_score_obj("o1")], [], scs)
        cmp = opt.compare(results)
        assert "best_scenario" in cmp

    def test_compare_empty(self):
        opt = ScenarioOptimizer()
        cmp = opt.compare([])
        assert cmp["best_scenario"] is None


# ═══════════════════════════════════════════════════════════════════════════════
# TestSensitivityAnalyzer
# ═══════════════════════════════════════════════════════════════════════════════

class TestSensitivityAnalyzer:
    def test_analyze_returns_keys(self):
        ana   = SensitivityAnalyzer()
        cands = [_cand("A", score=0.9), _cand("B", score=0.3)]
        objs  = [_score_obj("o1")]
        res   = ana.analyze_objective_weight(cands, objs, [], "o1", steps=3)
        assert "weights" in res
        assert len(res["weights"]) == 3

    def test_rank_changes_detected(self):
        ana   = SensitivityAnalyzer()
        # Two candidates with reversed objectives
        cands = [
            Candidate(name="A", payload={"x": 10.0}, evaluation_score=0.5),
            Candidate(name="B", payload={"x": 1.0},  evaluation_score=0.9),
        ]
        objs  = [_payload_obj("o_x", "x"), _score_obj("o_s")]
        res   = ana.analyze_objective_weight(cands, objs, [], "o_s", steps=5)
        assert "rank_changes" in res

    def test_single_step(self):
        ana = SensitivityAnalyzer()
        cands = [_cand("A", score=0.7)]
        res   = ana.analyze_objective_weight(cands, [], [], "none", steps=1)
        assert len(res["weights"]) == 2  # minimum 2 steps enforced

    def test_top_candidate_list_length(self):
        ana   = SensitivityAnalyzer()
        cands = [_cand("A", score=0.5)]
        objs  = [_score_obj("o1")]
        res   = ana.analyze_objective_weight(cands, objs, [], "o1", steps=4)
        assert len(res["top_candidate"]) == 4


# ═══════════════════════════════════════════════════════════════════════════════
# TestRobustnessEvaluator
# ═══════════════════════════════════════════════════════════════════════════════

class TestRobustnessEvaluator:
    def test_stability_range(self):
        ev    = RobustnessEvaluator()
        cands = [_cand("A", score=0.9), _cand("B", score=0.1)]
        res   = ev.evaluate(cands, [_score_obj("o1")], [], n_trials=20, seed=42)
        assert 0.0 <= res["stability"] <= 1.0

    def test_baseline_identified(self):
        ev    = RobustnessEvaluator()
        cands = [_cand("A", score=0.9)]
        res   = ev.evaluate(cands, [], [], n_trials=10, seed=1)
        assert res["baseline_optimal"] == cands[0].candidate_id

    def test_n_trials_in_result(self):
        ev  = RobustnessEvaluator()
        res = ev.evaluate([_cand()], [], [], n_trials=5, seed=0)
        assert res["n_trials"] == 5

    def test_noise_in_result(self):
        ev  = RobustnessEvaluator()
        res = ev.evaluate([_cand()], [], [], noise_level=0.1, n_trials=5, seed=0)
        assert res["noise_level"] == pytest.approx(0.1)


# ═══════════════════════════════════════════════════════════════════════════════
# TestOptimizationManager
# ═══════════════════════════════════════════════════════════════════════════════

class TestOptimizationManager:
    def _req(self, cands=None, objs=None, cons=None) -> OptimizationRequest:
        return OptimizationRequest(
            candidates  = cands or [_cand("A", score=0.9), _cand("B", score=0.3)],
            objectives  = objs  or [_score_obj("o1")],
            constraints = cons  or [],
        )

    def test_optimize_simple(self):
        mgr    = OptimizationManager()
        result = mgr.optimize(self._req())
        assert result.succeeded
        assert result.optimal_id is not None

    def test_recommend_best(self):
        mgr    = OptimizationManager()
        result = mgr.optimize(self._req())
        best   = next(c for c in result.candidates if c.candidate_id == result.optimal_id)
        assert best.name == "A"

    def test_infeasible_all_blocked(self):
        mgr    = OptimizationManager()
        req    = self._req(cons=[_threshold("t1", 0.99)])
        # Use CONSTRAINT algorithm which relaxes to least-violated
        req.algorithm_type = AlgorithmType.CONSTRAINT
        result = mgr.optimize(req)
        # ConstraintSatisfactionOptimizer relaxes → still returns an optimal_id
        assert result.optimal_id is not None

    def test_get_result(self):
        mgr    = OptimizationManager()
        result = mgr.optimize(self._req())
        fetched = mgr.get(result.result_id)
        assert fetched.result_id == result.result_id

    def test_not_found_raises(self):
        mgr = OptimizationManager()
        with pytest.raises(OptimizationNotFoundError):
            mgr.get("ghost-id")

    def test_history(self):
        mgr = OptimizationManager()
        for _ in range(3):
            mgr.optimize(self._req())
        assert len(mgr.recent(10)) == 3

    def test_statistics(self):
        mgr = OptimizationManager()
        mgr.optimize(self._req())
        s = mgr.statistics()
        assert s["total"] == 1
        assert s["success"] == 1

    def test_singleton(self):
        m1 = get_optimization_manager()
        m2 = get_optimization_manager()
        assert m1 is m2


# ═══════════════════════════════════════════════════════════════════════════════
# TestDecisionOptimizationEngine
# ═══════════════════════════════════════════════════════════════════════════════

class TestDecisionOptimizationEngine:
    def _req(self) -> OptimizationRequest:
        return OptimizationRequest(
            candidates  = [_cand("A", score=0.9), _cand("B", score=0.3)],
            objectives  = [_score_obj("o1")],
        )

    def test_initialize_and_running(self):
        eng = DecisionOptimizationEngine()
        assert not eng.is_running
        eng.initialize()
        assert eng.is_running
        eng.shutdown()

    def test_double_init_raises(self):
        eng = DecisionOptimizationEngine()
        eng.initialize()
        with pytest.raises(EngineAlreadyRunningError):
            eng.initialize()

    def test_not_initialized_raises(self):
        eng = DecisionOptimizationEngine()
        with pytest.raises(EngineNotInitializedError):
            eng.optimize(self._req())

    def test_shutdown(self):
        eng = DecisionOptimizationEngine()
        eng.initialize()
        eng.shutdown()
        assert not eng.is_running

    def test_optimize(self):
        eng = DecisionOptimizationEngine()
        eng.initialize()
        result = eng.optimize(self._req())
        assert result.succeeded

    def test_recommend(self):
        eng  = DecisionOptimizationEngine()
        eng.initialize()
        cands = [_cand("A", score=0.9), _cand("B", score=0.2)]
        result = eng.recommend(cands, objectives=[_score_obj("o1")])
        assert result.succeeded

    def test_async_optimize(self):
        eng = DecisionOptimizationEngine()
        eng.initialize()

        async def _run():
            return await eng.optimize_async(self._req())

        result = asyncio.run(_run())
        assert result.succeeded

    def test_register_objective(self):
        eng = DecisionOptimizationEngine()
        eng.initialize()
        o   = _score_obj("custom_o1")
        eng.register_objective(o)
        assert get_objective_registry().has("custom_o1")

    def test_register_constraint(self):
        eng = DecisionOptimizationEngine()
        eng.initialize()
        c   = _threshold("custom_c1", 0.5)
        eng.register_constraint(c)
        assert get_constraint_optimizer().has("custom_c1")

    def test_register_algorithm(self):
        eng = DecisionOptimizationEngine()
        eng.initialize()

        class TestAlg(OptimizationAlgorithm):
            @property
            def algorithm_id(self) -> str: return "test_alg"
            @property
            def name(self) -> str: return "Test"
            def optimize(self, *a, **k): return OptimizationSolution()

        eng.register_algorithm(TestAlg())
        assert get_algorithm_registry().has("test_alg")

    def test_health(self):
        eng = DecisionOptimizationEngine()
        eng.initialize()
        h   = eng.health()
        assert h["running"] is True
        assert h["version"] == "1.0.0"

    def test_stats(self):
        eng = DecisionOptimizationEngine()
        eng.initialize()
        s   = eng.stats()
        assert s["version"] == "1.0.0"

    def test_singleton(self):
        e1 = get_decision_optimization_engine()
        e2 = get_decision_optimization_engine()
        assert e1 is e2


# ═══════════════════════════════════════════════════════════════════════════════
# TestConcurrency
# ═══════════════════════════════════════════════════════════════════════════════

class TestConcurrency:
    def test_concurrent_optimizations(self):
        mgr     = OptimizationManager()
        results = []
        errors  = []

        def _run(i: int):
            try:
                cands = [_cand(f"A{i}", score=float(i) / 10)]
                req   = OptimizationRequest(
                    candidates = cands,
                    objectives = [_score_obj("o1")],
                )
                results.append(mgr.optimize(req))
            except Exception as e:  # noqa: BLE001
                errors.append(e)

        threads = [threading.Thread(target=_run, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors)  == 0
        assert len(results) == 10

    def test_concurrent_registry(self):
        reg    = get_objective_registry()
        errors = []

        def _reg(i: int):
            try:
                reg.register(_score_obj(f"concurrent_{i}"), overwrite=True)
            except Exception as e:  # noqa: BLE001
                errors.append(e)

        threads = [threading.Thread(target=_reg, args=(i,)) for i in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0


# ═══════════════════════════════════════════════════════════════════════════════
# TestOptimizationFactory
# ═══════════════════════════════════════════════════════════════════════════════

class TestOptimizationFactory:
    def test_make_candidate(self):
        c = OptimizationFactory.make_candidate("X", evaluation_score=0.7, risk=0.3)
        assert c.name == "X"
        assert c.evaluation_score == pytest.approx(0.7)
        assert c.get("risk") == pytest.approx(0.3)

    def test_make_score_objective(self):
        o = OptimizationFactory.make_score_objective("o1")
        c = _cand(score=0.8)
        assert o.evaluate(c) == pytest.approx(0.8)

    def test_make_function_objective(self):
        o = OptimizationFactory.make_function_objective("o1", "f", lambda c: c.evaluation_score * 2)
        assert o.evaluate(_cand(score=0.5)) == pytest.approx(1.0)

    def test_make_threshold_constraint(self):
        con = OptimizationFactory.make_threshold_constraint("c1", "C1", 0.6)
        assert con.check(_cand(score=0.7)).satisfied
        assert not con.check(_cand(score=0.5)).satisfied

    def test_make_request(self):
        cands = [_cand("A")]
        req   = OptimizationFactory.make_request(cands)
        assert isinstance(req, OptimizationRequest)
        assert len(req.candidates) == 1


# ═══════════════════════════════════════════════════════════════════════════════
# TestPackageImports
# ═══════════════════════════════════════════════════════════════════════════════

class TestPackageImports:
    def test_all_symbols_importable(self):
        import iios.decision_optimization as pkg
        for name in pkg.__all__:
            assert hasattr(pkg, name), f"Missing: {name}"

    def test_exception_hierarchy(self):
        assert issubclass(ObjectiveNotFoundError, OptimizationEngineError)
        assert issubclass(EngineAlreadyRunningError, OptimizationEngineError)
        assert issubclass(InfeasibleSolutionError, OptimizationEngineError)

    def test_version(self):
        import iios.decision_optimization as pkg
        assert pkg.__version__ == "1.0.0"
