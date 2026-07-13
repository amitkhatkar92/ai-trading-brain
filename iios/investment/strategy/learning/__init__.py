"""iios/investment/strategy/learning/__init__.py
Institutional Strategy Learning Engine — public API surface.

Observe → Learn → Explain → Recommend → Preserve institutional knowledge.

Constraints:
- Never modifies strategies automatically.
- Never retrains ML models.
- Never generates Buy/Sell/Hold decisions.
- All outputs are explainable, auditable, versioned, and reversible.
"""
from iios.investment.strategy.learning.learning_input import LearningObservation
from iios.investment.strategy.learning.learning_policy import (
    LearningPolicy,
    DEFAULT_POLICY,
    CONSERVATIVE_POLICY,
    AGGRESSIVE_POLICY,
    INSTITUTIONAL_POLICY,
)
from iios.investment.strategy.learning.learning_profile import StrategyLearningProfile
from iios.investment.strategy.learning.learning_snapshot import LearningSnapshot
from iios.investment.strategy.learning.learning_history import ObservationStore, LearningSnapshotStore
from iios.investment.strategy.learning.learning_events import (
    LearningEvent,
    LearningEventBus,
    LearningEventType,
)
from iios.investment.strategy.learning.learning_statistics import (
    clamp,
    safe_div,
    ewma,
    rolling_mean,
    linear_trend,
    normalised_trend,
    drift_magnitude,
    drift_score,
    z_score,
    coefficient_of_variation,
    consistency_score,
    improvement_rate,
    last_n,
    split_baseline_recent,
    percentile,
    above_threshold_rate,
)
from iios.investment.strategy.learning.success_pattern import SuccessPattern, SuccessPatternExtractor
from iios.investment.strategy.learning.failure_pattern import FailurePattern, FailurePatternExtractor
from iios.investment.strategy.learning.performance_drift import (
    DriftWindow,
    PerformanceDrift,
    PerformanceDriftAnalyzer,
)
from iios.investment.strategy.learning.performance_learning import (
    PerformanceLearningResult,
    PerformanceLearner,
)
from iios.investment.strategy.learning.parameter_analysis import (
    ParameterStabilityResult,
    ParameterAnalyzer,
)
from iios.investment.strategy.learning.regime_adaptation import (
    RegimeAdaptationResult,
    RegimeAdaptationAnalyzer,
)
from iios.investment.strategy.learning.adaptation_recommendations import AdaptationRecommendation
from iios.investment.strategy.learning.adaptation_engine import AdaptationReport, AdaptationEngine
from iios.investment.strategy.learning.degradation_statistics import (
    degradation_score,
    improvement_score,
    rolling_z_scores,
    cumulative_drift,
    max_drawdown_from_scores,
    drift_acceleration,
    signal_to_noise_ratio,
    is_statistically_significant,
)
from iios.investment.strategy.learning.drift_detector import (
    DriftType,
    DriftSignal,
    DriftDetector,
)
from iios.investment.strategy.learning.performance_monitor import StrategyPerformanceMonitor
from iios.investment.strategy.learning.degradation_detector import (
    DegradationLevel,
    DegradationReport,
    DegradationDetector,
)
from iios.investment.strategy.learning.lesson_registry import Lesson, LessonCategory, LessonRegistry
from iios.investment.strategy.learning.best_practices import BestPractice, BestPracticeExtractor
from iios.investment.strategy.learning.failure_library import FailureEntry, FailureLibrary
from iios.investment.strategy.learning.knowledge_engine import KnowledgeReport, KnowledgeEngine
from iios.investment.strategy.learning.recommendation_score import RecommendationScore, score_recommendation
from iios.investment.strategy.learning.recommendation_history import (
    RecommendationRecord,
    RecommendationHistory,
)
from iios.investment.strategy.learning.improvement_engine import ImprovementSuggestion, ImprovementEngine
from iios.investment.strategy.learning.recommendation_engine import (
    RecommendationType,
    Recommendation,
    RecommendationEngine,
)
from iios.investment.strategy.learning.learning_confidence import LearningConfidence
from iios.investment.strategy.learning.strategy_maturity import (
    MaturityLevel,
    StrategyMaturity,
    MaturityAssessor,
)
from iios.investment.strategy.learning.learning_quality import LearningQuality
from iios.investment.strategy.learning.learning_score import LearningScore, LearningScoreCalculator
from iios.investment.strategy.learning.strategy_learning_engine import StrategyLearningEngine

__all__ = [
    # Input
    "LearningObservation",
    # Policy
    "LearningPolicy",
    "DEFAULT_POLICY",
    "CONSERVATIVE_POLICY",
    "AGGRESSIVE_POLICY",
    "INSTITUTIONAL_POLICY",
    # Profile & History
    "StrategyLearningProfile",
    "LearningSnapshot",
    "ObservationStore",
    "LearningSnapshotStore",
    # Events
    "LearningEvent",
    "LearningEventBus",
    "LearningEventType",
    # Statistics helpers
    "clamp",
    "safe_div",
    "ewma",
    "rolling_mean",
    "linear_trend",
    "normalised_trend",
    "drift_magnitude",
    "drift_score",
    "z_score",
    "coefficient_of_variation",
    "consistency_score",
    "improvement_rate",
    "last_n",
    "split_baseline_recent",
    "percentile",
    "above_threshold_rate",
    # Pattern extraction
    "SuccessPattern",
    "SuccessPatternExtractor",
    "FailurePattern",
    "FailurePatternExtractor",
    # Performance
    "DriftWindow",
    "PerformanceDrift",
    "PerformanceDriftAnalyzer",
    "PerformanceLearningResult",
    "PerformanceLearner",
    # Parameters
    "ParameterStabilityResult",
    "ParameterAnalyzer",
    # Regime
    "RegimeAdaptationResult",
    "RegimeAdaptationAnalyzer",
    # Adaptation
    "AdaptationRecommendation",
    "AdaptationReport",
    "AdaptationEngine",
    # Degradation
    "degradation_score",
    "improvement_score",
    "rolling_z_scores",
    "cumulative_drift",
    "max_drawdown_from_scores",
    "drift_acceleration",
    "signal_to_noise_ratio",
    "is_statistically_significant",
    "DriftType",
    "DriftSignal",
    "DriftDetector",
    "StrategyPerformanceMonitor",
    "DegradationLevel",
    "DegradationReport",
    "DegradationDetector",
    # Knowledge
    "Lesson",
    "LessonCategory",
    "LessonRegistry",
    "BestPractice",
    "BestPracticeExtractor",
    "FailureEntry",
    "FailureLibrary",
    "KnowledgeReport",
    "KnowledgeEngine",
    # Recommendations
    "RecommendationScore",
    "score_recommendation",
    "RecommendationRecord",
    "RecommendationHistory",
    "ImprovementSuggestion",
    "ImprovementEngine",
    "RecommendationType",
    "Recommendation",
    "RecommendationEngine",
    # Scoring & Quality
    "LearningConfidence",
    "MaturityLevel",
    "StrategyMaturity",
    "MaturityAssessor",
    "LearningQuality",
    "LearningScore",
    "LearningScoreCalculator",
    # Main facade
    "StrategyLearningEngine",
]
