"""
iios/execution/analytics/predictive/constants.py
================================================
Constants for the Institutional Predictive Intelligence Framework.

C8 Execution Analytics & Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

import enum
from typing import Dict

VERSION = "1.0.0"

# ── System identifiers ────────────────────────────────────────────────────────

ENGINE_SYSTEM_ID    = "iios.execution.analytics.predictive.engine"
MANAGER_SYSTEM_ID   = "iios.execution.analytics.predictive.manager"
FORECASTER_SYSTEM_ID = "iios.execution.analytics.predictive.forecaster"
REGISTRY_SYSTEM_ID  = "iios.execution.analytics.predictive.registry"
FACTORY_SYSTEM_ID   = "iios.execution.analytics.predictive.factory"

# ── Actors ────────────────────────────────────────────────────────────────────

ACTOR_ENGINE     = "predictive_engine"
ACTOR_FORECASTER = "predictive_forecaster"
ACTOR_SYSTEM     = "system"
ACTOR_OPERATOR   = "operator"

# ── Operational defaults ──────────────────────────────────────────────────────

DEFAULT_MAX_REQUESTS    = 5_000
DEFAULT_MAX_HISTORY     = 2_000
DEFAULT_MIN_SAMPLES     = 3
DEFAULT_CONFIDENCE      = 0.5
DEFAULT_FORECAST_POINTS = 5      # number of future points per forecast


# ── Prediction domains ────────────────────────────────────────────────────────

class PredictionDomain(str, enum.Enum):
    """10 operational prediction domains."""

    EXECUTION_PERFORMANCE         = "execution_performance"
    GATEWAY_HEALTH                = "gateway_health"
    BROKER_STABILITY              = "broker_stability"
    RECOVERY_PROBABILITY          = "recovery_probability"
    MONITORING_HEALTH             = "monitoring_health"
    INFRASTRUCTURE_CAPACITY       = "infrastructure_capacity"
    QUEUE_BEHAVIOUR               = "queue_behaviour"
    LATENCY_FORECAST              = "latency_forecast"
    SYSTEM_AVAILABILITY           = "system_availability"
    PORTFOLIO_OPERATIONAL_HEALTH  = "portfolio_operational_health"


# ── Prediction types ──────────────────────────────────────────────────────────

class PredictionType(str, enum.Enum):
    """11 supported prediction types."""

    EXECUTION_VOLUME_FORECAST             = "execution_volume_forecast"
    EXPECTED_LATENCY                      = "expected_latency"
    GATEWAY_SATURATION                    = "gateway_saturation"
    BROKER_AVAILABILITY_FORECAST          = "broker_availability_forecast"
    RECOVERY_PROBABILITY                  = "recovery_probability"
    FAILURE_PROBABILITY                   = "failure_probability"
    CAPACITY_FORECAST                     = "capacity_forecast"
    QUEUE_GROWTH_FORECAST                 = "queue_growth_forecast"
    PERFORMANCE_DEGRADATION_RISK          = "performance_degradation_risk"
    INFRASTRUCTURE_UTILIZATION_FORECAST   = "infrastructure_utilization_forecast"
    OPERATIONAL_HEALTH_SCORE              = "operational_health_score"


# ── Forecast horizons ─────────────────────────────────────────────────────────

class ForecastHorizon(str, enum.Enum):
    """9 forecast time horizons."""

    NEXT_MINUTE          = "next_minute"
    NEXT_5_MINUTES       = "next_5_minutes"
    NEXT_15_MINUTES      = "next_15_minutes"
    NEXT_HOUR            = "next_hour"
    NEXT_TRADING_SESSION = "next_trading_session"
    DAILY                = "daily"
    WEEKLY               = "weekly"
    MONTHLY              = "monthly"
    CUSTOM               = "custom"


HORIZON_SECONDS: Dict[ForecastHorizon, float] = {
    ForecastHorizon.NEXT_MINUTE:          60.0,
    ForecastHorizon.NEXT_5_MINUTES:       300.0,
    ForecastHorizon.NEXT_15_MINUTES:      900.0,
    ForecastHorizon.NEXT_HOUR:            3_600.0,
    ForecastHorizon.NEXT_TRADING_SESSION: 23_400.0,
    ForecastHorizon.DAILY:                86_400.0,
    ForecastHorizon.WEEKLY:               604_800.0,
    ForecastHorizon.MONTHLY:              2_592_000.0,
    ForecastHorizon.CUSTOM:               0.0,
}


# ── Confidence levels ─────────────────────────────────────────────────────────

class ConfidenceLevel(str, enum.Enum):
    HIGH     = "high"       # >= 0.80
    MEDIUM   = "medium"     # >= 0.60
    LOW      = "low"        # >= 0.40
    VERY_LOW = "very_low"   # <  0.40


CONFIDENCE_THRESHOLDS: Dict[ConfidenceLevel, float] = {
    ConfidenceLevel.HIGH:     0.80,
    ConfidenceLevel.MEDIUM:   0.60,
    ConfidenceLevel.LOW:      0.40,
    ConfidenceLevel.VERY_LOW: 0.0,
}


def confidence_to_level(score: float) -> ConfidenceLevel:
    """Map a confidence score [0, 1] to a ConfidenceLevel."""
    if score >= CONFIDENCE_THRESHOLDS[ConfidenceLevel.HIGH]:
        return ConfidenceLevel.HIGH
    if score >= CONFIDENCE_THRESHOLDS[ConfidenceLevel.MEDIUM]:
        return ConfidenceLevel.MEDIUM
    if score >= CONFIDENCE_THRESHOLDS[ConfidenceLevel.LOW]:
        return ConfidenceLevel.LOW
    return ConfidenceLevel.VERY_LOW


# ── Trend types ───────────────────────────────────────────────────────────────

class TrendType(str, enum.Enum):
    IMPROVING  = "improving"
    DEGRADING  = "degrading"
    STABLE     = "stable"
    VOLATILE   = "volatile"
    UNKNOWN    = "unknown"


# ── Risk levels ───────────────────────────────────────────────────────────────

class RiskLevel(str, enum.Enum):
    CRITICAL = "critical"
    HIGH     = "high"
    MEDIUM   = "medium"
    LOW      = "low"
    MINIMAL  = "minimal"


RISK_SCORE_THRESHOLDS: Dict[RiskLevel, float] = {
    RiskLevel.CRITICAL: 0.85,
    RiskLevel.HIGH:     0.70,
    RiskLevel.MEDIUM:   0.50,
    RiskLevel.LOW:      0.30,
    RiskLevel.MINIMAL:  0.0,
}


def risk_score_to_level(score: float) -> RiskLevel:
    """Map a risk score [0, 1] to a RiskLevel."""
    if score >= RISK_SCORE_THRESHOLDS[RiskLevel.CRITICAL]:
        return RiskLevel.CRITICAL
    if score >= RISK_SCORE_THRESHOLDS[RiskLevel.HIGH]:
        return RiskLevel.HIGH
    if score >= RISK_SCORE_THRESHOLDS[RiskLevel.MEDIUM]:
        return RiskLevel.MEDIUM
    if score >= RISK_SCORE_THRESHOLDS[RiskLevel.LOW]:
        return RiskLevel.LOW
    return RiskLevel.MINIMAL


# ── Prediction event types ────────────────────────────────────────────────────

class PredictionEventType(str, enum.Enum):
    PREDICTION_STARTED          = "prediction_started"
    FORECAST_GENERATED          = "forecast_generated"
    TREND_FORECAST_COMPLETED    = "trend_forecast_completed"
    RISK_FORECAST_COMPLETED     = "risk_forecast_completed"
    CAPACITY_FORECAST_COMPLETED = "capacity_forecast_completed"
    PREDICTION_PUBLISHED        = "prediction_published"
    PREDICTION_FAILED           = "prediction_failed"


# ── Forecast algorithms ───────────────────────────────────────────────────────

class ForecastAlgorithm(str, enum.Enum):
    LINEAR      = "linear"       # ordinary least squares extrapolation
    EXPONENTIAL = "exponential"  # exponential smoothing with trend (Holt's)
    HYBRID      = "hybrid"       # linear trend + exponential level
