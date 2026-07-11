"""iios/investment/market/volatility/close_to_close_estimator.py
Close-to-close log-return standard-deviation estimator.

Uses successive close prices to compute the sample standard deviation of
log-returns, then annualises by multiplying by sqrt(annualisation_factor).
This is the most widely used baseline volatility estimator.
"""
from __future__ import annotations

import math
from typing import TYPE_CHECKING, List, Optional

from iios.investment.market.volatility.models import VolatilityEstimate

if TYPE_CHECKING:
    from iios.investment.market.structure.models import Bar


class CloseToCloseEstimator:
    """Log-return sample-std estimator using close prices only."""

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
        return f"close_to_close_{self._window}"

    @property
    def required_bars(self) -> int:
        return self._window + 1

    def estimate(self, bars: "List[Bar]") -> Optional[VolatilityEstimate]:
        if len(bars) < self.required_bars:
            return None

        closes = [b.close for b in bars[-self.required_bars:]]

        log_returns: List[float] = []
        for i in range(1, len(closes)):
            prev = closes[i - 1]
            curr = closes[i]
            if prev <= 0 or curr <= 0:
                continue
            log_returns.append(math.log(curr / prev))

        n = len(log_returns)
        if n < 2:
            return None

        mean = sum(log_returns) / n
        variance = sum((r - mean) ** 2 for r in log_returns) / (n - 1)
        std_dev = math.sqrt(variance)
        annualized = std_dev * math.sqrt(self._factor) * 100.0

        confidence = min(1.0, n / self._window)

        return VolatilityEstimate(
            estimator_name=self.name,
            raw_value=std_dev,
            annualized_pct=annualized,
            window_bars=self._window,
            confidence=confidence,
        )
