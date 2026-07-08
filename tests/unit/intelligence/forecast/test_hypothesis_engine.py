"""
tests/unit/intelligence/forecast/test_hypothesis_engine.py
===========================================================
Comprehensive test suite for the Hypothesis & Forecast Engine.
Target: ≥ 110 tests.
"""
from __future__ import annotations

import asyncio
import math
import threading
import time
import pytest

# ── Helpers ────────────────────────────────────────────────────────────────────

def _reset_all() -> None:
    from iios.intelligence.forecast.hypothesis_engine   import reset_hypothesis_engine
    from iios.intelligence.forecast.hypothesis_manager  import reset_hypothesis_manager
    from iios.intelligence.forecast.hypothesis_registry import reset_hypothesis_registry
    from iios.intelligence.forecast.hypothesis_factory  import reset_hypothesis_factory
    from iios.intelligence.forecast.hypothesis_context  import reset_forecast_context
    from iios.intelligence.forecast.forecast.forecast_engine   import reset_forecast_engine
    from iios.intelligence.forecast.forecast.forecast_manager  import reset_forecast_manager
    from iios.intelligence.forecast.forecast.forecast_registry import reset_forecast_registry
    from iios.intelligence.forecast.scenario.scenario_engine   import reset_scenario_engine
    from iios.intelligence.forecast.scenario.scenario_registry import reset_scenario_registry
    from iios.intelligence.forecast.probability.probability_engine import reset_probability_engine
    from iios.intelligence.forecast.uncertainty.uncertainty_engine import reset_uncertainty_engine
    from iios.intelligence.forecast.evaluation.forecast_evaluator import reset_forecast_evaluator
    from iios.intelligence.forecast.evaluation.forecast_tracker   import reset_forecast_tracker
    from iios.intelligence.forecast.evaluation.model_feedback     import reset_model_feedback

    reset_hypothesis_engine()
    reset_hypothesis_manager()
    reset_hypothesis_registry()
    reset_hypothesis_factory()
    reset_forecast_context()
    reset_forecast_engine()
    reset_forecast_manager()
    reset_forecast_registry()
    reset_scenario_engine()
    reset_scenario_registry()
    reset_probability_engine()
    reset_uncertainty_engine()
    reset_forecast_evaluator()
    reset_forecast_tracker()
    reset_model_feedback()


@pytest.fixture(autouse=True)
def clean_state():
    _reset_all()
    yield
    _reset_all()


# ── Constants / Enums ─────────────────────────────────────────────────────────

class TestConstants:
    def test_hypothesis_type_values(self):
        from iios.intelligence.forecast.hypothesis_constants import HypothesisType
        assert HypothesisType.DIRECTIONAL.value == "directional"
        assert HypothesisType.CAUSAL.value == "causal"
        assert HypothesisType.NULL.value == "null"
        assert HypothesisType.ALTERNATIVE.value == "alternative"

    def test_hypothesis_status_values(self):
        from iios.intelligence.forecast.hypothesis_constants import HypothesisStatus
        assert HypothesisStatus.DRAFT.value == "draft"
        assert HypothesisStatus.CONFIRMED.value == "confirmed"
        assert HypothesisStatus.REJECTED.value == "rejected"

    def test_forecast_horizon_values(self):
        from iios.intelligence.forecast.hypothesis_constants import ForecastHorizon
        assert ForecastHorizon.INTRADAY.value == "intraday"
        assert ForecastHorizon.ULTRA_LONG.value == "ultra_long"

    def test_forecast_type_values(self):
        from iios.intelligence.forecast.hypothesis_constants import ForecastType
        assert ForecastType.POINT.value == "point"
        assert ForecastType.ENSEMBLE.value == "ensemble"

    def test_scenario_type_values(self):
        from iios.intelligence.forecast.hypothesis_constants import ScenarioType
        assert ScenarioType.BASE_CASE.value == "base_case"
        assert ScenarioType.BLACK_SWAN.value == "black_swan"

    def test_probability_method_values(self):
        from iios.intelligence.forecast.hypothesis_constants import ProbabilityMethod
        assert ProbabilityMethod.BAYESIAN.value == "bayesian"
        assert ProbabilityMethod.MONTE_CARLO.value == "monte_carlo"

    def test_evaluation_metric_values(self):
        from iios.intelligence.forecast.hypothesis_constants import EvaluationMetric
        assert EvaluationMetric.MAE.value == "mae"
        assert EvaluationMetric.CALIBRATION.value == "calibration"

    def test_uncertainty_type_values(self):
        from iios.intelligence.forecast.hypothesis_constants import UncertaintyType
        assert UncertaintyType.ALEATORIC.value == "aleatoric"
        assert UncertaintyType.EPISTEMIC.value == "epistemic"

    def test_version_string(self):
        from iios.intelligence.forecast.hypothesis_constants import HYPOTHESIS_ENGINE_VERSION
        assert HYPOTHESIS_ENGINE_VERSION == "1.0.0"

    def test_max_limits(self):
        from iios.intelligence.forecast.hypothesis_constants import (
            MAX_HYPOTHESES, MAX_FORECASTS, MAX_SCENARIOS,
        )
        assert MAX_HYPOTHESES >= 100
        assert MAX_FORECASTS  >= 100
        assert MAX_SCENARIOS  >= 10


# ── Exceptions ────────────────────────────────────────────────────────────────

