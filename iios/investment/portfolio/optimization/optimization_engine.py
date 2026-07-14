"""iios/investment/portfolio/optimization/optimization_engine.py

Pluggable optimization algorithms.

Each algorithm receives a list of AssetProxy objects (symbol, return proxy,
risk proxy, prior weight) and a set of parameters and returns raw optimized
weights as Dict[str, float].

All math uses the standard library only (math, statistics).
No numpy, no scipy.

Optimization proxy model:
    expected_return_i  = conviction_i          (from PositionAllocation)
    risk_i             = risk_score_i          (from PositionAllocation)
    prior_weight_i     = allocated_weight_i    (from AllocationPlan)

The optimizer does NOT change the set of positions — only their weights.
"""
from __future__ import annotations

import abc
import math
import statistics
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from iios.investment.portfolio.optimization.optimization_types import (
    ConvergenceStatus,
    DEFAULT_CONVERGENCE_TOLERANCE,
    DEFAULT_LEARNING_RATE,
    DEFAULT_MAX_ITERATIONS,
    DEFAULT_RISK_AVERSION,
    OptimizationMethod,
)


# ---------------------------------------------------------------------------
# AssetProxy — minimal representation of one asset for the optimizer
# ---------------------------------------------------------------------------

@dataclass
class AssetProxy:
    """
    One asset's data consumed by the optimizer.
    All fields are pure scalars — no market data, no external I/O.
    """

    symbol:          str   = ""
    expected_return: float = 0.5    # conviction
    risk:            float = 0.5    # risk_score
    confidence:      float = 0.5    # confidence
    prior_weight:    float = 0.0    # allocated_weight from AllocationPlan
    sector:          str   = "unknown"
    industry:        str   = "unknown"
    asset_class:     str   = "equity"


# ---------------------------------------------------------------------------
# Convergence result
# ---------------------------------------------------------------------------

@dataclass
class ConvergenceResult:
    status:             ConvergenceStatus = ConvergenceStatus.ANALYTICAL
    iterations:         int               = 0
    final_gradient_norm:float             = 0.0


# ---------------------------------------------------------------------------
# Abstract base
# ---------------------------------------------------------------------------

class OptimizationAlgorithm(abc.ABC):
    """
    Abstract optimization algorithm.

    Subclasses implement `_compute_weights` which returns a raw weight dict.
    The base class handles normalization and constraint projection.
    """

    @property
    @abc.abstractmethod
    def method(self) -> OptimizationMethod: ...

    def optimize(
        self,
        assets:        List[AssetProxy],
        min_weight:    float              = 0.0,
        max_weight:    float              = 0.25,
        risk_aversion: float              = DEFAULT_RISK_AVERSION,
        max_iter:      int                = DEFAULT_MAX_ITERATIONS,
        tol:           float              = DEFAULT_CONVERGENCE_TOLERANCE,
        lr:            float              = DEFAULT_LEARNING_RATE,
        extra:         Dict[str, Any]     = None,
    ) -> Tuple[Dict[str, float], ConvergenceResult]:
        """
        Returns (weights_dict, convergence_result) where weights_dict maps
        symbol → optimized_weight and sum(weights_dict.values()) ≈ 1.0.
        """
        if not assets:
            return {}, ConvergenceResult(status=ConvergenceStatus.TRIVIAL)

        raw, conv = self._compute_weights(
            assets, min_weight, max_weight, risk_aversion, max_iter, tol, lr,
            extra or {}
        )

        # Normalize to sum = 1
        raw = _normalize(raw, min_weight, max_weight)
        return raw, conv

    @abc.abstractmethod
    def _compute_weights(
        self,
        assets:        List[AssetProxy],
        min_weight:    float,
        max_weight:    float,
        risk_aversion: float,
        max_iter:      int,
        tol:           float,
        lr:            float,
        extra:         Dict[str, Any],
    ) -> Tuple[Dict[str, float], ConvergenceResult]: ...


# ---------------------------------------------------------------------------
# Utility: projection onto weight simplex [min_w, max_w] summing to 1
# ---------------------------------------------------------------------------

