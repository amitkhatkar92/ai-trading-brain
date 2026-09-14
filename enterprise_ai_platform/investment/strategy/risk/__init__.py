"""enterprise_ai_platform/investment/strategy/risk/__init__.py
Public API for the Institutional Strategy Risk Engine.

The engine evaluates risk by consuming upstream intelligence from:
  - Strategy Evaluation Intelligence  (evaluation_score, sharpe_ratio, etc.)
  - Strategy Opportunity Intelligence (opportunity_score)
  - Strategy Portfolio Intelligence   (portfolio_weight, portfolio_size)
  - Market Intelligence Integration   (current_regime, market_liquidity)
  - Company Intelligence Integration  (sectors, asset_types)

It does NOT independently evaluate markets or companies.
It does NOT execute trades.
It does NOT generate Buy/Sell/Hold recommendations.
"""
from enterprise_ai_platform.investment.strategy.risk.risk_input import StrategyRiskInput
from enterprise_ai_platform.investment.strategy.risk.risk_statistics import (
    parametric_var,
    parametric_cvar,
    expected_daily_loss,
    expected_weekly_loss,
    expected_monthly_loss,
    vol_risk_score,
    drawdown_risk_score as stat_drawdown_risk_score,
    sharpe_risk_score,
    tail_risk_score,
    regime_mismatch_penalty,
    vol_level_penalty,
    clamp,
)
from enterprise_ai_platform.investment.strategy.risk.market_risk import (
    MarketRiskAnalyzer,
    MarketRiskResult,
)
from enterprise_ai_platform.investment.strategy.risk.execution_risk import (
    ExecutionRiskAnalyzer,
    ExecutionRiskResult,
)
from enterprise_ai_platform.investment.strategy.risk.liquidity_risk import (
    LiquidityRiskAnalyzer,
    LiquidityRiskResult,
)
from enterprise_ai_platform.investment.strategy.risk.model_risk import (
    ModelRiskAnalyzer,
    ModelRiskResult,
)
from enterprise_ai_platform.investment.strategy.risk.risk_analysis import (
    RiskAnalysis,
    RiskAnalysisResult,
)
from enterprise_ai_platform.investment.strategy.risk.drawdown_statistics import (
    calmar_ratio,
    ulcer_index,
    pain_index,
    expected_drawdown,
    max_expected_drawdown,
    recovery_days_estimate,
    recovery_probability,
    drawdown_risk_score as dd_drawdown_risk_score,
)
from enterprise_ai_platform.investment.strategy.risk.drawdown_profile import DrawdownProfile
from enterprise_ai_platform.investment.strategy.risk.recovery_analysis import (
    RecoveryAnalysis,
    RecoveryReport,
    RecoveryCategory,
)
from enterprise_ai_platform.investment.strategy.risk.drawdown_engine import (
    DrawdownEngine,
    DrawdownReport,
)
from enterprise_ai_platform.investment.strategy.risk.stress_scenarios import (
    StressScenario,
    MARKET_CRASH,
    VOLATILITY_SPIKE,
    LIQUIDITY_SHOCK,
    GAP_EVENT,
    CORRELATION_BREAKDOWN,
    EXTREME_TREND,
    EXTREME_RANGE,
    FLASH_CRASH,
    BUILTIN_SCENARIOS,
)
from enterprise_ai_platform.investment.strategy.risk.stress_statistics import (
    stressed_vol,
    stressed_drawdown,
    stressed_expected_loss,
    risk_amplification,
    survival_probability,
    aggregate_stress_score,
    worst_case_loss,
)
from enterprise_ai_platform.investment.strategy.risk.scenario_engine import (
    ScenarioEngine,
    ScenarioResult,
)
from enterprise_ai_platform.investment.strategy.risk.stress_testing import (
    StressTestingEngine,
    StressTestReport,
)
from enterprise_ai_platform.investment.strategy.risk.risk_limits import (
    RiskLimits,
    DEFAULT_LIMITS,
    CONSERVATIVE_LIMITS,
    AGGRESSIVE_LIMITS,
    INSTITUTIONAL_LIMITS,
)
from enterprise_ai_platform.investment.strategy.risk.risk_constraints import (
    RiskConstraints,
    ConstraintCheckResult,
    ConstraintCheck,
    ConstraintStatus,
)
from enterprise_ai_platform.investment.strategy.risk.limit_monitor import (
    LimitMonitor,
    LimitBreachEvent,
)
from enterprise_ai_platform.investment.strategy.risk.risk_policy import (
    RiskPolicy,
    DEFAULT_POLICY,
    CONSERVATIVE_POLICY,
    AGGRESSIVE_POLICY,
    INSTITUTIONAL_POLICY,
)
from enterprise_ai_platform.investment.strategy.risk.risk_score import (
    RiskScore,
    RiskScoreCalculator,
)
from enterprise_ai_platform.investment.strategy.risk.risk_confidence import RiskConfidence
from enterprise_ai_platform.investment.strategy.risk.risk_quality import RiskQuality
from enterprise_ai_platform.investment.strategy.risk.risk_health import (
    RiskHealth,
    RiskHealthStatus,
)
from enterprise_ai_platform.investment.strategy.risk.risk_events import (
    RiskEventBus,
    RiskEvent,
    RiskEventType,
)
from enterprise_ai_platform.investment.strategy.risk.strategy_risk_profile import StrategyRiskProfile
from enterprise_ai_platform.investment.strategy.risk.strategy_risk_snapshot import StrategyRiskSnapshot
from enterprise_ai_platform.investment.strategy.risk.strategy_risk_history import StrategyRiskHistory
from enterprise_ai_platform.investment.strategy.risk.strategy_risk_engine import StrategyRiskEngine

