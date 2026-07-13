"""iios/investment/strategy/evaluation/__init__.py"""
# ── Existing lightweight evaluators (preserved) ──────────────────────────────
from iios.investment.strategy.evaluation.strategy_score import StrategyScore
from iios.investment.strategy.evaluation.strategy_evaluator import StrategyEvaluator
from iios.investment.strategy.evaluation.strategy_ranker import StrategyRanker
from iios.investment.strategy.evaluation.strategy_comparator import StrategyComparator

# ── Shared data types ─────────────────────────────────────────────────────────
from iios.investment.strategy.evaluation.trade import Trade
from iios.investment.strategy.evaluation.equity_curve import EquityCurve, EquityPoint
from iios.investment.strategy.evaluation.evaluation_input import EvaluationInput

# ── Sub-engine results ────────────────────────────────────────────────────────
from iios.investment.strategy.evaluation.performance_metrics import PerformanceMetrics
from iios.investment.strategy.evaluation.performance_history import PerformanceHistory
from iios.investment.strategy.evaluation.risk_evaluation import RiskMetrics
from iios.investment.strategy.evaluation.drawdown_analysis import DrawdownMetrics
from iios.investment.strategy.evaluation.volatility_analysis import VolatilityMetrics
from iios.investment.strategy.evaluation.tail_risk import TailRiskMetrics
from iios.investment.strategy.evaluation.trade_statistics import TradeStatistics
from iios.investment.strategy.evaluation.execution_quality import ExecutionMetrics
from iios.investment.strategy.evaluation.trade_distribution import TradeDistribution
from iios.investment.strategy.evaluation.trade_quality import TradeQualityReport
from iios.investment.strategy.evaluation.walk_forward_analysis import WalkForwardReport
from iios.investment.strategy.evaluation.monte_carlo_analysis import MonteCarloReport
from iios.investment.strategy.evaluation.stress_testing import StressTestReport
from iios.investment.strategy.evaluation.robustness_engine import RobustnessReport
from iios.investment.strategy.evaluation.strategy_explanation import StrategyExplanation
from iios.investment.strategy.evaluation.confidence_score import ConfidenceFactors

# ── Scoring and approval ──────────────────────────────────────────────────────
from iios.investment.strategy.evaluation.evaluation_grade import (
    EvaluationGrade, grade_from_score, grade_label
)
from iios.investment.strategy.evaluation.approval_engine import (
    ApprovalStatus, ApprovalResult, ApprovalCriteria, ApprovalEngine
)
from iios.investment.strategy.evaluation.institutional_score import InstitutionalStrategyScore

# ── Main engine ───────────────────────────────────────────────────────────────
from iios.investment.strategy.evaluation.strategy_evaluation_engine import (
    StrategyEvaluationEngine, EvaluationReport
)

__all__ = [
    # Existing
    "StrategyScore", "StrategyEvaluator", "StrategyRanker", "StrategyComparator",
    # Data types
    "Trade", "EquityCurve", "EquityPoint", "EvaluationInput",
    # Performance
    "PerformanceMetrics", "PerformanceHistory",
    # Risk
    "RiskMetrics", "DrawdownMetrics", "VolatilityMetrics", "TailRiskMetrics",
    # Trade quality
    "TradeStatistics", "ExecutionMetrics", "TradeDistribution", "TradeQualityReport",
    # Robustness
    "WalkForwardReport", "MonteCarloReport", "StressTestReport", "RobustnessReport",
    # Explainability
    "StrategyExplanation",
    # Confidence + scoring
    "ConfidenceFactors", "EvaluationGrade", "grade_from_score", "grade_label",
    "ApprovalStatus", "ApprovalResult", "ApprovalCriteria", "ApprovalEngine",
    "InstitutionalStrategyScore",
    # Engine
    "StrategyEvaluationEngine", "EvaluationReport",
]
