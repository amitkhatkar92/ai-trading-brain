"""
constants.py — iios.risk.assessment
=====================================
Enumerations, identifiers, and defaults for the Risk Assessment &
Optimization Framework.

C11 Risk Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

from enum import Enum
from typing import Dict, FrozenSet, Tuple

# ---------------------------------------------------------------------------
# System identifiers
# ---------------------------------------------------------------------------
ASSESSMENT_SYSTEM_ID: str = "iios:risk:assessment"
CALCULATOR_SYSTEM_ID: str = "iios:risk:assessment:calculator"
REGISTRY_SYSTEM_ID:   str = "iios:risk:assessment:registry"
MODEL_REGISTRY_ID:    str = "iios:risk:assessment:models"
OPTIMIZER_SYSTEM_ID:  str = "iios:risk:assessment:optimizer"
FACTORY_SYSTEM_ID:    str = "iios:risk:assessment:factory"

# ---------------------------------------------------------------------------
# Versioning
# ---------------------------------------------------------------------------
VERSION:        str = "1.0.0"
SCHEMA_VERSION: str = "1.0"

# ---------------------------------------------------------------------------
# Actors
# ---------------------------------------------------------------------------
ACTOR_ASSESSMENT_ENGINE: str = "iios:risk:assessment:engine"
ACTOR_CALCULATOR:        str = "iios:risk:assessment:calculator"
ACTOR_OPTIMIZER:         str = "iios:risk:assessment:optimizer"
ACTOR_SYSTEM:            str = "iios:system"
ACTOR_OPERATOR:          str = "operator"

# ---------------------------------------------------------------------------
# Default quantitative parameters
# ---------------------------------------------------------------------------
DEFAULT_MAX_ASSESSMENTS:         int   = 10_000
DEFAULT_MAX_HISTORY:             int   = 1_000
DEFAULT_MAX_MODELS:              int   = 500
DEFAULT_CONFIDENCE_LEVEL:        float = 0.95
DEFAULT_VAR_HORIZON_DAYS:        int   = 1
DEFAULT_LOOKBACK_DAYS:           int   = 252
DEFAULT_MONTE_CARLO_SIMULATIONS: int   = 10_000
DEFAULT_ASSESSMENT_TIMEOUT_S:    float = 60.0
DEFAULT_EWMA_DECAY:              float = 0.94
DEFAULT_RISK_FREE_RATE:          float = 0.05
DEFAULT_MAX_CONCENTRATION:       float = 0.25   # 25% single-position limit
DEFAULT_VAR_CONFIDENCE_LEVELS: Tuple[float, ...] = (0.90, 0.95, 0.99)

# Limit thresholds
LIMIT_WARNING_THRESHOLD:  float = 0.80
LIMIT_BREACH_THRESHOLD:   float = 1.00
LIMIT_CRITICAL_THRESHOLD: float = 1.10

# Risk score bands (out of 100)
RISK_SCORE_LOW:    float = 30.0
RISK_SCORE_MEDIUM: float = 60.0
RISK_SCORE_HIGH:   float = 80.0

# Minimum returns needed for meaningful VaR calculation
MIN_RETURNS_FOR_VAR: int = 10


# ---------------------------------------------------------------------------
# AssessmentDomain — 12 risk domains
# ---------------------------------------------------------------------------
class AssessmentDomain(str, Enum):
    """Classification of risk assessment domains."""
    MARKET_RISK         = "market_risk"
    PORTFOLIO_RISK      = "portfolio_risk"
    POSITION_RISK       = "position_risk"
    CREDIT_RISK         = "credit_risk"
    LIQUIDITY_RISK      = "liquidity_risk"
    OPERATIONAL_RISK    = "operational_risk"
    INFRASTRUCTURE_RISK = "infrastructure_risk"
    COUNTERPARTY_RISK   = "counterparty_risk"
    CONCENTRATION_RISK  = "concentration_risk"
    EXPOSURE_RISK       = "exposure_risk"
    MODEL_RISK          = "model_risk"
    ENTERPRISE_RISK     = "enterprise_risk"


# ---------------------------------------------------------------------------
# AssessmentCapability — 15 capabilities
# ---------------------------------------------------------------------------
class AssessmentCapability(str, Enum):
    """Individual quantitative assessment capabilities."""
    VALUE_AT_RISK              = "value_at_risk"
    EXPECTED_SHORTFALL         = "expected_shortfall"
    MAXIMUM_DRAWDOWN           = "maximum_drawdown"
    VOLATILITY_ANALYSIS        = "volatility_analysis"
    EXPOSURE_ANALYSIS          = "exposure_analysis"
    SENSITIVITY_ANALYSIS       = "sensitivity_analysis"
    CONCENTRATION_ANALYSIS     = "concentration_analysis"
    CORRELATION_ANALYSIS       = "correlation_analysis"
    STRESS_TESTING             = "stress_testing"
    SCENARIO_ANALYSIS          = "scenario_analysis"
    LIMIT_UTILIZATION          = "limit_utilization"
    CAPITAL_AT_RISK            = "capital_at_risk"
    LIQUIDITY_ASSESSMENT       = "liquidity_assessment"
    RISK_FORECASTING           = "risk_forecasting"
    RISK_MITIGATION_PLANNING   = "risk_mitigation_planning"


# ---------------------------------------------------------------------------
# OptimizationObjective — 8 objectives
# ---------------------------------------------------------------------------
class OptimizationObjective(str, Enum):
    """Risk optimization goals."""
    MINIMIZE_PORTFOLIO_RISK           = "minimize_portfolio_risk"
    MINIMIZE_CONCENTRATION            = "minimize_concentration"
    MINIMIZE_TAIL_RISK                = "minimize_tail_risk"
    OPTIMIZE_CAPITAL_ALLOCATION       = "optimize_capital_allocation"
    OPTIMIZE_LIQUIDITY                = "optimize_liquidity"
    OPTIMIZE_EXPOSURE                 = "optimize_exposure"
    IMPROVE_RISK_ADJUSTED_PERFORMANCE = "improve_risk_adjusted_performance"
    IMPROVE_PORTFOLIO_STABILITY       = "improve_portfolio_stability"


# ---------------------------------------------------------------------------
# ModelType — 7 quantitative model types
# ---------------------------------------------------------------------------
class ModelType(str, Enum):
    """Quantitative model classification."""
    HISTORICAL_SIMULATION = "historical_simulation"
    PARAMETRIC            = "parametric"
    MONTE_CARLO           = "monte_carlo"
    FACTOR_MODEL          = "factor_model"
    SENSITIVITY_MODEL     = "sensitivity_model"
    CORRELATION_MODEL     = "correlation_model"
    CUSTOM_INSTITUTIONAL  = "custom_institutional"


# ---------------------------------------------------------------------------
# StressScenario — 8 pre-defined stress scenarios
# ---------------------------------------------------------------------------
class StressScenario(str, Enum):
    """Pre-defined stress testing scenarios."""
    HISTORICAL_EVENTS   = "historical_events"
    MARKET_CRASH        = "market_crash"
    INTEREST_RATE_SHOCK = "interest_rate_shock"
    VOLATILITY_SPIKE    = "volatility_spike"
    LIQUIDITY_CRISIS    = "liquidity_crisis"
    SECTOR_SHOCK        = "sector_shock"
    CURRENCY_SHOCK      = "currency_shock"
    CUSTOM              = "custom"


# ---------------------------------------------------------------------------
# ScenarioType — 6 scenario types
# ---------------------------------------------------------------------------
class ScenarioType(str, Enum):
    """Forward scenario classifications."""
    BEST_CASE     = "best_case"
    EXPECTED_CASE = "expected_case"
    WORST_CASE    = "worst_case"
    BLACK_SWAN    = "black_swan"
    CUSTOM        = "custom"
    MULTI_FACTOR  = "multi_factor"


# ---------------------------------------------------------------------------
# AssessmentStatus
# ---------------------------------------------------------------------------
class AssessmentStatus(str, Enum):
    """Lifecycle state of a risk assessment."""
    CREATED    = "created"
    PROCESSING = "processing"
    COMPLETED  = "completed"
    FAILED     = "failed"
    CANCELLED  = "cancelled"


# ---------------------------------------------------------------------------
# AssessmentEventType — 10 domain events
# ---------------------------------------------------------------------------
class AssessmentEventType(str, Enum):
    """Domain events emitted by the assessment framework."""
    ASSESSMENT_STARTED          = "assessment_started"
    MODELS_LOADED               = "models_loaded"
    RISK_CALCULATED             = "risk_calculated"
    STRESS_TEST_COMPLETED       = "stress_test_completed"
    SCENARIO_ANALYSIS_COMPLETED = "scenario_analysis_completed"
    OPTIMIZATION_COMPLETED      = "optimization_completed"
    MITIGATION_GENERATED        = "mitigation_generated"
    ASSESSMENT_VALIDATED        = "assessment_validated"
    ASSESSMENT_PUBLISHED        = "assessment_published"
    ASSESSMENT_FAILED           = "assessment_failed"


# ---------------------------------------------------------------------------
# ValidationCode
# ---------------------------------------------------------------------------
class ValidationCode(str, Enum):
    """Validation check identifiers."""
    INPUT_CONSISTENT         = "input_consistent"
    MODEL_CONSISTENT         = "model_consistent"
    CALCULATION_INTEGRITY    = "calculation_integrity"
    ASSESSMENT_COMPLETE      = "assessment_complete"
    OPTIMIZATION_INTEGRITY   = "optimization_integrity"
    FORECAST_CONSISTENT      = "forecast_consistent"
    MITIGATION_CONSISTENT    = "mitigation_consistent"
    RETURNS_SUFFICIENT       = "returns_sufficient"
    WEIGHTS_VALID            = "weights_valid"
    PORTFOLIO_VALUE_POSITIVE = "portfolio_value_positive"


# ---------------------------------------------------------------------------
# ForecastHorizon
# ---------------------------------------------------------------------------
class ForecastHorizon(str, Enum):
    """Risk forecast time horizons."""
    DAY     = "day"
    WEEK    = "week"
    MONTH   = "month"
    QUARTER = "quarter"


FORECAST_HORIZON_DAYS: Dict[ForecastHorizon, int] = {
    ForecastHorizon.DAY:     1,
    ForecastHorizon.WEEK:    5,
    ForecastHorizon.MONTH:   21,
    ForecastHorizon.QUARTER: 63,
}


# ---------------------------------------------------------------------------
# LimitStatus
# ---------------------------------------------------------------------------
class LimitStatus(str, Enum):
    """Utilization status relative to defined limits."""
    OK       = "ok"
    WARNING  = "warning"
    BREACH   = "breach"
    CRITICAL = "critical"


# ---------------------------------------------------------------------------
# Deterministic stress shock parameters
# ---------------------------------------------------------------------------
STRESS_SHOCK_PARAMS: Dict[StressScenario, Dict[str, float]] = {
    StressScenario.MARKET_CRASH:        {"equity_shock": -0.35, "vol_multiplier": 3.0},
    StressScenario.INTEREST_RATE_SHOCK: {"rate_shock_bps": 200.0, "bond_impact": -0.08},
    StressScenario.VOLATILITY_SPIKE:    {"vol_multiplier": 4.0,  "equity_shock": -0.15},
    StressScenario.LIQUIDITY_CRISIS:    {"liquidity_haircut": 0.40, "equity_shock": -0.20},
    StressScenario.SECTOR_SHOCK:        {"sector_shock": -0.25,  "equity_shock": -0.10},
    StressScenario.CURRENCY_SHOCK:      {"fx_shock": -0.20,      "equity_shock": -0.08},
    StressScenario.HISTORICAL_EVENTS:   {"equity_shock": -0.45,  "vol_multiplier": 5.0},
    StressScenario.CUSTOM:              {"equity_shock": -0.10,  "vol_multiplier": 1.5},
}

# Scenario probability weights (must not be used for policy — informational only)
SCENARIO_PROBABILITIES: Dict[ScenarioType, float] = {
    ScenarioType.BEST_CASE:     0.20,
    ScenarioType.EXPECTED_CASE: 0.55,
    ScenarioType.WORST_CASE:    0.20,
    ScenarioType.BLACK_SWAN:    0.05,
    ScenarioType.CUSTOM:        0.00,
    ScenarioType.MULTI_FACTOR:  0.00,
}

# Return multipliers relative to expected return for scenario projections
SCENARIO_RETURN_MULTIPLIERS: Dict[ScenarioType, float] = {
    ScenarioType.BEST_CASE:     2.0,
    ScenarioType.EXPECTED_CASE: 1.0,
    ScenarioType.WORST_CASE:   -1.5,
    ScenarioType.BLACK_SWAN:   -4.0,
    ScenarioType.CUSTOM:        0.0,
    ScenarioType.MULTI_FACTOR: -2.0,
}

# Mitigation action keywords by risk driver
MITIGATION_TRIGGERS: Dict[str, str] = {
    "concentration_high":  "Reduce top position weights to below concentration limit",
    "var_high":            "Reduce gross exposure or add hedges to lower VaR",
    "es_high":             "Add tail risk protection (options or stop-losses)",
    "drawdown_high":       "Reduce leverage and increase diversification",
    "limit_breach":        "Immediately reduce positions breaching risk limits",
    "liquidity_low":       "Shift allocation toward more liquid instruments",
    "volatility_high":     "Reduce position sizes or add volatility hedges",
    "stress_loss_high":    "Reduce exposure to stress-sensitive positions",
    "correlation_high":    "Diversify across lower-correlated assets",
    "forecast_risk_high":  "Pre-emptively reduce risk ahead of forecast horizon",
}

# All valid assessment domains as a frozenset for fast membership checks
ALL_DOMAINS: FrozenSet[str] = frozenset(d.value for d in AssessmentDomain)
