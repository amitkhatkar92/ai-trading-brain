"""iios/investment/portfolio/risk/__init__.py"""
# ── Existing exports (preserved for backward compatibility) ────────────────
from iios.investment.portfolio.risk.risk_profile import RiskProfile
from iios.investment.portfolio.risk.risk_statistics import RiskStatistics
from iios.investment.portfolio.risk.risk_registry import RiskRegistry
from iios.investment.portfolio.risk.drawdown_engine import DrawdownAnalysis, DrawdownEngine
from iios.investment.portfolio.risk.risk_analyzer import RiskAnalyzer
from iios.investment.portfolio.risk.risk_engine import RiskEngine

# ── New: Risk types ────────────────────────────────────────────────────────
from iios.investment.portfolio.risk.risk_types import (
    RiskGrade, RiskLevel, RiskStatus, RiskCategory, DrawdownLevel,
    StressTestSeverity, ExposureType, AlertSeverity, TrendDirection, RunStatus,
    RiskPosition, positions_from_plan,
    portfolio_variance, portfolio_volatility,
    var_parametric, cvar_parametric,
    weighted_average, bucket_weights, hhi,
    risk_score_to_level, risk_score_to_grade, drawdown_to_level,
)

# ── New: Risk analysis modules ─────────────────────────────────────────────
from iios.investment.portfolio.risk.market_risk import (
    MarketRiskResult, analyze_market_risk,
)
from iios.investment.portfolio.risk.credit_risk import (
    CreditRiskResult, analyze_credit_risk,
)
from iios.investment.portfolio.risk.liquidity_risk import (
    LiquidityRiskResult, analyze_liquidity_risk,
)
from iios.investment.portfolio.risk.currency_risk import (
    CurrencyRiskResult, analyze_currency_risk,
)
from iios.investment.portfolio.risk.interest_rate_risk import (
    InterestRateRiskResult, analyze_interest_rate_risk,
)
from iios.investment.portfolio.risk.concentration_risk import (
    ConcentrationRiskResult, analyze_concentration_risk,
)
from iios.investment.portfolio.risk.tail_risk import (
    TailRiskResult, analyze_tail_risk,
)

# ── New: Exposure analysis ─────────────────────────────────────────────────
from iios.investment.portfolio.risk.asset_exposure import (
    AssetExposureResult, analyze_asset_exposure,
)
from iios.investment.portfolio.risk.factor_exposure import (
    FactorExposureResult, analyze_factor_exposure,
)
from iios.investment.portfolio.risk.style_exposure import (
    StyleExposureResult, analyze_style_exposure,
)
from iios.investment.portfolio.risk.exposure_statistics import (
    ExposureStatistics, compute_exposure_statistics,
)
from iios.investment.portfolio.risk.portfolio_exposure import (
    PortfolioExposureReport, PortfolioExposureAnalyzer,
)

# ── New: Drawdown ──────────────────────────────────────────────────────────
from iios.investment.portfolio.risk.drawdown_analysis import (
    DrawdownAnalysisResult, analyze_drawdown,
)
from iios.investment.portfolio.risk.drawdown_statistics import (
    DrawdownDistribution, compute_drawdown_distribution,
)
from iios.investment.portfolio.risk.drawdown_forecast import (
    DrawdownForecast, forecast_drawdown,
)
from iios.investment.portfolio.risk.recovery_analysis import (
    RecoveryAnalysis, analyze_recovery,
)

# ── New: Stress testing ────────────────────────────────────────────────────
from iios.investment.portfolio.risk.scenario_library import Scenario, SCENARIOS
from iios.investment.portfolio.risk.scenario_engine import (
    ScenarioResult, ScenarioEngine, PositionStressImpact,
)
from iios.investment.portfolio.risk.stress_testing import (
    StressTestReport, StressTestEngine,
)
from iios.investment.portfolio.risk.stress_statistics import (
    StressStatistics, StressStatisticsSnapshot,
)

