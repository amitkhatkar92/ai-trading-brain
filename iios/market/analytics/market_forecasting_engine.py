"""
market_forecasting_engine.py — iios.market.analytics
=====================================================
Market forecasting sub-engine.

C12 Market Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from .constants import (
    ForecastDirection,
    ForecastHorizon,
    ForecastType,
    MarketRegime,
    TrendDirection,
)
from .market_analytics_context import MarketAnalyticsContext
from .market_analytics_response import ForecastResult, RegimeResult


def _mean_return(returns: List[float]) -> float:
    return sum(returns) / len(returns) if returns else 0.0


def _std_return(returns: List[float]) -> float:
    if len(returns) < 2:
        return 0.0
    mu  = _mean_return(returns)
    var = sum((r - mu) ** 2 for r in returns) / (len(returns) - 1)
    return var ** 0.5


def _returns(prices: List[float]) -> List[float]:
    result = []
    for i in range(1, len(prices)):
        if prices[i - 1] != 0:
            result.append((prices[i] - prices[i - 1]) / prices[i - 1])
    return result


class MarketForecastingEngine:
    """
    Stateless forecasting sub-engine.

    Generates a set of :class:`~.market_analytics_response.ForecastResult`
    objects — one per requested :class:`~.constants.ForecastHorizon` —
    using a simple mean-reversion / trend continuation heuristic.
    """

    _HORIZONS = [ForecastHorizon.DAY, ForecastHorizon.WEEK, ForecastHorizon.MONTH]

    def run(
        self,
        context:      MarketAnalyticsContext,
        request_data: Dict[str, Any],
        regime:       Optional[RegimeResult] = None,
    ) -> Tuple[ForecastResult, ...]:
        index_prices: Dict[str, List[float]] = request_data.get("index_prices", {})

        combined = self._combined(index_prices)
        if not combined:
            return ()

        rets = _returns(combined)
        mu   = _mean_return(rets)
        sig  = _std_return(rets)

        results = []
        for horizon in self._HORIZONS:
            if horizon.value == context.forecast_horizon.value or True:
                results.append(self._generate(
                    combined, rets, mu, sig, horizon, regime
                ))

        return tuple(results)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _generate(
        self,
        prices:  List[float],
        rets:    List[float],
        mu:      float,
        sig:     float,
        horizon: ForecastHorizon,
        regime:  Optional[RegimeResult],
    ) -> ForecastResult:
        from .constants import FORECAST_HORIZON_BARS
        bars = FORECAST_HORIZON_BARS.get(horizon, 1)

        current = prices[-1]
        # Expected return scaled by horizon
        exp_ret = mu * bars

        # Bias from regime
        if regime:
            bias_map = {
                MarketRegime.STRONG_BULL: 0.005,
                MarketRegime.BULL:        0.002,
                MarketRegime.NEUTRAL:     0.0,
                MarketRegime.BEAR:       -0.002,
                MarketRegime.STRONG_BEAR:-0.005,
                MarketRegime.UNKNOWN:     0.0,
            }
            exp_ret += bias_map.get(regime.regime, 0.0) * bars

        sigma_range  = sig * (bars ** 0.5) * 1.645
        upside  = current * (1.0 + exp_ret + sigma_range)
        downside = max(0.0, current * (1.0 + exp_ret - sigma_range))

        confidence = min(0.90, max(0.30,
            0.65 + (regime.confidence * 0.25 if regime else 0.0)
        ))

        if exp_ret > 0.002:
            direction = ForecastDirection.BULLISH
        elif exp_ret < -0.002:
            direction = ForecastDirection.BEARISH
        else:
            direction = ForecastDirection.NEUTRAL

        return ForecastResult(
            forecast_type   = ForecastType.TREND_CONTINUATION,
            horizon         = horizon,
            direction       = direction,
            confidence      = confidence,
            expected_return = exp_ret,
            upside_target   = upside,
            downside_target = downside,
            rationale       = (
                f"Horizon {horizon.value}: exp_ret={exp_ret:.3f}, "
                f"range=[{downside:.1f}, {upside:.1f}]"
            ),
        )

    @staticmethod
    def _combined(index_prices: Dict[str, List[float]]) -> List[float]:
        series = [v for v in index_prices.values() if v]
        if not series:
            return []
        min_len = min(len(s) for s in series)
        trimmed = [s[-min_len:] for s in series]
        return [sum(bar) / len(bar) for bar in zip(*trimmed)]
