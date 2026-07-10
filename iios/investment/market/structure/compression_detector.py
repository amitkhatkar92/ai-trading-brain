"""iios/investment/market/structure/compression_detector.py
Detect volatility compression and squeezes.
Pure range-based — no Bollinger Bands, no ATR indicator.
"""
from __future__ import annotations

import logging
from typing import List, Optional

from iios.investment.market.structure.models import Bar, ConsolidationState, ConsolidationType

logger = logging.getLogger(__name__)


class CompressionDetector:
    """Detect bar-range compression and volatility squeezes."""

    def __init__(
        self,
        window: int = 10,
        compression_threshold: float = 0.7,
        squeeze_threshold: float = 0.5,
    ) -> None:
        self._window = window
        self._compression_threshold = compression_threshold
        self._squeeze_threshold = squeeze_threshold

    def detect(self, bars: List[Bar]) -> Optional[ConsolidationState]:
        """Return ConsolidationState of COMPRESSION or VOLATILITY_SQUEEZE, or None."""
        if len(bars) < self._window + 2:
            return None

        ratio = self.compression_ratio(bars)

        if ratio > self._compression_threshold:
            return None  # Not compressing

        recent = bars[-self._window :]
        high = max(b.high for b in recent)
        low = min(b.low for b in recent)
        avg_range = sum(b.range for b in recent) / len(recent)
        initial_range = recent[0].range if recent else avg_range
        tightest = min(b.range for b in recent)
        vol_trend = self._volume_trend(recent)

        ctype = (
            ConsolidationType.VOLATILITY_SQUEEZE
            if self.is_squeezing(bars)
            else ConsolidationType.COMPRESSION
        )

        return ConsolidationState(
            consolidation_type=ctype,
            start_index=recent[0].index,
            high_bound=high,
            low_bound=low,
            bar_count=len(recent),
            avg_range=avg_range,
            initial_range=initial_range,
            tightest_range=tightest,
            volume_trend=vol_trend,
            active=True,
        )

    def compression_ratio(self, bars: List[Bar]) -> float:
        """Current avg_range / initial avg_range. <1 = compressing."""
        if len(bars) < self._window + 2:
            return 1.0

        # Compare earliest window vs latest window
        early = bars[: self._window]
        late = bars[-self._window :]
        early_avg = sum(b.range for b in early) / len(early)
        late_avg = sum(b.range for b in late) / len(late)

        if early_avg == 0:
            return 1.0
        return late_avg / early_avg

    def is_squeezing(self, bars: List[Bar]) -> bool:
        """True if both range AND bar-to-bar displacement are below thresholds."""
        if len(bars) < self._window + 2:
            return False

        recent = bars[-self._window :]
        avg_range = sum(b.range for b in recent) / len(recent)

        # Bar-to-bar displacement = |close[i] - close[i-1]|
        displacements = [
            abs(recent[i].close - recent[i - 1].close) for i in range(1, len(recent))
        ]
        avg_displacement = sum(displacements) / len(displacements) if displacements else 0.0

        # Reference: earlier window
        early = bars[: self._window]
        early_avg_range = sum(b.range for b in early) / len(early)
        early_displ = [
            abs(early[i].close - early[i - 1].close) for i in range(1, len(early))
        ]
        early_avg_disp = sum(early_displ) / len(early_displ) if early_displ else 0.0

        if early_avg_range == 0 or early_avg_disp == 0:
            return False

        range_ratio = avg_range / early_avg_range
        disp_ratio = avg_displacement / early_avg_disp if early_avg_disp > 0 else 1.0

        return (
            range_ratio < self._squeeze_threshold
            and disp_ratio < self._squeeze_threshold
        )

    def _volume_trend(self, bars: List[Bar]) -> str:
        if len(bars) < 4:
            return "neutral"
        n = len(bars)
        first_avg = sum(b.volume for b in bars[: n // 2]) / (n // 2)
        second_avg = sum(b.volume for b in bars[n // 2 :]) / (n - n // 2)
        if second_avg > first_avg * 1.2:
            return "increasing"
        if second_avg < first_avg * 0.8:
            return "decreasing"
        return "neutral"