class TestExceptions:
    def test_base_error_code(self):
        from iios.intelligence.forecast.hypothesis_exceptions import HypothesisForecastError
        e = HypothesisForecastError("test")
        assert "HFE-000" in str(e)

    def test_hypothesis_not_found(self):
        from iios.intelligence.forecast.hypothesis_exceptions import HypothesisNotFoundError
        e = HypothesisNotFoundError("h-001")
        assert "HFE-011" in str(e)
        assert "h-001" in str(e)

    def test_hypothesis_already_exists(self):
        from iios.intelligence.forecast.hypothesis_exceptions import HypothesisAlreadyExistsError
        e = HypothesisAlreadyExistsError("h-002")
        assert "HFE-012" in str(e)

    def test_hypothesis_state_error(self):
        from iios.intelligence.forecast.hypothesis_exceptions import HypothesisStateError
        e = HypothesisStateError("h-003", "draft", "active")
        assert "HFE-013" in str(e)

    def test_hypothesis_expired(self):
        from iios.intelligence.forecast.hypothesis_exceptions import HypothesisExpiredError
        e = HypothesisExpiredError("h-004")
        assert "HFE-014" in str(e)

    def test_forecast_not_found(self):
        from iios.intelligence.forecast.hypothesis_exceptions import ForecastNotFoundError
        e = ForecastNotFoundError("f-001")
        assert "HFE-021" in str(e)

    def test_insufficient_data(self):
        from iios.intelligence.forecast.hypothesis_exceptions import InsufficientDataError
        e = InsufficientDataError(10, 3)
        assert "HFE-023" in str(e)
        assert "10" in str(e)

    def test_scenario_not_found(self):
        from iios.intelligence.forecast.hypothesis_exceptions import ScenarioNotFoundError
        e = ScenarioNotFoundError("s-001")
        assert "HFE-031" in str(e)

    def test_insufficient_scenarios(self):
        from iios.intelligence.forecast.hypothesis_exceptions import InsufficientScenariosError
        e = InsufficientScenariosError(2, 1)
        assert "HFE-033" in str(e)

    def test_probability_out_of_range(self):
        from iios.intelligence.forecast.hypothesis_exceptions import ProbabilityOutOfRangeError
        e = ProbabilityOutOfRangeError(1.5)
        assert "HFE-041" in str(e)

    def test_no_forecast_to_evaluate(self):
        from iios.intelligence.forecast.hypothesis_exceptions import NoForecastToEvaluateError
        e = NoForecastToEvaluateError("f-999")
        assert "HFE-051" in str(e)

    def test_engine_not_initialized(self):
        from iios.intelligence.forecast.hypothesis_exceptions import ForecastEngineNotInitializedError
        e = ForecastEngineNotInitializedError()
        assert "HFE-061" in str(e)

    def test_engine_already_running(self):
        from iios.intelligence.forecast.hypothesis_exceptions import ForecastEngineAlreadyRunningError
        e = ForecastEngineAlreadyRunningError()
        assert "HFE-062" in str(e)


# ── Context ───────────────────────────────────────────────────────────────────

class TestForecastContext:
    def test_get_returns_state(self):
        from iios.intelligence.forecast.hypothesis_context import get_forecast_context
        ctx = get_forecast_context()
        assert ctx is not None

    def test_hypothesis_scope(self):
        from iios.intelligence.forecast.hypothesis_context import hypothesis_scope, get_forecast_context
        from iios.intelligence.forecast.hypothesis_constants import ForecastHorizon
        with hypothesis_scope("h-abc", ForecastHorizon.INTRADAY) as ctx:
            assert ctx.hypothesis_id == "h-abc"
            assert ctx.horizon == ForecastHorizon.INTRADAY
        ctx2 = get_forecast_context()
        assert ctx2.hypothesis_id is None

    def test_forecast_scope(self):
        from iios.intelligence.forecast.hypothesis_context import forecast_scope
        with forecast_scope("f-xyz") as ctx:
            assert ctx.forecast_id == "f-xyz"

    def test_scenario_scope(self):
        from iios.intelligence.forecast.hypothesis_context import scenario_scope
        with scenario_scope("s-001") as ctx:
            assert ctx.scenario_id == "s-001"

    def test_nested_scope_restores(self):
        from iios.intelligence.forecast.hypothesis_context import hypothesis_scope
        with hypothesis_scope("outer") as ctx:
            with hypothesis_scope("inner") as ctx2:
                assert ctx2.hypothesis_id == "inner"
            assert ctx.hypothesis_id == "outer"

    def test_diagnostics(self):
        from iios.intelligence.forecast.hypothesis_context import get_forecast_context
        ctx = get_forecast_context()
        ctx.add_diagnostic("WARNING", "test warning", "test")
        assert len(ctx.warnings()) == 1


# ── Hypothesis model ──────────────────────────────────────────────────────────

class TestHypothesisModel:
    def test_create_hypothesis(self):
        from iios.intelligence.forecast.hypothesis_registry import Hypothesis
        from iios.intelligence.forecast.hypothesis_constants import HypothesisType, HypothesisStatus
        h = Hypothesis(statement="Test hypothesis")
        assert h.hypothesis_id != ""
        assert h.status == HypothesisStatus.DRAFT
        assert h.hypothesis_type == HypothesisType.GENERIC
        assert 0.0 <= h.probability <= 1.0

    def test_is_active_states(self):
        from iios.intelligence.forecast.hypothesis_registry import Hypothesis
        from iios.intelligence.forecast.hypothesis_constants import HypothesisStatus
        h = Hypothesis()
        h.status = HypothesisStatus.ACTIVE
        assert h.is_active
        h.status = HypothesisStatus.TESTING
        assert h.is_active
        h.status = HypothesisStatus.CONFIRMED
        assert not h.is_active

    def test_is_terminal_states(self):
        from iios.intelligence.forecast.hypothesis_registry import Hypothesis
        from iios.intelligence.forecast.hypothesis_constants import HypothesisStatus
        for status in (HypothesisStatus.CONFIRMED, HypothesisStatus.REJECTED,
                       HypothesisStatus.RETIRED, HypothesisStatus.ARCHIVED):
            h = Hypothesis()
            h.status = status
            assert h.is_terminal

    def test_is_not_expired(self):
        from iios.intelligence.forecast.hypothesis_registry import Hypothesis
        h = Hypothesis(ttl_s=86400.0)
        assert not h.is_expired

    def test_is_expired_zero_ttl(self):
        from iios.intelligence.forecast.hypothesis_registry import Hypothesis
        h = Hypothesis(ttl_s=0.0)
        assert not h.is_expired   # 0 = never expires

    def test_to_dict(self):
        from iios.intelligence.forecast.hypothesis_registry import Hypothesis
        h = Hypothesis(statement="hello")
        d = h.to_dict()
        assert d["statement"] == "hello"
        assert "hypothesis_id" in d
        assert "status" in d

    def test_add_evidence(self):
        from iios.intelligence.forecast.hypothesis_registry import Hypothesis
        h = Hypothesis()
        h.add_evidence("e1")
        h.add_evidence("e1")  # duplicate — should not double-add
        assert h.evidence_ids == ["e1"]

    def test_add_forecast(self):
        from iios.intelligence.forecast.hypothesis_registry import Hypothesis
        h = Hypothesis()
        h.add_forecast("f1")
        assert "f1" in h.forecast_ids


