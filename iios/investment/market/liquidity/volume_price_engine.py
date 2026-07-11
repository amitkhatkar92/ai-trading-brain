"""iios/investment/market/liquidity/volume_price_engine.py
Orchestrates effort-result, confirmation, and absorption analysis.
"""
from __future__ import annotations

import logging
from typing import List, Optional

from iios.investment.market.liquidity.models import VolumeBar, EffortResultAnalysis
from iios.investment.market.liquidity.effort_result import EffortResultAnalyzer
from iios.investment.market.liquidity.confirmation_engine import ConfirmationEngine
from iios.investment.market.liquidity.absorption_detector import AbsorptionDetector

logger = logging.getLogger(__name__)


class VolumePriceEngine:
    """
    Orchestrates effort-result, confirmation, and absorption analysis.
    Stateful — maintains rolling window.
    """

    def __init__(
        self,
        window: int = 10,
        effort_result_analyzer: Optional[EffortResultAnalyzer] = None,
        confirmation_engine: Optional[ConfirmationEngine] = None,
        absorption_detector: Optional[AbsorptionDetector] = None,
    ) -> None:
        self._window = window
        self._effort_result_analyzer = effort_result_analyzer or EffortResultAnalyzer()
        self._confirmation_engine = confirmation_engine or ConfirmationEngine()
        self._absorption_detector = absorption_detector or AbsorptionDetector(window=window)
        self._current: Optional[EffortResultAnalysis] = None
        self._current_vbar: Optional[VolumeBar] = None

    def update(
        self,
        vbar: VolumeBar,
        avg_volume: float,
        avg_range: float,
    ) -> EffortResultAnalysis:
        """Process a new bar and return enriched EffortResultAnalysis."""
        er = self._effort_result_analyzer.analyze(vbar, avg_volume, avg_range)
        self._absorption_detector.update(vbar, er)
        self._current = er
        self._current_vbar = vbar
        return er

    def initialize(
        self, vbars: List[VolumeBar], avg_volume: float, avg_range: float
    ) -> EffortResultAnalysis:
        last: Optional[EffortResultAnalysis] = None
        for vbar in vbars:
            last = self.update(vbar, avg_volume, avg_range)
        if last is None:
            raise ValueError("initialize() requires at least one bar")
        return last

    def current_analysis(self) -> Optional[EffortResultAnalysis]:
        return self._current

    def is_in_climax(self) -> bool:
        buy_climax, _ = self._absorption_detector.detect_buying_climax()
        sell_climax, _ = self._absorption_detector.detect_selling_climax()
        return buy_climax or sell_climax

    def is_in_absorption(self) -> bool:
        detected, _ = self._absorption_detector.detect_absorption()
        return detected

    def confirmation_strength(self, relative_volume: float) -> float:
        if self._current_vbar is None:
            return 0.0
        return self._confirmation_engine.confirmation_strength(
            self._current_vbar,
            relative_volume,
        )
