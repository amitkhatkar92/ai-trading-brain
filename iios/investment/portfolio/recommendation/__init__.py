"""iios/investment/portfolio/recommendation/__init__.py

Public API for the Institutional Portfolio Recommendation Engine.
"""
from __future__ import annotations

# ---------------------------------------------------------------------------
# Types and constants
# ---------------------------------------------------------------------------
from iios.investment.portfolio.recommendation.recommendation_types import (
    # Constants
    RISK_BUDGET_HIGH_THRESHOLD,
    RISK_BUDGET_LOW_THRESHOLD,
    VAR_CRITICAL_THRESHOLD,
    DRAWDOWN_SEVERE_THRESHOLD,
    EQUITY_OVERWEIGHT_THRESHOLD,
    EQUITY_UNDERWEIGHT_THRESHOLD,
    CASH_HIGH_THRESHOLD,
    CASH_LOW_THRESHOLD,
    INTERNATIONAL_LOW_THRESHOLD,
    HHI_CONCENTRATED_THRESHOLD,
    MIN_EFFECTIVE_POSITIONS,
    MAX_SECTOR_CONCENTRATION,
    SHARPE_POOR_THRESHOLD,
    CONSTRUCTION_QUALITY_MIN,
    OPTIMIZATION_QUALITY_MIN,
    MIN_CONFIDENCE_TO_PUBLISH,
    MAX_ACTIVE_RECOMMENDATIONS,
    REC_COOLDOWN_HOURS,
    DEFAULT_EXPIRY_HOURS,
    CRITICAL_EXPIRY_HOURS,
    HIGH_EXPIRY_HOURS,
    LOW_EXPIRY_HOURS,
    NO_ACTION_EXPIRY_HOURS,
    REC_SCORE_EXCELLENT,
    REC_SCORE_GOOD,
    REC_SCORE_AVERAGE,
    REC_SCORE_BELOW_AVERAGE,
    # Enums
    RecommendationAction,
    RecommendationPriority,
    RecommendationRisk,
    RecommendationStatus,
    LifecycleState,
    RecommendationGrade,
    RecommendationLevel,
    ValidationStatus,
    PolicyType,
    # Core types
    PortfolioIntelligence,
    intelligence_from_any,
    # Utilities
    now_utc,
    recommendation_score_to_grade,
    recommendation_score_to_level,
    action_to_category,
    priority_to_expiry_hours,
)

# ---------------------------------------------------------------------------
# Recommendation models
# ---------------------------------------------------------------------------
from iios.investment.portfolio.recommendation.portfolio_recommendation import (
    PortfolioRecommendation,
    RecommendationCandidate,
    build_recommendation,
)
from iios.investment.portfolio.recommendation.recommendation_snapshot import (
    RecommendationHistory,
    RecommendationRecord,
)
from iios.investment.portfolio.recommendation.recommendation_history import (
    PortfolioRecommendationHistory,
)
from iios.investment.portfolio.recommendation.recommendation_statistics import (
    PortfolioRecommendationStatistics,
    RecommendationRunMetric,
    RecommendationStatisticsSnapshot,
)

# ---------------------------------------------------------------------------
# Policies and registry
# ---------------------------------------------------------------------------
from iios.investment.portfolio.recommendation.recommendation_policies import (
    InstitutionalPolicy,
    PolicyParameters,
)
from iios.investment.portfolio.recommendation.recommendation_registry import (
    RecommendationPolicyRegistry,
)

# ---------------------------------------------------------------------------
# Rules and logic
# ---------------------------------------------------------------------------
from iios.investment.portfolio.recommendation.portfolio_rules import (
    evaluate_risk_overextension,
    evaluate_var_breach,
    evaluate_drawdown_severity,
    evaluate_risk_capacity,
    evaluate_equity_overweight,
    evaluate_equity_underweight,
    evaluate_cash_excess,
    evaluate_cash_deficiency,
    evaluate_international_underweight,
    evaluate_concentration,
    evaluate_insufficient_positions,
    evaluate_sector_concentration,
    evaluate_sharpe_deterioration,
    evaluate_information_ratio_poor,
    evaluate_calmar_deterioration,
    evaluate_construction_quality,
    evaluate_optimization_quality,
    evaluate_rebalance_trigger,
    evaluate_defensive_signal,
    evaluate_hedge_signal,
    evaluate_aggressive_signal,
)
from iios.investment.portfolio.recommendation.recommendation_logic import (
    RecommendationLogic,
)

# ---------------------------------------------------------------------------
# Scoring and confidence
# ---------------------------------------------------------------------------
from iios.investment.portfolio.recommendation.recommendation_score import (
    RecommendationDimensionScore,
    RecommendationScore,
    RecommendationScoreCalculator,
)
from iios.investment.portfolio.recommendation.recommendation_confidence import (
    calculate_confidence,
    intelligence_quality_score,
)

# ---------------------------------------------------------------------------
# Lifecycle and expiration
# ---------------------------------------------------------------------------
from iios.investment.portfolio.recommendation.recommendation_lifecycle import (
    LifecycleManager,
    get_allowed_transitions,
    is_active,
    is_terminal,
    is_valid_transition,
    state_to_status,
)
from iios.investment.portfolio.recommendation.recommendation_expiration import (
    compute_expires_at,
    filter_expired,
    hours_remaining,
    is_expired,
)
from iios.investment.portfolio.recommendation.recommendation_tracker import (
    RecommendationTracker,
)