def _normalize(
    weights: Dict[str, float],
    min_w:   float,
    max_w:   float,
) -> Dict[str, float]:
    """
    Project weights onto the simplex where each weight is in [min_w, max_w]
    and the sum equals 1.0.  Uses iterative clipping + renormalization.
    """
    syms = list(weights)
    n    = len(syms)
    if n == 0:
        return {}

    w = [max(min_w, min(max_w, weights[s])) for s in syms]

    # Iterative projection: clip then rescale, up to 50 rounds
    for _ in range(50):
        total = sum(w)
        if total <= 0:
            w = [1.0 / n for _ in syms]
            break
        scale   = 1.0 / total
        w       = [x * scale for x in w]
        clamped = False
        for i in range(n):
            if w[i] < min_w:
                w[i]    = min_w
                clamped = True
            elif w[i] > max_w:
                w[i]    = max_w
                clamped = True
        if not clamped:
            break

    total = sum(w)
    if total > 0:
        w = [x / total for x in w]

    return {s: w[i] for i, s in enumerate(syms)}


def _safe_div(num: float, den: float, default: float = 0.0) -> float:
    return num / den if den != 0.0 else default


# ---------------------------------------------------------------------------
# 1. Equal Weight
# ---------------------------------------------------------------------------

class EqualWeightOptimizer(OptimizationAlgorithm):
    """All positions receive equal weight."""

    @property
    def method(self) -> OptimizationMethod:
        return OptimizationMethod.EQUAL_WEIGHT

    def _compute_weights(self, assets, min_w, max_w, risk_av, max_iter, tol, lr, extra):
        n = len(assets)
        w = {a.symbol: 1.0 / n for a in assets}
        return w, ConvergenceResult(status=ConvergenceStatus.ANALYTICAL)


# ---------------------------------------------------------------------------
# 2. Minimum Variance  (diagonal covariance)
# w_i ∝ 1 / σ_i²
# ---------------------------------------------------------------------------

class MinimumVarianceOptimizer(OptimizationAlgorithm):
    """Minimizes portfolio variance assuming diagonal covariance."""

    @property
    def method(self) -> OptimizationMethod:
        return OptimizationMethod.MINIMUM_VARIANCE

    def _compute_weights(self, assets, min_w, max_w, risk_av, max_iter, tol, lr, extra):
        raw: Dict[str, float] = {}
        for a in assets:
            sigma_sq = max(1e-8, a.risk ** 2)
            raw[a.symbol] = 1.0 / sigma_sq
        return raw, ConvergenceResult(status=ConvergenceStatus.ANALYTICAL)


# ---------------------------------------------------------------------------
# 3. Risk Parity / Equal Risk Contribution  (diagonal covariance)
# w_i ∝ 1 / σ_i  — each position contributes equal marginal risk
# ---------------------------------------------------------------------------

class RiskParityOptimizer(OptimizationAlgorithm):
    """Equal risk contribution under diagonal covariance assumption."""

    @property
    def method(self) -> OptimizationMethod:
        return OptimizationMethod.RISK_PARITY

    def _compute_weights(self, assets, min_w, max_w, risk_av, max_iter, tol, lr, extra):
        raw: Dict[str, float] = {}
        for a in assets:
            raw[a.symbol] = _safe_div(1.0, max(1e-8, a.risk), 1.0)
        return raw, ConvergenceResult(status=ConvergenceStatus.ANALYTICAL)


class EqualRiskContributionOptimizer(RiskParityOptimizer):
    @property
    def method(self) -> OptimizationMethod:
        return OptimizationMethod.EQUAL_RISK_CONTRIBUTION


# ---------------------------------------------------------------------------
# 4. Maximum Diversification  (diagonal covariance)
# w_i ∝ σ_i / Σ w_j σ_j  →  analytical: w_i ∝ 1/σ_i (same as risk parity)
# ---------------------------------------------------------------------------

class MaximumDiversificationOptimizer(OptimizationAlgorithm):
    @property
    def method(self) -> OptimizationMethod:
        return OptimizationMethod.MAXIMUM_DIVERSIFICATION

    def _compute_weights(self, assets, min_w, max_w, risk_av, max_iter, tol, lr, extra):
        raw: Dict[str, float] = {}
        for a in assets:
            raw[a.symbol] = _safe_div(1.0, max(1e-8, a.risk), 1.0)
        return raw, ConvergenceResult(status=ConvergenceStatus.ANALYTICAL)


# ---------------------------------------------------------------------------
# 5. Maximum Sharpe  (diagonal covariance)
# w_i ∝ μ_i / σ_i²   (Sharpe-tangency with diagonal Σ)
# ---------------------------------------------------------------------------

