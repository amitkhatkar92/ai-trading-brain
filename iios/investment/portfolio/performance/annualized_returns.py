"""iios/investment/portfolio/performance/annualized_returns.py

Annualized and CAGR return calculations for multiple horizons.
"""
from __future__ import annotations

import math
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class AnnualizedReturns:
    """Annualized return calculations across multiple time horizons."""

    result_id:        str   = field(default_factory=lambda: str(uuid.uuid4()))
    portfolio_id:     str   = ""

    # CAGR at various horizons
    cagr_1y:          Optional[float] = None
    cagr_3y:          Optional[float] = None
    cagr_5y:          Optional[float] = None
    cagr_10y:         Optional[float] = None
    cagr_since_inception: Optional[float] = None

    # Monthly / quarterly aggregates (using geometric mean)
    monthly_geo_mean:   Optional[float] = None
    quarterly_geo_mean: Optional[float] = None
    annual_geo_mean:    Optional[float] = None

    # Arithmetic mean (for comparison)
    arithmetic_mean:    float          = 0.0

    # Best/worst year
    best_year_return:   Optional[float] = None
    worst_year_return:  Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {k: (round(v, 4) if isinstance(v, float) else v)
                for k, v in {
                    "cagr_1y":             self.cagr_1y,
                    "cagr_3y":             self.cagr_3y,
                    "cagr_5y":             self.cagr_5y,
                    "cagr_since_inception":self.cagr_since_inception,
                    "monthly_geo_mean":    self.monthly_geo_mean,
                    "arithmetic_mean":     self.arithmetic_mean,
                }.items()}


def compute_annualized_returns(
    monthly_returns:     List[float],
    portfolio_id:        str   = "",
    months_per_year:     int   = 12,
    additional_series:   Optional[Dict[str, List[float]]] = None,
) -> AnnualizedReturns:
    """
    Compute CAGR for various horizons from a list of monthly returns.

    ``monthly_returns`` = list of monthly period returns (most recent last).
    """
    n = len(monthly_returns)
    if n == 0:
        return AnnualizedReturns(portfolio_id=portfolio_id)

    # Arithmetic mean
    arith = sum(monthly_returns) / n

    # Geometric mean (monthly → annualized)
    monthly_geo = _geo_mean(monthly_returns)
    quarterly_geo = _geo_mean(_resample_to_quarterly(monthly_returns))
    annual_geo    = _geo_mean(_resample_to_annual(monthly_returns, months_per_year))

    # CAGR at horizons (take last N months)
    def _cagr(months: int) -> Optional[float]:
        if n < months:
            return None
        subset = monthly_returns[-months:]
        total  = _compound(subset)
        return (1.0 + total) ** (12.0 / months) - 1.0

    cagr_1y   = _cagr(12)
    cagr_3y   = _cagr(36)
    cagr_5y   = _cagr(60)
    cagr_10y  = _cagr(120)
    cagr_si   = (1.0 + _compound(monthly_returns)) ** (12.0 / n) - 1.0

    # Best / worst year
    annual_rets = _resample_to_annual(monthly_returns, months_per_year)
    best_y  = max(annual_rets) if annual_rets else None
    worst_y = min(annual_rets) if annual_rets else None

    return AnnualizedReturns(
        portfolio_id         = portfolio_id,
        cagr_1y              = _r(cagr_1y),
        cagr_3y              = _r(cagr_3y),
        cagr_5y              = _r(cagr_5y),
        cagr_10y             = _r(_cagr(120)),
        cagr_since_inception = round(cagr_si, 6),
        monthly_geo_mean     = round(monthly_geo, 6) if monthly_geo is not None else None,
        quarterly_geo_mean   = round(quarterly_geo, 6) if quarterly_geo is not None else None,
        annual_geo_mean      = round(annual_geo, 6) if annual_geo is not None else None,
        arithmetic_mean      = round(arith, 6),
        best_year_return     = _r(best_y),
        worst_year_return    = _r(worst_y),
    )


def _r(v: Optional[float]) -> Optional[float]:
    return round(v, 6) if v is not None else None


def _compound(returns: List[float]) -> float:
    r = 1.0
    for x in returns:
        r *= (1.0 + x)
    return r - 1.0


def _geo_mean(returns: List[float]) -> Optional[float]:
    if not returns:
        return None
    n = len(returns)
    log_sum = sum(math.log(max(1.0 + r, 1e-12)) for r in returns)
    return math.exp(log_sum / n) - 1.0


def _resample_to_quarterly(monthly: List[float]) -> List[float]:
    result = []
    for i in range(0, len(monthly) - 2, 3):
        chunk = monthly[i:i + 3]
        if len(chunk) == 3:
            result.append(_compound(chunk))
    return result


def _resample_to_annual(monthly: List[float], mpy: int = 12) -> List[float]:
    result = []
    for i in range(0, len(monthly) - mpy + 1, mpy):
        chunk = monthly[i:i + mpy]
        if len(chunk) == mpy:
            result.append(_compound(chunk))
    return result
