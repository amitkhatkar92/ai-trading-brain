"""iios/investment/strategy/risk/risk_statistics.py
Pure-function math helpers for risk calculations.
No side effects, no state.  All functions accept plain floats/lists.
"""
from __future__ import annotations

import math
from typing import List, Optional, Tuple


# ── clamp / safe ─────────────────────────────────────────────────────────────

def clamp(v: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, v))


def safe_div(num: float, denom: float, default: float = 0.0) -> float:
    return num / denom if abs(denom) > 1e-12 else default


# ── normal distribution approximations ───────────────────────────────────────
# Abramowitz & Stegun approximation (max error < 1.5e-7)

def _norm_pdf(x: float) -> float:
    return math.exp(-0.5 * x * x) / math.sqrt(2.0 * math.pi)


def _norm_cdf(x: float) -> float:
    a1 = 0.254829592; a2 = -0.284496736; a3 = 1.421413741
    a4 = -1.453152027; a5 = 1.061405429; p = 0.3275911
    sign = -1 if x < 0 else 1
    t = 1.0 / (1.0 + p * abs(x))
    y = ((((a5 * t + a4) * t + a3) * t + a2) * t + a1) * t
    return 0.5 * (1.0 + sign * (1.0 - y * math.exp(-x * x)))


# ── volatility helpers ────────────────────────────────────────────────────────

def annualized_to_daily_vol(ann_vol: float) -> float:
    return ann_vol / math.sqrt(252.0)


def annualized_to_weekly_vol(ann_vol: float) -> float:
    return ann_vol / math.sqrt(52.0)


def annualized_to_monthly_vol(ann_vol: float) -> float:
    return ann_vol / math.sqrt(12.0)


# ── Value at Risk (parametric, normal) ────────────────────────────────────────

def parametric_var(
    mu: float, sigma: float, confidence: float = 0.95
) -> float:
    """
    Parametric VaR (loss is positive).
    confidence = 0.95 → 1-day, 95% VaR.
    """
    z = _norm_cdf_inv(confidence)
    return max(0.0, z * sigma - mu)


def _norm_cdf_inv(p: float) -> float:
    """
    Rational approximation for Φ⁻¹(p).
    Peter Acklam's algorithm — max abs error < 1.15e-9.
    """
    if p <= 0.0:
        return float("-inf")
    if p >= 1.0:
        return float("inf")

    a = [-3.969683028665376e+01,  2.209460984245205e+02,
         -2.759285104469687e+02,  1.383577518672690e+02,
         -3.066479806614716e+01,  2.506628277459239e+00]
    b = [-5.447609879822406e+01,  1.615858368580409e+02,
         -1.556989798598866e+02,  6.680131188771972e+01,
         -1.328068155288572e+01]
    c = [-7.784894002430293e-03, -3.223964580411365e-01,
         -2.400758277161838e+00, -2.549732539343734e+00,
          4.374664141464968e+00,  2.938163982698783e+00]
    d = [7.784695709041462e-03,  3.224671290700398e-01,
         2.445134137142996e+00,  3.754408661907416e+00]

    lo = 0.02425
    hi = 1.0 - lo

    if lo <= p <= hi:
        q = p - 0.5
        r = q * q
        return (q * (((((a[0]*r+a[1])*r+a[2])*r+a[3])*r+a[4])*r+a[5]) /
                    (((((b[0]*r+b[1])*r+b[2])*r+b[3])*r+b[4])*r+1.0))
    elif p < lo:
        r = math.sqrt(-2.0 * math.log(p))
        return -(((((c[0]*r+c[1])*r+c[2])*r+c[3])*r+c[4])*r+c[5]) / \
                ((((d[0]*r+d[1])*r+d[2])*r+d[3])*r+1.0)
    else:
        r = math.sqrt(-2.0 * math.log(1.0 - p))
        return -(((((c[0]*r+c[1])*r+c[2])*r+c[3])*r+c[4])*r+c[5]) / \
                ((((d[0]*r+d[1])*r+d[2])*r+d[3])*r+1.0)


def parametric_cvar(
    mu: float, sigma: float, confidence: float = 0.95
) -> float:
    """
    Parametric CVaR / Expected Shortfall.
    CVaR = mu_loss + sigma * phi(Z) / (1-confidence)
    """
    z = _norm_cdf_inv(confidence)
    es = sigma * _norm_pdf(z) / (1.0 - confidence)
    return max(0.0, es - mu)


# ── expected loss helpers ─────────────────────────────────────────────────────

def expected_daily_loss(ann_vol: float, confidence: float = 0.95) -> float:
    """Expected daily loss (as fraction of capital) at given confidence."""
    daily_vol = annualized_to_daily_vol(ann_vol)
    return parametric_var(0.0, daily_vol, confidence)


def expected_weekly_loss(ann_vol: float, confidence: float = 0.95) -> float:
    weekly_vol = annualized_to_weekly_vol(ann_vol)
    return parametric_var(0.0, weekly_vol, confidence)


def expected_monthly_loss(ann_vol: float, confidence: float = 0.95) -> float:
    monthly_vol = annualized_to_monthly_vol(ann_vol)
    return parametric_var(0.0, monthly_vol, confidence)


# ── vol risk score (0–100) ────────────────────────────────────────────────────

def vol_risk_score(ann_vol: float, low: float = 0.08, high: float = 0.50) -> float:
    """0 at vol=low, 100 at vol=high."""
    return clamp(safe_div(ann_vol - low, high - low, 0.0) * 100.0)


def drawdown_risk_score(max_dd: float, ceiling: float = 0.40) -> float:
    """0 at max_dd=0, 100 at max_dd>=ceiling."""
    return clamp(safe_div(max_dd, ceiling, 0.0) * 100.0)


def sharpe_risk_score(sharpe: float) -> float:
    """Inverse Sharpe — higher Sharpe → lower risk."""
    if sharpe >= 2.0:
        return 5.0
    if sharpe >= 1.5:
        return 15.0
    if sharpe >= 1.0:
        return 30.0
    if sharpe >= 0.5:
        return 55.0
    return 80.0


def tail_risk_score(max_dd: float, win_rate: float) -> float:
    """Tail risk proxy from drawdown depth and win-rate."""
    return clamp(max_dd * (1.0 - win_rate) * 400.0)


def regime_mismatch_penalty(is_mismatched: bool) -> float:
    return 45.0 if is_mismatched else 0.0


def vol_level_penalty(level: str) -> float:
    return {"low": 0.0, "normal": 10.0, "high": 35.0, "extreme": 65.0}.get(level, 10.0)
