"""
risk_measurement_engine.py — iios.risk.assessment
===================================================
Core risk measurement: volatility, correlation, drawdown, and
maximum-loss statistics.

C11 Risk Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

import math
import statistics
from typing import Dict, List, Optional, Tuple

from .constants import DEFAULT_EWMA_DECAY, VERSION


class RiskMeasurementEngine:
    """
    Core statistical measurement engine for risk analytics.

    All methods are pure functions of their inputs — no state mutated.
    """

    VERSION: str = VERSION

    # ------------------------------------------------------------------
    # Volatility
    # ------------------------------------------------------------------

    def calculate_annualised_volatility(
        self,
        returns:       List[float],
        trading_days:  int = 252,
    ) -> float:
        """
        Annualised volatility from daily returns.

        σ_annual = σ_daily × √trading_days
        """
        if len(returns) < 2:
            return 0.0
        return statistics.stdev(returns) * math.sqrt(trading_days)

    def calculate_ewma_volatility(
        self,
        returns: List[float],
        decay:   float = DEFAULT_EWMA_DECAY,
        trading_days: int = 252,
    ) -> float:
        """EWMA annualised volatility."""
        if len(returns) < 2:
            return 0.0
        ewma_var = returns[-1] ** 2
        for r in reversed(returns[:-1]):
            ewma_var = decay * ewma_var + (1.0 - decay) * r ** 2
        return math.sqrt(ewma_var) * math.sqrt(trading_days)

    # ------------------------------------------------------------------
    # Correlation
    # ------------------------------------------------------------------

    def calculate_correlation(
        self,
        series_a: List[float],
        series_b: List[float],
    ) -> float:
        """
        Pearson correlation coefficient between two return series.

        Returns 0.0 when either series has fewer than 2 observations or
        has zero variance.
        """
        n = min(len(series_a), len(series_b))
        if n < 2:
            return 0.0
        a = series_a[-n:]
        b = series_b[-n:]
        mean_a = statistics.mean(a)
        mean_b = statistics.mean(b)
        cov    = sum((x - mean_a) * (y - mean_b) for x, y in zip(a, b)) / (n - 1)
        std_a  = statistics.stdev(a)
        std_b  = statistics.stdev(b)
        if std_a == 0 or std_b == 0:
            return 0.0
        return cov / (std_a * std_b)

    def calculate_correlation_matrix(
        self,
        series_dict: Dict[str, List[float]],
    ) -> Dict[Tuple[str, str], float]:
        """
        Calculate pairwise correlations for all series in the dict.

        Returns a dict of (key_i, key_j) → correlation.
        """
        keys = list(series_dict.keys())
        result: Dict[Tuple[str, str], float] = {}
        for i, ki in enumerate(keys):
            for kj in keys[i:]:
                corr = self.calculate_correlation(series_dict[ki], series_dict[kj])
                result[(ki, kj)] = corr
                result[(kj, ki)] = corr
        return result

    # ------------------------------------------------------------------
    # Return statistics
    # ------------------------------------------------------------------

    def calculate_sharpe_ratio(
        self,
        returns:       List[float],
        risk_free_rate: float = 0.05,
        trading_days:   int   = 252,
    ) -> float:
        """
        Annualised Sharpe ratio.

        SR = (μ_annual − r_f) / σ_annual
        """
        if len(returns) < 2:
            return 0.0
        mu_daily  = statistics.mean(returns)
        vol_daily = statistics.stdev(returns)
        if vol_daily == 0:
            return 0.0
        mu_annual  = mu_daily * trading_days
        vol_annual = vol_daily * math.sqrt(trading_days)
        return (mu_annual - risk_free_rate) / vol_annual

    def calculate_sortino_ratio(
        self,
        returns:       List[float],
        risk_free_rate: float = 0.0,
        trading_days:   int   = 252,
    ) -> float:
        """
        Annualised Sortino ratio (using downside deviation).
        """
        if len(returns) < 2:
            return 0.0
        target_return    = risk_free_rate / trading_days
        downside_returns = [r for r in returns if r < target_return]
        if not downside_returns or len(downside_returns) < 2:
            return 0.0
        downside_vol = statistics.stdev(downside_returns) * math.sqrt(trading_days)
        if downside_vol == 0:
            return 0.0
        mu_annual = statistics.mean(returns) * trading_days
        return (mu_annual - risk_free_rate) / downside_vol

    def calculate_calmar_ratio(
        self,
        returns:      List[float],
        max_drawdown: float,
        trading_days: int = 252,
    ) -> float:
        """
        Calmar ratio = annualised return / |max drawdown|.
        """
        if max_drawdown == 0 or not returns:
            return 0.0
        annual_return = statistics.mean(returns) * trading_days
        return annual_return / abs(max_drawdown)

    # ------------------------------------------------------------------
    # Liquidity proxy
    # ------------------------------------------------------------------

    def estimate_liquidity_score(
        self,
        portfolio_value:    float,
        daily_volume_proxy: float,
    ) -> float:
        """
        Estimate liquidity as portfolio-value / daily-volume ratio.

        Score 0.0 (illiquid) → 1.0 (highly liquid).
        """
        if daily_volume_proxy <= 0:
            return 0.0
        ratio = portfolio_value / daily_volume_proxy
        # Penalise if portfolio > 20% of daily volume
        return max(0.0, min(1.0, 1.0 - ratio / 5.0))
