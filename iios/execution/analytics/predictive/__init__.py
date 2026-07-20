"""
iios/execution/analytics/predictive/__init__.py
===============================================
Public API for the Institutional Predictive Intelligence Framework (C8 M4).

Primary entry point: PredictiveIntelligenceEngine

C8 Execution Analytics & Intelligence — Phase 1, Module 4
"""

# Primary public interface
from .predictive_intelligence_engine import PredictiveIntelligenceEngine

# Request / Context
from .predictive_request import PredictionRequest, make_prediction_request
from .predictive_context import PredictiveContext, make_predictive_context

# Response types
from .predictive_response import (
    CapacityForecast,
    Forecast,
    ForecastPoint,
    ForecastSummary,
    OperationalForecast,
    PredictionReport,
    PredictiveSnapshot,
    ProbabilityReport,
    RiskForecast,
    make_predictive_snapshot,
)

# Constants
from .constants import (
    ConfidenceLevel,
    ForecastAlgorithm,
    ForecastHorizon,
    HORIZON_SECONDS,
    CONFIDENCE_THRESHOLDS,
    RISK_SCORE_THRESHOLDS,
    PredictionDomain,
    PredictionEventType,
    PredictionType,
    RiskLevel,
    TrendType,
    confidence_to_level,
    risk_score_to_level,
    ENGINE_SYSTEM_ID,
    MANAGER_SYSTEM_ID,
    FORECASTER_SYSTEM_ID,
    REGISTRY_SYSTEM_ID,
    FACTORY_SYSTEM_ID,
    DEFAULT_FORECAST_POINTS,
)

# Exceptions
from .exceptions import (
    PredictiveIntelligenceError,
    PredictiveEngineNotRunningError,
    PredictionRequestNotFoundError,
    PredictionForecastError,
    PredictionValidationError,
    PredictionModelError,
    PredictionConfidenceError,
    PredictionCapacityError,
    PredictionRiskError,
)

# Supporting components
from .predictive_anomaly_detector import AnomalyResult, PredictiveAnomalyDetector
from .predictive_capacity_estimator import PredictiveCapacityEstimator
from .predictive_events import (
    PredictiveIntelligenceEvent,
    make_capacity_forecast_completed_event,
    make_forecast_generated_event,
    make_prediction_failed_event,
    make_prediction_published_event,
    make_prediction_started_event,
    make_risk_forecast_completed_event,
    make_trend_forecast_completed_event,
)
from .predictive_factory import PredictiveIntelligenceFactory
from .predictive_forecaster import PredictiveForecaster
from .predictive_history import PredictiveIntelligenceHistory
from .predictive_manager import PredictiveManager
from .predictive_model_registry import ForecastModel, PredictiveModelRegistry
from .predictive_probability import PredictiveProbabilityEstimator
from .predictive_registry import PredictiveIntelligenceRegistry
from .predictive_risk_estimator import PredictiveRiskEstimator
from .predictive_scorer import PredictiveScorer
from .predictive_statistics import PredictiveIntelligenceStatistics
from .predictive_trend_engine import PredictiveTrendEngine
from .predictive_validation import PredictiveValidationResult, PredictiveValidator

__all__ = [
    # Primary interface
    "PredictiveIntelligenceEngine",
    # Request / Context
    "PredictionRequest",
    "make_prediction_request",
    "PredictiveContext",
    "make_predictive_context",
    # Response types
    "CapacityForecast",
    "Forecast",
    "ForecastPoint",
    "ForecastSummary",
    "OperationalForecast",
    "PredictionReport",
    "PredictiveSnapshot",
    "ProbabilityReport",
    "RiskForecast",
    "make_predictive_snapshot",
    # Constants
    "ConfidenceLevel",
    "ForecastAlgorithm",
    "ForecastHorizon",
    "HORIZON_SECONDS",
    "CONFIDENCE_THRESHOLDS",
    "RISK_SCORE_THRESHOLDS",
    "PredictionDomain",
    "PredictionEventType",
    "PredictionType",
    "RiskLevel",
    "TrendType",
    "confidence_to_level",
    "risk_score_to_level",
    "ENGINE_SYSTEM_ID",
    "MANAGER_SYSTEM_ID",
    "FORECASTER_SYSTEM_ID",
    "REGISTRY_SYSTEM_ID",
    "FACTORY_SYSTEM_ID",
    "DEFAULT_FORECAST_POINTS",
    # Exceptions
    "PredictiveIntelligenceError",
    "PredictiveEngineNotRunningError",
    "PredictionRequestNotFoundError",
    "PredictionForecastError",
    "PredictionValidationError",
    "PredictionModelError",
    "PredictionConfidenceError",
    "PredictionCapacityError",
    "PredictionRiskError",
    # Supporting components
    "AnomalyResult",
    "PredictiveAnomalyDetector",
    "PredictiveCapacityEstimator",
    "PredictiveIntelligenceEvent",
    "make_capacity_forecast_completed_event",
    "make_forecast_generated_event",
    "make_prediction_failed_event",
    "make_prediction_published_event",
    "make_prediction_started_event",
    "make_risk_forecast_completed_event",
    "make_trend_forecast_completed_event",
    "PredictiveIntelligenceFactory",
    "PredictiveForecaster",
    "PredictiveIntelligenceHistory",
    "PredictiveManager",
    "ForecastModel",
    "PredictiveModelRegistry",
    "PredictiveProbabilityEstimator",
    "PredictiveIntelligenceRegistry",
    "PredictiveRiskEstimator",
    "PredictiveScorer",
    "PredictiveIntelligenceStatistics",
    "PredictiveTrendEngine",
    "PredictiveValidationResult",
    "PredictiveValidator",
]
