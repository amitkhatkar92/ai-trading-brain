"""
iios.risk.assessment
=====================
Institutional Risk Assessment & Optimization Framework — C11 Risk Intelligence, Module 4.

Public exports from this package:

Constants & Enumerations
------------------------
ASSESSMENT_SYSTEM_ID, CALCULATOR_SYSTEM_ID, REGISTRY_SYSTEM_ID,
MODEL_REGISTRY_ID, OPTIMIZER_SYSTEM_ID, FACTORY_SYSTEM_ID, VERSION
AssessmentDomain, AssessmentCapability, OptimizationObjective,
ModelType, StressScenario, ScenarioType, AssessmentStatus,
AssessmentEventType, ValidationCode, ForecastHorizon, LimitStatus

Exceptions
----------
RiskAssessmentError, RiskAssessmentEngineNotRunningError,
RiskAssessmentNotFoundError, RiskAssessmentValidationError,
RiskModelNotFoundError, RiskCalculationError,
RiskAssessmentRegistryError, RiskAssessmentConfigurationError,
RiskOptimizationError, RiskStressTestError, RiskScenarioError,
RiskForecastError, RiskMitigationError, RiskAssessmentCapacityError

Value Objects (Requests / Responses)
--------------------------------------
RiskAssessmentContext, RiskAssessmentRequest
VaRReport, ExpectedShortfallReport
StressScenarioResult, StressTestReport
ScenarioOutcome, ScenarioAnalysisReport
ExposureReport
RiskForecast
MitigationAction, MitigationPlan
OptimizationRecommendation, RiskOptimizationReport
RiskAssessmentSummary, RiskAssessmentReport

Validation
----------
AssessmentValidationCheck, AssessmentValidationResult

Calculation Results
-------------------
ConcentrationResult, SensitivityResult, RiskScoreComponents,
LimitUtilisationResult, CalculationBundle

Model Registry
--------------
RiskModel

Events
------
RiskAssessmentEvent
make_assessment_started, make_models_loaded, make_risk_calculated,
make_stress_test_completed, make_scenario_analysis_completed,
make_optimization_completed, make_mitigation_generated,
make_assessment_validated, make_assessment_published,
make_assessment_failed

Services
--------
RiskAssessmentValidator, RiskAssessmentRegistry, RiskAssessmentHistory,
RiskAssessmentStatistics, RiskAssessmentFactory, RiskModelRegistry,
RiskVaREngine, RiskExpectedShortfallEngine, RiskMeasurementEngine,
RiskStressTestingEngine, RiskScenarioEngine, RiskSensitivityEngine,
RiskExposureEngine, RiskConcentrationEngine, RiskLimitEngine,
RiskForecastingEngine, RiskScoreEngine, RiskMitigationEngine,
RiskOptimizationEngine, RiskCalculationEngine, RiskAssessmentManager

Engine (primary public interface)
-----------------------------------
RiskAssessmentEngine, RiskAssessmentEngineStatus
"""
from __future__ import annotations