# ── Hypothesis Registry ───────────────────────────────────────────────────────

class TestHypothesisRegistry:
    def test_add_and_get(self):
        from iios.intelligence.forecast.hypothesis_registry import Hypothesis, get_hypothesis_registry
        reg = get_hypothesis_registry()
        h   = Hypothesis(statement="test")
        reg.add(h)
        assert reg.get(h.hypothesis_id) is h

    def test_duplicate_raises(self):
        from iios.intelligence.forecast.hypothesis_registry import Hypothesis, get_hypothesis_registry
        from iios.intelligence.forecast.hypothesis_exceptions import HypothesisAlreadyExistsError
        reg = get_hypothesis_registry()
        h   = Hypothesis(statement="dup")
        reg.add(h)
        with pytest.raises(HypothesisAlreadyExistsError):
            reg.add(h)

    def test_overwrite_allowed(self):
        from iios.intelligence.forecast.hypothesis_registry import Hypothesis, get_hypothesis_registry
        reg = get_hypothesis_registry()
        h   = Hypothesis(statement="original")
        reg.add(h)
        reg.add(h, overwrite=True)
        assert reg.has(h.hypothesis_id)

    def test_get_not_found(self):
        from iios.intelligence.forecast.hypothesis_registry import get_hypothesis_registry
        from iios.intelligence.forecast.hypothesis_exceptions import HypothesisNotFoundError
        reg = get_hypothesis_registry()
        with pytest.raises(HypothesisNotFoundError):
            reg.get("no-such-id")

    def test_remove(self):
        from iios.intelligence.forecast.hypothesis_registry import Hypothesis, get_hypothesis_registry
        reg = get_hypothesis_registry()
        h   = Hypothesis()
        reg.add(h)
        reg.remove(h.hypothesis_id)
        assert not reg.has(h.hypothesis_id)

    def test_get_by_type(self):
        from iios.intelligence.forecast.hypothesis_registry import Hypothesis, get_hypothesis_registry
        from iios.intelligence.forecast.hypothesis_constants import HypothesisType
        reg = get_hypothesis_registry()
        h   = Hypothesis(hypothesis_type=HypothesisType.CAUSAL)
        reg.add(h)
        by_type = reg.get_by_type(HypothesisType.CAUSAL)
        assert any(x.hypothesis_id == h.hypothesis_id for x in by_type)

    def test_get_active(self):
        from iios.intelligence.forecast.hypothesis_registry import Hypothesis, get_hypothesis_registry
        from iios.intelligence.forecast.hypothesis_constants import HypothesisStatus
        reg = get_hypothesis_registry()
        h   = Hypothesis()
        h.status = HypothesisStatus.ACTIVE
        reg.add(h)
        assert any(x.hypothesis_id == h.hypothesis_id for x in reg.get_active())

    def test_stats(self):
        from iios.intelligence.forecast.hypothesis_registry import Hypothesis, get_hypothesis_registry
        reg = get_hypothesis_registry()
        reg.add(Hypothesis(statement="s1"))
        reg.add(Hypothesis(statement="s2"))
        stats = reg.stats()
        assert stats["total"] == 2


# ── Hypothesis Factory ────────────────────────────────────────────────────────

class TestHypothesisFactory:
    def test_create(self):
        from iios.intelligence.forecast.hypothesis_factory import get_hypothesis_factory
        from iios.intelligence.forecast.hypothesis_constants import HypothesisStatus
        f = get_hypothesis_factory()
        h = f.create("My hypothesis")
        assert h.statement == "My hypothesis"
        assert h.status == HypothesisStatus.DRAFT

    def test_probability_clamped(self):
        from iios.intelligence.forecast.hypothesis_factory import get_hypothesis_factory
        f = get_hypothesis_factory()
        h = f.create("test", probability=2.0)
        assert h.probability == 1.0
        h2 = f.create("test2", probability=-0.5)
        assert h2.probability == 0.0

    def test_create_from_template(self):
        from iios.intelligence.forecast.hypothesis_factory import get_hypothesis_factory
        from iios.intelligence.forecast.hypothesis_constants import HypothesisType
        f = get_hypothesis_factory()
        h = f.create_from_template("null", "H0: no effect")
        assert h.hypothesis_type == HypothesisType.NULL

    def test_create_null_alternative_pair(self):
        from iios.intelligence.forecast.hypothesis_factory import get_hypothesis_factory
        from iios.intelligence.forecast.hypothesis_constants import HypothesisType
        f     = get_hypothesis_factory()
        h0, h1 = f.create_null_alternative_pair("H0", "H1")
        assert h0.hypothesis_type == HypothesisType.NULL
        assert h1.hypothesis_type == HypothesisType.ALTERNATIVE

    def test_unknown_template_raises(self):
        from iios.intelligence.forecast.hypothesis_factory import get_hypothesis_factory
        f = get_hypothesis_factory()
        with pytest.raises(KeyError):
            f.create_from_template("no_such_template", "x")

    def test_list_templates(self):
        from iios.intelligence.forecast.hypothesis_factory import get_hypothesis_factory
        f = get_hypothesis_factory()
        templates = f.list_templates()
        assert "null" in templates
        assert "alternative" in templates


# ── Hypothesis Session ────────────────────────────────────────────────────────

class TestHypothesisSession:
    def test_lifecycle(self):
        from iios.intelligence.forecast.hypothesis_session import HypothesisSession
        s = HypothesisSession(hypothesis_id="h-001")
        assert s.status == HypothesisSession.PENDING
        s.start()
        assert s.status == HypothesisSession.ACTIVE
        s.begin_testing()
        assert s.status == HypothesisSession.TESTING
        s.complete("done")
        assert s.is_terminal

    def test_fail(self):
        from iios.intelligence.forecast.hypothesis_session import HypothesisSession
        s = HypothesisSession()
        s.start()
        s.fail("oops")
        assert s.status == HypothesisSession.FAILED

    def test_cancel(self):
        from iios.intelligence.forecast.hypothesis_session import HypothesisSession
        s = HypothesisSession()
        s.start()
        s.cancel("aborted")
        assert s.status == HypothesisSession.CANCELLED

    def test_double_complete_raises(self):
        from iios.intelligence.forecast.hypothesis_session import HypothesisSession
        from iios.intelligence.forecast.hypothesis_exceptions import HypothesisStateError
        s = HypothesisSession()
        s.start()
        s.complete()
        with pytest.raises(HypothesisStateError):
            s.complete()

    def test_to_dict(self):
        from iios.intelligence.forecast.hypothesis_session import HypothesisSession
        s = HypothesisSession(hypothesis_id="h-abc")
        s.start()
        d = s.to_dict()
        assert d["hypothesis_id"] == "h-abc"
        assert "status" in d


