"""iios/investment/market/regime/regime_classifier.py
Abstract base class and default rule-based regime classifier.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Optional, TYPE_CHECKING

from iios.investment.market.market_constants import (
    BreadthCondition,
    MarketRegime,
    TrendDirection,
    VolatilityLevel,
)
from iios.investment.market.market_state.market_snapshot import MarketSnapshot

if TYPE_CHECKING:
    pass


class RegimeClassifier(ABC):
    """Pluggable regime classifier interface."""

    @property
    @abstractmethod
    def classifier_id(self) -> str: ...

    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    def classify(
        self,
        snapshot: MarketSnapshot,
        history:  list[MarketSnapshot],
    ) -> tuple[MarketRegime, float]:
        """Return (regime, confidence ∈ [0, 1])."""
        ...

    def to_dict(self) -> dict[str, Any]:
        return {"classifier_id": self.classifier_id, "name": self.name}


class DefaultRegimeClassifier(RegimeClassifier):
    """
    Deterministic rule-based classifier.

    Priority rules (highest first):
    1. CRISIS          — extreme volatility + down trend + very_narrow breadth
    2. BEAR            — down trend + narrow/very_narrow breadth
    3. BULL            — up trend + broad/very_broad breadth
    4. RECOVERY        — up trend + moderate breadth
    5. HIGH_VOLATILITY — extreme or high volatility
    6. LOW_VOLATILITY  — very_low volatility
    7. EXPANSION       — up trend + low volatility
    8. SIDEWAYS        — sideways trend
    9. CONTRACTION     — down trend (residual)
    10. UNKNOWN        — fallback
    """

    @property
    def classifier_id(self) -> str:
        return "default"

    @property
    def name(self) -> str:
        return "Default Rule-Based Regime Classifier"

    def classify(
        self,
        snapshot: MarketSnapshot,
        history:  list[MarketSnapshot],
    ) -> tuple[MarketRegime, float]:
        vol   = snapshot.volatility
        trend = snapshot.trend
        brd   = snapshot.breadth

        # 1 — Crisis
        if (
            vol   == VolatilityLevel.EXTREME
            and trend == TrendDirection.DOWN
            and brd   == BreadthCondition.VERY_NARROW
        ):
            return MarketRegime.CRISIS, 0.92

        # 2 — Bear
        if trend == TrendDirection.DOWN and brd in (
            BreadthCondition.NARROW, BreadthCondition.VERY_NARROW
        ):
            return MarketRegime.BEAR, 0.85

        # 3 — Bull
        if trend == TrendDirection.UP and brd in (
            BreadthCondition.BROAD, BreadthCondition.VERY_BROAD
        ):
            return MarketRegime.BULL, 0.85

        # 4 — Recovery
        if trend == TrendDirection.UP and brd == BreadthCondition.MODERATE:
            return MarketRegime.RECOVERY, 0.70

        # 5 — High volatility
        if vol in (VolatilityLevel.EXTREME, VolatilityLevel.HIGH):
            return MarketRegime.HIGH_VOLATILITY, 0.75

        # 6 — Low volatility
        if vol == VolatilityLevel.VERY_LOW:
            return MarketRegime.LOW_VOLATILITY, 0.75

        # 7 — Expansion
        if trend == TrendDirection.UP and vol == VolatilityLevel.LOW:
            return MarketRegime.EXPANSION, 0.65

        # 8 — Sideways
        if trend == TrendDirection.SIDEWAYS:
            return MarketRegime.SIDEWAYS, 0.70

        # 9 — Contraction
        if trend == TrendDirection.DOWN:
            return MarketRegime.CONTRACTION, 0.65

        return MarketRegime.UNKNOWN, 0.30


class StructureBasedClassifier(RegimeClassifier):
    """
    Classifier that uses MarketStructureSnapshot for richer classification.
    Delegates to RegimeDetector internally.

    Converts RegimeType → MarketRegime for compatibility with RegimeClassifier interface.
    """

    @property
    def classifier_id(self) -> str:
        return "structure_based"

    @property
    def name(self) -> str:
        return "Structure-Based Regime Classifier"

    def __init__(self) -> None:
        from iios.investment.market.regime.regime_detector import RegimeDetector
        self._detector = RegimeDetector()

    def classify(
        self,
        snapshot: "MarketSnapshot",
        history: list["MarketSnapshot"],
    ) -> tuple[MarketRegime, float]:
        """Falls back to DefaultRegimeClassifier (no structure snapshot available)."""
        return DefaultRegimeClassifier().classify(snapshot, history)

    def classify_from_structure(
        self,
        structure_snapshot: "Any",
        market_snapshot: "Any | None" = None,
    ) -> tuple[MarketRegime, float, "Any"]:
        """Primary method: returns (MarketRegime, confidence, RegimeType)."""
        from iios.investment.market.regime.models import regime_type_to_market_regime
        obs = self._detector.observe(structure_snapshot, market_snapshot)
        primary, secondary, confidence = self._detector.detect(obs)
        return regime_type_to_market_regime(primary), confidence, primary