class MaximumSharpeOptimizer(OptimizationAlgorithm):
    @property
    def method(self) -> OptimizationMethod:
        return OptimizationMethod.MAXIMUM_SHARPE

    def _compute_weights(self, assets, min_w, max_w, risk_av, max_iter, tol, lr, extra):
        raw: Dict[str, float] = {}
        for a in assets:
            mu       = max(0.0, a.expected_return)
            sigma_sq = max(1e-8, a.risk ** 2)
            raw[a.symbol] = _safe_div(mu, sigma_sq, 0.0)
        # Guard: if all mu are 0, fall back to equal weight
        if all(v == 0.0 for v in raw.values()):
            n = len(assets)
            raw = {a.symbol: 1.0 / n for a in assets}
        return raw, ConvergenceResult(status=ConvergenceStatus.ANALYTICAL)


# ---------------------------------------------------------------------------
# 6. Maximum Sortino  (use downside risk proxy = risk_score²)
# w_i ∝ μ_i / DR_i²   (DR_i = risk_score × confidence as downside proxy)
# ---------------------------------------------------------------------------

class MaximumSortinoOptimizer(OptimizationAlgorithm):
    @property
    def method(self) -> OptimizationMethod:
        return OptimizationMethod.MAXIMUM_SORTINO

    def _compute_weights(self, assets, min_w, max_w, risk_av, max_iter, tol, lr, extra):
        raw: Dict[str, float] = {}
        for a in assets:
            mu          = max(0.0, a.expected_return)
            # Downside risk proxy: risk scaled by (1 - confidence)
            down_risk   = max(1e-8, a.risk * (1.0 - a.confidence + 0.01))
            raw[a.symbol] = _safe_div(mu, down_risk ** 2, 0.0)
        if all(v == 0.0 for v in raw.values()):
            n = len(assets)
            raw = {a.symbol: 1.0 / n for a in assets}
        return raw, ConvergenceResult(status=ConvergenceStatus.ANALYTICAL)


# ---------------------------------------------------------------------------
# 7. Mean-Variance Optimization  (projected gradient ascent)
# Maximize: Σ w_i μ_i  −  λ/2 Σ w_i² σ_i²
# Gradient: μ_i − λ w_i σ_i²
# Analytical solution (unconstrained): w_i* = μ_i / (λ σ_i²)
# We use analytical solution first, then project onto constraint set.
# ---------------------------------------------------------------------------

class MeanVarianceOptimizer(OptimizationAlgorithm):
    @property
    def method(self) -> OptimizationMethod:
        return OptimizationMethod.MEAN_VARIANCE

    def _compute_weights(self, assets, min_w, max_w, risk_av, max_iter, tol, lr, extra):
        lam  = max(0.1, risk_av)
        raw: Dict[str, float] = {}
        for a in assets:
            mu       = max(0.0, a.expected_return)
            sigma_sq = max(1e-8, a.risk ** 2)
            raw[a.symbol] = _safe_div(mu, lam * sigma_sq, 0.0)
        if all(v == 0.0 for v in raw.values()):
            n = len(assets)
            raw = {a.symbol: 1.0 / n for a in assets}
        return raw, ConvergenceResult(status=ConvergenceStatus.ANALYTICAL)


# ---------------------------------------------------------------------------
# 8. Maximum Utility  (CARA utility: w maximizes Σwμ − λ/2 · Σw²σ²)
# Identical to mean-variance with explicit lambda
# ---------------------------------------------------------------------------

class MaximumUtilityOptimizer(MeanVarianceOptimizer):
    @property
    def method(self) -> OptimizationMethod:
        return OptimizationMethod.MAXIMUM_UTILITY


# ---------------------------------------------------------------------------
# 9. Minimum Turnover  (stay as close to prior weights as possible)
# Quadratic penalty on (w - w_prior)
# Optimal: w = w_prior (trivially)
# With bounds: project w_prior onto [min_w, max_w]
# ---------------------------------------------------------------------------

class MinimumTurnoverOptimizer(OptimizationAlgorithm):
    @property
    def method(self) -> OptimizationMethod:
        return OptimizationMethod.MINIMUM_TURNOVER

    def _compute_weights(self, assets, min_w, max_w, risk_av, max_iter, tol, lr, extra):
        raw = {a.symbol: max(0.0, a.prior_weight) for a in assets}
        total = sum(raw.values())
        if total <= 0:
            n = len(assets)
            raw = {a.symbol: 1.0 / n for a in assets}
        return raw, ConvergenceResult(status=ConvergenceStatus.ANALYTICAL)