__all__ = [
    # Input
    "StrategyRiskInput",
    # Statistics
    "parametric_var", "parametric_cvar",
    "expected_daily_loss", "expected_weekly_loss", "expected_monthly_loss",
    "vol_risk_score", "stat_drawdown_risk_score", "sharpe_risk_score",
    "tail_risk_score", "regime_mismatch_penalty", "vol_level_penalty", "clamp",
    # Market / Execution / Liquidity / Model risk
    "MarketRiskAnalyzer", "MarketRiskResult",
    "ExecutionRiskAnalyzer", "ExecutionRiskResult",
    "LiquidityRiskAnalyzer", "LiquidityRiskResult",
    "ModelRiskAnalyzer", "ModelRiskResult",
    # Risk analysis orchestrator
    "RiskAnalysis", "RiskAnalysisResult",
    # Drawdown
    "calmar_ratio", "ulcer_index", "pain_index",
    "expected_drawdown", "max_expected_drawdown",
    "recovery_days_estimate", "recovery_probability", "dd_drawdown_risk_score",
    "DrawdownProfile",
    "RecoveryAnalysis", "RecoveryReport", "RecoveryCategory",
    "DrawdownEngine", "DrawdownReport",
    # Stress testing
    "StressScenario",
    "MARKET_CRASH", "VOLATILITY_SPIKE", "LIQUIDITY_SHOCK",
    "GAP_EVENT", "CORRELATION_BREAKDOWN",
    "EXTREME_TREND", "EXTREME_RANGE", "FLASH_CRASH",
    "BUILTIN_SCENARIOS",
    "stressed_vol", "stressed_drawdown", "stressed_expected_loss",
    "risk_amplification", "survival_probability",
    "aggregate_stress_score", "worst_case_loss",
    "ScenarioEngine", "ScenarioResult",
    "StressTestingEngine", "StressTestReport",
    # Risk limits & constraints
    "RiskLimits",
    "DEFAULT_LIMITS", "CONSERVATIVE_LIMITS", "AGGRESSIVE_LIMITS", "INSTITUTIONAL_LIMITS",
    "RiskConstraints", "ConstraintCheckResult", "ConstraintCheck", "ConstraintStatus",
    "LimitMonitor", "LimitBreachEvent",
    # Policy
    "RiskPolicy",
    "DEFAULT_POLICY", "CONSERVATIVE_POLICY", "AGGRESSIVE_POLICY", "INSTITUTIONAL_POLICY",
    # Score & meta
    "RiskScore", "RiskScoreCalculator",
    "RiskConfidence", "RiskQuality",
    "RiskHealth", "RiskHealthStatus",
    # Events
    "RiskEventBus", "RiskEvent", "RiskEventType",
    # Profile / snapshot / history
    "StrategyRiskProfile", "StrategyRiskSnapshot", "StrategyRiskHistory",
    # Main engine
    "StrategyRiskEngine",
]