# ── Forecast Statistics ───────────────────────────────────────────────────────

class TestForecastStatistics:
    def test_mean(self):
        from iios.intelligence.forecast.forecast.forecast_statistics import mean
        assert mean([1.0, 2.0, 3.0]) == pytest.approx(2.0)
        assert mean([]) == 0.0

    def test_std_dev(self):
        from iios.intelligence.forecast.forecast.forecast_statistics import std_dev
        v = std_dev([2.0, 4.0, 4.0, 4.0, 5.0, 5.0, 7.0, 9.0], sample=False)
        assert v == pytest.approx(2.0, rel=0.01)

    def test_percentile(self):
        from iios.intelligence.forecast.forecast.forecast_statistics import percentile
        data = list(range(1, 101))  # 1..100
        assert percentile(data, 50) == pytest.approx(50.5, rel=0.01)

    def test_confidence_interval(self):
        from iios.intelligence.forecast.forecast.forecast_statistics import confidence_interval
        data = [float(i) for i in range(1, 101)]
        lo, hi = confidence_interval(data, 0.90)
        assert lo < hi

    def test_mae(self):
        from iios.intelligence.forecast.forecast.forecast_statistics import mae
        assert mae([1.0, 2.0], [1.5, 2.5]) == pytest.approx(0.5)

    def test_rmse(self):
        from iios.intelligence.forecast.forecast.forecast_statistics import rmse
        assert rmse([0.0], [1.0]) == pytest.approx(1.0)

    def test_mape(self):
        from iios.intelligence.forecast.forecast.forecast_statistics import mape
        assert mape([100.0], [110.0]) == pytest.approx(0.0909, rel=0.01)

    def test_directional_accuracy(self):
        from iios.intelligence.forecast.forecast.forecast_statistics import directional_accuracy
        assert directional_accuracy([1.0, -1.0], [2.0, -0.5]) == pytest.approx(1.0)
        assert directional_accuracy([1.0, -1.0], [-1.0, 1.0]) == pytest.approx(0.0)

    def test_clamp_probability(self):
        from iios.intelligence.forecast.forecast.forecast_statistics import clamp_probability
        assert clamp_probability(-0.5) == 0.0
        assert clamp_probability(1.5)  == 1.0
        assert clamp_probability(0.7)  == pytest.approx(0.7)

    def test_weighted_mean(self):
        from iios.intelligence.forecast.forecast.forecast_statistics import weighted_mean
        assert weighted_mean([1.0, 2.0], [1.0, 3.0]) == pytest.approx(1.75)


# ── Forecast Model ────────────────────────────────────────────────────────────

class TestForecastModel:
    def test_point_model(self):
        from iios.intelligence.forecast.forecast.forecast_model import PointForecastModel
        m   = PointForecastModel(uncertainty=0.10)
        out = m.predict({"value": 100.0})
        assert out["value"] == pytest.approx(100.0)
        assert out["range_low"]  < 100.0
        assert out["range_high"] > 100.0

    def test_ensemble_model(self):
        from iios.intelligence.forecast.forecast.forecast_model import (
            PointForecastModel, WeightedEnsembleForecastModel,
        )
        m1  = PointForecastModel(uncertainty=0.1)
        m2  = PointForecastModel(uncertainty=0.2)
        ens = WeightedEnsembleForecastModel([m1, m2])
        out = ens.predict({"value": 50.0})
        assert out["value"] == pytest.approx(50.0)

    def test_ensemble_empty(self):
        from iios.intelligence.forecast.forecast.forecast_model import WeightedEnsembleForecastModel
        ens = WeightedEnsembleForecastModel([])
        out = ens.predict({"value": 0.0})
        assert out["confidence"] == 0.0


# ── Forecast Result ───────────────────────────────────────────────────────────

class TestForecastResult:
    def test_fields(self):
        from iios.intelligence.forecast.forecast.forecast_result import ForecastResult
        r = ForecastResult(
            hypothesis_id = "h-001",
            value         = 100.0,
            range_low     = 90.0,
            range_high    = 110.0,
        )
        assert r.range_width == pytest.approx(20.0)
        assert not r.is_expired

    def test_to_dict(self):
        from iios.intelligence.forecast.forecast.forecast_result import ForecastResult
        r = ForecastResult(hypothesis_id="h-001", value=50.0)
        d = r.to_dict()
        assert d["hypothesis_id"] == "h-001"
        assert d["value"] == pytest.approx(50.0)


# ── Forecast Registry ─────────────────────────────────────────────────────────

class TestForecastRegistry:
    def test_add_and_get(self):
        from iios.intelligence.forecast.forecast.forecast_registry import (
            ForecastRegistry, get_forecast_registry,
        )
        from iios.intelligence.forecast.forecast.forecast_result import ForecastResult
        reg = get_forecast_registry()
        r   = ForecastResult(hypothesis_id="h1")
        reg.add(r)
        assert reg.get(r.forecast_id) is r

    def test_not_found_raises(self):
        from iios.intelligence.forecast.forecast.forecast_registry import get_forecast_registry
        from iios.intelligence.forecast.hypothesis_exceptions import ForecastNotFoundError
        reg = get_forecast_registry()
        with pytest.raises(ForecastNotFoundError):
            reg.get("nope")

    def test_for_hypothesis(self):
        from iios.intelligence.forecast.forecast.forecast_registry import get_forecast_registry
        from iios.intelligence.forecast.forecast.forecast_result import ForecastResult
        reg = get_forecast_registry()
        r1  = ForecastResult(hypothesis_id="h-abc")
        r2  = ForecastResult(hypothesis_id="h-abc")
        reg.add(r1)
        reg.add(r2)
        results = reg.for_hypothesis("h-abc")
        assert len(results) == 2


