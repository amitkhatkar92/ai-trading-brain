"""
iios/intelligence/forecast/hypothesis_engine.py
================================================
HypothesisEngine — the mandatory top-level gateway.
All public consumers interact exclusively through this class.
"""
from __future__ import annotations

import threading
from typing import Any

from .forecast.forecast_model import ForecastModel
from .forecast.forecast_result import ForecastResult
from .hypothesis_constants import (
    HYPOTHESIS_ENGINE_VERSION,
    HypothesisType,
    ForecastHorizon,
    ForecastType,
    ProbabilityMethod,
    DEFAULT_CONFIDENCE_INTERVAL,
    DEFAULT_FORECAST_TTL_S,
    DEFAULT_HYPOTHESIS_TTL_S,
    DEFAULT_PRIOR_PROBABILITY,
)
from .hypothesis_exceptions import (
    ForecastEngineNotInitializedError,
    ForecastEngineAlreadyRunningError,
)
from .hypothesis_manager import HypothesisManager, get_hypothesis_manager
from .hypothesis_registry import Hypothesis
from .hypothesis_result import HypothesisResult
from .hypothesis_session import HypothesisSession
from .evaluation.prediction_accuracy import AccuracyReport
from .probability.probability_engine import ProbabilityEstimate
from .scenario.scenario_comparator import ScenarioComparison
from .scenario.scenario_generator import Scenario
from .uncertainty.uncertainty_engine import UncertaintyReport