# ── New: Scoring, health, quality, confidence ──────────────────────────────
from iios.investment.portfolio.risk.portfolio_risk_score import (
    RiskScore, RiskDimensionScore, RiskScoreCalculator, RiskScoreHistory,
)
from iios.investment.portfolio.risk.risk_health import (
    RiskHealthReport, RiskHealthMonitor,
)
from iios.investment.portfolio.risk.risk_quality import (
    RiskQualityReport, RiskQualityAssessor,
)
from iios.investment.portfolio.risk.risk_confidence import (
    RiskConfidenceReport, compute_risk_confidence,
)

# ── New: Profile and history ───────────────────────────────────────────────
from iios.investment.portfolio.risk.portfolio_risk_profile import PortfolioRiskProfile
from iios.investment.portfolio.risk.portfolio_risk_snapshot import (
    RiskRecord, RiskHistory,
)
from iios.investment.portfolio.risk.portfolio_risk_history import PortfolioRiskHistory
from iios.investment.portfolio.risk.portfolio_risk_statistics import (
    PortfolioRiskStatistics, RiskStatisticsSnapshot, RiskRunMetric,
)

# ── New: Main engine ───────────────────────────────────────────────────────
from iios.investment.portfolio.risk.portfolio_risk_engine import (
    PortfolioRiskEngine, RiskIntegrationRefs, MonitoringReport,
)

__all__ = [
    # Existing
    "RiskProfile", "RiskStatistics", "RiskRegistry",
    "DrawdownAnalysis", "DrawdownEngine",
    "RiskAnalyzer", "RiskEngine",
    # Types
    "RiskGrade", "RiskLevel", "RiskStatus", "RiskCategory", "DrawdownLevel",
    "StressTestSeverity", "ExposureType", "AlertSeverity", "TrendDirection",
    "RunStatus", "RiskPosition", "positions_from_plan",
    "portfolio_variance", "portfolio_volatility",
    "var_parametric", "cvar_parametric",
    "weighted_average", "bucket_weights", "hhi",
    "risk_score_to_level", "risk_score_to_grade", "drawdown_to_level",
    # Risk analysis
    "MarketRiskResult", "analyze_market_risk",
    "CreditRiskResult", "analyze_credit_risk",
    "LiquidityRiskResult", "analyze_liquidity_risk",
    "CurrencyRiskResult", "analyze_currency_risk",
    "InterestRateRiskResult", "analyze_interest_rate_risk",
    "ConcentrationRiskResult", "analyze_concentration_risk",
    "TailRiskResult", "analyze_tail_risk",
    # Exposure
    "AssetExposureResult", "analyze_asset_exposure",
    "FactorExposureResult", "analyze_factor_exposure",
    "StyleExposureResult", "analyze_style_exposure",
    "ExposureStatistics", "compute_exposure_statistics",
    "PortfolioExposureReport", "PortfolioExposureAnalyzer",
    # Drawdown
    "DrawdownAnalysisResult", "analyze_drawdown",
    "DrawdownDistribution", "compute_drawdown_distribution",
    "DrawdownForecast", "forecast_drawdown",
    "RecoveryAnalysis", "analyze_recovery",
    # Stress
    "Scenario", "SCENARIOS",
    "ScenarioResult", "ScenarioEngine", "PositionStressImpact",
    "StressTestReport", "StressTestEngine",
    "StressStatistics", "StressStatisticsSnapshot",
    # Scoring
    "RiskScore", "RiskDimensionScore", "RiskScoreCalculator", "RiskScoreHistory",
    "RiskHealthReport", "RiskHealthMonitor",
    "RiskQualityReport", "RiskQualityAssessor",
    "RiskConfidenceReport", "compute_risk_confidence",
    # Profile & history
    "PortfolioRiskProfile",
    "RiskRecord", "RiskHistory",
    "PortfolioRiskHistory",
    "PortfolioRiskStatistics", "RiskStatisticsSnapshot", "RiskRunMetric",
    # Engine
    "PortfolioRiskEngine", "RiskIntegrationRefs", "MonitoringReport",
]
