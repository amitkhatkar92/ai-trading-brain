"""
iios/intelligence/forecast/__init__.py
Public surface of the Hypothesis & Forecast Engine.
"""
from __future__ import annotations

from .hypothesis_constants import (
    HypothesisType,
    HypothesisStatus,
    ForecastHorizon,
    ForecastType,
    ScenarioType,
    ProbabilityMethod,
    EvaluationMetric,
    UncertaintyType,
    HYPOTHESIS_ENGINE_VERSION,
)
from .hypothesis_exceptions import (
    HypothesisForecastError,
    HypothesisError,
    HypothesisNotFoundError,
    HypothesisAlreadyExistsError,
    HypothesisStateError,
    HypothesisExpiredError,
    ForecastError,
    ForecastNotFoundError,
    ForecastModelError,
    InsufficientDataError,
    ForecastExpiredError,
    ScenarioError,
    ScenarioNotFoundError,
    ScenarioValidationError,
    InsufficientScenariosError,
    ProbabilityError,
    ProbabilityOutOfRangeError,
    DistributionError,
    EvaluationError,
    NoForecastToEvaluateError,
    EvaluationMetricError,
    ForecastEngineError,
    ForecastEngineNotInitializedError,
    ForecastEngineAlreadyRunningError,
)
from .hypothesis_registry import Hypothesis, HypothesisRegistry, get_hypothesis_registry
from .hypothesis_factory import HypothesisFactory, get_hypothesis_factory
from .hypothesis_engine import HypothesisEngine, get_hypothesis_engine, reset_hypothesis_engine

__all__ = [
    # Enums / constants
    "HypothesisType",
    "HypothesisStatus",
    "ForecastHorizon",
    "ForecastType",
    "ScenarioType",
    "ProbabilityMethod",
    "EvaluationMetric",
    "UncertaintyType",
    "HYPOTHESIS_ENGINE_VERSION",
    # Exceptions
    "HypothesisForecastError",
    "HypothesisError",
    "HypothesisNotFoundError",
    "HypothesisAlreadyExistsError",
    "HypothesisStateError",
    "HypothesisExpiredError",
    "ForecastError",
    "ForecastNotFoundError",
    "ForecastModelError",
    "InsufficientDataError",
    "ForecastExpiredError",
    "ScenarioError",
    "ScenarioNotFoundError",
    "ScenarioValidationError",
    "InsufficientScenariosError",
    "ProbabilityError",
    "ProbabilityOutOfRangeError",
    "DistributionError",
    "EvaluationError",
    "NoForecastToEvaluateError",
    "EvaluationMetricError",
    "ForecastEngineError",
    "ForecastEngineNotInitializedError",
    "ForecastEngineAlreadyRunningError",
    # Models
    "Hypothesis",
    "HypothesisRegistry",
    # Factories / registries
    "HypothesisFactory",
    "get_hypothesis_registry",
    "get_hypothesis_factory",
    # Gateway
    "HypothesisEngine",
    "get_hypothesis_engine",
    "reset_hypothesis_engine",
]
