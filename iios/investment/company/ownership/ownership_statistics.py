"""iios/investment/company/ownership/ownership_statistics.py
Pure statistical scoring functions for the Ownership Intelligence Engine.
All inputs are safe (None-tolerant). All outputs are 0-100 floats.
Risk-oriented scores use HIGHER = MORE RISKY convention.
"""
from __future__ import annotations

import math
import statistics
from typing import Dict, Optional, Sequence


# ── Utilities ─────────────────────────────────────────────────────────────────

def clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, value))


def safe_mean(values: Sequence[Optional[float]]) -> Optional[float]:
    clean = [v for v in values if v is not None]
    return statistics.mean(clean) if clean else None


def pct_to_100(v: Optional[float]) -> Optional[float]:
    """Convert fractional (0-1) or already 0-100 to 0-100 range."""
    if v is None:
        return None
    return v * 100.0 if v <= 1.0 else float(v)


# ── Promoter / Insider Holding Scores ────────────────────────────────────────

def score_promoter_holding(pct: Optional[float]) -> float:
    """
    Score promoter holding percentage.
    Optimal: 40-65% (strong alignment without minority squeeze risk).
    Too low (<20%) → weak alignment; too high (>75%) → minority risk.
    """
    if pct is None:
        return 35.0  # insufficient data penalty
    p = pct_to_100(pct)
    assert p is not None
    if p < 0:
        return 0.0
    if p < 5:
        return 5.0
    if p < 20:
        # 5-25 → 5-40 (weak alignment, low conviction)
        return 5.0 + (p - 5) / 15 * 35
    if p < 40:
        # 20-40 → 40-80 (building alignment)
        return 40.0 + (p - 20) / 20 * 40
    if p <= 65:
        # 40-65 → 80-100 (optimal zone)
        return 80.0 + (p - 40) / 25 * 20
    if p <= 75:
        # 65-75 → 100-75 (slight minority risk starts)
        return 100.0 - (p - 65) / 10 * 25
    # >75 → 75-20 (concentrated control risk)
    return clamp(75.0 - (p - 75) / 25 * 55)


def score_institutional_holding(pct: Optional[float]) -> float:
    """
    Score institutional investor participation.
    Higher institutional holding = stronger market endorsement.
    Optimal: 20-55%.  > 60% can be fragile (forced selling risk).
    """
    if pct is None:
        return 30.0
    p = pct_to_100(pct)
    assert p is not None
    if p < 0:
        return 0.0
    if p < 5:
        return 5.0 + p / 5 * 20
    if p < 15:
        return 25.0 + (p - 5) / 10 * 30
    if p < 25:
        return 55.0 + (p - 15) / 10 * 25
    if p <= 55:
        return 80.0 + (p - 25) / 30 * 20
    if p <= 70:
        return 100.0 - (p - 55) / 15 * 20
    return clamp(80.0 - (p - 70) / 30 * 40)


def score_free_float(pct: Optional[float]) -> float:
    """
    Score free float percentage.
    Optimal: 25-65%. Too low → illiquid; too high → no promoter skin in game.
    """
    if pct is None:
        return 40.0
    p = pct_to_100(pct)
    assert p is not None
    if p < 5:
        return 5.0
    if p < 15:
        return 5.0 + (p - 5) / 10 * 30
    if p < 25:
        return 35.0 + (p - 15) / 10 * 35
    if p <= 65:
        return 70.0 + (p - 25) / 40 * 30
    if p <= 80:
        return 100.0 - (p - 65) / 15 * 25
    return clamp(75.0 - (p - 80) / 20 * 40)


def score_insider_holding(pct: Optional[float]) -> float:
    """
    Score executive/board personal ownership stake.
    Higher management ownership = better alignment.
    """
    if pct is None:
        return 35.0
    p = pct_to_100(pct)
    assert p is not None
    if p <= 0:
        return 0.0
    if p < 0.5:
        return 10.0
    if p < 2:
        return 10.0 + (p - 0.5) / 1.5 * 30
    if p < 5:
        return 40.0 + (p - 2) / 3 * 30
    if p < 10:
        return 70.0 + (p - 5) / 5 * 20
    return clamp(90.0 + (p - 10) / 15 * 10)


# ── Pledge / Risk Scoring ─────────────────────────────────────────────────────