# ---------------------------------------------------------------------------
# 10. Black-Litterman  (simplified, diagonal Σ)
#
# Prior: w_mkt = prior_weight (from AllocationPlan)
# Equilibrium: π_i = λ σ_i² w_prior_i  (reverse-engineered implied return)
# Views: q_i = conviction_i  (analyst conviction as return view)
# Ω_i = σ²_view = (1 - confidence_i)  (uncertainty about view)
# P = identity (each asset has an absolute view)
#
# BL formula (scalar version per asset with P=I):
# E[R]_BL = π_i + tau σ_i² / (tau σ_i² + omega_i) * (q_i - π_i)
# w_BL_i ∝ E[R]_BL_i / (lambda σ_i²)
# ---------------------------------------------------------------------------

class BlackLittermanOptimizer(OptimizationAlgorithm):
    _TAU: float = 0.05   # Scaling of uncertainty in prior

    @property
    def method(self) -> OptimizationMethod:
        return OptimizationMethod.BLACK_LITTERMAN

    def _compute_weights(self, assets, min_w, max_w, risk_av, max_iter, tol, lr, extra):
        tau = extra.get("tau", self._TAU)
        lam = max(0.1, risk_av)
        raw: Dict[str, float] = {}

        for a in assets:
            sigma_sq = max(1e-8, a.risk ** 2)
            w_prior  = max(0.0, a.prior_weight)

            # Implied equilibrium return
            pi_i     = lam * sigma_sq * w_prior

            # View + uncertainty
            q_i      = a.expected_return
            omega_i  = max(1e-8, 1.0 - a.confidence)

            # BL blended return
            bl_factor = (tau * sigma_sq) / (tau * sigma_sq + omega_i)
            e_r_bl    = pi_i + bl_factor * (q_i - pi_i)

            # BL weight ∝ E[R] / (λ σ²)
            raw[a.symbol] = _safe_div(max(0.0, e_r_bl), lam * sigma_sq, 0.0)

        if all(v == 0.0 for v in raw.values()):
            n = len(assets)
            raw = {a.symbol: 1.0 / n for a in assets}

        return raw, ConvergenceResult(status=ConvergenceStatus.ANALYTICAL)


# ---------------------------------------------------------------------------
# 11. Hierarchical Risk Parity
#
# Step 1 — Cluster by sector (each sector is a cluster)
# Step 2 — Equal weight to each cluster
# Step 3 — Within each cluster, inverse-risk weights
# ---------------------------------------------------------------------------

class HierarchicalRiskParityOptimizer(OptimizationAlgorithm):
    @property
    def method(self) -> OptimizationMethod:
        return OptimizationMethod.HIERARCHICAL_RISK_PARITY

    def _compute_weights(self, assets, min_w, max_w, risk_av, max_iter, tol, lr, extra):
        # Group by sector
        clusters: Dict[str, List[AssetProxy]] = {}
        for a in assets:
            clusters.setdefault(a.sector, []).append(a)

        n_clusters = len(clusters)
        cluster_weight = 1.0 / max(1, n_clusters)

        raw: Dict[str, float] = {}
        for sector, members in clusters.items():
            # Inverse-risk within cluster
            inv_risks   = [_safe_div(1.0, max(1e-8, m.risk), 1.0) for m in members]
            total_inv   = sum(inv_risks)
            for m, inv_r in zip(members, inv_risks):
                frac        = _safe_div(inv_r, total_inv, 1.0 / len(members))
                raw[m.symbol] = cluster_weight * frac

        return raw, ConvergenceResult(status=ConvergenceStatus.ANALYTICAL)


# ---------------------------------------------------------------------------
# 12. Maximum Calmar  (return / max drawdown proxy)
# Proxy: max_drawdown ≈ risk_score² × (1 − confidence)
# w_i ∝ μ_i / drawdown_proxy_i
# ---------------------------------------------------------------------------

class MaximumCalmarOptimizer(OptimizationAlgorithm):
    @property
    def method(self) -> OptimizationMethod:
        return OptimizationMethod.MAXIMUM_CALMAR

    def _compute_weights(self, assets, min_w, max_w, risk_av, max_iter, tol, lr, extra):
        raw: Dict[str, float] = {}
        for a in assets:
            mu       = max(0.0, a.expected_return)
            drawdown = max(1e-8, a.risk ** 2 * (1.0 - a.confidence + 0.01))
            raw[a.symbol] = _safe_div(mu, drawdown, 0.0)
        if all(v == 0.0 for v in raw.values()):
            n = len(assets)
            raw = {a.symbol: 1.0 / n for a in assets}
        return raw, ConvergenceResult(status=ConvergenceStatus.ANALYTICAL)
