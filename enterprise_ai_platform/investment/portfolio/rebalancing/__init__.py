"""enterprise_ai_platform/investment/portfolio/rebalancing/__init__.py

Public API for the Institutional Portfolio Rebalancing Engine.
"""
from __future__ import annotations

# ---------------------------------------------------------------------------
# Types and constants
# ---------------------------------------------------------------------------
from enterprise_ai_platform.investment.portfolio.rebalancing.rebalancing_types import (
    # Constants
    DRIFT_THRESHOLD_MINOR,
    DRIFT_THRESHOLD_MODERATE,
    DRIFT_THRESHOLD_SIGNIFICANT,
    DRIFT_THRESHOLD_CRITICAL,
    MIN_TRADE_SIZE_PCT,
    MAX_TURNOVER_SINGLE_REBAL,
    MAX_TURNOVER_ANNUAL,
    TRANSACTION_COST_EQUITY,
    TRANSACTION_COST_BOND,
    TRANSACTION_COST_FIXED_INR,
    MARKET_IMPACT_FACTOR,
    MARKET_IMPACT_THRESHOLD,
    TAX_RATE_STCG,
    TAX_RATE_LTCG,
    LTCG_HOLDING_DAYS,
    MIN_BENEFIT_COST_RATIO,
    MIN_DRIFT_REDUCTION_PCT,
    CALENDAR_MONTHLY_DAYS,
    CALENDAR_QUARTERLY_DAYS,
    CALENDAR_ANNUAL_DAYS,
    REBAL_SCORE_EXCELLENT,
    REBAL_SCORE_GOOD,
    REBAL_SCORE_AVERAGE,
    REBAL_SCORE_BELOW_AVERAGE,
    # Enums
    RebalanceTrigger,
    RebalanceStatus,
    DriftLevel,
    TradeSide,
    TradePriority,
    PolicyType,
    ValidationStatus,
    RebalanceGrade,
    RebalanceLevel,
    # Core types
    CurrentPosition,
    TargetPosition,
    # Factories
    current_positions_from_any,
    target_positions_from_any,
    # Utilities
    classify_drift_level,
    rebalance_score_to_grade,
    rebalance_score_to_level,
    aggregate_drift_level,
    portfolio_weighted_risk,
    portfolio_weighted_liquidity,
    now_utc,
)

# ---------------------------------------------------------------------------
# Drift analysis
# ---------------------------------------------------------------------------
from enterprise_ai_platform.investment.portfolio.rebalancing.allocation_drift import (
    AllocationDrift,
    PositionDrift,
    compute_allocation_drift,
)
from enterprise_ai_platform.investment.portfolio.rebalancing.risk_drift import (
    RiskDrift,
    compute_risk_drift,
)
from enterprise_ai_platform.investment.portfolio.rebalancing.exposure_drift import (
    ExposureBucketDrift,
    ExposureDrift,
    compute_exposure_drift,
)
from enterprise_ai_platform.investment.portfolio.rebalancing.drift_statistics import (
    DriftStatistics,
    DriftStatisticsSnapshot,
)
from enterprise_ai_platform.investment.portfolio.rebalancing.drift_engine import (
    DriftEngine,
    DriftReport,
)

# ---------------------------------------------------------------------------
# Policy
# ---------------------------------------------------------------------------
from enterprise_ai_platform.investment.portfolio.rebalancing.rebalance_policy import (
    PolicyEvalResult,
    PolicyParameters,
    RebalancePolicy,
)
from enterprise_ai_platform.investment.portfolio.rebalancing.policy_registry import (
    PolicyRegistry,
)
from enterprise_ai_platform.investment.portfolio.rebalancing.rebalance_rules import (
    evaluate_benefit_cost_rule,
    evaluate_calendar_rule,
    evaluate_cashflow_rule,
    evaluate_risk_rule,
    evaluate_tax_rule,
    evaluate_threshold_rule,
    evaluate_volatility_rule,
)
from enterprise_ai_platform.investment.portfolio.rebalancing.policy_engine import (
    PolicyEngine,
    PolicyEngineResult,
)

# ---------------------------------------------------------------------------
# Trade planning
# ---------------------------------------------------------------------------
from enterprise_ai_platform.investment.portfolio.rebalancing.position_changes import (
    PositionChange,
    compute_position_changes,
)
from enterprise_ai_platform.investment.portfolio.rebalancing.trade_priority import (
    assign_trade_priority,
    prioritize_trades,
)
from enterprise_ai_platform.investment.portfolio.rebalancing.execution_estimator import (
    ExecutionEstimate,
    ExecutionEstimator,
    TradeEstimate,
)
from enterprise_ai_platform.investment.portfolio.rebalancing.trade_planner import (
    TradePlan,
    TradePlanner,
)

# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------
from enterprise_ai_platform.investment.portfolio.rebalancing.validation_report import (
    ValidationCheck,
    ValidationReport,
    build_validation_report,
)
from enterprise_ai_platform.investment.portfolio.rebalancing.policy_validator import (
    PolicyValidator,
)
from enterprise_ai_platform.investment.portfolio.rebalancing.cost_validator import (
    CostValidator,
)
from enterprise_ai_platform.investment.portfolio.rebalancing.rebalance_validator import (
    MasterValidationReport,
    RebalanceValidator,
)

