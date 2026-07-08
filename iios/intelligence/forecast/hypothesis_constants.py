"""
iios/intelligence/forecast/hypothesis_constants.py
==================================================
Shared constants and enumerations for the Hypothesis & Forecast Engine.
"""
from __future__ import annotations

from enum import Enum, IntEnum


class HypothesisType(str, Enum):
    DIRECTIONAL   = "directional"    # Predicts direction (up/down)
    CAUSAL        = "causal"         # Identifies cause-effect
    CORRELATIONAL = "correlational"  # Identifies co-movement
    PREDICTIVE    = "predictive"     # Numeric prediction
    EXPLANATORY   = "explanatory"    # Explains observed phenomenon
    COMPARATIVE   = "comparative"    # Compares alternatives
    CONDITIONAL   = "conditional"    # If X then Y
    NULL          = "null"           # No effect (H₀)
    ALTERNATIVE   = "alternative"    # There is an effect (H₁)
    GENERIC       = "generic"


class HypothesisStatus(str, Enum):
    DRAFT     = "draft"
    ACTIVE    = "active"
    TESTING   = "testing"
    CONFIRMED = "confirmed"
    REJECTED  = "rejected"
    SUSPENDED = "suspended"
    RETIRED   = "retired"
    ARCHIVED  = "archived"


class ForecastHorizon(str, Enum):
    INTRADAY    = "intraday"     # Within the same day
    SHORT_TERM  = "short_term"   # 1 day – 1 week
    MEDIUM_TERM = "medium_term"  # 1 week – 1 month
    LONG_TERM   = "long_term"    # 1 month – 1 year
    ULTRA_LONG  = "ultra_long"   # > 1 year


class ForecastType(str, Enum):
    POINT         = "point"          # Single value
    RANGE         = "range"          # Low–high band
    DISTRIBUTION  = "distribution"   # Full probability distribution
    SCENARIO      = "scenario"       # Named narrative
    ENSEMBLE      = "ensemble"       # Average of multiple models
    PROBABILISTIC = "probabilistic"  # Probability-weighted


class ScenarioType(str, Enum):
    BASE_CASE   = "base_case"
    BULL_CASE   = "bull_case"
    BEAR_CASE   = "bear_case"
    STRESS_CASE = "stress_case"
    BLACK_SWAN  = "black_swan"
    ALTERNATIVE = "alternative"


class ProbabilityMethod(str, Enum):
    FREQUENTIST = "frequentist"
    BAYESIAN    = "bayesian"
    SUBJECTIVE  = "subjective"
    ENSEMBLE    = "ensemble"
    MONTE_CARLO = "monte_carlo"


class EvaluationMetric(str, Enum):
    MAE         = "mae"         # Mean absolute error
    RMSE        = "rmse"        # Root mean squared error
    MAPE        = "mape"        # Mean absolute % error
    ACCURACY    = "accuracy"    # Directional accuracy
    CALIBRATION = "calibration" # Are CI widths correct?
    SHARPNESS   = "sharpness"   # How narrow are CIs?
    RESOLUTION  = "resolution"  # Vary from base rate?


class UncertaintyType(str, Enum):
    ALEATORIC = "aleatoric"  # Inherent randomness
    EPISTEMIC = "epistemic"  # Model ignorance
    MODEL     = "model"      # Model mis-specification
    DATA      = "data"       # Data quality
    PARAMETER = "parameter"  # Parameter estimation


class RevisionReason(str, Enum):
    NEW_EVIDENCE   = "new_evidence"
    MODEL_UPDATE   = "model_update"
    MARKET_SHOCK   = "market_shock"
    CALIBRATION    = "calibration"
    MANUAL         = "manual"
    SCHEDULED      = "scheduled"


# ── Version ────────────────────────────────────────────────────────────────────
HYPOTHESIS_ENGINE_VERSION = "1.0.0"

# ── Hard limits ────────────────────────────────────────────────────────────────
MAX_HYPOTHESES        = 1_000
MAX_FORECASTS         = 5_000
MAX_SCENARIOS         = 200
MAX_EVALUATIONS       = 10_000
MAX_REVISIONS         = 50     # per forecast

# ── Defaults ──────────────────────────────────────────────────────────────────
DEFAULT_HYPOTHESIS_TTL_S    = 86_400.0   # 24 h
DEFAULT_FORECAST_TTL_S      =  3_600.0   #  1 h
DEFAULT_CONFIDENCE_INTERVAL = 0.90       # 90 % CI
DEFAULT_PRIOR_PROBABILITY   = 0.50       # neutral Bayesian prior

# ── Scenario weights ───────────────────────────────────────────────────────────
SCENARIO_WEIGHT_PROBABILITY = 0.40
SCENARIO_WEIGHT_IMPACT      = 0.35
SCENARIO_WEIGHT_CONFIDENCE  = 0.25

# ── System identifiers ─────────────────────────────────────────────────────────
SYSTEM_FORECASTER_ID   = "iios:forecaster:system"
FORECAST_CHANNEL_NAME  = "iios:forecast:broadcast"
