"""enterprise_ai_platform/investment/market/regime/__init__.py
Public API for the Institutional Market Regime Engine.
"""
from __future__ import annotations

from enterprise_ai_platform.investment.market.regime.models import (
    RegimeType,
    TransitionType,
    RegimeObservation,
    RegimeSnapshot,
    TransitionEvent,
    StrategyCompatibility,
    regime_type_to_market_regime,
)
from enterprise_ai_platform.investment.market.regime.regime_state import RegimeState
from enterprise_ai_platform.investment.market.regime.regime_detector import RegimeDetector
from enterprise_ai_platform.investment.market.regime.regime_classifier import (
    RegimeClassifier,
    DefaultRegimeClassifier,
    StructureBasedClassifier,
)
from enterprise_ai_platform.investment.market.regime.regime_history import RegimeHistory
from enterprise_ai_platform.investment.market.regime.regime_transition import RegimeTransition
from enterprise_ai_platform.investment.market.regime.transition_detector import TransitionDetector
from enterprise_ai_platform.investment.market.regime.transition_probability import TransitionProbabilityModel
from enterprise_ai_platform.investment.market.regime.transition_statistics import TransitionStatistics, RegimeStats
from enterprise_ai_platform.investment.market.regime.regime_confidence import RegimeConfidenceCalculator
from enterprise_ai_platform.investment.market.regime.regime_score import RegimeScore, RegimeScorer
from enterprise_ai_platform.investment.market.regime.confidence_history import ConfidenceHistory
from enterprise_ai_platform.investment.market.regime.strategy_permissions import StrategyType, REGIME_PERMISSIONS
from enterprise_ai_platform.investment.market.regime.regime_constraints import (
    RegimeConstraint,
    REGIME_CONSTRAINTS,
    RegimeConstraintEngine,
)
from enterprise_ai_platform.investment.market.regime.strategy_regime_mapper import StrategyRegimeMapper
from enterprise_ai_platform.investment.market.regime.market_regime_engine import (
    InstitutionalMarketRegimeEngine,
    MarketRegimeEngine,
)

__all__ = [
    # models
    "RegimeType",
    "TransitionType",
    "RegimeObservation",
    "RegimeSnapshot",
    "TransitionEvent",
    "StrategyCompatibility",
    "regime_type_to_market_regime",
    # state
    "RegimeState",
    # detector
    "RegimeDetector",
    # classifiers
    "RegimeClassifier",
    "DefaultRegimeClassifier",
    "StructureBasedClassifier",
    # history / transition records
    "RegimeHistory",
    "RegimeTransition",
    # transition analysis
    "TransitionDetector",
    "TransitionProbabilityModel",
    "TransitionStatistics",
    "RegimeStats",
    # scoring / confidence
    "RegimeConfidenceCalculator",
    "RegimeScore",
    "RegimeScorer",
    "ConfidenceHistory",
    # strategy integration
    "StrategyType",
    "REGIME_PERMISSIONS",
    "RegimeConstraint",
    "REGIME_CONSTRAINTS",
    "RegimeConstraintEngine",
    "StrategyRegimeMapper",
    # engines
    "InstitutionalMarketRegimeEngine",
    "MarketRegimeEngine",
]
