"""iios/investment/portfolio/performance/__init__.py

Portfolio Performance Engine public API.
"""

from iios.investment.portfolio.performance.performance_types import (
    PerformanceGrade,
    PerformanceLevel,
    PerformanceTrend,
    ReturnPeriod,
    AttributionMethod,
    BenchmarkType,
    RunStatus,
    PerformancePosition,
    positions_from_plan,
    portfolio_return,
    portfolio_expected_return,
    portfolio_vol_proxy,
    downside_deviation,
    sharpe_from_positions,
    normalize_sharpe,
    normalize_alpha,
    performance_score_to_grade,
    performance_score_to_level,
)

from iios.investment.portfolio.performance.return_analysis import (
    ReturnAnalysis,
    analyze_returns,
)

from iios.investment.portfolio.performance.return_statistics import (
    ReturnDistribution,
    compute_return_statistics,
)

from iios.investment.portfolio.performance.rolling_returns import (
    RollingReturnWindow,
    RollingReturns,
    compute_rolling_returns,
)

from iios.investment.portfolio.performance.annualized_returns import (
    AnnualizedReturns,
    compute_annualized_returns,
)

from iios.investment.portfolio.performance.benchmark_registry import (
    Benchmark,
    BenchmarkRegistry,
    BENCHMARKS,
)

from iios.investment.portfolio.performance.benchmark_engine import (
    BenchmarkEngine,
    BenchmarkReport,
)

from iios.investment.portfolio.performance.benchmark_comparison import (
    BenchmarkComparison,
    compare_to_benchmark,
)

from iios.investment.portfolio.performance.benchmark_statistics import (
    BenchmarkStatistics,
    BenchmarkStatisticsSnapshot,
)

from iios.investment.portfolio.performance.sector_attribution import (
    SectorAttribution,
    SectorAttributionRecord,
    compute_sector_attribution,
)

from iios.investment.portfolio.performance.security_attribution import (
    SecurityAttribution,
    SecurityAttributionRecord,
    compute_security_attribution,
)

from iios.investment.portfolio.performance.factor_attribution import (
    FactorAttribution,
    FactorAttributionRecord,
    compute_factor_attribution,
)

from iios.investment.portfolio.performance.strategy_attribution import (
    StrategyAttribution,
    StrategyAttributionRecord,
    compute_strategy_attribution,
)

from iios.investment.portfolio.performance.performance_attribution import (
    AttributionResult,
    PortfolioAttributionEngine,
)

from iios.investment.portfolio.performance.risk_adjusted_returns import (
    RiskAdjustedReturns,
    compute_risk_adjusted_returns,
)

from iios.investment.portfolio.performance.performance_ratios import (
    PerformanceRatios,
    compute_all_ratios,
)

from iios.investment.portfolio.performance.ratio_statistics import (
    RatioStatistics,
    RatioStatisticsSnapshot,
)

from iios.investment.portfolio.performance.performance_quality import (
    PerformanceQualityReport,
    PerformanceQualityAssessor,
)

from iios.investment.portfolio.performance.performance_score import (
    PerformanceDimensionScore,
    PerformanceScore,
    PerformanceScoreCalculator,
    PerformanceScoreHistory,
)

from iios.investment.portfolio.performance.performance_health import (
    PerformanceHealthReport,
    PerformanceHealthMonitor,
)

from iios.investment.portfolio.performance.performance_confidence import (
    PerformanceConfidenceReport,
    compute_performance_confidence,
)

from iios.investment.portfolio.performance.performance_forecast import (
    PerformanceForecast,
    forecast_performance,
)

from iios.investment.portfolio.performance.performance_profile import PerformanceProfile

from iios.investment.portfolio.performance.performance_snapshot import (
    PerformanceRecord,
    PerformanceHistory,
)

from iios.investment.portfolio.performance.performance_history import (
    PortfolioPerformanceHistory,
)

from iios.investment.portfolio.performance.performance_statistics import (
    PerformanceRunMetric,
    PerformanceStatisticsSnapshot,
    PortfolioPerformanceStatistics,
)

from iios.investment.portfolio.performance.portfolio_performance_engine import (
    PerformanceIntegrationRefs,
    PortfolioPerformanceEngine,
)

__all__ = [
    # Enums / types
    "PerformanceGrade", "PerformanceLevel", "PerformanceTrend",
    "ReturnPeriod", "AttributionMethod", "BenchmarkType", "RunStatus",
    "PerformancePosition",
    # factories / utilities
    "positions_from_plan", "portfolio_return", "portfolio_expected_return",
    "portfolio_vol_proxy", "downside_deviation", "sharpe_from_positions",
    "normalize_sharpe", "normalize_alpha",
    "performance_score_to_grade", "performance_score_to_level",
    # returns
    "ReturnAnalysis", "analyze_returns",
    "ReturnDistribution", "compute_return_statistics",
    "RollingReturnWindow", "RollingReturns", "compute_rolling_returns",
    "AnnualizedReturns", "compute_annualized_returns",
    # benchmarks
    "Benchmark", "BenchmarkRegistry", "BENCHMARKS",
    "BenchmarkEngine", "BenchmarkReport",
    "BenchmarkComparison", "compare_to_benchmark",
    "BenchmarkStatistics", "BenchmarkStatisticsSnapshot",
    # attribution
    "SectorAttribution", "SectorAttributionRecord", "compute_sector_attribution",
    "SecurityAttribution", "SecurityAttributionRecord", "compute_security_attribution",
    "FactorAttribution", "FactorAttributionRecord", "compute_factor_attribution",
    "StrategyAttribution", "StrategyAttributionRecord", "compute_strategy_attribution",
    "AttributionResult", "PortfolioAttributionEngine",
    # risk-adjusted
    "RiskAdjustedReturns", "compute_risk_adjusted_returns",
    "PerformanceRatios", "compute_all_ratios",
    "RatioStatistics", "RatioStatisticsSnapshot",
    # scoring / quality
    "PerformanceQualityReport", "PerformanceQualityAssessor",
    "PerformanceDimensionScore", "PerformanceScore",
    "PerformanceScoreCalculator", "PerformanceScoreHistory",
    # operational
    "PerformanceHealthReport", "PerformanceHealthMonitor",
    "PerformanceConfidenceReport", "compute_performance_confidence",
    "PerformanceForecast", "forecast_performance",
    # profiles
    "PerformanceProfile",
    "PerformanceRecord", "PerformanceHistory",
    "PortfolioPerformanceHistory",
    "PerformanceRunMetric", "PerformanceStatisticsSnapshot",
    "PortfolioPerformanceStatistics",
    # engine
    "PerformanceIntegrationRefs", "PortfolioPerformanceEngine",
]
