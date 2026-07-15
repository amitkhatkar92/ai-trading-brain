"""iios/investment/portfolio/performance/benchmark_comparison.py

Alpha, beta, tracking error, information ratio, active return.
"""
from __future__ import annotations

import math
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from iios.investment.portfolio.performance.benchmark_registry import Benchmark
from iios.investment.portfolio.performance.performance_types import (
    RISK_FREE_RATE_ANNUAL, PerformancePosition, portfolio_vol_proxy,
)


@dataclass(frozen=True)
class BenchmarkComparison:
    """Benchmark comparison metrics: alpha, beta, TE, IR."""

    result_id:          str       = field(default_factory=lambda: str(uuid.uuid4()))
    portfolio_id:       str       = ""
    benchmark_id:       str       = "nifty50"
    benchmark_name:     str       = "NIFTY 50"

    # Returns
    portfolio_return:   float     = 0.0   # annualized
    benchmark_return:   float     = 0.0   # annualized
    active_return:      float     = 0.0   # alpha (excess over benchmark)
    excess_return:      float     = 0.0   # excess over risk-free

    # Risk-adjusted
    alpha:              float     = 0.0   # Jensen's alpha (annualized)
    beta:               float     = 0.0   # market beta proxy
    tracking_error:     float     = 0.0   # annualized tracking error
    information_ratio:  float     = 0.0   # active_return / tracking_error
    r_squared:          float     = 0.0   # R² of portfolio vs benchmark

    # Assessment
    outperforms:        bool      = False
    warnings:           tuple     = field(default_factory=tuple)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "benchmark_id":      self.benchmark_id,
            "benchmark_name":    self.benchmark_name,
            "portfolio_return":  round(self.portfolio_return, 4),
            "benchmark_return":  round(self.benchmark_return, 4),
            "active_return":     round(self.active_return, 4),
            "alpha":             round(self.alpha, 4),
            "beta":              round(self.beta, 4),
            "tracking_error":    round(self.tracking_error, 4),
            "information_ratio": round(self.information_ratio, 4),
            "outperforms":       self.outperforms,
        }


def compare_to_benchmark(
    positions:        List[PerformancePosition],
    benchmark:        Benchmark,
    portfolio_return: float,
    portfolio_id:     str = "",
    period_years:     float = 1.0,
) -> BenchmarkComparison:
    """
    Compare portfolio vs a benchmark.

    ``portfolio_return`` = annualized portfolio return.
    Beta and tracking error are estimated from vol proxies when
    actual return series are unavailable.
    """
    bmk_ret     = benchmark.expected_return
    active_ret  = portfolio_return - bmk_ret
    excess_ret  = portfolio_return - RISK_FREE_RATE_ANNUAL

    # Vol proxies
    port_vol   = portfolio_vol_proxy(positions)
    bmk_vol    = benchmark.annual_vol_proxy

    # Beta proxy: β = ρ(p,b) × σ_p / σ_b
    # Correlation proxy: equity-heavy portfolios vs equity benchmark ≈ 0.75
    avg_ac = _dominant_asset_class(positions)
    rho = 0.75 if avg_ac in ("equity", "stock") else 0.50
    beta = (rho * port_vol / bmk_vol) if bmk_vol > 1e-10 else 1.0
    beta = round(max(0.0, beta), 4)

    # Jensen's alpha: α = R_p - [R_f + β × (R_m - R_f)]
    expected_by_capm = RISK_FREE_RATE_ANNUAL + beta * (bmk_ret - RISK_FREE_RATE_ANNUAL)
    alpha = portfolio_return - expected_by_capm

    # Tracking error: proxy = |σ_p - σ_b| + |ρ_p_b| corrected
    # TE ≈ sqrt(σ_p² + σ_b² - 2ρσ_pσ_b)
    te = math.sqrt(max(0.0,
        port_vol ** 2 + bmk_vol ** 2 - 2 * rho * port_vol * bmk_vol
    ))
    te = max(te, 0.001)   # floor to avoid division by zero

    # Information ratio
    ir = active_ret / te if te > 1e-10 else 0.0

    # R² proxy: ρ²
    r_sq = rho ** 2

    warnings = []
    if abs(tracking_error := te) > 0.20:
        warnings.append(f"High tracking error {te:.1%} vs {benchmark.name}")
    if beta < 0.3:
        warnings.append(f"Very low beta {beta:.2f} — low market sensitivity")
    elif beta > 1.8:
        warnings.append(f"High beta {beta:.2f} — amplified market sensitivity")

    return BenchmarkComparison(
        portfolio_id       = portfolio_id,
        benchmark_id       = benchmark.benchmark_id,
        benchmark_name     = benchmark.name,
        portfolio_return   = round(portfolio_return, 6),
        benchmark_return   = round(bmk_ret, 6),
        active_return      = round(active_ret, 6),
        excess_return      = round(excess_ret, 6),
        alpha              = round(alpha, 6),
        beta               = beta,
        tracking_error     = round(te, 6),
        information_ratio  = round(ir, 6),
        r_squared          = round(r_sq, 4),
        outperforms        = active_ret > 0,
        warnings           = tuple(warnings),
    )


def _dominant_asset_class(positions: List[PerformancePosition]) -> str:
    if not positions:
        return "equity"
    weights: Dict[str, float] = {}
    for p in positions:
        weights[p.asset_class] = weights.get(p.asset_class, 0.0) + p.weight
    return max(weights, key=weights.__getitem__, default="equity")
