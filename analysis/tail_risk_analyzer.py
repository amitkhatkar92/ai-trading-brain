"""
analysis/tail_risk_analyzer.py
====================================
OPTIONS_RISK_AUDIT_001 — Per-strategy risk metric computation.

No IO. No database. Pure functions over a list of pnl_r values.

Metrics
-------
profit_factor     : sum(wins) / |sum(losses)|  — the only PF that matters
expected_value    : WR × avg_win − (1−WR) × avg_loss   (per trade, in R)
win_rate          : wins / total
avg_win           : mean of winning R multiples
avg_loss          : mean of losing R multiples (positive number)
win_loss_ratio    : avg_win / avg_loss  (Profit Ratio)
kelly_pct         : (EV / avg_win) × 100   — optimal bet size %
sharpe            : annualised Sharpe on per-trade R series
sortino           : annualised Sortino (downside deviation only)
max_consecutive_loss : longest losing streak
pct_large_losses  : % of trades with loss > 2R (tail event proxy)

Annualisation assumption: 52 entries/year per strategy (weekly trades),
which is conservative. Adjust TRADES_PER_YEAR if needed.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List, Optional


TRADES_PER_YEAR = 52      # one trade per week per strategy; scale to annualise


@dataclass
class RiskMetrics:
    strategy:             str
    regime:               str          # "ALL" or specific regime
    n:                    int
    win_rate:             float        # %
    profit_factor:        float
    expected_value:       float        # per trade, in R
    avg_win:              float        # R
    avg_loss:             float        # R (positive)
    win_loss_ratio:       float        # avg_win / avg_loss
    kelly_pct:            float        # optimal position size %
    sharpe:               float        # annualised
    sortino:              float        # annualised
    max_consecutive_loss: int
    pct_large_losses:     float        # % of trades losing > 2R
    verdict:              str          # TRADE / WATCH / AVOID
    verdict_reason:       str


def _mean(xs: List[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def _std(xs: List[float]) -> float:
    if len(xs) < 2:
        return 0.0
    m = _mean(xs)
    variance = sum((x - m) ** 2 for x in xs) / (len(xs) - 1)
    return math.sqrt(variance)


def _downside_std(xs: List[float], target: float = 0.0) -> float:
    """Downside deviation — only values below target."""
    neg = [min(0.0, x - target) for x in xs]
    if len(neg) < 2:
        return 1e-9
    variance = sum(x ** 2 for x in neg) / len(neg)
    return math.sqrt(variance) or 1e-9


def _max_consecutive_losses(wins_losses: List[str]) -> int:
    """Longest run of 'LOSS' in a sequence."""
    current = max_streak = 0
    for wl in wins_losses:
        if wl == "LOSS":
            current += 1
            max_streak = max(max_streak, current)
        else:
            current = 0
    return max_streak


def compute_risk_metrics(
    strategy:    str,
    pnl_r_list:  List[float],       # signed R-multiples per trade (+1.0 or −2.0)
    wins_losses: List[str],          # parallel "WIN"/"LOSS" list
    regime:      str = "ALL",
) -> RiskMetrics:
    """
    Compute full risk metrics for one strategy from its trade R-multiples.

    Args:
        strategy   : strategy name
        pnl_r_list : list of signed R-multiples (positive for wins, negative for losses)
        wins_losses: parallel "WIN"/"LOSS" classification list
        regime     : regime label for grouping

    Returns:
        RiskMetrics dataclass with all computed values.
    """
    n = len(pnl_r_list)
    if n == 0:
        return RiskMetrics(
            strategy=strategy, regime=regime, n=0,
            win_rate=0, profit_factor=0, expected_value=0,
            avg_win=0, avg_loss=0, win_loss_ratio=0, kelly_pct=0,
            sharpe=0, sortino=0, max_consecutive_loss=0,
            pct_large_losses=0, verdict="NO_DATA", verdict_reason="No trades",
        )

    wins  = [r for r in pnl_r_list if r > 0]
    losses= [r for r in pnl_r_list if r <= 0]

    win_rate   = len(wins) / n * 100
    avg_win    = _mean(wins) if wins else 0.0
    avg_loss   = abs(_mean(losses)) if losses else 0.0  # positive magnitude

    gross_profit = sum(wins) if wins else 0.0
    gross_loss   = abs(sum(losses)) if losses else 1e-9
    pf           = gross_profit / gross_loss

    ev = _mean(pnl_r_list)   # expected R per trade

    wl_ratio = (avg_win / avg_loss) if avg_loss > 0 else 0.0

    # Kelly formula: f* = EV / avg_win  (simplified; positive only when EV > 0)
    kelly_pct = max(0.0, ev / avg_win * 100) if avg_win > 0 else 0.0
    kelly_pct = min(kelly_pct, 25.0)   # cap at 25% (practical safety)

    # Annualised Sharpe on R-multiple series
    mu  = _mean(pnl_r_list)
    sd  = _std(pnl_r_list) or 1e-9
    sharpe = (mu / sd) * math.sqrt(TRADES_PER_YEAR)

    # Annualised Sortino (target = 0R)
    dsd    = _downside_std(pnl_r_list, 0.0)
    sortino= (mu / dsd) * math.sqrt(TRADES_PER_YEAR)

    max_consec = _max_consecutive_losses(wins_losses)

    # Tail: % of trades that lose more than 2R
    pct_large = len([r for r in pnl_r_list if r < -2.0]) / n * 100

    # ── Verdict ───────────────────────────────────────────────────────────────
    # Governed by: EV, PF, Sharpe, consecutive loss streak
    if pf >= 1.3 and ev > 0.10 and sharpe > 0.5 and max_consec <= 10:
        verdict        = "TRADE"
        verdict_reason = f"PF={pf:.2f}, EV={ev:+.3f}R, Sharpe={sharpe:.2f}"
    elif pf >= 1.0 and ev > 0 and sharpe > 0:
        verdict        = "WATCH"
        verdict_reason = (
            f"Marginally profitable: PF={pf:.2f}, EV={ev:+.3f}R — "
            f"needs more real data or tighter regime filter"
        )
    else:
        verdict        = "AVOID"
        verdict_reason = (
            f"Negative expectancy: PF={pf:.2f}, EV={ev:+.3f}R"
            + (f", {max_consec} consecutive losses possible" if max_consec > 8 else "")
        )

    return RiskMetrics(
        strategy             = strategy,
        regime               = regime,
        n                    = n,
        win_rate             = round(win_rate, 1),
        profit_factor        = round(pf, 3),
        expected_value       = round(ev, 4),
        avg_win              = round(avg_win, 3),
        avg_loss             = round(avg_loss, 3),
        win_loss_ratio       = round(wl_ratio, 3),
        kelly_pct            = round(kelly_pct, 1),
        sharpe               = round(sharpe, 3),
        sortino              = round(sortino, 3),
        max_consecutive_loss = max_consec,
        pct_large_losses     = round(pct_large, 1),
        verdict              = verdict,
        verdict_reason       = verdict_reason,
    )


def compute_regime_risk(
    strategy: str,
    records:  list,         # list of dicts with keys: pnl_r, win_loss, regime
) -> dict:
    """
    Compute risk metrics broken down by regime for one strategy.

    Returns dict keyed by regime name (plus "ALL").
    """
    regimes = list({r["regime"] for r in records}) + ["ALL"]
    result  = {}
    for regime in regimes:
        subset = records if regime == "ALL" else [r for r in records if r["regime"] == regime]
        pnl_r  = [r["pnl_r"]    for r in subset]
        wl     = [r["win_loss"] for r in subset]
        result[regime] = compute_risk_metrics(strategy, pnl_r, wl, regime)
    return result
