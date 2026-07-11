"""iios/investment/market/liquidity/volume_engine.py
Stateful volume analysis engine.
"""
from __future__ import annotations

import logging
from typing import List, Optional, Tuple, TYPE_CHECKING

from iios.investment.market.liquidity.models import VolumeBar, VolumeLevel, VolumeTrend, VolumeProfile
from iios.investment.market.liquidity.volume_statistics import VolumeStatistics
from iios.investment.market.liquidity.volume_history import VolumeHistory
from iios.investment.market.liquidity.volume_profile import VolumeProfileAnalyzer

if TYPE_CHECKING:
    from iios.investment.market.structure.models import Bar

logger = logging.getLogger(__name__)


class VolumeEngine:
    """
    Stateful volume analysis engine.
    Maintains rolling window and emits VolumeBar + VolumeProfile on each update.
    """

    def __init__(
        self,
        window: int = 20,
        stats: Optional[VolumeStatistics] = None,
        history: Optional[VolumeHistory] = None,
        profile_analyzer: Optional[VolumeProfileAnalyzer] = None,
    ) -> None:
        self._window = window
        self._stats = stats or VolumeStatistics(window=window)
        self._history = history or VolumeHistory(max_size=500)
        self._profile_analyzer = profile_analyzer or VolumeProfileAnalyzer()
        self._current_vbar: Optional[VolumeBar] = None
        self._current_profile: Optional[VolumeProfile] = None

    def update(self, bar: "Bar") -> Tuple[VolumeBar, VolumeProfile]:
        """Process a new bar and return (VolumeBar, VolumeProfile)."""
        # 1. Update stats
        self._stats.update(bar.volume)

        # 2. Build VolumeBar
        price_change = abs(bar.close - bar.open)
        bar_range = bar.range
        safe_range = max(bar_range, 0.001)
        safe_open = max(bar.open, 0.001)

        vbar = VolumeBar(
            index=bar.index,
            timestamp=bar.timestamp,
            volume=bar.volume,
            relative_volume=self._stats.relative(bar.volume),
            normalized_volume=self._stats.normalized(bar.volume),
            price_change=price_change,
            price_change_pct=price_change / safe_open * 100.0,
            bar_range=bar_range,
            is_up=bar.close >= bar.open,
            body_pct=bar.body / safe_range,
            close_position=(bar.close - bar.low) / safe_range,
            volume_level=self._stats.classify(bar.volume),
        )

        # 3. Record in history
        self._history.record(vbar)

        # 4. Build VolumeProfile
        profile = self._profile_analyzer.analyze(
            self._history.recent(self._window), window=self._window
        )

        self._current_vbar = vbar
        self._current_profile = profile
        return vbar, profile

    def initialize(self, bars: List["Bar"]) -> Tuple[VolumeBar, VolumeProfile]:
        """Bulk-initialize from historical bars. Returns last pair."""
        last_pair: Optional[Tuple[VolumeBar, VolumeProfile]] = None
        for bar in bars:
            last_pair = self.update(bar)
        if last_pair is None:
            raise ValueError("initialize() requires at least one bar")
        return last_pair

    def current_profile(self) -> Optional[VolumeProfile]:
        return self._current_profile

    def current_volume_bar(self) -> Optional[VolumeBar]:
        return self._current_vbar

    def classify_current(self) -> VolumeLevel:
        if self._current_vbar is None:
            return VolumeLevel.NONE
        return self._current_vbar.volume_level

    def volume_trend(self) -> VolumeTrend:
        if self._current_profile is None:
            return VolumeTrend.STABLE
        return self._current_profile.volume_trend
