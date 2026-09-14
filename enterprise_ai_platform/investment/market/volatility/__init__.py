"""enterprise_ai_platform/investment/market/volatility/__init__.py
Institutional Volatility Intelligence Engine — public API.
"""
from __future__ import annotations

# ── Models ────────────────────────────────────────────────────────────────
from enterprise_ai_platform.investment.market.volatility.models import (
    VolatilityRegimeType,
    VolatilityBehaviour,
    VolatilityEventType,
    RiskLevel,
    StrategyType,
    VolatilityTransitionType,
    VolatilityEstimate,
    VolatilityEvent,
    VolatilityState,
    VolatilityProfile,
    VolatilityRegimeSnapshot,
    BehaviourSnapshot,
    RiskProfile,
    StrategyCompatibility,
    ConfidenceScore,
    VolatilityIntelligenceSnapshot,
)

# ── Estimator framework ────────────────────────────────────────────────────
from enterprise_ai_platform.investment.market.volatility.volatility_estimator import VolatilityEstimator
from enterprise_ai_platform.investment.market.volatility.estimator_registry import EstimatorRegistry
from enterprise_ai_platform.investment.market.volatility.close_to_close_estimator import CloseToCloseEstimator
from enterprise_ai_platform.investment.market.volatility.high_low_estimator import HighLowEstimator
from enterprise_ai_platform.investment.market.volatility.ohlc_estimator import OHLCEstimator

# ── Statistics ────────────────────────────────────────────────────────────
from enterprise_ai_platform.investment.market.volatility.volatility_statistics import VolatilityStatistics

# ── State & profile ───────────────────────────────────────────────────────
from enterprise_ai_platform.investment.market.volatility.volatility_state import VolatilityStateTracker
from enterprise_ai_platform.investment.market.volatility.volatility_profile import VolatilityProfileAnalyzer
from enterprise_ai_platform.investment.market.volatility.volatility_history import VolatilityHistory
from enterprise_ai_platform.investment.market.volatility.volatility_engine import VolatilityEngine

# ── Regime ────────────────────────────────────────────────────────────────
from enterprise_ai_platform.investment.market.volatility.regime_classifier import RegimeClassifier
from enterprise_ai_platform.investment.market.volatility.regime_transition import (
    RegimeTransition,
    RegimeTransitionDetector,
)

# ── Behaviour ─────────────────────────────────────────────────────────────
from enterprise_ai_platform.investment.market.volatility.volatility_expansion import (
    ExpansionState,
    VolatilityExpansionDetector,
)
from enterprise_ai_platform.investment.market.volatility.volatility_compression import (
    CompressionState,
    VolatilityCompressionDetector,
)
from enterprise_ai_platform.investment.market.volatility.volatility_cycles import VolatilityCycleAnalyzer

# ── Risk ──────────────────────────────────────────────────────────────────
from enterprise_ai_platform.investment.market.volatility.risk_score import (
    execution_risk_score,
    gap_risk_score,
    overnight_risk_score,
    portfolio_risk_score,
    market_risk_score,
    strategy_risk_score,
)
from enterprise_ai_platform.investment.market.volatility.risk_profile import RiskProfileBuilder
from enterprise_ai_platform.investment.market.volatility.risk_statistics import RiskStatistics, RiskStats
from enterprise_ai_platform.investment.market.volatility.volatility_risk import VolatilityRiskAssessor

# ── Strategy ──────────────────────────────────────────────────────────────
from enterprise_ai_platform.investment.market.volatility.strategy_permissions import (
    get_permissions,
    get_recommended,
    get_restricted,
)
from enterprise_ai_platform.investment.market.volatility.volatility_constraints import (
    VolatilityConstraints,
    get_constraints,
)
from enterprise_ai_platform.investment.market.volatility.strategy_volatility_mapper import StrategyVolatilityMapper

# ── Confidence ────────────────────────────────────────────────────────────
from enterprise_ai_platform.investment.market.volatility.confidence_score import compute_confidence
from enterprise_ai_platform.investment.market.volatility.volatility_confidence import VolatilityConfidenceCalculator
from enterprise_ai_platform.investment.market.volatility.confidence_history import ConfidenceHistory

# ── Main engine ───────────────────────────────────────────────────────────
from enterprise_ai_platform.investment.market.volatility.volatility_intelligence_engine import (
    InstitutionalVolatilityIntelligenceEngine,
)