# ── Constants & enumerations ────────────────────────────────────────────────
from .constants import (
    ACTOR_ASSESSMENT_ENGINE,
    ACTOR_CALCULATOR,
    ACTOR_OPERATOR,
    ACTOR_OPTIMIZER,
    ACTOR_SYSTEM,
    ASSESSMENT_SYSTEM_ID,
    CALCULATOR_SYSTEM_ID,
    DEFAULT_ASSESSMENT_TIMEOUT_S,
    DEFAULT_CONFIDENCE_LEVEL,
    DEFAULT_EWMA_DECAY,
    DEFAULT_LOOKBACK_DAYS,
    DEFAULT_MAX_ASSESSMENTS,
    DEFAULT_MAX_CONCENTRATION,
    DEFAULT_MAX_HISTORY,
    DEFAULT_MAX_MODELS,
    DEFAULT_MONTE_CARLO_SIMULATIONS,
    DEFAULT_RISK_FREE_RATE,
    DEFAULT_VAR_CONFIDENCE_LEVELS,
    DEFAULT_VAR_HORIZON_DAYS,
    FACTORY_SYSTEM_ID,
    FORECAST_HORIZON_DAYS,
    LIMIT_BREACH_THRESHOLD,
    LIMIT_CRITICAL_THRESHOLD,
    LIMIT_WARNING_THRESHOLD,
    MIN_RETURNS_FOR_VAR,
    MITIGATION_TRIGGERS,
    MODEL_REGISTRY_ID,
    OPTIMIZER_SYSTEM_ID,
    REGISTRY_SYSTEM_ID,
    RISK_SCORE_HIGH,
    RISK_SCORE_LOW,
    RISK_SCORE_MEDIUM,
    SCENARIO_PROBABILITIES,
    SCENARIO_RETURN_MULTIPLIERS,
    SCHEMA_VERSION,
    STRESS_SHOCK_PARAMS,
    VERSION,
    ALL_DOMAINS,
    AssessmentCapability,
    AssessmentDomain,
    AssessmentEventType,
    AssessmentStatus,
    ForecastHorizon,
    LimitStatus,
    ModelType,
    OptimizationObjective,
    ScenarioType,
    StressScenario,
    ValidationCode,
)

# ── Exceptions ──────────────────────────────────────────────────────────────
from .exceptions import (
    RiskAssessmentCapacityError,
    RiskAssessmentConfigurationError,
    RiskAssessmentEngineNotRunningError,
    RiskAssessmentError,
    RiskAssessmentNotFoundError,
    RiskAssessmentRegistryError,
    RiskAssessmentValidationError,
    RiskCalculationError,
    RiskForecastError,
    RiskMitigationError,
    RiskModelNotFoundError,
    RiskOptimizationError,
    RiskScenarioError,
    RiskStressTestError,
)

# ── Context & Request ───────────────────────────────────────────────────────
from .risk_assessment_context import RiskAssessmentContext
from .risk_assessment_request import RiskAssessmentRequest

# ── Response / Report value objects ─────────────────────────────────────────
from .risk_assessment_response import (
    ExposureReport,
    MitigationAction,
    MitigationPlan,
    OptimizationRecommendation,
    RiskAssessmentReport,
    RiskAssessmentSummary,
    RiskForecast,
    RiskOptimizationReport,
    ScenarioAnalysisReport,
    ScenarioOutcome,
    StressScenarioResult,
    StressTestReport,
    VaRReport,
    ExpectedShortfallReport,
)

# ── Events ──────────────────────────────────────────────────────────────────
from .risk_assessment_events import (
    RiskAssessmentEvent,
    make_assessment_failed,
    make_assessment_published,
    make_assessment_started,
    make_assessment_validated,
    make_mitigation_generated,
    make_models_loaded,
    make_optimization_completed,
    make_risk_calculated,
    make_scenario_analysis_completed,
    make_stress_test_completed,
)

# ── Validation ──────────────────────────────────────────────────────────────
from .risk_assessment_validator import (
    AssessmentValidationCheck,
    AssessmentValidationResult,
    RiskAssessmentValidator,
)

# ── Statistics & History ─────────────────────────────────────────────────────
from .risk_assessment_statistics import RiskAssessmentStatistics
from .risk_assessment_history import RiskAssessmentHistory

# ── Registry & Factory ───────────────────────────────────────────────────────
from .risk_assessment_registry import RiskAssessmentRegistry
from .risk_assessment_factory import RiskAssessmentFactory
from .risk_model_registry import RiskModel, RiskModelRegistry

# ── Calculation engines ──────────────────────────────────────────────────────
from .risk_var_engine import RiskVaREngine
from .risk_expected_shortfall_engine import RiskExpectedShortfallEngine
from .risk_measurement_engine import RiskMeasurementEngine
from .risk_stress_testing_engine import RiskStressTestingEngine
from .risk_scenario_engine import RiskScenarioEngine
from .risk_sensitivity_engine import RiskSensitivityEngine, SensitivityResult
from .risk_exposure_engine import RiskExposureEngine
from .risk_concentration_engine import ConcentrationResult, RiskConcentrationEngine
from .risk_limit_engine import LimitUtilisationResult, RiskLimitEngine
from .risk_forecasting_engine import RiskForecastingEngine
from .risk_score_engine import RiskScoreComponents, RiskScoreEngine
from .risk_mitigation_engine import RiskMitigationEngine
from .risk_optimization_engine import RiskOptimizationEngine
from .risk_calculation_engine import CalculationBundle, RiskCalculationEngine

