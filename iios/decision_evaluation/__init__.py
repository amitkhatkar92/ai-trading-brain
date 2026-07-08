"""
iios/decision_evaluation/__init__.py
Multi-Criteria Decision Evaluation Engine — public API.
"""
from __future__ import annotations

from .evaluation_constants import (
    CriterionDirection,
    CriterionType,
    DEFAULT_CRITERION_WEIGHT,
    DEFAULT_NORMALIZATION,
    DEFAULT_RANKING_METHOD,
    DEFAULT_SCORING_METHOD,
    EVALUATION_ENGINE_SYSTEM_ID,
    EVALUATION_ENGINE_VERSION,
    EvaluationMode,
    MAX_ALTERNATIVES_PER_REQUEST,
    MAX_CRITERIA_IN_REGISTRY,
    MAX_CRITERIA_PER_REQUEST,
    MAX_EVALUATION_HISTORY,
    NormalizationMethod,
    RankingMethod,
    ScoringMethod,
    WeightingStrategy,
)
from .evaluation_exceptions import (
    AggregationError,
    AlternativeError,
    AlternativeNotFoundError,
    CriterionAlreadyExistsError,
    CriterionError,
    CriterionNotFoundError,
    CriterionScoringError,
    EngineAlreadyRunningError,
    EngineLifecycleError,
    EngineNotInitializedError,
    EvaluationAlreadyExistsError,
    EvaluationEngineError,
    EvaluationError,
    EvaluationFailedError,
    EvaluationNotFoundError,
    InsufficientAlternativesError,
    InsufficientDataError,
    InvalidCriterionError,
    InvalidWeightError,
    NormalizationError,
    RankingAlgorithmNotFoundError,
    RankingError,
    RankingFailedError,
    RegistryError,
    RegistryOverflowError,
    ScoringError,
    TradeoffAnalysisFailedError,
    TradeoffError,
    UtilityFunctionError,
    WeightError,
    WeightSumError,
)
from .evaluation_context import (
    Alternative,
    EvalDiagnostic,
    EvaluationContextState,
    eval_stage_scope,
    evaluation_session,
    get_evaluation_context,
    reset_evaluation_context,
)
from .criteria.criterion import (
    BooleanCriterion,
    CompositeCriterion,
    Criterion,
    QualitativeCriterion,
    QuantitativeCriterion,
)
from .criteria.criteria_group import CriteriaGroup
from .criteria.criteria_manager import CriteriaManager
from .criteria.criteria_registry import (
    CriteriaRegistry,
    get_criteria_registry,
    reset_criteria_registry,
)
from .criteria.criteria_validator import CriteriaValidator, ValidationResult
from .scoring.score_calculator import AlternativeScore, CriterionScore, ScoreCalculator
from .scoring.score_normalizer import ScoreNormalizer
from .scoring.score_aggregator import ScoreAggregator
from .scoring.score_report import ScoreReport, build_score_report
from .scoring.scoring_engine import ScoringEngine
from .weighting.weight_manager import WeightManager
from .ranking.ranking_algorithm import (
    ParetoRanking,
    RankingAlgorithm,
    ScoreBasedRanking,
    UtilityRanking,
)
from .ranking.ranking_engine import RankingEngine
from .ranking.ranking_registry import (
    RankingRegistry,
    get_ranking_registry,
    reset_ranking_registry,
)
from .ranking.ranking_report import RankingReport, build_ranking_report
from .tradeoff.tradeoff_analyzer import (
    TradeoffAnalysis,
    TradeoffAnalyzer,
    TradeoffPair,
    TradeoffPoint,
)
from .tradeoff.utility_engine import (
    LinearUtility,
    PowerUtility,
    SigmoidUtility,
    StepUtility,
    UtilityEngine,
    UtilityFunction,
)
from .tradeoff.tradeoff_engine import TradeoffEngine
from .tradeoff.decision_matrix import DecisionMatrix, build_decision_matrix
from .analytics.evaluation_analytics import EvaluationAnalytics
from .evaluation_manager import (
    EvaluationManager,
    EvaluationRequest,
    EvaluationResult,
    get_evaluation_manager,
    reset_evaluation_manager,
)
from .evaluation_factory import EvaluationFactory
from .decision_evaluation_engine import (
    DecisionEvaluationEngine,
    get_decision_evaluation_engine,
    reset_decision_evaluation_engine,
)

__version__ = EVALUATION_ENGINE_VERSION

__all__ = [
    # Constants / enums
    "CriterionDirection", "CriterionType", "ScoringMethod", "NormalizationMethod",
    "RankingMethod", "WeightingStrategy", "EvaluationMode",
    "EVALUATION_ENGINE_VERSION", "EVALUATION_ENGINE_SYSTEM_ID",
    # Exceptions
    "EvaluationEngineError", "EvaluationError", "EvaluationNotFoundError",
    "EvaluationAlreadyExistsError", "EvaluationFailedError",
    "CriterionError", "CriterionNotFoundError", "CriterionAlreadyExistsError",
    "InvalidCriterionError", "CriterionScoringError",
    "ScoringError", "NormalizationError", "AggregationError", "InsufficientDataError",
    "RankingError", "RankingAlgorithmNotFoundError", "RankingFailedError",
    "TradeoffError", "TradeoffAnalysisFailedError", "UtilityFunctionError",
    "WeightError", "InvalidWeightError", "WeightSumError",
    "AlternativeError", "AlternativeNotFoundError", "InsufficientAlternativesError",
    "EngineLifecycleError", "EngineNotInitializedError", "EngineAlreadyRunningError",
    "RegistryError", "RegistryOverflowError",
    # Context
    "Alternative", "EvalDiagnostic", "EvaluationContextState",
    "evaluation_session", "eval_stage_scope",
    "get_evaluation_context", "reset_evaluation_context",
    # Criteria
    "Criterion", "QuantitativeCriterion", "QualitativeCriterion",
    "BooleanCriterion", "CompositeCriterion",
    "CriteriaGroup", "CriteriaManager",
    "CriteriaRegistry", "get_criteria_registry", "reset_criteria_registry",
    "CriteriaValidator", "ValidationResult",
    # Scoring
    "CriterionScore", "AlternativeScore", "ScoreCalculator",
    "ScoreNormalizer", "ScoreAggregator",
    "ScoreReport", "build_score_report", "ScoringEngine",
    # Weighting
    "WeightManager",
    # Ranking
    "RankingAlgorithm", "ScoreBasedRanking", "ParetoRanking", "UtilityRanking",
    "RankingEngine",
    "RankingRegistry", "get_ranking_registry", "reset_ranking_registry",
    "RankingReport", "build_ranking_report",
    # Trade-off / utility
    "TradeoffPair", "TradeoffPoint", "TradeoffAnalysis", "TradeoffAnalyzer",
    "TradeoffEngine",
    "UtilityFunction", "LinearUtility", "SigmoidUtility", "StepUtility", "PowerUtility",
    "UtilityEngine",
    "DecisionMatrix", "build_decision_matrix",
    # Analytics
    "EvaluationAnalytics",
    # Manager / request / result
    "EvaluationRequest", "EvaluationResult",
    "EvaluationManager", "get_evaluation_manager", "reset_evaluation_manager",
    # Factory
    "EvaluationFactory",
    # Engine
    "DecisionEvaluationEngine",
    "get_decision_evaluation_engine", "reset_decision_evaluation_engine",
]