# ---------------------------------------------------------------------------
# Validation and quality
# ---------------------------------------------------------------------------
from iios.investment.portfolio.recommendation.recommendation_validator import (
    RecValidationReport,
    RecommendationValidator,
    ValidationCheck,
)
from iios.investment.portfolio.recommendation.recommendation_quality import (
    RecommendationQualityAssessor,
    RecommendationQualityReport,
)

# ---------------------------------------------------------------------------
# Health and monitoring
# ---------------------------------------------------------------------------
from iios.investment.portfolio.recommendation.recommendation_health import (
    RecommendationHealthMonitor,
    RecommendationHealthReport,
)
from iios.investment.portfolio.recommendation.recommendation_monitor import (
    RecommendationMonitor,
    RecommendationMonitorReport,
)

# ---------------------------------------------------------------------------
# Main engine
# ---------------------------------------------------------------------------
from iios.investment.portfolio.recommendation.portfolio_recommendation_engine import (
    PortfolioRecommendationEngine,
)

__all__ = [
    # Constants
    "RISK_BUDGET_HIGH_THRESHOLD", "RISK_BUDGET_LOW_THRESHOLD",
    "VAR_CRITICAL_THRESHOLD", "DRAWDOWN_SEVERE_THRESHOLD",
    "EQUITY_OVERWEIGHT_THRESHOLD", "EQUITY_UNDERWEIGHT_THRESHOLD",
    "CASH_HIGH_THRESHOLD", "CASH_LOW_THRESHOLD",
    "INTERNATIONAL_LOW_THRESHOLD", "HHI_CONCENTRATED_THRESHOLD",
    "MIN_EFFECTIVE_POSITIONS", "MAX_SECTOR_CONCENTRATION",
    "SHARPE_POOR_THRESHOLD", "CONSTRUCTION_QUALITY_MIN", "OPTIMIZATION_QUALITY_MIN",
    "MIN_CONFIDENCE_TO_PUBLISH", "MAX_ACTIVE_RECOMMENDATIONS", "REC_COOLDOWN_HOURS",
    "DEFAULT_EXPIRY_HOURS", "CRITICAL_EXPIRY_HOURS", "HIGH_EXPIRY_HOURS",
    "LOW_EXPIRY_HOURS", "NO_ACTION_EXPIRY_HOURS",
    "REC_SCORE_EXCELLENT", "REC_SCORE_GOOD", "REC_SCORE_AVERAGE", "REC_SCORE_BELOW_AVERAGE",
    # Enums
    "RecommendationAction", "RecommendationPriority", "RecommendationRisk",
    "RecommendationStatus", "LifecycleState", "RecommendationGrade",
    "RecommendationLevel", "ValidationStatus", "PolicyType",
    # Core types
    "PortfolioIntelligence", "intelligence_from_any",
    "now_utc", "recommendation_score_to_grade", "recommendation_score_to_level",
    "action_to_category", "priority_to_expiry_hours",
    # Models
    "PortfolioRecommendation", "RecommendationCandidate", "build_recommendation",
    "RecommendationRecord", "RecommendationHistory",
    "PortfolioRecommendationHistory",
    "RecommendationRunMetric", "RecommendationStatisticsSnapshot",
    "PortfolioRecommendationStatistics",
    # Policies
    "InstitutionalPolicy", "PolicyParameters",
    "RecommendationPolicyRegistry",
    # Rules
    "evaluate_risk_overextension", "evaluate_var_breach",
    "evaluate_drawdown_severity", "evaluate_risk_capacity",
    "evaluate_equity_overweight", "evaluate_equity_underweight",
    "evaluate_cash_excess", "evaluate_cash_deficiency",
    "evaluate_international_underweight",
    "evaluate_concentration", "evaluate_insufficient_positions",
    "evaluate_sector_concentration",
    "evaluate_sharpe_deterioration", "evaluate_information_ratio_poor",
    "evaluate_calmar_deterioration",
    "evaluate_construction_quality", "evaluate_optimization_quality",
    "evaluate_rebalance_trigger",
    "evaluate_defensive_signal", "evaluate_hedge_signal", "evaluate_aggressive_signal",
    "RecommendationLogic",
    # Scoring
    "RecommendationDimensionScore", "RecommendationScore", "RecommendationScoreCalculator",
    "calculate_confidence", "intelligence_quality_score",
    # Lifecycle
    "LifecycleManager", "get_allowed_transitions", "is_active", "is_terminal",
    "is_valid_transition", "state_to_status",
    "compute_expires_at", "filter_expired", "hours_remaining", "is_expired",
    "RecommendationTracker",
    # Validation & quality
    "ValidationCheck", "RecValidationReport", "RecommendationValidator",
    "RecommendationQualityAssessor", "RecommendationQualityReport",
    # Health & monitor
    "RecommendationHealthMonitor", "RecommendationHealthReport",
    "RecommendationMonitor", "RecommendationMonitorReport",
    # Engine
    "PortfolioRecommendationEngine",
]