class HypothesisEngine:
    """
    Top-level gateway for the Hypothesis & Forecast Engine.

    Usage::

        engine = get_hypothesis_engine()
        engine.initialize()

        hyp = engine.create_hypothesis("Price will rise 5%", HypothesisType.DIRECTIONAL)
        engine.activate(hyp.hypothesis_id)
        session = engine.test(hyp.hypothesis_id)

        forecast = engine.forecast(hyp.hypothesis_id, {"value": 100.0})
        unc      = engine.estimate_uncertainty(forecast.forecast_id)
        prob     = engine.estimate_probability(hyp.hypothesis_id)

        scenarios = engine.generate_scenarios(hyp.hypothesis_id)
        result    = engine.confirm(hyp.hypothesis_id, probability=0.85)

        # After outcome is known:
        eval_result = engine.evaluate(forecast.forecast_id, actual_value=105.2)

    Async variant::

        forecast = await engine.forecast_async(hyp.hypothesis_id, {"value": 100.0})
    """

    def __init__(self) -> None:
        self._manager:     HypothesisManager | None = None
        self._running:     bool                      = False
        self._lock:        threading.RLock            = threading.RLock()

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def initialize(self) -> None:
        with self._lock:
            if self._running:
                raise ForecastEngineAlreadyRunningError()
            self._manager = get_hypothesis_manager()
            self._running = True

    def shutdown(self) -> None:
        with self._lock:
            self._running = False
            self._manager = None

    @property
    def is_running(self) -> bool:
        with self._lock:
            return self._running

    # ── Hypothesis lifecycle ──────────────────────────────────────────────────

    def create_hypothesis(
        self,
        statement:       str,
        hypothesis_type: HypothesisType = HypothesisType.GENERIC,
        probability:     float           = DEFAULT_PRIOR_PROBABILITY,
        confidence:      float           = 0.0,
        parent_id:       str | None      = None,
        tags:            list[str] | None = None,
        ttl_s:           float            = DEFAULT_HYPOTHESIS_TTL_S,
        metadata:        dict[str, Any] | None = None,
    ) -> Hypothesis:
        return self._mgr.create_hypothesis(
            statement       = statement,
            hypothesis_type = hypothesis_type,
            probability     = probability,
            confidence      = confidence,
            parent_id       = parent_id,
            tags            = tags,
            ttl_s           = ttl_s,
            metadata        = metadata,
        )

    def get_hypothesis(self, hypothesis_id: str) -> Hypothesis:
        return self._mgr.get_hypothesis(hypothesis_id)

    def activate(self, hypothesis_id: str) -> Hypothesis:
        return self._mgr.activate(hypothesis_id)

    def test(
        self,
        hypothesis_id: str,
        evidence_ids:  list[str] | None = None,
    ) -> HypothesisSession:
        return self._mgr.test(hypothesis_id, evidence_ids=evidence_ids)

    def confirm(
        self,
        hypothesis_id: str,
        probability:   float = 1.0,
        note:          str   = "",
    ) -> HypothesisResult:
        return self._mgr.confirm(hypothesis_id, probability=probability, note=note)

    def reject(
        self,
        hypothesis_id: str,
        reason:        str   = "",
        probability:   float = 0.0,
    ) -> HypothesisResult:
        return self._mgr.reject(hypothesis_id, reason=reason, probability=probability)

    def suspend(self, hypothesis_id: str, reason: str = "") -> Hypothesis:
        return self._mgr.suspend(hypothesis_id, reason=reason)

    def archive(self, hypothesis_id: str) -> Hypothesis:
        return self._mgr.archive(hypothesis_id)

    # ── Forecasting ───────────────────────────────────────────────────────────

    def forecast(
        self,
        hypothesis_id:       str,
        inputs:              dict[str, Any],
        model_id:            str              = "default",
        horizon:             ForecastHorizon  = ForecastHorizon.SHORT_TERM,
        forecast_type:       ForecastType     = ForecastType.POINT,
        confidence_interval: float            = DEFAULT_CONFIDENCE_INTERVAL,
        ttl_s:               float            = DEFAULT_FORECAST_TTL_S,
    ) -> ForecastResult:
        return self._mgr.forecast(
            hypothesis_id       = hypothesis_id,
            inputs              = inputs,
            model_id            = model_id,
            horizon             = horizon,
            forecast_type       = forecast_type,
            confidence_interval = confidence_interval,
            ttl_s               = ttl_s,
        )

    async def forecast_async(
        self,
        hypothesis_id: str,
        inputs:        dict[str, Any],
        **kwargs: Any,
    ) -> ForecastResult:
        return await self._mgr.forecast_async(hypothesis_id, inputs, **kwargs)

    # ── Scenarios ─────────────────────────────────────────────────────────────

    def generate_scenarios(
        self,
        hypothesis_id:    str,
        base_probability: float = 0.50,
        bull_probability: float = 0.25,
        bear_probability: float = 0.25,
    ) -> list[Scenario]:
        return self._mgr.generate_scenarios(
            hypothesis_id, base_probability, bull_probability, bear_probability
        )

    def compare_scenarios(self, scenario_ids: list[str]) -> ScenarioComparison:
        return self._mgr.compare_scenarios(scenario_ids)

    # ── Probability ───────────────────────────────────────────────────────────

    def estimate_probability(
        self,
        hypothesis_id:          str,
        method:                 ProbabilityMethod = ProbabilityMethod.BAYESIAN,
        likelihood_given_true:  float              = 0.7,
        likelihood_given_false: float              = 0.3,
    ) -> ProbabilityEstimate:
        return self._mgr.estimate_probability(
            hypothesis_id,
            method                 = method,
            likelihood_given_true  = likelihood_given_true,
            likelihood_given_false = likelihood_given_false,
        )

    # ── Uncertainty ───────────────────────────────────────────────────────────

    def estimate_uncertainty(self, forecast_id: str) -> UncertaintyReport:
        return self._mgr.estimate_uncertainty(forecast_id)

    # ── Evaluation ────────────────────────────────────────────────────────────

    def evaluate(self, forecast_id: str, actual_value: float) -> AccuracyReport:
        return self._mgr.evaluate(forecast_id, actual_value)

    # ── Model registration ────────────────────────────────────────────────────

    def register_model(self, model: ForecastModel) -> None:
        self._mgr._forecast_mgr.register_model(model)

    # ── Stats / Health ────────────────────────────────────────────────────────

    def stats(self) -> dict[str, Any]:
        return {
            "version":    HYPOTHESIS_ENGINE_VERSION,
            "running":    self._running,
            **self._mgr.stats(),
        }

    def health(self) -> dict[str, Any]:
        return {
            "version": HYPOTHESIS_ENGINE_VERSION,
            **self._mgr.health(),
        }

    # ── Internal ──────────────────────────────────────────────────────────────

    @property
    def _mgr(self) -> HypothesisManager:
        with self._lock:
            if not self._running or self._manager is None:
                raise ForecastEngineNotInitializedError()
            return self._manager


# ── Singleton ──────────────────────────────────────────────────────────────────

_LOCK:   threading.Lock           = threading.Lock()
_ENGINE: HypothesisEngine | None = None


def get_hypothesis_engine() -> HypothesisEngine:
    global _ENGINE
    if _ENGINE is None:
        with _LOCK:
            if _ENGINE is None:
                _ENGINE = HypothesisEngine()
    return _ENGINE


def reset_hypothesis_engine() -> None:
    global _ENGINE
    with _LOCK:
        _ENGINE = None