# ── Forecast Engine ───────────────────────────────────────────────────────────

class TestForecastEngine:
    def test_run_default_model(self):
        from iios.intelligence.forecast.forecast.forecast_engine import get_forecast_engine
        engine = get_forecast_engine()
        result = engine.run("h-001", {"value": 75.0})
        assert result.value == pytest.approx(75.0)
        assert result.hypothesis_id == "h-001"

    def test_unknown_model_raises(self):
        from iios.intelligence.forecast.forecast.forecast_engine import get_forecast_engine
        from iios.intelligence.forecast.hypothesis_exceptions import ForecastModelError
        engine = get_forecast_engine()
        with pytest.raises(ForecastModelError):
            engine.run("h-001", {}, model_id="no_such_model")

    def test_register_model(self):
        from iios.intelligence.forecast.forecast.forecast_engine import get_forecast_engine
        from iios.intelligence.forecast.forecast.forecast_model import PointForecastModel, ForecastModelConfig
        engine = get_forecast_engine()
        cfg    = ForecastModelConfig(model_id="custom", name="Custom")
        m      = PointForecastModel(config=cfg)
        engine.register_model(m)
        assert "custom" in engine.list_models()

    def test_stats(self):
        from iios.intelligence.forecast.forecast.forecast_engine import get_forecast_engine
        engine = get_forecast_engine()
        engine.run("h-001", {"value": 10.0})
        s = engine.stats()
        assert s["forecasts_run"] == 1


# ── Scenario ──────────────────────────────────────────────────────────────────

class TestScenarioGenerator:
    def test_generate_base_set(self):
        from iios.intelligence.forecast.scenario.scenario_generator import ScenarioGenerator
        gen = ScenarioGenerator()
        scenarios = gen.generate_base_set("h-001")
        assert len(scenarios) == 3
        total_prob = sum(s.probability for s in scenarios)
        assert total_prob == pytest.approx(1.0, rel=0.001)

    def test_generate_stress_set(self):
        from iios.intelligence.forecast.scenario.scenario_generator import ScenarioGenerator
        gen = ScenarioGenerator()
        scenarios = gen.generate_stress_set("h-001")
        assert len(scenarios) == 2

    def test_create_invalid_probability(self):
        from iios.intelligence.forecast.scenario.scenario_generator import ScenarioGenerator
        from iios.intelligence.forecast.hypothesis_exceptions import ScenarioValidationError
        gen = ScenarioGenerator()
        with pytest.raises(ScenarioValidationError):
            gen.create("h-001", "Bad", probability=1.5)

    def test_scenario_to_dict(self):
        from iios.intelligence.forecast.scenario.scenario_generator import Scenario
        from iios.intelligence.forecast.hypothesis_constants import ScenarioType
        s = Scenario(
            hypothesis_id = "h-001",
            name          = "Base",
            scenario_type = ScenarioType.BASE_CASE,
        )
        d = s.to_dict()
        assert d["name"] == "Base"
        assert d["scenario_type"] == "base_case"


class TestScenarioEngine:
    def test_generate_and_compare(self):
        from iios.intelligence.forecast.scenario.scenario_engine import get_scenario_engine
        eng       = get_scenario_engine()
        scenarios = eng.generate_base_set("h-001")
        ids       = [s.scenario_id for s in scenarios]
        cmp       = eng.compare(ids)
        assert cmp.top_scenario_id in ids

    def test_compare_insufficient_raises(self):
        from iios.intelligence.forecast.scenario.scenario_engine import get_scenario_engine
        from iios.intelligence.forecast.hypothesis_exceptions import InsufficientScenariosError
        eng = get_scenario_engine()
        scenarios = eng.generate_base_set("h-xyz")
        with pytest.raises(InsufficientScenariosError):
            eng.compare([scenarios[0].scenario_id])

    def test_compare_for_hypothesis(self):
        from iios.intelligence.forecast.scenario.scenario_engine import get_scenario_engine
        eng = get_scenario_engine()
        eng.generate_base_set("h-002")
        cmp = eng.compare_for_hypothesis("h-002")
        assert cmp.top_scenario_id != ""


# ── Probability Engine ────────────────────────────────────────────────────────

class TestProbabilityEngine:
    def test_bayesian_update(self):
        from iios.intelligence.forecast.probability.probability_engine import get_probability_engine
        eng = get_probability_engine()
        result = eng.bayesian_update("h-001", 0.8, 0.3)
        assert 0.0 < result.probability < 1.0

    def test_bayesian_increases_for_strong_evidence(self):
        from iios.intelligence.forecast.probability.probability_engine import get_probability_engine
        eng = get_probability_engine()
        eng.set_prior("h-002", 0.5)
        result = eng.bayesian_update("h-002", 0.95, 0.05)
        assert result.probability > 0.5

    def test_invalid_probability_raises(self):
        from iios.intelligence.forecast.probability.probability_engine import get_probability_engine
        from iios.intelligence.forecast.hypothesis_exceptions import ProbabilityOutOfRangeError
        eng = get_probability_engine()
        with pytest.raises(ProbabilityOutOfRangeError):
            eng.bayesian_update("h-003", 1.5, 0.1)

    def test_ensemble_estimate(self):
        from iios.intelligence.forecast.probability.probability_engine import get_probability_engine
        eng    = get_probability_engine()
        result = eng.ensemble_estimate([0.4, 0.6, 0.5])
        assert 0.4 <= result.probability <= 0.6

    def test_monte_carlo(self):
        from iios.intelligence.forecast.probability.probability_engine import get_probability_engine
        eng    = get_probability_engine()
        result = eng.monte_carlo(0.5, volatility=0.05, n_simulations=500, seed=42)
        assert 0.0 <= result.probability <= 1.0
        assert result.lower <= result.probability <= result.upper

    def test_frequentist(self):
        from iios.intelligence.forecast.probability.probability_engine import get_probability_engine
        eng    = get_probability_engine()
        result = eng.frequentist(60, 100)
        assert result.probability == pytest.approx(0.6)

    def test_frequentist_zero_trials_raises(self):
        from iios.intelligence.forecast.probability.probability_engine import get_probability_engine
        from iios.intelligence.forecast.hypothesis_exceptions import DistributionError
        eng = get_probability_engine()
        with pytest.raises(DistributionError):
            eng.frequentist(0, 0)


