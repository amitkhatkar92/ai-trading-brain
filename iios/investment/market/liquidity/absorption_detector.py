"""iios/investment/market/liquidity/absorption_detector.py
Detects institutional absorption and buying/selling climaxes.
"""
from __future__ import annotations

import logging
from collections import deque
from typing import Tuple

from iios.investment.market.liquidity.models import VolumeBar, EffortResultAnalysis

logger = logging.getLogger(__name__)


class AbsorptionDetector:
    """
    Detects institutional absorption and buying/selling climaxes.
    Maintains a short rolling window for pattern detection.
    """

    def __init__(self, window: int = 5) -> None:
        self._window = window
        self._vbars: deque[VolumeBar] = deque(maxlen=window)
        self._analyses: deque[EffortResultAnalysis] = deque(maxlen=window)

    def update(self, vbar: VolumeBar, er_analysis: EffortResultAnalysis) -> None:
        self._vbars.append(vbar)
        self._analyses.append(er_analysis)

    def detect_buying_climax(self) -> Tuple[bool, float]:
        """
        Returns (detected, confidence).
        Buying climax: 1+ bars with is_climax=True AND initiative_buying=True,
        then close_position drops on next bar.
        """
        analyses = list(self._analyses)
        vbars = list(self._vbars)
        if len(analyses) < 2:
            return False, 0.0

        for i, (a, v) in enumerate(zip(analyses[:-1], vbars[:-1])):
            if a.is_climax and a.initiative_buying:
                # Check if next bar shows weakness (close_position drops)
                next_vbar = vbars[i + 1]
                if next_vbar.close_position < v.close_position:
                    return True, a.climax_score
        return False, 0.0

    def detect_selling_climax(self) -> Tuple[bool, float]:
        """Selling climax: is_climax AND initiative_selling."""
        analyses = list(self._analyses)
        vbars = list(self._vbars)
        if len(analyses) < 2:
            return False, 0.0

        for i, (a, v) in enumerate(zip(analyses[:-1], vbars[:-1])):
            if a.is_climax and a.initiative_selling:
                next_vbar = vbars[i + 1]
                if next_vbar.close_position > v.close_position:
                    return True, a.climax_score
        return False, 0.0

    def detect_absorption(self) -> Tuple[bool, float]:
        """Absorption: is_absorption=True AND 2+ consecutive such bars."""
        analyses = list(self._analyses)
        if len(analyses) < 2:
            return False, 0.0

        consecutive = 0
        max_strength = 0.0
        for a in reversed(analyses):
            if a.is_absorption:
                consecutive += 1
                if a.absorption_strength > max_strength:
                    max_strength = a.absorption_strength
            else:
                break

        if consecutive >= 2:
            return True, max_strength
        return False, 0.0

    def reset(self) -> None:
        self._vbars.clear()
        self._analyses.clear()
