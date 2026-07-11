"""iios/investment/market/volatility/__init__.py
Institutional Volatility Intelligence Engine — public API.
"""
from __future__ import annotations

# ── Models ────────────────────────────────────────────────────────────────
from iios.investment.market.volatility.models import (
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
from iios.investment.market.volatility.volatility_estimator import VolatilityEstimator
from iios.investment.market.volatility.estimator_registry import EstimatorRegistry
from iios.investment.market.volatility.close_to_close_estimator import CloseToCloseEstimator
from iios.investment.market.volatility.high_low_estimator import HighLowEstimator
from iios.investment.market.volatility.ohlc_estimator import OHLCEstimator

# ── Statistics ────────────────────────────────────────────────────────────
from iios.investment.market.volatility.volatility_statistics import VolatilityStatistics

# ── State & profile ───────────────────────────────────────────────────────
from iios.investment.market.volatility.volatility_state import VolatilityStateTracker
from iios.investment.market.volatility.volatility_profile import VolatilityProfileAnalyzer
from iios.investment.market.volatility.volatility_history import VolatilityHistory
from iios.investment.market.volatility.volatility_engine import VolatilityEngine

# ── Regime ────────────────────────────────────────────────────────────────
from iios.investment.market.volatility.regime_classifier import RegimeClassifier
from iios.investment.market.volatility.regime_transition import (
    RegimeTransition,
    RegimeTransitionDetector,
)

# ── Behaviour ─────────────────────────────────────────────────────────────
from iios.investment.market.volatility.volatility_expansion import (
    ExpansionState,
    VolatilityExpansionDetector,
)
from iios.investment.market.volatility.volatility_compression import (
    CompressionState,
    VolatilityCompressionDetector,
)
from iios.investment.market.volatility.volatility_cycles import VolatilityCycleAnalyzer

# ── Risk ──────────────────────────────────────────────────────────────────
from iios.investment.market.volatility.risk_score import (
    execution_risk_score,
    gap_risk_score,
    overnight_risk_score,
    portfolio_risk_score,
    market_risk_score,
    strategy_risk_score,
)
from iios.investment.market.volatility.risk_profile import RiskProfileBuilder
from iios.investment.market.volatility.risk_statistics import RiskStatistics, RiskStats
from iios.investment.market.volatility.volatility_risk import VolatilityRiskAssessor

# ── Strategy ──────────────────────────────────────────────────────────────
from iios.investment.market.volatility.strategy_permissions import (
    get_permissions,
    get_recommended,
    get_restricted,
)
from iios.investment.market.volatility.volatility_constraints import (
    VolatilityConstraints,
    get_constraints,
)
from iios.investment.market.volatility.strategy_volatility_mapper import StrategyVolatilityMapper

# ── Confidence ────────────────────────────────────────────────────────────
from iios.investment.market.volatility.confidence_score import compute_confidence
from iios.investment.market.volatility.volatility_confidence import VolatilityConfidenceCalculator
from iios.investment.market.volatility.confidence_history import ConfidenceHistory

# ── Main engine ───────────────────────────────────────────────────────────
from iios.investment.market.volatility.volatility_intelligence_engine import (
    InstitutionalVolatilityIntelligenceEngine,
)