def score_pledge_risk(pledge_pct_of_promoter: Optional[float]) -> float:
    """
    Risk score for promoter share pledging.
    HIGHER score = HIGHER risk.
    pledge_pct_of_promoter: % of promoter's holding that is pledged (0-100).
    """
    if pledge_pct_of_promoter is None:
        return 20.0   # mild uncertainty
    p = pct_to_100(pledge_pct_of_promoter)
    assert p is not None
    p = clamp(p, 0, 100)
    if p <= 5:
        return 5.0
    if p <= 20:
        return 5.0 + (p - 5) / 15 * 25
    if p <= 40:
        return 30.0 + (p - 20) / 20 * 30
    if p <= 60:
        return 60.0 + (p - 40) / 20 * 25
    return clamp(85.0 + (p - 60) / 40 * 15)


# ── Promoter Change / Stability ───────────────────────────────────────────────

def score_promoter_stability(
    change_3m: Optional[float],   # pp change in promoter holding (last 3 months)
    change_1y: Optional[float],   # pp change in last 1 year
) -> float:
    """
    Score promoter holding stability.
    Stable/increasing holding → high score.
    Consistent selling → low score.
    """
    if change_3m is None and change_1y is None:
        return 50.0   # no data → neutral

    scores: list[float] = []
    if change_3m is not None:
        c3 = float(change_3m)
        if c3 >= 2.0:
            scores.append(100.0)
        elif c3 >= 0.5:
            scores.append(85.0)
        elif c3 >= -0.5:
            scores.append(70.0)
        elif c3 >= -2.0:
            scores.append(45.0)
        elif c3 >= -5.0:
            scores.append(20.0)
        else:
            scores.append(0.0)

    if change_1y is not None:
        c1 = float(change_1y)
        if c1 >= 5.0:
            scores.append(100.0)
        elif c1 >= 2.0:
            scores.append(85.0)
        elif c1 >= -1.0:
            scores.append(70.0)
        elif c1 >= -5.0:
            scores.append(40.0)
        else:
            scores.append(10.0)

    return clamp(statistics.mean(scores))


def score_institutional_change(change_3m: Optional[float]) -> float:
    """
    Score direction of institutional holding change (3 months).
    Increasing = positive signal.
    """
    if change_3m is None:
        return 50.0
    c = float(change_3m)
    if c >= 3.0:
        return 100.0
    if c >= 1.0:
        return 80.0
    if c >= 0.0:
        return 65.0
    if c >= -2.0:
        return 40.0
    if c >= -5.0:
        return 20.0
    return 5.0


# ── Insider Transaction Scores ────────────────────────────────────────────────

def score_insider_buying(
    buy_count: int,
    sell_count: int,
    net_sentiment: Optional[float],
) -> float:
    """
    Score insider buying activity (0-100).
    Higher = more net buying (positive alignment signal).
    """
    if buy_count == 0 and sell_count == 0:
        return 50.0   # no activity → neutral

    total = buy_count + sell_count
    if total == 0:
        buy_ratio = 0.5
    else:
        buy_ratio = buy_count / total

    # Base from buy ratio
    base = buy_ratio * 100.0

    # Adjust for net sentiment if available
    if net_sentiment is not None:
        sentiment_adj = clamp((net_sentiment + 100) / 200 * 100, 0, 100)
        return clamp((base * 0.6 + sentiment_adj * 0.4))

    return clamp(base)


# ── Concentration ─────────────────────────────────────────────────────────────

def score_top10_concentration(top10_pct: Optional[float]) -> float:
    """
    Score top-10 holder concentration (0-100).
    Optimal: 40-70%.  Too low = widely scattered; too high = illiquid.
    """
    if top10_pct is None:
        return 50.0
    p = pct_to_100(top10_pct)
    assert p is not None
    if p < 20:
        return 30.0   # too dispersed, low quality
    if p < 40:
        return 30.0 + (p - 20) / 20 * 40
    if p <= 70:
        return 70.0 + (p - 40) / 30 * 30
    if p <= 85:
        return 100.0 - (p - 70) / 15 * 30
    return clamp(70.0 - (p - 85) / 15 * 40)


# ── Capital Return Scores ─────────────────────────────────────────────────────

