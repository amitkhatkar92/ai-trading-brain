"""iios/investment/market/volatility/ohlc_estimator.py
OHLC-based volatility estimator.

Combines the overnight (open-to-open) component with the intraday range
component using a variance-weighted blend.  Each per-bar variance
contribution is computed from:
  - overnight_term  = (ln O_i / C_{i-1})^2   → captures gap risk
  - range_term      = (ln H_i / L_i)^2 / (4 * ln 2)   → intraday range
  - close_term      = (2*ln2 - 1) * (ln C_i / O_i)^2  → open-to-close

The result is annualised consistently with the other estimators.
"""
from __future__ import annotations

import math
from typing import TYPE_CHECKING, List, Optional

from iios.investment.market.volatility.models import VolatilityEstimate

if TYPE_CHECKING:
    from iios.investment.market.structure.models import Bar

_4LN2 = 4.0 * math.log(2.0)           # ≈ 2.7726
_CLOSE_COEFF = 2.0 * math.log(2.0) - 1.0  # ≈ 0.3863


class OHLCEstimator:
    """OHLC-based variance estimator blending overnight and intraday components."""

    def __init__(
        self,
        window: int = 20,
        annualization_factor: float = 252.0,
        overnight_weight: float = 0.2,
    ) -> None:
        if window < 2:
            raise ValueError("window must be >= 2")
        if not (0.0 <= overnight_weight <= 1.0):
            raise ValueError("overnight_weight must be in [0, 1]")
        self._window = window
        self._factor = annualization_factor
        self._overnight_w = overnight_weight
        self._intraday_w = 1.0 - overnight_weight

    # ── Protocol interface ─────────────────────────────────────────────────

    @property
    def name(self) -> str:
        return f"ohlc_{self._window}"

    @property
    def required_bars(self) -> int:
        return self._window + 1  # need previous close

    def estimate(self, bars: "List[Bar]") -> Optional[VolatilityEstimate]:
        if len(bars) < self.required_bars:
            return None

        sample = bars[-self.required_bars:]
        variances: List[float] = []

        for i in range(1, len(sample)):
            prev = sample[i - 1]
            curr = sample[i]
            if (
                prev.close <= 0
                or curr.open <= 0
                or curr.high <= 0
                or curr.low <= 0
                or curr.close <= 0
                or curr.high < curr.low
            ):
                continue

            overnight = (math.log(curr.open / prev.close)) ** 2

            hl_log = math.log(curr.high / curr.low)
            intraday_range = (hl_log ** 2) / _4LN2

            co_log = math.log(curr.close / curr.open)
            close_oc = _CLOSE_COEFF * (co_log ** 2)

            daily_var = (
                self._overnight_w * overnight
                + self._intraday_w * (intraday_range - close_oc)
            )
            variances.append(max(0.0, daily_var))

        n = len(variances)
        if n < 2:
            return None

        mean_var = sum(variances) / n
        raw = math.sqrt(mean_var)
        annualized = raw * math.sqrt(self._factor) * 100.0

        confidence = min(1.0, n / self._window)

        return VolatilityEstimate(
            estimator_name=self.name,
            raw_value=raw,
            annualized_pct=annualized,
            window_bars=self._window,
            confidence=confidence,
        )
