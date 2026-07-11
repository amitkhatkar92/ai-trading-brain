"""iios/investment/market/liquidity/liquidity_engine.py
Stateful liquidity analysis engine.
"""
from __future__ import annotations

import logging
from typing import List, Optional, Tuple, TYPE_CHECKING

from iios.investment.market.liquidity.models import (
    VolumeBar, VolumeProfile, ParticipationSnapshot,
    LiquidityProfile,
)
from iios.investment.market.liquidity.liquidity_profile import LiquidityProfileAnalyzer
from iios.investment.market.liquidity.liquidity_score import LiquidityScoreCalculator
from iios.investment.market.liquidity.liquidity_history import LiquidityHistory

if TYPE_CHECKING:
    from iios.investment.market.regime.models import RegimeType

logger = logging.getLogger(__name__)


class LiquidityEngine:
    """Stateful liquidity analysis engine."""

    def __init__(
        self,
        window: int = 20,
        profile_analyzer: Optional[LiquidityProfileAnalyzer] = None,
        score_calculator: Optional[LiquidityScoreCalculator] = None,
        history: Optional[LiquidityHistory] = None,
    ) -> None:
        self._window = window
        self._profile_analyzer = profile_analyzer or LiquidityProfileAnalyzer()
        self._score_calculator = score_calculator or LiquidityScoreCalculator()
        self._history = history or LiquidityHistory(max_size=500)
        self._current_profile: Optional[LiquidityProfile] = None
        self._current_score: float = 0.0
        self._max_historical_volume: float = 0.0

    def update(
        self,
        vbars: List[VolumeBar],
        avg_volume: float,
        participation: ParticipationSnapshot,
        volume_quality: float,
        volume_profile: VolumeProfile,
        regime: Optional["RegimeType"] = None,
    ) -> Tuple[LiquidityProfile, float]:
        """Returns (LiquidityProfile, liquidity_score)."""
        # Track max historical volume for depth calculation
        if vbars:
            latest_vol = vbars[-1].volume
            if latest_vol > self._max_historical_volume:
                self._max_historical_volume = latest_vol

        profile = self._profile_analyzer.analyze(
            vbars, avg_volume, self._max_historical_volume
        )
        score = self._score_calculator.calculate(
            profile, participation, volume_quality, volume_profile, regime
        )

        self._history.record(profile)
        self._current_profile = profile
        self._current_score = score
        return profile, score

    def current_profile(self) -> Optional[LiquidityProfile]:
        return self._current_profile

    def current_score(self) -> float:
        return self._current_score

    def is_liquid(self, threshold: float = 50.0) -> bool:
        return self._current_score >= threshold
