"""iios/investment/market/breadth/divergence_detector.py
Detects breadth divergences — situations where breadth and price context
are moving in opposite directions.
"""
from __future__ import annotations

from collections import deque
from typing import Deque, List, Optional

from iios.investment.market.breadth.models import (
    BreadthData,
    DivergenceSignal,
    DivergenceType,
    MarketHealthSnapshot,
    ParticipationSnapshot,
)


class DivergenceDetector:
    """
    Detects 6 types of divergence.

    For divergences that require external price context (market_regime,
    trend_stage), the detector uses the string values passed from the main
    engine.  When context is unavailable it falls back to internal
    breadth-vs-MA analysis.
    """

    def __init__(
        self,
        short_window: int = 5,
        long_window: int = 20,
        confirm_bars: int = 3,
    ) -> None:
        self._short_w    = short_window
        self._long_w     = long_window
        self._confirm    = confirm_bars

        self._breadth_history: Deque[float]  = deque(maxlen=long_window)
        self._ma20_history: Deque[float]     = deque(maxlen=long_window)
        self._health_history: Deque[float]   = deque(maxlen=long_window)

        # Active divergence counters
        self._bull_bars: int = 0
        self._bear_bars: int = 0
        self._part_bull_bars: int = 0
        self._part_bear_bars: int = 0
        self._lead_bull_bars: int = 0
        self._lead_bear_bars: int = 0

    def detect(
        self,
        breadth: BreadthData,
        participation: ParticipationSnapshot,
        health: MarketHealthSnapshot,
        market_regime: Optional[str] = None,
        trend_stage: Optional[str]   = None,
    ) -> List[DivergenceSignal]:
        self._breadth_history.append(breadth.breadth_pct)
        self._ma20_history.append(participation.above_ma20_pct)
        self._health_history.append(health.health_score)

        signals: List[DivergenceSignal] = []

        if len(self._breadth_history) < self._short_w:
            return signals

        breadth_trend  = self._trend(self._breadth_history)
        ma20_trend     = self._trend(self._ma20_history)
        health_trend_v = self._trend(self._health_history)

        # ── Bullish / Bearish breadth divergence ──────────────────────────
        #   Bullish: breadth improving while context is bearish
        #   Bearish: breadth weakening while context is bullish

        context_bearish = self._is_context_bearish(market_regime, trend_stage)
        context_bullish = self._is_context_bullish(market_regime, trend_stage)

        if breadth_trend > 0.05 and context_bearish:
            self._bull_bars += 1
            self._bear_bars = 0
        elif breadth_trend < -0.05 and context_bullish:
            self._bear_bars += 1
            self._bull_bars = 0
        else:
            self._bull_bars = max(0, self._bull_bars - 1)
            self._bear_bars = max(0, self._bear_bars - 1)

        if self._bull_bars > 0:
            strength = min(1.0, self._bull_bars / self._confirm * 0.8 + 0.2)
            signals.append(DivergenceSignal(
                divergence_type=DivergenceType.BULLISH_BREADTH,
                strength=round(strength, 3),
                bars_active=self._bull_bars,
                description="Breadth improving while market context is bearish",
                confirmed=self._bull_bars >= self._confirm,
            ))

        if self._bear_bars > 0:
            strength = min(1.0, self._bear_bars / self._confirm * 0.8 + 0.2)
            signals.append(DivergenceSignal(
                divergence_type=DivergenceType.BEARISH_BREADTH,
                strength=round(strength, 3),
                bars_active=self._bear_bars,
                description="Breadth weakening while market context is bullish",
                confirmed=self._bear_bars >= self._confirm,
            ))

        # ── Participation divergence ───────────────────────────────────────
        #   Internal: MA20% moving opposite to breadth_pct

        if breadth_trend > 0.05 and ma20_trend < -0.03:
            self._part_bear_bars += 1
            self._part_bull_bars = 0
        elif breadth_trend < -0.05 and ma20_trend > 0.03:
            self._part_bull_bars += 1
            self._part_bear_bars = 0
        else:
            self._part_bull_bars = max(0, self._part_bull_bars - 1)
            self._part_bear_bars = max(0, self._part_bear_bars - 1)

        if self._part_bull_bars > 0:
            strength = min(1.0, 0.3 + abs(ma20_trend) * 2)
            signals.append(DivergenceSignal(
                divergence_type=DivergenceType.PARTICIPATION_BULLISH,
                strength=round(strength, 3),
                bars_active=self._part_bull_bars,
                description="MA participation improving despite weak headline breadth",
                confirmed=self._part_bull_bars >= self._confirm,
            ))

        if self._part_bear_bars > 0:
            strength = min(1.0, 0.3 + abs(ma20_trend) * 2)
            signals.append(DivergenceSignal(
                divergence_type=DivergenceType.PARTICIPATION_BEARISH,
                strength=round(strength, 3),
                bars_active=self._part_bear_bars,
                description="MA participation weakening despite positive headline breadth",
                confirmed=self._part_bear_bars >= self._confirm,
            ))

        # ── Leadership divergence ─────────────────────────────────────────

        if health.leadership_breadth > 0.65 and breadth_trend < -0.05:
            self._lead_bull_bars += 1
            self._lead_bear_bars = 0
        elif health.leadership_breadth < 0.35 and breadth_trend > 0.05:
            self._lead_bear_bars += 1
            self._lead_bull_bars = 0
        else:
            self._lead_bull_bars = max(0, self._lead_bull_bars - 1)
            self._lead_bear_bars = max(0, self._lead_bear_bars - 1)

        if self._lead_bull_bars > 0:
            strength = min(1.0, 0.3 + health.leadership_breadth * 0.5)
            signals.append(DivergenceSignal(
                divergence_type=DivergenceType.LEADERSHIP_BULLISH,
                strength=round(strength, 3),
                bars_active=self._lead_bull_bars,
                description="Leadership broadening despite headline breadth weakness",
                confirmed=self._lead_bull_bars >= self._confirm,
            ))

        if self._lead_bear_bars > 0:
            strength = min(1.0, 0.3 + (1 - health.leadership_breadth) * 0.5)
            signals.append(DivergenceSignal(
                divergence_type=DivergenceType.LEADERSHIP_BEARISH,
                strength=round(strength, 3),
                bars_active=self._lead_bear_bars,
                description="Leadership narrowing despite positive headline breadth",
                confirmed=self._lead_bear_bars >= self._confirm,
            ))

        return signals

    # ── Internal ──────────────────────────────────────────────────────────

    def _trend(self, history: Deque[float]) -> float:
        """Slope proxy: (recent avg - older avg) normalised."""
        vals = list(history)
        n = len(vals)
        if n < 3:
            return 0.0
        half = max(1, n // 2)
        recent = sum(vals[-half:]) / half
        older  = sum(vals[:half]) / half
        baseline = max(older, 1e-8)
        return (recent - older) / baseline

    _BEARISH_KEYWORDS = {"bearish", "bear", "downtrend", "down", "falling",
                          "weak", "declining", "markdown"}
    _BULLISH_KEYWORDS = {"bullish", "bull", "uptrend", "up", "rising",
                          "strong", "advancing", "markup"}

    def _is_context_bearish(
        self, market_regime: Optional[str], trend_stage: Optional[str]
    ) -> bool:
        tokens = set()
        if market_regime:
            tokens.update(market_regime.lower().replace("_", " ").split())
        if trend_stage:
            tokens.update(trend_stage.lower().replace("_", " ").split())
        return bool(tokens & self._BEARISH_KEYWORDS)

    def _is_context_bullish(
        self, market_regime: Optional[str], trend_stage: Optional[str]
    ) -> bool:
        tokens = set()
        if market_regime:
            tokens.update(market_regime.lower().replace("_", " ").split())
        if trend_stage:
            tokens.update(trend_stage.lower().replace("_", " ").split())
        return bool(tokens & self._BULLISH_KEYWORDS)
