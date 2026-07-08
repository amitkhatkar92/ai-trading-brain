"""
iios/intelligence/forecast/hypothesis_manager.py
================================================
HypothesisManager — orchestrates the full hypothesis lifecycle.
"""
from __future__ import annotations

import threading
import time
from typing import Any

from .forecast.forecast_manager import ForecastManager, get_forecast_manager
from .forecast.forecast_result import ForecastResult
from .hypothesis_constants import (
    HypothesisStatus,
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
    HypothesisNotFoundError,
    HypothesisStateError,
    HypothesisExpiredError,
)
from .hypothesis_factory import HypothesisFactory, get_hypothesis_factory
from .hypothesis_registry import Hypothesis, HypothesisRegistry, get_hypothesis_registry
from .hypothesis_result import HypothesisResult
from .hypothesis_session import HypothesisSession
from .probability.probability_engine import ProbabilityEngine, ProbabilityEstimate, get_probability_engine
from .scenario.scenario_engine import ScenarioEngine, get_scenario_engine
from .scenario.scenario_comparator import ScenarioComparison
from .scenario.scenario_generator import Scenario
from .uncertainty.uncertainty_engine import UncertaintyEngine, UncertaintyReport, get_uncertainty_engine
from .evaluation.forecast_evaluator import ForecastEvaluator, get_forecast_evaluator
from .evaluation.prediction_accuracy import AccuracyReport