def score_dividend_policy(
    payout_ratio: Optional[float],
    eps_cagr: Optional[float],
) -> float:
    """
    Score dividend policy discipline.
    Optimal payout: 25-50% for growth company; higher acceptable for mature.
    """
    if payout_ratio is None:
        return 45.0
    p = pct_to_100(payout_ratio)
    assert p is not None
    p = clamp(p, 0, 100)

    # Base score from payout ratio
    if p <= 0:
        # No dividend — could be growth reinvestment (neutral-positive for high-growth)
        base = 45.0
    elif p < 15:
        base = 55.0
    elif p < 30:
        base = 75.0
    elif p <= 50:
        base = 90.0
    elif p <= 75:
        base = 75.0 - (p - 50) / 25 * 25
    else:
        base = 50.0 - (p - 75) / 25 * 40

    # Adjust: high-growth companies should retain more
    if eps_cagr is not None and eps_cagr > 0.20 and p > 60:
        base -= 10.0   # penalize high payout for high-growth firms

    return clamp(base)


def score_buyback_quality(
    avg_roic: Optional[float],
    fcf_margin: Optional[float],
) -> float:
    """
    Score buyback quality proxy.
    High-ROIC + strong FCF → buybacks create value.
    """
    scores: list[float] = []
    if avg_roic is not None:
        if avg_roic >= 0.20:
            scores.append(100.0)
        elif avg_roic >= 0.15:
            scores.append(80.0)
        elif avg_roic >= 0.10:
            scores.append(60.0)
        elif avg_roic >= 0.05:
            scores.append(35.0)
        else:
            scores.append(10.0)

    if fcf_margin is not None:
        if fcf_margin >= 0.15:
            scores.append(100.0)
        elif fcf_margin >= 0.10:
            scores.append(80.0)
        elif fcf_margin >= 0.05:
            scores.append(60.0)
        elif fcf_margin >= 0:
            scores.append(35.0)
        else:
            scores.append(0.0)

    return clamp(safe_mean(scores) or 45.0)


# ── Economic Value ─────────────────────────────────────────────────────────────

def score_roic_spread(avg_roic: Optional[float]) -> float:
    """
    Score ROIC economic spread over estimated cost of capital.
    Uses a generic 10% WACC proxy; positive spread = value creation.
    """
    WACC_PROXY = 0.10
    if avg_roic is None:
        return 40.0
    spread = avg_roic - WACC_PROXY
    if spread >= 0.15:
        return 100.0
    if spread >= 0.08:
        return 80.0 + (spread - 0.08) / 0.07 * 20
    if spread >= 0.0:
        return 50.0 + (spread / 0.08) * 30
    if spread >= -0.05:
        return 30.0 + (1 + spread / 0.05) * 20
    return clamp(10.0 + max(0, (spread + 0.15) / 0.10) * 20)


def score_roe_sustainability(
    avg_roe: Optional[float],
    payout_ratio: Optional[float],
) -> float:
    """
    Sustainable growth rate proxy: ROE × (1 - payout).
    Score based on sustainable growth rate.
    """
    if avg_roe is None:
        return 40.0
    retention = 1.0 - (pct_to_100(payout_ratio) or 30) / 100
    sgr = avg_roe * retention
    if sgr >= 0.18:
        return 100.0
    if sgr >= 0.12:
        return 80.0
    if sgr >= 0.07:
        return 65.0
    if sgr >= 0.03:
        return 45.0
    if sgr >= 0:
        return 30.0
    return 10.0


# ── Dilution ──────────────────────────────────────────────────────────────────

def score_dilution_risk(esop_outstanding_pct: Optional[float]) -> float:
    """
    Risk from potential dilution via ESOPs.
    HIGHER score = HIGHER dilution risk.
    """
    if esop_outstanding_pct is None:
        return 15.0
    p = pct_to_100(esop_outstanding_pct)
    assert p is not None
    if p <= 1:
        return 5.0
    if p <= 3:
        return 15.0
    if p <= 5:
        return 30.0
    if p <= 8:
        return 55.0
    return clamp(55.0 + (p - 8) / 7 * 45)


# ── Label ─────────────────────────────────────────────────────────────────────

def _label_ownership_score(score: float) -> str:
    if score >= 80:
        return "exceptional"
    if score >= 65:
        return "strong"
    if score >= 50:
        return "adequate"
    if score >= 35:
        return "weak"
    return "poor"