# ── Manager ──────────────────────────────────────────────────────────────────
from .risk_assessment_manager import RiskAssessmentManager

# ── Engine (primary public interface) ────────────────────────────────────────
from .risk_assessment_engine import RiskAssessmentEngine, RiskAssessmentEngineStatus

__all__ = [
    # Constants
    "ASSESSMENT_SYSTEM_ID", "CALCULATOR_SYSTEM_ID", "REGISTRY_SYSTEM_ID",
    "MODEL_REGISTRY_ID", "OPTIMIZER_SYSTEM_ID", "FACTORY_SYSTEM_ID",
    "VERSION", "SCHEMA_VERSION",
    "DEFAULT_CONFIDENCE_LEVEL", "DEFAULT_VAR_HORIZON_DAYS", "DEFAULT_LOOKBACK_DAYS",
    "DEFAULT_EWMA_DECAY", "DEFAULT_RISK_FREE_RATE", "DEFAULT_MAX_CONCENTRATION",
    "MIN_RETURNS_FOR_VAR", "ALL_DOMAINS",
    # Enums
    "AssessmentDomain", "AssessmentCapability", "OptimizationObjective",
    "ModelType", "StressScenario", "ScenarioType", "AssessmentStatus",
    "AssessmentEventType", "ValidationCode", "ForecastHorizon", "LimitStatus",
    # Exceptions
    "RiskAssessmentError", "RiskAssessmentEngineNotRunningError",
    "RiskAssessmentNotFoundError", "RiskAssessmentValidationError",
    "RiskModelNotFoundError", "RiskCalculationError",
    "RiskAssessmentRegistryError", "RiskAssessmentConfigurationError",
    "RiskOptimizationError", "RiskStressTestError", "RiskScenarioError",
    "RiskForecastError", "RiskMitigationError", "RiskAssessmentCapacityError",
    # Value objects
    "RiskAssessmentContext", "RiskAssessmentRequest",
    "VaRReport", "ExpectedShortfallReport",
    "StressScenarioResult", "StressTestReport",
    "ScenarioOutcome", "ScenarioAnalysisReport",
    "ExposureReport", "RiskForecast",
    "MitigationAction", "MitigationPlan",
    "OptimizationRecommendation", "RiskOptimizationReport",
    "RiskAssessmentSummary", "RiskAssessmentReport",
    # Validation
    "AssessmentValidationCheck", "AssessmentValidationResult",
    # Calculation results
    "ConcentrationResult", "SensitivityResult", "RiskScoreComponents",
    "LimitUtilisationResult", "CalculationBundle",
    # Model registry
    "RiskModel",
    # Events
    "RiskAssessmentEvent",
    "make_assessment_started", "make_models_loaded", "make_risk_calculated",
    "make_stress_test_completed", "make_scenario_analysis_completed",
    "make_optimization_completed", "make_mitigation_generated",
    "make_assessment_validated", "make_assessment_published",
    "make_assessment_failed",
    # Services
    "RiskAssessmentValidator", "RiskAssessmentRegistry", "RiskAssessmentHistory",
    "RiskAssessmentStatistics", "RiskAssessmentFactory", "RiskModelRegistry",
    "RiskVaREngine", "RiskExpectedShortfallEngine", "RiskMeasurementEngine",
    "RiskStressTestingEngine", "RiskScenarioEngine", "RiskSensitivityEngine",
    "RiskExposureEngine", "RiskConcentrationEngine", "RiskLimitEngine",
    "RiskForecastingEngine", "RiskScoreEngine", "RiskMitigationEngine",
    "RiskOptimizationEngine", "RiskCalculationEngine", "RiskAssessmentManager",
    # Engine
    "RiskAssessmentEngine", "RiskAssessmentEngineStatus",
]
