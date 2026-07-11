"""iios/investment/market/volatility/high_low_estimator.py
Range-based volatility estimator.

Uses the natural log of the high/low ratio per bar, normalised so that its
expected value under a random walk equals the close-to-close standard
deviation.  This estimator is more efficient (lower variance) than the
close-to-close estimator because it uses intraday information.

The normalisation constant sqrt(4 * ln 2) converts the mean absolute
log(H/L) to a standard-deviation-equivalent so that results from this
estimator are directly comparable to the close-to-close estimator.
"""
from __future__ import annotations

import math
from typing import TYPE_CHECKING, List, Optional

from iios.investment.market.volatility.models import VolatilityEstimate

if TYPE_CHECKING:
    from iios.investment.market.structure.models import Bar

_NORM = math.sqrt(4.0 * math.log(2.0))   # ≈ 1.6651


class HighLowEstimator:
    """Range-based volatility estimator (log H/L series)."""

    def __init__(
        self,
        window: int = 20,
        annualization_factor: float = 252.0,
    ) -> None:
        if window < 2:
            raise ValueError("window must be >= 2")
        self._window = window
        self._factor = annualization_factor

    # ── Protocol interface ─────────────────────────────────────────────────

    @property
    def name(self) -> str:
        return f"high_low_{self._window}"

    @property
    def required_bars(self) -> int:
        return self._window

    def estimate(self, bars: "List[Bar]") -> Optional[VolatilityEstimate]:
        if len(bars) < self.required_bars:
            return None

        sample = bars[-self._window:]
        hl_values: List[float] = []
        for b in sample:
            if b.high > 0 and b.low > 0 and b.high >= b.low:
                hl_values.append(math.log(b.high / b.low))

        n = len(hl_values)
        if n < 2:
            return None

        mean_hl = sum(hl_values) / n
        # Normalise to std-dev equivalent
        raw = mean_hl / _NORM
        annualized = raw * math.sqrt(self._factor) * 100.0

        confidence = min(1.0, n / self._window)

        return VolatilityEstimate(
            estimator_name=self.name,
            raw_value=raw,
            annualized_pct=annualized,
            window_bars=self._window,
            confidence=confidence,
        )