# ── Confidence Distribution ───────────────────────────────────────────────────

class TestConfidenceDistribution:
    def test_normal_distribution(self):
        from iios.intelligence.forecast.probability.confidence_distribution import NormalDistribution
        nd = NormalDistribution(mu=0.0, sigma=1.0)
        lo, hi = nd.ci(0.90)
        assert lo < 0.0 < hi

    def test_invalid_sigma(self):
        from iios.intelligence.forecast.probability.confidence_distribution import NormalDistribution
        with pytest.raises(ValueError):
            NormalDistribution(mu=0.0, sigma=0.0)

    def test_fit_normal(self):
        from iios.intelligence.forecast.probability.confidence_distribution import fit_normal
        nd = fit_normal([1.0, 2.0, 3.0, 4.0, 5.0])
        assert nd.mu == pytest.approx(3.0)
        assert nd.sigma > 0

    def test_bayesian_update(self):
        from iios.intelligence.forecast.probability.confidence_distribution import (
            NormalDistribution, bayesian_update,
        )
        prior   = NormalDistribution(mu=0.0, sigma=1.0)
        obs     = NormalDistribution(mu=1.0, sigma=0.5)
        posterior = bayesian_update(prior.mu, prior.sigma, obs.mu, obs.sigma)
        assert prior.mu < posterior.mu < obs.mu

    def test_probability_above(self):
        from iios.intelligence.forecast.probability.confidence_distribution import NormalDistribution
        nd = NormalDistribution(mu=0.0, sigma=1.0)
        assert nd.probability_above(0.0) == pytest.approx(0.5, abs=0.01)


# ── Risk Distribution ─────────────────────────────────────────────────────────

class TestRiskDistribution:
    def test_fat_tail(self):
        from iios.intelligence.forecast.probability.risk_distribution import RiskDistribution
        rd  = RiskDistribution(mu=0.0, sigma=1.0, tail_factor=2.0)
        lo1, hi1 = rd.ci(0.90)
        rd2 = RiskDistribution(mu=0.0, sigma=1.0, tail_factor=1.0)
        lo2, hi2 = rd2.ci(0.90)
        # fat-tailed should be wider
        assert (hi1 - lo1) > (hi2 - lo2)

    def test_invalid_tail_factor(self):
        from iios.intelligence.forecast.probability.risk_distribution import RiskDistribution
        with pytest.raises(ValueError):
            RiskDistribution(mu=0.0, sigma=1.0, tail_factor=0.5)

    def test_var(self):
        from iios.intelligence.forecast.probability.risk_distribution import RiskDistribution
        rd = RiskDistribution(mu=0.0, sigma=1.0, tail_factor=1.0)
        v  = rd.var(0.95)
        assert isinstance(v, float)


# ── Uncertainty Engine ────────────────────────────────────────────────────────

class TestUncertaintyEngine:
    def test_estimate_returns_report(self):
        from iios.intelligence.forecast.uncertainty.uncertainty_engine import get_uncertainty_engine
        from iios.intelligence.forecast.forecast.forecast_result import ForecastResult
        eng    = get_uncertainty_engine()
        result = ForecastResult(
            forecast_id = "f-001",
            value       = 100.0,
            range_low   = 90.0,
            range_high  = 110.0,
            confidence  = 0.7,
        )
        report = eng.estimate(result)
        assert report.forecast_id == "f-001"
        assert 0.0 <= report.total <= 1.0
        assert report.confidence == pytest.approx(1.0 - report.total, rel=0.01)

    def test_components_present(self):
        from iios.intelligence.forecast.uncertainty.uncertainty_engine import get_uncertainty_engine
        from iios.intelligence.forecast.forecast.forecast_result import ForecastResult
        from iios.intelligence.forecast.hypothesis_constants import UncertaintyType
        eng    = get_uncertainty_engine()
        result = ForecastResult(value=50.0, range_low=45.0, range_high=55.0)
        report = eng.estimate(result)
        types  = {c.uncertainty_type for c in report.components}
        assert UncertaintyType.ALEATORIC in types
        assert UncertaintyType.EPISTEMIC in types

    def test_inject_component(self):
        from iios.intelligence.forecast.uncertainty.uncertainty_engine import get_uncertainty_engine
        from iios.intelligence.forecast.forecast.forecast_result import ForecastResult
        from iios.intelligence.forecast.hypothesis_constants import UncertaintyType
        eng    = get_uncertainty_engine()
        result = ForecastResult(forecast_id="f-inject", value=10.0, range_low=9.0, range_high=11.0)
        eng.inject_component("f-inject", UncertaintyType.DATA, 0.8, "manual override")
        report = eng.estimate(result)
        types  = {c.uncertainty_type for c in report.components}
        assert UncertaintyType.DATA in types

    def test_estimate_from_values(self):
        from iios.intelligence.forecast.uncertainty.uncertainty_engine import get_uncertainty_engine
        eng    = get_uncertainty_engine()
        report = eng.estimate_from_values("f-002", 100.0, 90.0, 110.0, 0.8)
        assert report.total >= 0.0


# ── Evaluation ────────────────────────────────────────────────────────────────

class TestPredictionAccuracy:
    def test_compute_accuracy(self):
        from iios.intelligence.forecast.evaluation.prediction_accuracy import (
            compute_accuracy, AccuracyReport,
        )
        from iios.intelligence.forecast.hypothesis_constants import EvaluationMetric
        report = compute_accuracy("f-001", predicted=100.0, actual=110.0,
                                  range_low=90.0, range_high=120.0)
        assert isinstance(report, AccuracyReport)
        mae_score = report.score_for(EvaluationMetric.MAE)
        assert mae_score == pytest.approx(10.0)

    def test_calibration_within_range(self):
        from iios.intelligence.forecast.evaluation.prediction_accuracy import compute_accuracy
        from iios.intelligence.forecast.hypothesis_constants import EvaluationMetric
        report = compute_accuracy("f-002", 100.0, 105.0, 90.0, 110.0)
        calib  = report.score_for(EvaluationMetric.CALIBRATION)
        assert calib == pytest.approx(1.0)

    def test_calibration_outside_range(self):
        from iios.intelligence.forecast.evaluation.prediction_accuracy import compute_accuracy
        from iios.intelligence.forecast.hypothesis_constants import EvaluationMetric
        report = compute_accuracy("f-003", 100.0, 200.0, 90.0, 110.0)
        calib  = report.score_for(EvaluationMetric.CALIBRATION)
        assert calib == pytest.approx(0.0)

    def test_to_dict(self):
        from iios.intelligence.forecast.evaluation.prediction_accuracy import compute_accuracy
        report = compute_accuracy("f-004", 100.0, 100.0)
        d      = report.to_dict()
        assert "composite" in d
        assert d["composite"] >= 0.0