# ---------------------------------------------------------------------------
# Scoring and quality
# ---------------------------------------------------------------------------
from enterprise_ai_platform.investment.portfolio.rebalancing.rebalance_score import (
    RebalanceDimensionScore,
    RebalanceScore,
    RebalanceScoreCalculator,
    RebalanceScoreHistory,
)
from enterprise_ai_platform.investment.portfolio.rebalancing.rebalance_quality import (
    RebalanceQualityAssessor,
    RebalanceQualityReport,
)

# ---------------------------------------------------------------------------
# Plan and history
# ---------------------------------------------------------------------------
from enterprise_ai_platform.investment.portfolio.rebalancing.rebalance_plan import (
    RebalancePlan,
)
from enterprise_ai_platform.investment.portfolio.rebalancing.rebalance_snapshot import (
    RebalanceHistory,
    RebalanceRecord,
)
from enterprise_ai_platform.investment.portfolio.rebalancing.rebalance_history import (
    PortfolioRebalanceHistory,
)
from enterprise_ai_platform.investment.portfolio.rebalancing.rebalance_statistics import (
    PortfolioRebalanceStatistics,
    RebalanceRunMetric,
    RebalanceStatisticsSnapshot,
)

# ---------------------------------------------------------------------------
# Forecast and health
# ---------------------------------------------------------------------------
from enterprise_ai_platform.investment.portfolio.rebalancing.rebalance_forecast import (
    RebalanceForecast,
    forecast_rebalance_benefit,
)
from enterprise_ai_platform.investment.portfolio.rebalancing.rebalance_health import (
    RebalanceHealthMonitor,
    RebalanceHealthReport,
)

# ---------------------------------------------------------------------------
# Main engine
# ---------------------------------------------------------------------------
from enterprise_ai_platform.investment.portfolio.rebalancing.portfolio_rebalancing_engine import (
    PortfolioRebalancingEngine,
    RebalancingIntegrationRefs,
)

__all__ = [
    # Constants
    "DRIFT_THRESHOLD_MINOR", "DRIFT_THRESHOLD_MODERATE",
    "DRIFT_THRESHOLD_SIGNIFICANT", "DRIFT_THRESHOLD_CRITICAL",
    "MIN_TRADE_SIZE_PCT", "MAX_TURNOVER_SINGLE_REBAL", "MAX_TURNOVER_ANNUAL",
    "TRANSACTION_COST_EQUITY", "TRANSACTION_COST_BOND", "TRANSACTION_COST_FIXED_INR",
    "MARKET_IMPACT_FACTOR", "MARKET_IMPACT_THRESHOLD",
    "TAX_RATE_STCG", "TAX_RATE_LTCG", "LTCG_HOLDING_DAYS",
    "MIN_BENEFIT_COST_RATIO", "MIN_DRIFT_REDUCTION_PCT",
    "CALENDAR_MONTHLY_DAYS", "CALENDAR_QUARTERLY_DAYS", "CALENDAR_ANNUAL_DAYS",
    "REBAL_SCORE_EXCELLENT", "REBAL_SCORE_GOOD", "REBAL_SCORE_AVERAGE", "REBAL_SCORE_BELOW_AVERAGE",
    # Enums
    "RebalanceTrigger", "RebalanceStatus", "DriftLevel", "TradeSide",
    "TradePriority", "PolicyType", "ValidationStatus", "RebalanceGrade", "RebalanceLevel",
    # Core types
    "CurrentPosition", "TargetPosition",
    "current_positions_from_any", "target_positions_from_any",
    # Utilities
    "classify_drift_level", "rebalance_score_to_grade", "rebalance_score_to_level",
    "aggregate_drift_level", "portfolio_weighted_risk", "portfolio_weighted_liquidity", "now_utc",
    # Drift
    "AllocationDrift", "PositionDrift", "compute_allocation_drift",
    "RiskDrift", "compute_risk_drift",
    "ExposureBucketDrift", "ExposureDrift", "compute_exposure_drift",
    "DriftStatistics", "DriftStatisticsSnapshot",
    "DriftEngine", "DriftReport",
    # Policy
    "PolicyEvalResult", "PolicyParameters", "RebalancePolicy",
    "PolicyRegistry",
    "evaluate_threshold_rule", "evaluate_calendar_rule", "evaluate_risk_rule",
    "evaluate_volatility_rule", "evaluate_tax_rule", "evaluate_cashflow_rule",
    "evaluate_benefit_cost_rule",
    "PolicyEngine", "PolicyEngineResult",
    # Trade planning
    "PositionChange", "compute_position_changes",
    "assign_trade_priority", "prioritize_trades",
    "TradeEstimate", "ExecutionEstimate", "ExecutionEstimator",
    "TradePlan", "TradePlanner",
    # Validation
    "ValidationCheck", "ValidationReport", "build_validation_report",
    "PolicyValidator", "CostValidator",
    "MasterValidationReport", "RebalanceValidator",
    # Scoring
    "RebalanceDimensionScore", "RebalanceScore", "RebalanceScoreCalculator", "RebalanceScoreHistory",
    "RebalanceQualityAssessor", "RebalanceQualityReport",
    # Plan and history
    "RebalancePlan",
    "RebalanceRecord", "RebalanceHistory",
    "PortfolioRebalanceHistory",
    "RebalanceRunMetric", "RebalanceStatisticsSnapshot", "PortfolioRebalanceStatistics",
    # Forecast and health
    "RebalanceForecast", "forecast_rebalance_benefit",
    "RebalanceHealthMonitor", "RebalanceHealthReport",
    # Main engine
    "PortfolioRebalancingEngine", "RebalancingIntegrationRefs",
]
