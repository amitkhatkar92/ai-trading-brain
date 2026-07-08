"""tests/unit/decision_evaluation/test_evaluation_engine.py"""
from __future__ import annotations

import asyncio
import threading
import time

import pytest

from iios.decision_evaluation import (
    # Constants
    CriterionDirection, CriterionType, EvaluationMode, NormalizationMethod,
    RankingMethod, ScoringMethod, WeightingStrategy,
    EVALUATION_ENGINE_VERSION,
    # Exceptions
    CriterionAlreadyExistsError, CriterionNotFoundError,
    EngineAlreadyRunningError, EngineNotInitializedError,
    EvaluationEngineError, EvaluationNotFoundError,
    InsufficientAlternativesError, InvalidWeightError, WeightSumError,
    RegistryOverflowError, RankingAlgorithmNotFoundError,
    # Context
    Alternative, evaluation_session, eval_stage_scope,
    get_evaluation_context, reset_evaluation_context,
    # Criteria
    Criterion, QuantitativeCriterion, QualitativeCriterion,
    BooleanCriterion, CompositeCriterion,
    CriteriaGroup, CriteriaManager, CriteriaValidator, ValidationResult,
    get_criteria_registry, reset_criteria_registry,
    # Scoring
    CriterionScore, AlternativeScore, ScoreCalculator,
    ScoreNormalizer, ScoreAggregator, ScoringEngine,
    ScoreReport, build_score_report,
    # Weighting
    WeightManager,
    # Ranking
    RankingAlgorithm, ScoreBasedRanking, ParetoRanking, UtilityRanking,
    RankingEngine, RankingReport, build_ranking_report,
    get_ranking_registry, reset_ranking_registry,
    # Tradeoff / Utility
    TradeoffPair, TradeoffPoint, TradeoffAnalysis, TradeoffAnalyzer,
    TradeoffEngine, DecisionMatrix, build_decision_matrix,
    UtilityFunction, LinearUtility, SigmoidUtility, StepUtility, PowerUtility,
    UtilityEngine,
    # Analytics
    EvaluationAnalytics,
    # Manager / Engine
    EvaluationRequest, EvaluationResult,
    EvaluationManager, get_evaluation_manager, reset_evaluation_manager,
    EvaluationFactory,
    DecisionEvaluationEngine,
    get_decision_evaluation_engine, reset_decision_evaluation_engine,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _alt(name: str = "A", **payload) -> Alternative:
    return Alternative(name=name, payload=payload)


def _quant(cid: str, key: str, direction: str = "maximize", weight: float = 1.0) -> QuantitativeCriterion:
    return QuantitativeCriterion(
        criterion_id = cid,
        name         = cid,
        extractor    = lambda alt: float(alt.get(key, 0.0)),
        direction    = CriterionDirection(direction),
        weight       = weight,
    )


def _qual(cid: str, scorer, weight: float = 1.0) -> QualitativeCriterion:
    return QualitativeCriterion(criterion_id=cid, name=cid, scorer=scorer, weight=weight)


def _bool_crit(cid: str, predicate, weight: float = 1.0) -> BooleanCriterion:
    return BooleanCriterion(criterion_id=cid, name=cid, predicate=predicate, weight=weight)


@pytest.fixture(autouse=True)
def _reset_all():
    reset_decision_evaluation_engine()
    reset_evaluation_manager()
    reset_criteria_registry()
    reset_ranking_registry()
    reset_evaluation_context()
    yield
    reset_decision_evaluation_engine()
    reset_evaluation_manager()
    reset_criteria_registry()
    reset_ranking_registry()
    reset_evaluation_context()


# ═══════════════════════════════════════════════════════════════════════════════
# TestConstants
# ═══════════════════════════════════════════════════════════════════════════════

class TestConstants:
    def test_criterion_direction_values(self):
        assert CriterionDirection.MAXIMIZE.value == "maximize"
        assert CriterionDirection.MINIMIZE.value == "minimize"
        assert CriterionDirection.TARGET.value   == "target"

    def test_scoring_method_values(self):
        assert ScoringMethod.WEIGHTED_SUM.value     == "weighted_sum"
        assert ScoringMethod.WEIGHTED_PRODUCT.value == "weighted_product"

    def test_normalization_method_values(self):
        assert NormalizationMethod.MINMAX.value == "minmax"
        assert NormalizationMethod.ZSCORE.value == "zscore"
        assert NormalizationMethod.NONE.value   == "none"

    def test_ranking_method_values(self):
        assert RankingMethod.SCORE.value     == "score"
        assert RankingMethod.PARETO.value    == "pareto"
        assert RankingMethod.UTILITY.value   == "utility"

    def test_weighting_strategy_values(self):
        assert WeightingStrategy.EQUAL.value    == "equal"
        assert WeightingStrategy.MANUAL.value   == "manual"
        assert WeightingStrategy.PRIORITY.value == "priority"

    def test_version(self):
        assert EVALUATION_ENGINE_VERSION == "1.0.0"


# ═══════════════════════════════════════════════════════════════════════════════
# TestExceptions
# ═══════════════════════════════════════════════════════════════════════════════

class TestExceptions:
    def test_base_exception(self):
        e = EvaluationEngineError("test", "EE-999")
        assert "EE-999" in str(e)
        assert "test"   in str(e)

    def test_criterion_not_found(self):
        e = CriterionNotFoundError("c1")
        assert "c1" in str(e)
        assert e.code == "EE-021"

    def test_criterion_already_exists(self):
        e = CriterionAlreadyExistsError("c1")
        assert "c1" in str(e)
        assert e.code == "EE-022"

    def test_invalid_weight(self):
        e = InvalidWeightError("c1", -1.0)
        assert "EE-061" in str(e)

    def test_engine_not_initialized(self):
        e = EngineNotInitializedError()
        assert "EE-081" in str(e)

    def test_engine_already_running(self):
        e = EngineAlreadyRunningError()
        assert "EE-082" in str(e)

    def test_insufficient_alternatives(self):
        e = InsufficientAlternativesError(0, required=1)
        assert "EE-072" in str(e)

    def test_registry_overflow(self):
        e = RegistryOverflowError(10)
        assert "EE-091" in str(e)
        assert "10" in str(e)

    def test_hierarchy(self):
        assert issubclass(CriterionNotFoundError, EvaluationEngineError)
        assert issubclass(EngineNotInitializedError, EvaluationEngineError)
        assert issubclass(InvalidWeightError, EvaluationEngineError)

    def test_evaluation_not_found(self):
        e = EvaluationNotFoundError("eval-123")
        assert "EE-011" in str(e)


# ═══════════════════════════════════════════════════════════════════════════════
# TestAlternative
# ═══════════════════════════════════════════════════════════════════════════════

class TestAlternative:
    def test_defaults(self):
        a = Alternative()
        assert a.alternative_id
        assert a.confidence == 1.0
        assert a.payload == {}

    def test_get_key(self):
        a = _alt("X", score=42.0)
        assert a.get("score") == 42.0
        assert a.get("missing", -1) == -1

    def test_to_dict(self):
        a = _alt("A", v=1)
        d = a.to_dict()
        assert d["name"] == "A"
        assert "score" in d["payload_keys"] or "v" in d["payload_keys"]

    def test_unique_ids(self):
        a1 = Alternative()
        a2 = Alternative()
        assert a1.alternative_id != a2.alternative_id


# ═══════════════════════════════════════════════════════════════════════════════
# TestEvaluationContextScope
# ═══════════════════════════════════════════════════════════════════════════════

class TestEvaluationContextScope:
    def test_evaluation_session(self):
        with evaluation_session(source_id="test", mode=EvaluationMode.AUDIT) as ctx:
            assert ctx.source_id == "test"
            assert ctx.mode == EvaluationMode.AUDIT

    def test_stage_scope(self):
        with evaluation_session() as ctx:
            assert ctx.current_stage == ""
            with eval_stage_scope("scoring"):
                assert ctx.current_stage == "scoring"
            assert ctx.current_stage == ""

    def test_diagnostics(self):
        with evaluation_session() as ctx:
            ctx.add_diagnostic("WARNING", "low confidence")
            ctx.add_diagnostic("ERROR", "missing value")
            assert len(ctx.warnings()) == 1
            assert len(ctx.errors()) == 1

    def test_elapsed(self):
        with evaluation_session() as ctx:
            time.sleep(0.01)
            assert ctx.elapsed_ms() > 0


# ═══════════════════════════════════════════════════════════════════════════════
# TestQuantitativeCriterion
# ═══════════════════════════════════════════════════════════════════════════════

class TestQuantitativeCriterion:
    def test_score_maximize(self):
        c   = _quant("q1", "val")
        alt = _alt("A", val=10.0)
        assert c.score(alt) == 10.0

    def test_score_minimize(self):
        c   = _quant("q1", "cost", direction="minimize")
        alt = _alt("A", cost=5.0)
        assert c.score(alt) == 5.0  # raw value; normalization is done later
        assert c.direction == CriterionDirection.MINIMIZE

    def test_missing_key_returns_zero(self):
        c   = _quant("q1", "absent")
        alt = _alt("A")
        assert c.score(alt) == 0.0

    def test_exception_in_extractor(self):
        c = QuantitativeCriterion(
            criterion_id="bad", name="bad",
            extractor=lambda _: 1 / 0,  # noqa: ZeroDivisionError
        )
        assert c.score(_alt()) == 0.0

    def test_to_dict(self):
        c = _quant("q1", "val")
        d = c.to_dict()
        assert d["criterion_id"] == "q1"
        assert d["direction"]    == "maximize"


# ═══════════════════════════════════════════════════════════════════════════════
# TestQualitativeCriterion
# ═══════════════════════════════════════════════════════════════════════════════

class TestQualitativeCriterion:
    def test_score_range(self):
        c   = _qual("q1", lambda a: float(a.get("q", 0.5)))
        alt = _alt("A", q=0.8)
        assert c.score(alt) == pytest.approx(0.8)

    def test_clipped_above_one(self):
        c   = _qual("q1", lambda _: 2.0)  # scorer returns 2.0
        assert c.score(_alt()) == pytest.approx(1.0)

    def test_clipped_below_zero(self):
        c   = _qual("q1", lambda _: -1.0)
        assert c.score(_alt()) == pytest.approx(0.0)


# ═══════════════════════════════════════════════════════════════════════════════
# TestBooleanCriterion
# ═══════════════════════════════════════════════════════════════════════════════

class TestBooleanCriterion:
    def test_true_returns_one(self):
        c = _bool_crit("b1", lambda _: True)
        assert c.score(_alt()) == 1.0

    def test_false_returns_zero(self):
        c = _bool_crit("b1", lambda _: False)
        assert c.score(_alt()) == 0.0

    def test_exception_returns_zero(self):
        c = _bool_crit("b1", lambda _: 1 / 0)  # noqa: ZeroDivisionError
        assert c.score(_alt()) == 0.0


# ═══════════════════════════════════════════════════════════════════════════════
# TestCompositeCriterion
# ═══════════════════════════════════════════════════════════════════════════════

class TestCompositeCriterion:
    def test_weighted_average(self):
        c1   = _qual("c1", lambda _: 1.0)
        c2   = _qual("c2", lambda _: 0.0)
        comp = CompositeCriterion("comp", "composite", [c1, c2], sub_weights=[1.0, 1.0])
        assert comp.score(_alt()) == pytest.approx(0.5)

    def test_all_pass(self):
        c1   = _bool_crit("c1", lambda _: True)
        c2   = _bool_crit("c2", lambda _: True)
        comp = CompositeCriterion("comp", "c", [c1, c2])
        assert comp.score(_alt()) == pytest.approx(1.0)

    def test_empty_returns_zero(self):
        comp = CompositeCriterion("comp", "c", [])
        assert comp.score(_alt()) == 0.0


# ═══════════════════════════════════════════════════════════════════════════════
# TestCriteriaGroup
# ═══════════════════════════════════════════════════════════════════════════════

class TestCriteriaGroup:
    def test_add_criterion(self):
        g = CriteriaGroup("g1", "group")
        c = _quant("q1", "v")
        g.add(c)
        assert g.criterion_count() == 1

    def test_remove_criterion(self):
        g = CriteriaGroup("g1", "group", [_quant("q1", "v")])
        removed = g.remove("q1")
        assert removed
        assert g.criterion_count() == 0

    def test_score_group_average(self):
        c1 = _qual("c1", lambda _: 0.8)
        c2 = _qual("c2", lambda _: 0.4)
        g  = CriteriaGroup("g1", "g", [c1, c2], aggregation="weighted_average")
        score = g.score_group(_alt())
        assert score == pytest.approx(0.6)

    def test_score_group_min(self):
        c1 = _qual("c1", lambda _: 0.8)
        c2 = _qual("c2", lambda _: 0.4)
        g  = CriteriaGroup("g1", "g", [c1, c2], aggregation="min")
        assert g.score_group(_alt()) == pytest.approx(0.4)

    def test_to_dict(self):
        g = CriteriaGroup("g1", "group")
        d = g.to_dict()
        assert d["group_id"] == "g1"


# ═══════════════════════════════════════════════════════════════════════════════
# TestCriteriaRegistry
# ═══════════════════════════════════════════════════════════════════════════════

class TestCriteriaRegistry:
    def test_register_and_get(self):
        reg = get_criteria_registry()
        c   = _quant("q1", "val")
        reg.register(c)
        assert reg.get("q1") is c

    def test_duplicate_raises(self):
        reg = get_criteria_registry()
        reg.register(_quant("q2", "v"))
        with pytest.raises(CriterionAlreadyExistsError):
            reg.register(_quant("q2", "v"))

    def test_overwrite(self):
        reg = get_criteria_registry()
        c1  = _quant("q3", "v")
        c2  = _quant("q3", "v")
        reg.register(c1)
        reg.register(c2, overwrite=True)
        assert reg.get("q3") is c2

    def test_not_found_raises(self):
        reg = get_criteria_registry()
        with pytest.raises(CriterionNotFoundError):
            reg.get("nonexistent")

    def test_by_type(self):
        reg = get_criteria_registry()
        reg.register(_quant("q4", "v"))
        reg.register(_qual("q5", lambda _: 0.5))
        quant = reg.by_type(CriterionType.QUANTITATIVE)
        qual  = reg.by_type(CriterionType.QUALITATIVE)
        assert any(c.criterion_id == "q4" for c in quant)
        assert any(c.criterion_id == "q5" for c in qual)

    def test_singleton(self):
        r1 = get_criteria_registry()
        r2 = get_criteria_registry()
        assert r1 is r2


# ═══════════════════════════════════════════════════════════════════════════════
# TestCriteriaValidator
# ═══════════════════════════════════════════════════════════════════════════════

class TestCriteriaValidator:
    def test_valid(self):
        v   = CriteriaValidator()
        res = v.validate_criteria([_quant("c1", "v")])
        assert res.valid

    def test_empty_list(self):
        v   = CriteriaValidator()
        res = v.validate_criteria([])
        assert not res.valid

    def test_duplicate_ids(self):
        v   = CriteriaValidator()
        res = v.validate_criteria([_quant("c1", "v"), _quant("c1", "v")])
        assert not res.valid
        assert any("duplicate" in e for e in res.errors)

    def test_validate_alternatives(self):
        v  = CriteriaValidator()
        a1 = _alt("A")
        a2 = Alternative(alternative_id=a1.alternative_id, name="A2")
        res = v.validate_alternatives([a1, a2])
        assert not res.valid


# ═══════════════════════════════════════════════════════════════════════════════
# TestCriterionScore
# ═══════════════════════════════════════════════════════════════════════════════

class TestCriterionScore:
    def test_defaults(self):
        cs = CriterionScore(criterion_id="c1", criterion_name="C1", alternative_id="a1")
        assert cs.raw_score == 0.0
        assert cs.normalized_score == 0.0

    def test_to_dict(self):
        cs = CriterionScore("c1", "C1", "a1", raw_score=5.0, normalized_score=0.8, weight=0.5)
        d  = cs.to_dict()
        assert d["criterion_id"] == "c1"
        assert d["normalized_score"] == 0.8

    def test_weighted_score_computation(self):
        cs = CriterionScore("c1", "C1", "a1", normalized_score=0.8, weight=0.5, weighted_score=0.4)
        assert cs.weighted_score == pytest.approx(0.4)


# ═══════════════════════════════════════════════════════════════════════════════
# TestAlternativeScore
# ═══════════════════════════════════════════════════════════════════════════════

class TestAlternativeScore:
    def _make(self) -> AlternativeScore:
        cs1 = CriterionScore("c1", "C1", "a1", normalized_score=0.8, weight=0.5, weighted_score=0.4)
        cs2 = CriterionScore("c2", "C2", "a1", normalized_score=0.4, weight=0.5, weighted_score=0.2)
        return AlternativeScore("a1", "A", [cs1, cs2], composite_score=0.6)

    def test_get_criterion_score(self):
        a = self._make()
        assert a.get_criterion_score("c1").criterion_id == "c1"

    def test_missing_criterion_score(self):
        a = self._make()
        assert a.get_criterion_score("missing") is None

    def test_to_dict(self):
        a = self._make()
        d = a.to_dict()
        assert d["composite_score"] == pytest.approx(0.6)

    def test_rank_default_zero(self):
        a = AlternativeScore("a1", "A")
        assert a.rank == 0


# ═══════════════════════════════════════════════════════════════════════════════
# TestScoreCalculator
# ═══════════════════════════════════════════════════════════════════════════════

class TestScoreCalculator:
    def test_calculate_quantitative(self):
        calc = ScoreCalculator()
        alts = [_alt("A", v=10.0)]
        crit = [_quant("c1", "v")]
        raw  = calc.calculate(alts, crit)
        assert raw[alts[0].alternative_id]["c1"] == pytest.approx(10.0)

    def test_calculate_qualitative(self):
        calc = ScoreCalculator()
        alts = [_alt("A")]
        crit = [_qual("c1", lambda _: 0.7)]
        raw  = calc.calculate(alts, crit)
        assert raw[alts[0].alternative_id]["c1"] == pytest.approx(0.7)

    def test_calculate_boolean(self):
        calc = ScoreCalculator()
        alts = [_alt("A")]
        crit = [_bool_crit("c1", lambda _: True)]
        raw  = calc.calculate(alts, crit)
        assert raw[alts[0].alternative_id]["c1"] == pytest.approx(1.0)

    def test_multiple_alternatives(self):
        calc = ScoreCalculator()
        alts = [_alt("A", v=1.0), _alt("B", v=2.0)]
        crit = [_quant("c1", "v")]
        raw  = calc.calculate(alts, crit)
        assert len(raw) == 2

    def test_not_applicable_criterion(self):
        calc  = ScoreCalculator()
        alt   = _alt("A", v=5.0)
        crit  = QuantitativeCriterion(
            criterion_id = "c1", name = "C1",
            extractor    = lambda a: float(a.get("v", 0)),
            condition    = lambda _: False,  # never applicable
        )
        raw = calc.calculate([alt], [crit])
        assert raw[alt.alternative_id]["c1"] == 0.0


# ═══════════════════════════════════════════════════════════════════════════════
# TestScoreNormalizer
# ═══════════════════════════════════════════════════════════════════════════════

class TestScoreNormalizer:
    def _raw(self, alts, key="v"):
        return {a.alternative_id: {key: a.get(key, 0.0)} for a in alts}

    def test_minmax_maximize(self):
        alts = [_alt("A", v=0.0), _alt("B", v=10.0)]
        crit = [_quant("v", "v")]
        norm = ScoreNormalizer().normalize(self._raw(alts), crit)
        scores = [norm[a.alternative_id]["v"] for a in alts]
        assert min(scores) == pytest.approx(0.0)
        assert max(scores) == pytest.approx(1.0)

    def test_minmax_minimize(self):
        alts = [_alt("A", v=0.0), _alt("B", v=10.0)]
        crit = [_quant("v", "v", direction="minimize")]
        norm = ScoreNormalizer().normalize(self._raw(alts), crit)
        # minimize: lower raw → higher norm
        a_id = alts[0].alternative_id
        b_id = alts[1].alternative_id
        assert norm[a_id]["v"] > norm[b_id]["v"]

    def test_all_equal_returns_one(self):
        alts = [_alt("A", v=5.0), _alt("B", v=5.0)]
        crit = [_quant("v", "v")]
        norm = ScoreNormalizer().normalize(self._raw(alts), crit)
        for a in alts:
            assert norm[a.alternative_id]["v"] == pytest.approx(1.0)

    def test_single_alternative(self):
        alts = [_alt("A", v=7.0)]
        crit = [_quant("v", "v")]
        norm = ScoreNormalizer().normalize(self._raw(alts), crit)
        assert norm[alts[0].alternative_id]["v"] == pytest.approx(1.0)

    def test_zscore_midpoint_for_equal(self):
        alts = [_alt("A", v=5.0), _alt("B", v=5.0)]
        crit = [_quant("v", "v")]
        norm = ScoreNormalizer().normalize(
            self._raw(alts), crit, NormalizationMethod.ZSCORE
        )
        for a in alts:
            assert norm[a.alternative_id]["v"] == pytest.approx(0.5)

    def test_none_method_clips(self):
        alts = [_alt("A", v=0.3), _alt("B", v=0.7)]
        crit = [_qual("v", lambda a: a.get("v", 0.0))]
        raw  = {a.alternative_id: {"v": a.get("v", 0.0)} for a in alts}
        norm = ScoreNormalizer().normalize(raw, crit, NormalizationMethod.NONE)
        for a in alts:
            v = norm[a.alternative_id]["v"]
            assert 0.0 <= v <= 1.0


# ═══════════════════════════════════════════════════════════════════════════════
# TestScoreAggregator
# ═══════════════════════════════════════════════════════════════════════════════

class TestScoreAggregator:
    def _setup(self, n_alts: int = 2):
        alts = [_alt(f"A{i}", v=float(i)) for i in range(n_alts)]
        crit = [_quant("c1", "v", weight=1.0)]
        return alts, crit

    def test_weighted_sum(self):
        alts, crit = self._setup(2)
        norm   = {a.alternative_id: {"c1": 0.5} for a in alts}
        agg    = ScoreAggregator()
        scored = agg.aggregate(alts, crit, norm, {"c1": 1.0}, ScoringMethod.WEIGHTED_SUM)
        for a in scored:
            assert a.composite_score == pytest.approx(0.5)

    def test_weighted_product(self):
        alts = [_alt("A"), _alt("B")]
        crit = [_quant("c1", "v"), _quant("c2", "v")]
        norm = {a.alternative_id: {"c1": 0.5, "c2": 0.8} for a in alts}
        agg  = ScoreAggregator()
        scored = agg.aggregate(alts, crit, norm, {"c1": 0.5, "c2": 0.5}, ScoringMethod.WEIGHTED_PRODUCT)
        for a in scored:
            # 0.5^0.5 * 0.8^0.5 ≈ 0.632
            assert a.composite_score > 0.0

    def test_equal_weights_sum_to_one(self):
        alts   = [_alt("A")]
        crit   = [_quant("c1", "v"), _quant("c2", "v")]
        norm   = {alts[0].alternative_id: {"c1": 0.8, "c2": 0.6}}
        agg    = ScoreAggregator()
        scored = agg.aggregate(alts, crit, norm, {"c1": 0.5, "c2": 0.5}, ScoringMethod.WEIGHTED_SUM)
        assert scored[0].composite_score == pytest.approx(0.7)

    def test_criterion_score_attached(self):
        alts   = [_alt("A")]
        crit   = [_quant("c1", "v")]
        norm   = {alts[0].alternative_id: {"c1": 0.9}}
        agg    = ScoreAggregator()
        scored = agg.aggregate(alts, crit, norm, {"c1": 1.0}, ScoringMethod.WEIGHTED_SUM)
        cs = scored[0].criterion_scores[0]
        assert cs.criterion_id == "c1"
        assert cs.normalized_score == pytest.approx(0.9)

    def test_empty_alternatives(self):
        agg    = ScoreAggregator()
        scored = agg.aggregate([], [], {}, {})
        assert scored == []


# ═══════════════════════════════════════════════════════════════════════════════
# TestScoreReport
# ═══════════════════════════════════════════════════════════════════════════════

class TestScoreReport:
    def _scored(self):
        return [
            AlternativeScore("a1", "A1", composite_score=0.8),
            AlternativeScore("a2", "A2", composite_score=0.6),
            AlternativeScore("a3", "A3", composite_score=0.4),
        ]

    def test_build_report(self):
        rep = build_score_report(self._scored(), total_criteria=2)
        assert rep.total_alternatives == 3
        assert rep.min_score == pytest.approx(0.4)
        assert rep.max_score == pytest.approx(0.8)

    def test_avg_score(self):
        rep = build_score_report(self._scored())
        assert rep.avg_score == pytest.approx((0.8 + 0.6 + 0.4) / 3)

    def test_to_dict(self):
        rep = build_score_report(self._scored())
        d   = rep.to_dict()
        assert "report_id" in d
        assert "avg_score" in d


# ═══════════════════════════════════════════════════════════════════════════════
# TestScoringEngine
# ═══════════════════════════════════════════════════════════════════════════════

class TestScoringEngine:
    def test_score_single_criterion(self):
        eng    = ScoringEngine()
        alts   = [_alt("A", v=10.0), _alt("B", v=5.0)]
        crit   = [_quant("c1", "v")]
        scored = eng.score(alts, crit)
        ids    = {a.alternative_id: a.composite_score for a in scored}
        # A should have higher score
        a_id = alts[0].alternative_id
        b_id = alts[1].alternative_id
        assert ids[a_id] > ids[b_id]

    def test_minimize_direction(self):
        eng    = ScoringEngine()
        alts   = [_alt("A", cost=100.0), _alt("B", cost=10.0)]
        crit   = [_quant("c1", "cost", direction="minimize")]
        scored = eng.score(alts, crit)
        ids    = {a.alternative_id: a.composite_score for a in scored}
        # B (lower cost) should have higher score
        b_id = alts[1].alternative_id
        a_id = alts[0].alternative_id
        assert ids[b_id] > ids[a_id]

    def test_custom_weights(self):
        eng    = ScoringEngine()
        alts   = [_alt("A", v=1.0)]
        crit   = [_quant("c1", "v"), _quant("c2", "v")]
        scored = eng.score(alts, crit, weights={"c1": 0.9, "c2": 0.1})
        assert len(scored) == 1
        assert scored[0].composite_score >= 0

    def test_weighted_product_method(self):
        eng    = ScoringEngine()
        alts   = [_alt("A", v=5.0)]
        crit   = [_quant("c1", "v")]
        scored = eng.score(alts, crit, method=ScoringMethod.WEIGHTED_PRODUCT)
        assert scored[0].composite_score >= 0

    def test_empty_criteria(self):
        eng    = ScoringEngine()
        scored = eng.score([_alt("A")], [])
        assert scored == []

    def test_empty_alternatives(self):
        eng    = ScoringEngine()
        scored = eng.score([], [_quant("c1", "v")])
        assert scored == []

    def test_summary(self):
        eng    = ScoringEngine()
        scored = eng.score([_alt("A", v=5.0), _alt("B", v=3.0)], [_quant("c1", "v")])
        s      = eng.summary(scored)
        assert s["total"] == 2


# ═══════════════════════════════════════════════════════════════════════════════
# TestWeightManager
# ═══════════════════════════════════════════════════════════════════════════════

class TestWeightManager:
    def test_set_get_weight(self):
        wm = WeightManager()
        wm.set_weight("c1", 2.0)
        assert wm.get_weight("c1") == pytest.approx(2.0)

    def test_invalid_weight_raises(self):
        wm = WeightManager()
        with pytest.raises(InvalidWeightError):
            wm.set_weight("c1", -0.1)

    def test_equal_weights(self):
        wm = WeightManager()
        w  = wm.equal_weights(["c1", "c2", "c3"])
        assert sum(w.values()) == pytest.approx(1.0)
        for v in w.values():
            assert v == pytest.approx(1 / 3)

    def test_normalize_weights(self):
        wm = WeightManager()
        w  = wm.normalize_weights({"c1": 3.0, "c2": 1.0})
        assert w["c1"] == pytest.approx(0.75)
        assert w["c2"] == pytest.approx(0.25)

    def test_resolve_uses_criterion_weight(self):
        wm   = WeightManager()
        crit = [_quant("c1", "v", weight=2.0), _quant("c2", "v", weight=2.0)]
        w    = wm.resolve(crit)
        assert sum(w.values()) == pytest.approx(1.0)

    def test_equal_strategy(self):
        wm   = WeightManager(WeightingStrategy.EQUAL)
        crit = [_quant("c1", "v"), _quant("c2", "v")]
        w    = wm.resolve(crit)
        assert w["c1"] == pytest.approx(0.5)


# ═══════════════════════════════════════════════════════════════════════════════
# TestRankingAlgorithm
# ═══════════════════════════════════════════════════════════════════════════════

class TestRankingAlgorithm:
    def _scored(self, scores):
        alts = []
        for i, s in enumerate(scores):
            a = AlternativeScore(f"a{i}", f"A{i}", composite_score=s)
            alts.append(a)
        return alts

    def test_score_based_rank(self):
        alts   = self._scored([0.3, 0.7, 0.5])
        ranked = ScoreBasedRanking().rank(alts)
        assert ranked[0].composite_score == pytest.approx(0.7)

    def test_score_based_descending(self):
        alts   = self._scored([0.1, 0.5, 0.9])
        ranked = ScoreBasedRanking().rank(alts)
        scores = [a.composite_score for a in ranked]
        assert scores == sorted(scores, reverse=True)

    def test_rank_assigns_integers(self):
        alts   = self._scored([0.5, 0.8, 0.2])
        ranked = ScoreBasedRanking().rank(alts)
        for i, a in enumerate(ranked, start=1):
            assert a.rank == i

    def test_pareto_rank(self):
        # 2-criterion case: a0 dominates a1
        c1_a0 = CriterionScore("c1", "C1", "a0", normalized_score=0.9)
        c2_a0 = CriterionScore("c2", "C2", "a0", normalized_score=0.8)
        c1_a1 = CriterionScore("c1", "C1", "a1", normalized_score=0.6)
        c2_a1 = CriterionScore("c2", "C2", "a1", normalized_score=0.5)
        a0 = AlternativeScore("a0", "A0", [c1_a0, c2_a0], composite_score=0.85)
        a1 = AlternativeScore("a1", "A1", [c1_a1, c2_a1], composite_score=0.55)
        ranked = ParetoRanking().rank([a0, a1])
        assert ranked[0].alternative_id == "a0"
        assert ranked[0].rank == 1
        assert ranked[1].rank == 2

    def test_pareto_no_domination(self):
        # Two alternatives that don't dominate each other
        c1_a0 = CriterionScore("c1", "C1", "a0", normalized_score=0.9)
        c2_a0 = CriterionScore("c2", "C2", "a0", normalized_score=0.2)
        c1_a1 = CriterionScore("c1", "C1", "a1", normalized_score=0.2)
        c2_a1 = CriterionScore("c2", "C2", "a1", normalized_score=0.9)
        a0 = AlternativeScore("a0", "A0", [c1_a0, c2_a0], composite_score=0.55)
        a1 = AlternativeScore("a1", "A1", [c1_a1, c2_a1], composite_score=0.55)
        ranked = ParetoRanking().rank([a0, a1])
        assert all(a.rank == 1 for a in ranked)

    def test_utility_rank(self):
        alts   = self._scored([0.2, 0.8, 0.5])
        ranked = UtilityRanking(utility_fn=lambda s: s).rank(alts)
        assert ranked[0].composite_score >= ranked[-1].composite_score


# ═══════════════════════════════════════════════════════════════════════════════
# TestRankingEngine
# ═══════════════════════════════════════════════════════════════════════════════

class TestRankingEngine:
    def _scored_list(self):
        return [
            AlternativeScore("a1", "A1", composite_score=0.7),
            AlternativeScore("a2", "A2", composite_score=0.3),
            AlternativeScore("a3", "A3", composite_score=0.9),
        ]

    def test_rank_score_method(self):
        eng    = RankingEngine()
        ranked = eng.rank(self._scored_list(), method=RankingMethod.SCORE)
        assert ranked[0].composite_score == pytest.approx(0.9)

    def test_top_alternative(self):
        eng    = RankingEngine()
        ranked = eng.rank(self._scored_list())
        top    = eng.top(ranked)
        assert top is not None
        assert top.composite_score == pytest.approx(0.9)

    def test_pareto_frontier(self):
        eng   = RankingEngine()
        alts  = self._scored_list()
        front = eng.pareto_frontier(alts)
        assert isinstance(front, list)

    def test_rank_preserves_alternatives(self):
        eng    = RankingEngine()
        alts   = self._scored_list()
        ranked = eng.rank(alts)
        assert len(ranked) == len(alts)

    def test_summary(self):
        eng  = RankingEngine()
        s    = eng.summary(self._scored_list())
        assert s["total"] == 3


# ═══════════════════════════════════════════════════════════════════════════════
# TestRankingReport
# ═══════════════════════════════════════════════════════════════════════════════

class TestRankingReport:
    def _ranked(self):
        a1 = AlternativeScore("a1", "A1", composite_score=0.9, rank=1)
        a2 = AlternativeScore("a2", "A2", composite_score=0.6, rank=2)
        return [a1, a2]

    def test_build_report(self):
        rep = build_ranking_report(self._ranked())
        assert rep.ranked_ids[0] == "a1"
        assert rep.top_alternative_id == "a1"

    def test_pareto_frontier(self):
        rep = build_ranking_report(self._ranked(), pareto_frontier=["a1"])
        assert "a1" in rep.pareto_frontier

    def test_to_dict(self):
        rep = build_ranking_report(self._ranked())
        d   = rep.to_dict()
        assert "ranked_ids" in d


# ═══════════════════════════════════════════════════════════════════════════════
# TestDecisionMatrix
# ═══════════════════════════════════════════════════════════════════════════════

class TestDecisionMatrix:
    def _matrix(self):
        alts  = [_alt("A"), _alt("B")]
        crit  = [_quant("c1", "v"), _quant("c2", "v")]
        raw   = {a.alternative_id: {"c1": 1.0, "c2": 2.0} for a in alts}
        norm  = {a.alternative_id: {"c1": 0.5, "c2": 0.7} for a in alts}
        w     = {"c1": 0.5, "c2": 0.5}
        scored = [AlternativeScore(a.alternative_id, a.name, composite_score=0.6) for a in alts]
        return build_decision_matrix(alts, crit, raw, norm, w, scored)

    def test_build_matrix(self):
        m = self._matrix()
        assert len(m.alternative_ids) == 2
        assert len(m.criterion_ids)   == 2

    def test_get_score(self):
        m  = self._matrix()
        s  = m.get_score(m.alternative_ids[0], "c1")
        assert s == pytest.approx(0.5)

    def test_tabular_format(self):
        m   = self._matrix()
        tab = m.tabular()
        assert "headers" in tab
        assert "rows"    in tab
        assert len(tab["rows"]) == 2

    def test_to_dict(self):
        m = self._matrix()
        d = m.to_dict()
        assert "matrix_id"        in d
        assert "composite_scores" in d


# ═══════════════════════════════════════════════════════════════════════════════
# TestTradeoffAnalyzer
# ═══════════════════════════════════════════════════════════════════════════════

class TestTradeoffAnalyzer:
    def _scored_pair(self):
        c1a = CriterionScore("c1", "C1", "a1", normalized_score=0.9)
        c2a = CriterionScore("c2", "C2", "a1", normalized_score=0.2)
        c1b = CriterionScore("c1", "C1", "a2", normalized_score=0.3)
        c2b = CriterionScore("c2", "C2", "a2", normalized_score=0.9)
        a1  = AlternativeScore("a1", "A1", [c1a, c2a], composite_score=0.55)
        a2  = AlternativeScore("a2", "A2", [c1b, c2b], composite_score=0.60)
        return [a1, a2]

    def test_analyze_pair(self):
        ana    = TradeoffAnalyzer()
        pair   = TradeoffPair("c1", "c2")
        result = ana.analyze(self._scored_pair(), [pair])
        assert pair.key() in result.points
        assert len(result.points[pair.key()]) == 2

    def test_pareto_frontier(self):
        ana      = TradeoffAnalyzer()
        frontier = ana.compute_pareto_frontier(self._scored_pair())
        # Neither dominates the other since trade-off → both should be on frontier
        assert len(frontier) == 2

    def test_dominated(self):
        # a0 strictly dominates a1
        c1a = CriterionScore("c1", "C1", "a0", normalized_score=0.9)
        c2a = CriterionScore("c2", "C2", "a0", normalized_score=0.9)
        c1b = CriterionScore("c1", "C1", "a1", normalized_score=0.5)
        c2b = CriterionScore("c2", "C2", "a1", normalized_score=0.5)
        a0  = AlternativeScore("a0", "A0", [c1a, c2a], composite_score=0.9)
        a1  = AlternativeScore("a1", "A1", [c1b, c2b], composite_score=0.5)
        ana  = TradeoffAnalyzer()
        result = ana.analyze([a0, a1], [])
        assert "a1" in result.dominated

    def test_empty_alternatives(self):
        ana    = TradeoffAnalyzer()
        result = ana.analyze([], [TradeoffPair("c1", "c2")])
        assert result.pareto_frontier == []

    def test_to_dict(self):
        ana    = TradeoffAnalyzer()
        result = ana.analyze(self._scored_pair(), [])
        d      = result.to_dict()
        assert "analysis_id" in d


# ═══════════════════════════════════════════════════════════════════════════════
# TestTradeoffEngine
# ═══════════════════════════════════════════════════════════════════════════════

class TestTradeoffEngine:
    def _scored(self):
        a = AlternativeScore("a1", "A1", composite_score=0.7)
        b = AlternativeScore("a2", "A2", composite_score=0.5)
        return [a, b]

    def test_analyze_without_pairs(self):
        eng    = TradeoffEngine()
        result = eng.analyze(self._scored())
        assert isinstance(result, TradeoffAnalysis)

    def test_analyze_with_pairs(self):
        eng    = TradeoffEngine()
        pair   = TradeoffPair("c1", "c2")
        result = eng.analyze(self._scored(), pairs=[pair])
        assert pair.key() in result.points

    def test_apply_utility(self):
        eng     = TradeoffEngine()
        alts    = self._scored()
        result  = eng.apply_utility(alts, LinearUtility(slope=2.0, intercept=0.0))
        assert result[0].composite_score == pytest.approx(alts[0].composite_score * 2.0)


# ═══════════════════════════════════════════════════════════════════════════════
# TestUtilityEngine
# ═══════════════════════════════════════════════════════════════════════════════

class TestUtilityEngine:
    def test_linear_utility(self):
        u = LinearUtility(slope=2.0, intercept=0.1)
        assert u.apply(0.5) == pytest.approx(1.1)

    def test_sigmoid_utility(self):
        u = SigmoidUtility(k=10.0, midpoint=0.5)
        assert u.apply(0.5) == pytest.approx(0.5)
        assert u.apply(1.0) > 0.9

    def test_step_utility(self):
        u = StepUtility([(0.0, 0.0), (0.5, 0.5), (0.8, 1.0)])
        assert u.apply(0.3) == pytest.approx(0.0)
        assert u.apply(0.6) == pytest.approx(0.5)
        assert u.apply(0.9) == pytest.approx(1.0)

    def test_power_utility_averse(self):
        u = PowerUtility(power=0.5)
        assert u.apply(0.25) == pytest.approx(0.5)

    def test_apply_utility_to_alternatives(self):
        eng  = UtilityEngine()
        alts = [AlternativeScore("a1", "A", composite_score=0.4)]
        res  = eng.apply_utility(alts, LinearUtility(slope=1.5))
        assert res[0].composite_score == pytest.approx(0.6)

    def test_utility_does_not_mutate_original(self):
        eng  = UtilityEngine()
        orig = AlternativeScore("a1", "A", composite_score=0.4)
        res  = eng.apply_utility([orig], LinearUtility(slope=2.0))
        assert orig.composite_score == pytest.approx(0.4)  # not mutated
        assert res[0].composite_score == pytest.approx(0.8)


# ═══════════════════════════════════════════════════════════════════════════════
# TestEvaluationAnalytics
# ═══════════════════════════════════════════════════════════════════════════════

class TestEvaluationAnalytics:
    def _result(self):
        """Full EvaluationResult with two alternatives and two criteria."""
        alts  = [_alt("A", v1=10.0, v2=2.0), _alt("B", v1=2.0, v2=10.0)]
        crit  = [_quant("c1", "v1"), _quant("c2", "v2")]
        eng   = ScoringEngine()
        scored = eng.score(alts, crit)
        r_eng  = RankingEngine()
        ranked = r_eng.rank(scored)
        result = EvaluationResult(
            request_id           = "test",
            alternatives         = alts,
            scored_alternatives  = scored,
            ranked_alternatives  = ranked,
        )
        return result, alts, crit

    def test_criterion_importance(self):
        result, _, _ = self._result()
        ana   = EvaluationAnalytics()
        imp   = ana.criterion_importance(result)
        # Both criteria have high variance (reversed patterns)
        assert "c1" in imp
        assert "c2" in imp

    def test_consistency_check_passes(self):
        result, _, _ = self._result()
        ana   = EvaluationAnalytics()
        check = ana.consistency_check(result)
        assert check["consistent"] is True

    def test_consistency_issues_detected(self):
        # Manually corrupt rank order
        a1 = AlternativeScore("a1", "A1", composite_score=0.2, rank=1)
        a2 = AlternativeScore("a2", "A2", composite_score=0.8, rank=2)
        result = EvaluationResult(ranked_alternatives=[a1, a2])
        ana    = EvaluationAnalytics()
        check  = ana.consistency_check(result)
        assert check["consistent"] is False

    def test_sensitivity_analysis(self):
        alts  = [_alt("A", v=10.0), _alt("B", v=5.0)]
        crit  = [_quant("c1", "v")]
        req   = EvaluationRequest(
            alternatives   = alts,
            criteria       = crit,
            scoring_method = ScoringMethod.WEIGHTED_SUM,
            normalization  = NormalizationMethod.MINMAX,
            ranking_method = RankingMethod.SCORE,
        )
        ana    = EvaluationAnalytics()
        result = ana.sensitivity_analysis(req, "c1", steps=3)
        assert "weights" in result
        assert len(result["weights"]) == 3

    def test_criterion_importance_empty(self):
        result = EvaluationResult()
        ana    = EvaluationAnalytics()
        imp    = ana.criterion_importance(result)
        assert imp == {}


# ═══════════════════════════════════════════════════════════════════════════════
# TestEvaluationManager
# ═══════════════════════════════════════════════════════════════════════════════

class TestEvaluationManager:
    def _simple_request(self):
        alts = [_alt("A", v=10.0), _alt("B", v=5.0)]
        crit = [_quant("c1", "v")]
        return EvaluationRequest(alternatives=alts, criteria=crit)

    def test_evaluate_simple(self):
        mgr    = EvaluationManager()
        req    = self._simple_request()
        result = mgr.evaluate(req)
        assert result.succeeded
        assert result.recommended_id is not None

    def test_recommend_best(self):
        mgr    = EvaluationManager()
        req    = self._simple_request()
        result = mgr.evaluate(req)
        # A has v=10 (higher), B has v=5 → A should be recommended
        best_name = next(
            a.name for a in result.alternatives
            if a.alternative_id == result.recommended_id
        )
        assert best_name == "A"

    def test_with_tradeoff(self):
        alts   = [_alt("A", v=10.0), _alt("B", v=5.0)]
        crit   = [_quant("c1", "v"), _quant("c2", "v")]
        req    = EvaluationRequest(
            alternatives  = alts,
            criteria      = crit,
            tradeoff_pairs = [TradeoffPair("c1", "c2")],
        )
        mgr    = EvaluationManager()
        result = mgr.evaluate(req)
        assert result.tradeoff_analysis is not None

    def test_evaluation_history(self):
        mgr = EvaluationManager()
        for _ in range(3):
            mgr.evaluate(self._simple_request())
        assert len(mgr.recent(10)) == 3

    def test_get_evaluation(self):
        mgr    = EvaluationManager()
        result = mgr.evaluate(self._simple_request())
        fetched = mgr.get(result.result_id)
        assert fetched.result_id == result.result_id

    def test_evaluation_not_found(self):
        mgr = EvaluationManager()
        with pytest.raises(EvaluationNotFoundError):
            mgr.get("nonexistent-id")

    def test_statistics(self):
        mgr = EvaluationManager()
        mgr.evaluate(self._simple_request())
        stats = mgr.statistics()
        assert stats["total"] == 1
        assert stats["success"] == 1

    def test_singleton(self):
        m1 = get_evaluation_manager()
        m2 = get_evaluation_manager()
        assert m1 is m2


# ═══════════════════════════════════════════════════════════════════════════════
# TestDecisionEvaluationEngine
# ═══════════════════════════════════════════════════════════════════════════════

class TestDecisionEvaluationEngine:
    def _req(self):
        alts = [_alt("A", v=9.0), _alt("B", v=4.0), _alt("C", v=7.0)]
        crit = [_quant("c1", "v")]
        return EvaluationRequest(alternatives=alts, criteria=crit)

    def test_initialize_and_running(self):
        eng = DecisionEvaluationEngine()
        assert not eng.is_running
        eng.initialize()
        assert eng.is_running

    def test_double_init_raises(self):
        eng = DecisionEvaluationEngine()
        eng.initialize()
        with pytest.raises(EngineAlreadyRunningError):
            eng.initialize()

    def test_not_initialized_raises(self):
        eng = DecisionEvaluationEngine()
        with pytest.raises(EngineNotInitializedError):
            eng.evaluate(self._req())

    def test_shutdown(self):
        eng = DecisionEvaluationEngine()
        eng.initialize()
        eng.shutdown()
        assert not eng.is_running

    def test_evaluate(self):
        eng = DecisionEvaluationEngine()
        eng.initialize()
        result = eng.evaluate(self._req())
        assert result.succeeded
        assert result.recommended_id is not None

    def test_recommend_shortcut(self):
        eng  = DecisionEvaluationEngine()
        eng.initialize()
        alts = [_alt("A", v=9.0), _alt("B", v=1.0)]
        crit = [_quant("c1", "v")]
        result = eng.recommend(alts, crit)
        assert result.succeeded

    def test_async_evaluate(self):
        eng = DecisionEvaluationEngine()
        eng.initialize()

        async def _run():
            return await eng.evaluate_async(self._req())

        result = asyncio.run(_run())
        assert result.succeeded

    def test_register_criterion(self):
        eng = DecisionEvaluationEngine()
        eng.initialize()
        c   = _quant("custom_c1", "v")
        eng.register_criterion(c)
        assert get_criteria_registry().has("custom_c1")

    def test_register_algorithm(self):
        eng = DecisionEvaluationEngine()
        eng.initialize()
        eng.register_algorithm(ScoreBasedRanking())
        assert get_ranking_registry().has("score_based")

    def test_health_running(self):
        eng = DecisionEvaluationEngine()
        eng.initialize()
        h   = eng.health()
        assert h["running"] is True
        assert h["version"] == "1.0.0"

    def test_stats_version(self):
        eng = DecisionEvaluationEngine()
        eng.initialize()
        s   = eng.stats()
        assert s["version"] == "1.0.0"
        assert s["running"] is True

    def test_singleton_pattern(self):
        e1 = get_decision_evaluation_engine()
        e2 = get_decision_evaluation_engine()
        assert e1 is e2


# ═══════════════════════════════════════════════════════════════════════════════
# TestConcurrency
# ═══════════════════════════════════════════════════════════════════════════════

class TestConcurrency:
    def test_concurrent_evaluations(self):
        mgr     = EvaluationManager()
        results = []
        errors  = []

        def _run():
            try:
                alts = [_alt("A", v=float(threading.get_ident() % 100))]
                crit = [_quant("c1", "v")]
                req  = EvaluationRequest(alternatives=alts, criteria=crit)
                results.append(mgr.evaluate(req))
            except Exception as e:  # noqa: BLE001
                errors.append(e)

        threads = [threading.Thread(target=_run) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors)  == 0
        assert len(results) == 10

    def test_concurrent_registry_access(self):
        reg    = get_criteria_registry()
        errors = []

        def _register(i):
            try:
                reg.register(_quant(f"concurrent_{i}", "v"), overwrite=True)
            except Exception as e:  # noqa: BLE001
                errors.append(e)

        threads = [threading.Thread(target=_register, args=(i,)) for i in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0


# ═══════════════════════════════════════════════════════════════════════════════
# TestPackageImports
# ═══════════════════════════════════════════════════════════════════════════════

class TestPackageImports:
    def test_all_symbols_importable(self):
        import iios.decision_evaluation as pkg
        for name in pkg.__all__:
            assert hasattr(pkg, name), f"Missing symbol: {name}"

    def test_exception_hierarchy(self):
        assert issubclass(CriterionNotFoundError,  EvaluationEngineError)
        assert issubclass(EngineAlreadyRunningError, EvaluationEngineError)
        assert issubclass(InvalidWeightError,       EvaluationEngineError)

    def test_version_accessible(self):
        import iios.decision_evaluation as pkg
        assert pkg.__version__ == "1.0.0"


# ═══════════════════════════════════════════════════════════════════════════════
# TestEvaluationFactory
# ═══════════════════════════════════════════════════════════════════════════════

class TestEvaluationFactory:
    def test_make_alternative(self):
        a = EvaluationFactory.make_alternative("X", score=5.0)
        assert a.name == "X"
        assert a.get("score") == 5.0

    def test_make_quantitative(self):
        c = EvaluationFactory.make_quantitative_criterion(
            "c1", "C1", lambda a: float(a.get("v", 0))
        )
        assert c.criterion_id == "c1"

    def test_make_qualitative(self):
        c = EvaluationFactory.make_qualitative_criterion("c1", "C1", lambda _: 0.7)
        assert c.criterion_id == "c1"

    def test_make_boolean(self):
        c = EvaluationFactory.make_boolean_criterion("c1", "C1", lambda _: True)
        assert c.score(_alt()) == 1.0

    def test_make_request(self):
        alts = [EvaluationFactory.make_alternative("A")]
        crit = [EvaluationFactory.make_boolean_criterion("c1", "C1", lambda _: True)]
        req  = EvaluationFactory.make_request(alts, crit)
        assert isinstance(req, EvaluationRequest)

    def test_make_linear_utility(self):
        u = EvaluationFactory.make_linear_utility(slope=2.0)
        assert u.apply(0.5) == pytest.approx(1.0)