class TestForecastTracker:
    def test_record_and_retrieve(self):
        from iios.intelligence.forecast.evaluation.forecast_tracker import (
            get_forecast_tracker, TrackedOutcome,
        )
        tracker = get_forecast_tracker()
        o       = TrackedOutcome("f1", "m1", 100.0, 105.0, 0.8)
        tracker.record(o)
        history = tracker.history("m1")
        assert len(history) == 1
        assert tracker.rolling_accuracy("m1") == pytest.approx(0.8)

    def test_rolling_accuracy_empty(self):
        from iios.intelligence.forecast.evaluation.forecast_tracker import get_forecast_tracker
        tracker = get_forecast_tracker()
        assert tracker.rolling_accuracy("unknown_model") == 0.0


class TestForecastEvaluator:
    def test_evaluate(self):
        from iios.intelligence.forecast.evaluation.forecast_evaluator import get_forecast_evaluator
        from iios.intelligence.forecast.forecast.forecast_registry import get_forecast_registry
        from iios.intelligence.forecast.forecast.forecast_result import ForecastResult
        registry  = get_forecast_registry()
        result    = ForecastResult(
            hypothesis_id = "h-001",
            model_id      = "default",
            value         = 100.0,
            range_low     = 90.0,
            range_high    = 110.0,
        )
        registry.add(result)
        evaluator = get_forecast_evaluator()
        report    = evaluator.evaluate(result.forecast_id, 105.0)
        assert result.is_evaluated
        assert result.actual_value == 105.0

    def test_evaluate_by_result(self):
        from iios.intelligence.forecast.evaluation.forecast_evaluator import get_forecast_evaluator
        from iios.intelligence.forecast.forecast.forecast_result import ForecastResult
        result    = ForecastResult(value=50.0, range_low=40.0, range_high=60.0)
        evaluator = get_forecast_evaluator()
        report    = evaluator.evaluate_by_result(result, 55.0)
        assert result.is_evaluated


# ── HypothesisEngine (top-level gateway) ──────────────────────────────────────

class TestHypothesisEngine:
    def _get_engine(self):
        from iios.intelligence.forecast.hypothesis_engine import get_hypothesis_engine
        eng = get_hypothesis_engine()
        eng.initialize()
        return eng

    def test_initialize_and_shutdown(self):
        from iios.intelligence.forecast.hypothesis_engine import get_hypothesis_engine
        eng = get_hypothesis_engine()
        assert not eng.is_running
        eng.initialize()
        assert eng.is_running
        eng.shutdown()
        assert not eng.is_running

    def test_double_initialize_raises(self):
        from iios.intelligence.forecast.hypothesis_exceptions import ForecastEngineAlreadyRunningError
        eng = self._get_engine()
        with pytest.raises(ForecastEngineAlreadyRunningError):
            eng.initialize()

    def test_use_before_init_raises(self):
        from iios.intelligence.forecast.hypothesis_engine import get_hypothesis_engine
        from iios.intelligence.forecast.hypothesis_exceptions import ForecastEngineNotInitializedError
        eng = get_hypothesis_engine()   # fresh — not initialized
        with pytest.raises(ForecastEngineNotInitializedError):
            eng.create_hypothesis("should fail")

    def test_create_hypothesis(self):
        eng = self._get_engine()
        h   = eng.create_hypothesis("Price will rise", tags=["test"])
        assert h.hypothesis_id != ""
        assert h.statement == "Price will rise"

    def test_activate(self):
        from iios.intelligence.forecast.hypothesis_constants import HypothesisStatus
        eng = self._get_engine()
        h   = eng.create_hypothesis("test activate")
        h2  = eng.activate(h.hypothesis_id)
        assert h2.status == HypothesisStatus.ACTIVE

    def test_test_starts_session(self):
        eng     = self._get_engine()
        h       = eng.create_hypothesis("test session")
        eng.activate(h.hypothesis_id)
        session = eng.test(h.hypothesis_id)
        assert session.is_active

    def test_confirm(self):
        from iios.intelligence.forecast.hypothesis_constants import HypothesisStatus
        eng    = self._get_engine()
        h      = eng.create_hypothesis("confirm me")
        result = eng.confirm(h.hypothesis_id, probability=0.9, note="confirmed!")
        assert result.is_confirmed
        assert result.probability == pytest.approx(0.9)

    def test_reject(self):
        from iios.intelligence.forecast.hypothesis_constants import HypothesisStatus
        eng    = self._get_engine()
        h      = eng.create_hypothesis("reject me")
        result = eng.reject(h.hypothesis_id, reason="contradicted")
        assert result.is_rejected

    def test_forecast(self):
        eng      = self._get_engine()
        h        = eng.create_hypothesis("forecast test")
        forecast = eng.forecast(h.hypothesis_id, {"value": 200.0})
        assert forecast.value == pytest.approx(200.0)
        assert forecast.hypothesis_id == h.hypothesis_id

    def test_generate_scenarios(self):
        eng       = self._get_engine()
        h         = eng.create_hypothesis("scenario test")
        scenarios = eng.generate_scenarios(h.hypothesis_id)
        assert len(scenarios) == 3

    def test_compare_scenarios(self):
        eng       = self._get_engine()
        h         = eng.create_hypothesis("compare test")
        scenarios = eng.generate_scenarios(h.hypothesis_id)
        ids       = [s.scenario_id for s in scenarios]
        cmp       = eng.compare_scenarios(ids)
        assert cmp.top_scenario_id in ids

    def test_estimate_probability(self):
        eng    = self._get_engine()
        h      = eng.create_hypothesis("prob test")
        result = eng.estimate_probability(h.hypothesis_id)
        assert 0.0 <= result.probability <= 1.0

    def test_estimate_uncertainty(self):
        eng      = self._get_engine()
        h        = eng.create_hypothesis("unc test")
        forecast = eng.forecast(h.hypothesis_id, {"value": 50.0})
        report   = eng.estimate_uncertainty(forecast.forecast_id)
        assert 0.0 <= report.total <= 1.0

    def test_evaluate(self):
        eng      = self._get_engine()
        h        = eng.create_hypothesis("eval test")
        forecast = eng.forecast(h.hypothesis_id, {"value": 100.0})
        report   = eng.evaluate(forecast.forecast_id, 105.0)
        assert report.composite >= 0.0

    def test_stats(self):
        eng   = self._get_engine()
        eng.create_hypothesis("stats test")
        stats = eng.stats()
        assert stats["version"] == "1.0.0"
        assert stats["running"] is True

    def test_health(self):
        eng    = self._get_engine()
        health = eng.health()
        assert health["status"] == "healthy"

    def test_register_custom_model(self):
        from iios.intelligence.forecast.forecast.forecast_model import PointForecastModel, ForecastModelConfig
        eng = self._get_engine()
        cfg = ForecastModelConfig(model_id="custom-v1", name="Custom")
        m   = PointForecastModel(config=cfg)
        eng.register_model(m)
        h        = eng.create_hypothesis("custom model test")
        forecast = eng.forecast(h.hypothesis_id, {"value": 10.0}, model_id="custom-v1")
        assert forecast.model_id == "custom-v1"

    def test_full_lifecycle(self):
        """Full end-to-end: create → activate → test → forecast → evaluate → confirm."""
        from iios.intelligence.forecast.hypothesis_constants import HypothesisStatus
        eng = self._get_engine()
        h   = eng.create_hypothesis(
            "Volatility will increase",
            tags=["integration"]
        )
        # activate
        eng.activate(h.hypothesis_id)
        # begin testing
        session = eng.test(h.hypothesis_id, evidence_ids=["e1", "e2"])
        assert session.is_active
        # forecast
        fc = eng.forecast(h.hypothesis_id, {"value": 22.5})
        assert fc.value == pytest.approx(22.5)
        # estimate probability
        prob = eng.estimate_probability(h.hypothesis_id)
        assert 0 < prob.probability < 1
        # estimate uncertainty
        unc = eng.estimate_uncertainty(fc.forecast_id)
        assert unc.total > 0
        # evaluate after outcome known
        report = eng.evaluate(fc.forecast_id, 23.1)
        assert report.composite > 0
        # confirm
        result = eng.confirm(h.hypothesis_id, probability=0.78)
        assert result.is_confirmed
        assert result.probability == pytest.approx(0.78)


