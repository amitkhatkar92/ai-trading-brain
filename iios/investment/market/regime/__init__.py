"""iios/investment/market/regime/__init__.py
Public API for the Institutional Market Regime Engine.
"""
from __future__ import annotations

from iios.investment.market.regime.models import (
    RegimeType,
    TransitionType,
    RegimeObservation,
    RegimeSnapshot,
    TransitionEvent,
    StrategyCompatibility,
    regime_type_to_market_regime,
)
from iios.investment.market.regime.regime_state import RegimeState
from iios.investment.market.regime.regime_detector import RegimeDetector
from iios.investment.market.regime.regime_classifier import (
    RegimeClassifier,
    DefaultRegimeClassifier,
    StructureBasedClassifier,
)
from iios.investment.market.regime.regime_history import RegimeHistory
from iios.investment.market.regime.regime_transition import RegimeTransition
from iios.investment.market.regime.transition_detector import TransitionDetector
from iios.investment.market.regime.transition_probability import TransitionProbabilityModel
from iios.investment.market.regime.transition_statistics import TransitionStatistics, RegimeStats
from iios.investment.market.regime.regime_confidence import RegimeConfidenceCalculator
from iios.investment.market.regime.regime_score import RegimeScore, RegimeScorer
from iios.investment.market.regime.confidence_history import ConfidenceHistory
from iios.investment.market.regime.strategy_permissions import StrategyType, REGIME_PERMISSIONS
from iios.investment.market.regime.regime_constraints import (
    RegimeConstraint,
    REGIME_CONSTRAINTS,
    RegimeConstraintEngine,
)
from iios.investment.market.regime.strategy_regime_mapper import StrategyRegimeMapper
from iios.investment.market.regime.market_regime_engine import (
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