class HypothesisManager:
    """
    Central lifecycle manager for the Hypothesis & Forecast Engine.

    Wraps HypothesisRegistry, ForecastManager, ScenarioEngine,
    ProbabilityEngine, UncertaintyEngine, and ForecastEvaluator
    into a clean API consumed by HypothesisEngine.
    """

    def __init__(self) -> None:
        self._registry:    HypothesisRegistry = get_hypothesis_registry()
        self._factory:     HypothesisFactory   = get_hypothesis_factory()
        self._forecast_mgr: ForecastManager    = get_forecast_manager()
        self._scenario_eng: ScenarioEngine     = get_scenario_engine()
        self._probability:  ProbabilityEngine  = get_probability_engine()
        self._uncertainty:  UncertaintyEngine  = get_uncertainty_engine()
        self._evaluator:    ForecastEvaluator  = get_forecast_evaluator()
        self._sessions:     dict[str, HypothesisSession] = {}
        self._lock:         threading.RLock    = threading.RLock()

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
        h = self._factory.create(
            statement       = statement,
            hypothesis_type = hypothesis_type,
            probability     = probability,
            confidence      = confidence,
            parent_id       = parent_id,
            tags            = tags,
            ttl_s           = ttl_s,
            metadata        = metadata,
        )
        self._registry.add(h)
        self._probability.set_prior(h.hypothesis_id, probability)
        return h

    def get_hypothesis(self, hypothesis_id: str) -> Hypothesis:
        return self._registry.get(hypothesis_id)

    def activate(self, hypothesis_id: str) -> Hypothesis:
        h = self._check_not_expired(hypothesis_id)
        if h.status != HypothesisStatus.DRAFT:
            raise HypothesisStateError(hypothesis_id, h.status.value, "draft")
        h.status = HypothesisStatus.ACTIVE
        h.touch()
        return h

    def test(
        self,
        hypothesis_id: str,
        evidence_ids:  list[str] | None = None,
    ) -> HypothesisSession:
        h = self._check_not_expired(hypothesis_id)
        if h.status not in (HypothesisStatus.DRAFT, HypothesisStatus.ACTIVE):
            raise HypothesisStateError(
                hypothesis_id, h.status.value, "draft or active"
            )
        h.status = HypothesisStatus.TESTING
        h.touch()
        for eid in (evidence_ids or []):
            h.add_evidence(eid)

        session = HypothesisSession(hypothesis_id=hypothesis_id)
        session.start()
        session.begin_testing()
        with self._lock:
            self._sessions[session.session_id] = session
        return session

    def confirm(
        self,
        hypothesis_id: str,
        probability:   float = 1.0,
        note:          str   = "",
    ) -> HypothesisResult:
        h = self._registry.get(hypothesis_id)
        h.status      = HypothesisStatus.CONFIRMED
        h.probability = max(0.0, min(1.0, probability))
        h.touch()
        return self._make_result(h, HypothesisStatus.CONFIRMED, note)

    def reject(
        self,
        hypothesis_id: str,
        reason:        str   = "",
        probability:   float = 0.0,
    ) -> HypothesisResult:
        h = self._registry.get(hypothesis_id)
        h.status      = HypothesisStatus.REJECTED
        h.probability = max(0.0, min(1.0, probability))
        h.touch()
        return self._make_result(h, HypothesisStatus.REJECTED, reason)

    def suspend(self, hypothesis_id: str, reason: str = "") -> Hypothesis:
        h = self._registry.get(hypothesis_id)
        h.status = HypothesisStatus.SUSPENDED
        h.touch()
        return h

    def archive(self, hypothesis_id: str) -> Hypothesis:
        h = self._registry.get(hypothesis_id)
        h.status = HypothesisStatus.ARCHIVED
        h.touch()
        return h

    # ── Forecasting ──────────────────────────────────────────────────────────

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
        self._check_not_expired(hypothesis_id)
        result = self._forecast_mgr.forecast(
            hypothesis_id       = hypothesis_id,
            inputs              = inputs,
            model_id            = model_id,
            horizon             = horizon,
            forecast_type       = forecast_type,
            confidence_interval = confidence_interval,
            ttl_s               = ttl_s,
        )
        h = self._registry.get(hypothesis_id)
        h.add_forecast(result.forecast_id)
        return result

    async def forecast_async(
        self,
        hypothesis_id: str,
        inputs:        dict[str, Any],
        **kwargs: Any,
    ) -> ForecastResult:
        """Async thin wrapper (runs synchronously in executor)."""
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: self.forecast(hypothesis_id, inputs, **kwargs),
        )

    # ── Scenarios ────────────────────────────────────────────────────────────

    def generate_scenarios(
        self,
        hypothesis_id:    str,
        base_probability: float = 0.50,
        bull_probability: float = 0.25,
        bear_probability: float = 0.25,
    ) -> list[Scenario]:
        self._check_not_expired(hypothesis_id)
        return self._scenario_eng.generate_base_set(
            hypothesis_id, base_probability, bull_probability, bear_probability
        )

    def compare_scenarios(self, scenario_ids: list[str]) -> ScenarioComparison:
        return self._scenario_eng.compare(scenario_ids)

    # ── Probability ──────────────────────────────────────────────────────────

    def estimate_probability(
        self,
        hypothesis_id:         str,
        method:                ProbabilityMethod = ProbabilityMethod.BAYESIAN,
        likelihood_given_true: float              = 0.7,
        likelihood_given_false: float             = 0.3,
    ) -> ProbabilityEstimate:
        self._check_not_expired(hypothesis_id)
        if method == ProbabilityMethod.BAYESIAN:
            return self._probability.bayesian_update(
                hypothesis_id,
                likelihood_given_true  = likelihood_given_true,
                likelihood_given_false = likelihood_given_false,
            )
        elif method == ProbabilityMethod.MONTE_CARLO:
            prior = self._probability.get_prior(hypothesis_id)
            return self._probability.monte_carlo(prior)
        else:
            prior = self._probability.get_prior(hypothesis_id)
            return self._probability.ensemble_estimate([prior])

    # ── Uncertainty ───────────────────────────────────────────────────────────

    def estimate_uncertainty(self, forecast_id: str) -> UncertaintyReport:
        result = self._forecast_mgr.get(forecast_id)
        return self._uncertainty.estimate(result)

    # ── Evaluation ───────────────────────────────────────────────────────────

    def evaluate(self, forecast_id: str, actual_value: float) -> AccuracyReport:
        return self._evaluator.evaluate(forecast_id, actual_value)

    # ── Stats / Health ────────────────────────────────────────────────────────

    def stats(self) -> dict[str, Any]:
        return {
            "hypotheses": self._registry.stats(),
            "forecasts":  self._forecast_mgr.stats(),
            "scenarios":  self._scenario_eng.stats(),
            "probability": self._probability.stats(),
            "uncertainty": self._uncertainty.stats(),
            "evaluation":  self._evaluator.stats(),
        }

    def health(self) -> dict[str, Any]:
        reg_stats = self._registry.stats()
        return {
            "status":            "healthy",
            "total_hypotheses":  reg_stats["total"],
            "active_hypotheses": reg_stats["active"],
        }

    # ── Internal helpers ─────────────────────────────────────────────────────

    def _check_not_expired(self, hypothesis_id: str) -> Hypothesis:
        h = self._registry.get(hypothesis_id)
        if h.is_expired:
            raise HypothesisExpiredError(hypothesis_id)
        return h

    @staticmethod
    def _make_result(
        h:      Hypothesis,
        status: HypothesisStatus,
        summary: str,
    ) -> HypothesisResult:
        return HypothesisResult(
            hypothesis_id = h.hypothesis_id,
            status        = status,
            probability   = h.probability,
            confidence    = h.confidence,
            evidence_ids  = list(h.evidence_ids),
            forecast_ids  = list(h.forecast_ids),
            summary       = summary,
        )


# ── Singleton ──────────────────────────────────────────────────────────────────

_LOCK:    threading.Lock              = threading.Lock()
_MANAGER: HypothesisManager | None   = None


def get_hypothesis_manager() -> HypothesisManager:
    global _MANAGER
    if _MANAGER is None:
        with _LOCK:
            if _MANAGER is None:
                _MANAGER = HypothesisManager()
    return _MANAGER


def reset_hypothesis_manager() -> None:
    global _MANAGER
    with _LOCK:
        _MANAGER = None
