"""iios/investment/strategy/portfolio/__init__.py
Public API for the Institutional Strategy Portfolio Engine.
"""
from __future__ import annotations

# Core strategy representation
from iios.investment.strategy.portfolio.portfolio_strategy import PortfolioStrategy

# Allocation
from iios.investment.strategy.portfolio.strategy_allocation import (
    StrategyAllocation, AllocationStatus, AllocationMethod
)

# Portfolio model
from iios.investment.strategy.portfolio.strategy_portfolio import (
    StrategyPortfolio, PortfolioType, PortfolioState
)

# Snapshots and history
from iios.investment.strategy.portfolio.portfolio_snapshot import (
    PortfolioSnapshot, AllocationSnapshot
)
from iios.investment.strategy.portfolio.portfolio_history import PortfolioHistory

# Statistics (pure functions)
from iios.investment.strategy.portfolio.portfolio_statistics import (
    project_weights, normalize_weights, jaccard,
    herfindahl_index, effective_n, diversification_ratio,
    weighted_average, gini_coefficient,
)

# Registry
from iios.investment.strategy.portfolio.portfolio_registry import PortfolioRegistry

# Construction
from iios.investment.strategy.portfolio.construction_constraints import (
    ConstructionConstraints,
    DEFAULT_CONSTRAINTS, CONCENTRATED_CONSTRAINTS,
    DIVERSIFIED_CONSTRAINTS, INSTITUTIONAL_CONSTRAINTS,
)
from iios.investment.strategy.portfolio.weight_optimizer import WeightOptimizer
from iios.investment.strategy.portfolio.allocation_engine import (
    AllocationEngine, AllocationResult
)
from iios.investment.strategy.portfolio.portfolio_constructor import (
    PortfolioConstructor, PortfolioConstructionError
)

# Optimization
from iios.investment.strategy.portfolio.optimization_statistics import (
    portfolio_return, portfolio_variance as opt_portfolio_variance,
    concentration_score, coverage_score, target_tracking_error,
)
from iios.investment.strategy.portfolio.constraint_solver import (
    ConstraintSolver, SolverResult
)
from iios.investment.strategy.portfolio.optimization_engine import (
    OptimizationEngine, OptimizationResult
)
from iios.investment.strategy.portfolio.portfolio_optimizer import PortfolioOptimizer

# Diversification
from iios.investment.strategy.portfolio.strategy_correlation import (
    StrategyCorrelation, CorrelationMatrix
)
from iios.investment.strategy.portfolio.overlap_analysis import (
    OverlapAnalysis, OverlapReport
)
from iios.investment.strategy.portfolio.redundancy_detector import (
    RedundancyDetector, RedundancyReport, RedundantPair
)
from iios.investment.strategy.portfolio.diversification_engine import (
    DiversificationEngine, DiversificationReport
)

# Lifecycle and events
from iios.investment.strategy.portfolio.portfolio_events import (
    PortfolioEvent, PortfolioEventType, PortfolioEventBus
)
from iios.investment.strategy.portfolio.portfolio_lifecycle import PortfolioLifecycle

# Monitor
from iios.investment.strategy.portfolio.portfolio_monitor import (
    PortfolioMonitor, PortfolioAlert, AlertSeverity
)

# Rebalancing
from iios.investment.strategy.portfolio.rebalance_policy import (
    RebalancePolicy, RebalanceTrigger,
    DEFAULT_POLICY, AGGRESSIVE_POLICY, CONSERVATIVE_POLICY,
)
from iios.investment.strategy.portfolio.rebalance_scheduler import (
    RebalanceScheduler, RebalanceDecision
)
from iios.investment.strategy.portfolio.rebalance_history import (
    RebalanceHistory, RebalanceRecord, RebalanceStatus
)
from iios.investment.strategy.portfolio.rebalancing_engine import (
    RebalancingEngine, RebalanceResult
)

# Scoring
from iios.investment.strategy.portfolio.portfolio_quality import PortfolioQuality
from iios.investment.strategy.portfolio.portfolio_confidence import PortfolioConfidence
from iios.investment.strategy.portfolio.portfolio_health import (
    PortfolioHealth, HealthStatus
)
from iios.investment.strategy.portfolio.portfolio_score import (
    PortfolioScore, PortfolioScoreCalculator
)

# Main engine
from iios.investment.strategy.portfolio.strategy_portfolio_engine import (
    StrategyPortfolioEngine
)

__all__ = [
    # Core
    "PortfolioStrategy",
    "StrategyAllocation", "AllocationStatus", "AllocationMethod",
    "StrategyPortfolio", "PortfolioType", "PortfolioState",
    # Snapshots
    "PortfolioSnapshot", "AllocationSnapshot",
    "PortfolioHistory",
    # Statistics
    "project_weights", "normalize_weights", "jaccard",
    "herfindahl_index", "effective_n", "diversification_ratio",
    "weighted_average", "gini_coefficient",
    # Registry
    "PortfolioRegistry",
    # Construction
    "ConstructionConstraints",
    "DEFAULT_CONSTRAINTS", "CONCENTRATED_CONSTRAINTS",
    "DIVERSIFIED_CONSTRAINTS", "INSTITUTIONAL_CONSTRAINTS",
    "WeightOptimizer",
    "AllocationEngine", "AllocationResult",
    "PortfolioConstructor", "PortfolioConstructionError",
    # Optimization
    "portfolio_return", "opt_portfolio_variance",
    "concentration_score", "coverage_score", "target_tracking_error",
    "ConstraintSolver", "SolverResult",
    "OptimizationEngine", "OptimizationResult",
    "PortfolioOptimizer",
    # Diversification
    "StrategyCorrelation", "CorrelationMatrix",
    "OverlapAnalysis", "OverlapReport",
    "RedundancyDetector", "RedundancyReport", "RedundantPair",
    "DiversificationEngine", "DiversificationReport",
    # Lifecycle
    "PortfolioEvent", "PortfolioEventType", "PortfolioEventBus",
    "PortfolioLifecycle",
    # Monitor
    "PortfolioMonitor", "PortfolioAlert", "AlertSeverity",
    # Rebalancing
    "RebalancePolicy", "RebalanceTrigger",
    "DEFAULT_POLICY", "AGGRESSIVE_POLICY", "CONSERVATIVE_POLICY",
    "RebalanceScheduler", "RebalanceDecision",
    "RebalanceHistory", "RebalanceRecord", "RebalanceStatus",
    "RebalancingEngine", "RebalanceResult",
    # Scoring
    "PortfolioQuality",
    "PortfolioConfidence",
    "PortfolioHealth", "HealthStatus",
    "PortfolioScore", "PortfolioScoreCalculator",
    # Main engine
    "StrategyPortfolioEngine",
]