# ── Async forecast ────────────────────────────────────────────────────────────

class TestAsyncForecast:
    def test_forecast_async(self):
        from iios.intelligence.forecast.hypothesis_engine import get_hypothesis_engine
        eng = get_hypothesis_engine()
        eng.initialize()

        async def run():
            h  = eng.create_hypothesis("async test")
            fc = await eng.forecast_async(h.hypothesis_id, {"value": 333.0})
            return fc

        fc = asyncio.run(run())
        assert fc.value == pytest.approx(333.0)


# ── Thread-safety ─────────────────────────────────────────────────────────────

class TestThreadSafety:
    def test_concurrent_hypothesis_creation(self):
        from iios.intelligence.forecast.hypothesis_engine import get_hypothesis_engine
        eng = get_hypothesis_engine()
        eng.initialize()

        errors:  list[Exception] = []
        results: list[str]        = []
        lock = threading.Lock()

        def create():
            try:
                h = eng.create_hypothesis(f"concurrent-{threading.get_ident()}")
                with lock:
                    results.append(h.hypothesis_id)
            except Exception as exc:
                with lock:
                    errors.append(exc)

        threads = [threading.Thread(target=create) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert len(results) == 20
        assert len(set(results)) == 20   # all IDs unique

    def test_concurrent_forecast(self):
        from iios.intelligence.forecast.hypothesis_engine import get_hypothesis_engine
        eng = get_hypothesis_engine()
        eng.initialize()
        h = eng.create_hypothesis("concurrent forecast")

        errors:    list[Exception] = []
        forecasts: list[str]        = []
        lock = threading.Lock()

        def do_forecast():
            try:
                fc = eng.forecast(h.hypothesis_id, {"value": 10.0})
                with lock:
                    forecasts.append(fc.forecast_id)
            except Exception as exc:
                with lock:
                    errors.append(exc)

        threads = [threading.Thread(target=do_forecast) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert len(forecasts) == 10


# ── HypothesisResult ──────────────────────────────────────────────────────────

class TestHypothesisResult:
    def test_is_confirmed(self):
        from iios.intelligence.forecast.hypothesis_result import HypothesisResult
        from iios.intelligence.forecast.hypothesis_constants import HypothesisStatus
        r = HypothesisResult(status=HypothesisStatus.CONFIRMED)
        assert r.is_confirmed
        assert not r.is_rejected

    def test_to_dict(self):
        from iios.intelligence.forecast.hypothesis_result import HypothesisResult
        r = HypothesisResult(hypothesis_id="h-001", probability=0.8)
        d = r.to_dict()
        assert d["hypothesis_id"] == "h-001"
        assert d["probability"] == pytest.approx(0.8)


# ── Package imports ───────────────────────────────────────────────────────────

class TestPackageImports:
    def test_top_level_imports(self):
        import iios.intelligence.forecast as pkg
        assert hasattr(pkg, "HypothesisEngine")
        assert hasattr(pkg, "get_hypothesis_engine")
        assert hasattr(pkg, "HypothesisType")
        assert hasattr(pkg, "ForecastHorizon")
        assert hasattr(pkg, "HypothesisForecastError")

    def test_version(self):
        from iios.intelligence.forecast import HYPOTHESIS_ENGINE_VERSION
        assert HYPOTHESIS_ENGINE_VERSION == "1.0.0"
