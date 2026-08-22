"""
risk_sensitivity_engine.py — iios.risk.assessment
===================================================
Sensitivity analysis engine — delta, gamma, and parameter perturbation.

C11 Risk Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from .constants import VERSION
from .exceptions import RiskCalculationError


class SensitivityResult:
    """
    Result of a sensitivity analysis for a single parameter.
    """
    __slots__ = ("parameter", "baseline", "shocked_up", "shocked_down",
                 "delta", "gamma", "shock_size")

    def __init__(
        self,
        parameter:   str,
        baseline:    float,
        shocked_up:  float,
        shocked_down: float,
        shock_size:  float,
    ) -> None:
        self.parameter    = parameter
        self.baseline     = baseline
        self.shocked_up   = shocked_up
        self.shocked_down = shocked_down
        self.shock_size   = shock_size
        # Delta ≈ first derivative
        self.delta = (shocked_up - shocked_down) / (2.0 * shock_size) if shock_size != 0 else 0.0
        # Gamma ≈ second derivative
        self.gamma = (shocked_up - 2.0 * baseline + shocked_down) / (shock_size ** 2) if shock_size != 0 else 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "parameter":   self.parameter,
            "baseline":    self.baseline,
            "shocked_up":  self.shocked_up,
            "shocked_down": self.shocked_down,
            "delta":       self.delta,
            "gamma":       self.gamma,
            "shock_size":  self.shock_size,
        }


class RiskSensitivityEngine:
    """
    Sensitivity analysis engine using parameter perturbation.

    All methods are pure functions — no state mutated.
    """

    VERSION: str = VERSION

    # ------------------------------------------------------------------
    # Parameter perturbation
    # ------------------------------------------------------------------

    def perturb(
        self,
        fn:         Callable[[float], float],
        baseline:   float,
        shock_size: float,
        parameter:  str = "param",
    ) -> SensitivityResult:
        """
        Compute delta and gamma for a scalar function via finite differences.

        Parameters
        ----------
        fn :
            Function mapping a parameter value to a risk metric.
        baseline :
            Baseline parameter value.
        shock_size :
            Absolute size of the shock applied up/down.
        parameter :
            Name label for the parameter.
        """
        if shock_size == 0:
            raise RiskCalculationError(
                "shock_size must be non-zero for sensitivity analysis",
                engine="SensitivityEngine",
            )
        val_base = fn(baseline)
        val_up   = fn(baseline + shock_size)
        val_down = fn(baseline - shock_size)
        return SensitivityResult(
            parameter    = parameter,
            baseline     = val_base,
            shocked_up   = val_up,
            shocked_down = val_down,
            shock_size   = shock_size,
        )

    # ------------------------------------------------------------------
    # Portfolio value sensitivity to equity price move
    # ------------------------------------------------------------------

    def equity_price_sensitivity(
        self,
        positions:       Dict[str, float],
        portfolio_value: float,
        price_shock_pct: float = 0.01,
    ) -> Dict[str, SensitivityResult]:
        """
        Estimate portfolio sensitivity (delta) to ±1% move in each position.

        Returns dict of position_id → SensitivityResult.
        """
        if portfolio_value <= 0:
            return {}
        results = {}
        for pos_id, weight in positions.items():
            pos_value = abs(weight) * portfolio_value
            # Portfolio PnL when position moves ±shock
            def pnl_up(shock: float, w: float = weight, pv: float = portfolio_value) -> float:
                return pv + w * pv * shock
            result = SensitivityResult(
                parameter    = pos_id,
                baseline     = portfolio_value,
                shocked_up   = pnl_up(price_shock_pct),
                shocked_down = pnl_up(-price_shock_pct),
                shock_size   = price_shock_pct,
            )
            results[pos_id] = result
        return results

    # ------------------------------------------------------------------
    # Portfolio sensitivity to volatility change
    # ------------------------------------------------------------------

    def volatility_sensitivity(
        self,
        returns:         List[float],
        portfolio_value: float,
        vol_shock_pct:   float = 0.10,
    ) -> SensitivityResult:
        """
        Sensitivity of VaR to a ±10% change in volatility.
        """
        import statistics as _stats
        if len(returns) < 2:
            return SensitivityResult("volatility", 0.0, 0.0, 0.0, vol_shock_pct)
        import math
        vol       = _stats.stdev(returns)
        mu        = _stats.mean(returns)
        z         = 1.6449  # 95%
        base_var  = portfolio_value * max(0.0, -mu + z * vol)
        up_var    = portfolio_value * max(0.0, -mu + z * vol * (1.0 + vol_shock_pct))
        down_var  = portfolio_value * max(0.0, -mu + z * vol * (1.0 - vol_shock_pct))
        return SensitivityResult(
            parameter    = "volatility",
            baseline     = base_var,
            shocked_up   = up_var,
            shocked_down = down_var,
            shock_size   = vol_shock_pct * vol,
        )
