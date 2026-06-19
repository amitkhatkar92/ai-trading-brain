"""
analysis/options_backtester.py
=================================
REAL_OPTIONS_AUDIT_002 — Strategy payoff simulation from real price data.

No Black-Scholes. No live system imports.

Each strategy is defined by a payoff rule:
    "given the underlying moved X% over N days,
     and VIX was Y, did this strategy win or lose?"

The approach reconstructs option payoffs from underlying price moves because:
- Historical NSE option chain data is not freely available
- Real underlying price + VIX captures the core P&L drivers
- Results are directly comparable to synthetic OPTIONS_AUDIT_001 findings

Strategy Model
--------------
We model each strategy as a "breakeven band" around the entry price.
The band width scales with VIX (higher VIX → wider strikes were selected
at entry → wider band needed to lose money).

    band_pct = BASE_BAND[strategy] × (1 + vix_scaling_factor)

Example for IRON_CONDOR:
    base band = ±2.0% (sold strikes placed 2% OTM at entry)
    vix_scale = max(0, (vix - 14) / 20)     so VIX 14 → 0.0x, VIX 22 → 0.4x
    effective band = ±2.0% × (1 + 0.4) = ±2.8% at VIX=22

Win/Loss rules
--------------
CREDIT spreads (net premium sellers):
    WIN if underlying stays inside band at expiry
    max_profit = credit received (modelled as 1.0R)
    max_loss   = width − credit  (modelled as 2.0R, i.e. RR=1:2)

DEBIT spreads (net premium buyers):
    WIN if underlying moves outside band
    max_profit = 3.0R
    max_loss   = 1.0R

These R-multiple defaults can be overridden per strategy.
The primary metric reported is win-rate and profit factor.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from analysis.nse_data_loader import MarketDay


# ── Strategy definitions ──────────────────────────────────────────────────────

# base_band_pct: percentage from entry price within which the underlying
#                must stay (for credit strategies) or must break out (for debit)
# win_if_inside: True = credit spread (win if stays inside band)
# holding_days : default holding period for backtesting
# r_win, r_loss: R-multiple for win and loss

_STRATEGY_PARAMS: Dict[str, dict] = {
    "BULL_PUT_SPREAD": dict(
        base_band_pct = 1.50,   # lower band only; put spread
        win_if_inside = True,   # win if underlying doesn't fall more than 1.5%
        is_directional= True,   # only care about downward breach
        direction_bias = "UP",  # strategy wins if market is flat/up
        holding_days  = 7,
        r_win         = 1.0,
        r_loss        = 2.0,
    ),
    "BEAR_CALL_SPREAD": dict(
        base_band_pct = 1.50,
        win_if_inside = True,
        is_directional= True,
        direction_bias = "DOWN",
        holding_days  = 7,
        r_win         = 1.0,
        r_loss        = 2.0,
    ),
    "IRON_CONDOR": dict(
        base_band_pct = 2.00,
        win_if_inside = True,
        is_directional= False,
        direction_bias = "NEUTRAL",
        holding_days  = 7,
        r_win         = 1.0,
        r_loss        = 2.5,
    ),
    "SHORT_STRANGLE": dict(
        base_band_pct = 2.50,
        win_if_inside = True,
        is_directional= False,
        direction_bias = "NEUTRAL",
        holding_days  = 7,
        r_win         = 1.0,
        r_loss        = 3.0,
    ),
    "LONG_STRANGLE": dict(
        base_band_pct = 2.50,
        win_if_inside = False,   # debit: wins if move > band
        is_directional= False,
        direction_bias = "NEUTRAL",
        holding_days  = 7,
        r_win         = 3.0,
        r_loss        = 1.0,
    ),
    "COVERED_CALL": dict(
        base_band_pct = 1.00,
        win_if_inside = True,   # wins if market doesn't rally past strike
        is_directional= True,
        direction_bias = "FLAT",
        holding_days  = 7,
        r_win         = 0.8,
        r_loss        = 1.5,
    ),
    "PROTECTIVE_PUT": dict(
        base_band_pct = 2.00,   # put kicks in if market drops > 2%
        win_if_inside = False,  # debit: wins on large downward move
        is_directional= True,
        direction_bias = "DOWN",
        holding_days  = 7,
        r_win         = 2.5,
        r_loss        = 0.5,   # small debit for protection
    ),
    "LONG_CALL": dict(
        base_band_pct = 1.50,
        win_if_inside = False,
        is_directional= True,
        direction_bias = "UP",
        holding_days  = 7,
        r_win         = 3.0,
        r_loss        = 1.0,
    ),
    "LONG_PUT": dict(
        base_band_pct = 1.50,
        win_if_inside = False,
        is_directional= True,
        direction_bias = "DOWN",
        holding_days  = 7,
        r_win         = 3.0,
        r_loss        = 1.0,
    ),
}

ALL_STRATEGIES = list(_STRATEGY_PARAMS.keys())


# ── VIX scaling ───────────────────────────────────────────────────────────────

def _vix_scale(vix: float) -> float:
    """
    How much wider the breakeven band is at a given VIX.
    At VIX 14: +0%.  At VIX 22: +40%.  At VIX 30: +80%.
    """
    return max(0.0, (vix - 14.0) / 20.0)


def _effective_band(strategy: str, vix: float) -> float:
    params  = _STRATEGY_PARAMS[strategy]
    base    = params["base_band_pct"]
    scale   = _vix_scale(vix)
    return base * (1.0 + scale)


# ── Core payoff engine ────────────────────────────────────────────────────────

@dataclass
class BacktestRecord:
    date:         str
    strategy:     str
    underlying:   str
    regime:       str
    vix:          float
    vix_bucket:   str
    direction:    str
    entry_price:  float
    ret_5d:       float
    ret_10d:      float
    band_pct:     float
    win_loss:     str       # "WIN" or "LOSS"
    pnl_r:        float     # R-multiple: +r_win or −r_loss
    holding_days: int
    breach_pct:   float     # how much the move exceeded (or stayed below) the band


def _wins(strategy: str, ret: float, band_pct: float) -> bool:
    """
    Explicit win condition per strategy.

    Credit strategies win when the underlying stays inside the breakeven band.
    Debit strategies win when the underlying moves outside the band.

    ret       : actual N-day return of the underlying (signed %)
    band_pct  : effective breakeven band (already VIX-adjusted)
    """
    if strategy == "BULL_PUT_SPREAD":
        # Credit: wins if market doesn't fall below the put strike
        return ret > -band_pct
    elif strategy == "BEAR_CALL_SPREAD":
        # Credit: wins if market doesn't rally above the call strike
        return ret < band_pct
    elif strategy in ("IRON_CONDOR", "SHORT_STRANGLE"):
        # Credit: wins if underlying stays within ±band
        return abs(ret) < band_pct
    elif strategy == "LONG_STRANGLE":
        # Debit: wins on large move either way
        return abs(ret) > band_pct
    elif strategy == "COVERED_CALL":
        # Credit: wins if market doesn't rally past the short call strike
        return ret < band_pct
    elif strategy in ("PROTECTIVE_PUT", "LONG_PUT"):
        # Debit: wins if market falls enough to cover debit
        return ret < -band_pct
    elif strategy == "LONG_CALL":
        # Debit: wins if market rallies enough
        return ret > band_pct
    return False


def simulate_strategy(
    day:      MarketDay,
    strategy: str,
    use_10d:  bool = False,
) -> BacktestRecord:
    """
    Simulate one strategy entry on one market day.

    Uses explicit per-strategy payoff rules (no generalised breach formula).
    Band width is VIX-adjusted: higher vol = wider strikes were placed at entry.
    """
    params   = _STRATEGY_PARAMS[strategy]
    band_pct = _effective_band(strategy, day.vix)
    holding  = params["holding_days"]
    ret      = day.ret_10d if use_10d else day.ret_5d

    win    = _wins(strategy, ret, band_pct)
    breach = max(0.0, abs(ret) - band_pct)   # magnitude beyond band (0 if inside)

    pnl_r  = params["r_win"] if win else -params["r_loss"]
    return BacktestRecord(
        date        = day.date,
        strategy    = strategy,
        underlying  = day.underlying,
        regime      = day.regime,
        vix         = day.vix,
        vix_bucket  = day.vix_bucket,
        direction   = day.direction,
        entry_price = day.close,
        ret_5d      = day.ret_5d,
        ret_10d     = day.ret_10d,
        band_pct    = round(band_pct, 3),
        win_loss    = "WIN" if win else "LOSS",
        pnl_r       = round(pnl_r, 2),
        holding_days= holding,
        breach_pct  = round(breach, 3),
    )


def backtest_all_strategies(
    days:     List[MarketDay],
    use_10d:  bool = False,
    strategies: Optional[List[str]] = None,
) -> List[BacktestRecord]:
    """
    Run all strategies across all days.

    Returns one BacktestRecord per (strategy, day) combination.
    """
    strats = strategies or ALL_STRATEGIES
    return [
        simulate_strategy(day, s, use_10d=use_10d)
        for day in days
        for s in strats
    ]


# ── Aggregate statistics ──────────────────────────────────────────────────────

@dataclass
class StrategyStats:
    strategy:     str
    regime:       str
    n:            int
    wins:         int
    win_rate:     float
    avg_pnl_r:    float
    profit_factor: float
    comparison:   str = ""   # vs synthetic finding


def aggregate_stats(
    records:  List[BacktestRecord],
    group_by: str = "strategy",
) -> Dict[str, StrategyStats]:
    """
    Aggregate win rates and profit factors, grouped by strategy (optionally × regime).

    Args:
        group_by: "strategy" → aggregate across all regimes
                  "strategy_regime" → break down by regime too
    """
    buckets: Dict[str, list] = {}
    for r in records:
        key = r.strategy if group_by == "strategy" else f"{r.strategy}|{r.regime}"
        buckets.setdefault(key, []).append(r)

    result = {}
    for key, recs in buckets.items():
        wins   = [r for r in recs if r.win_loss == "WIN"]
        losses = [r for r in recs if r.win_loss == "LOSS"]
        n      = len(recs)
        wr     = len(wins) / n if n else 0.0
        avg    = sum(r.pnl_r for r in recs) / n if n else 0.0

        gross_profit = sum(r.pnl_r for r in wins)  if wins   else 0.0
        gross_loss   = sum(abs(r.pnl_r) for r in losses) if losses else 1e-9
        pf           = gross_profit / gross_loss

        parts = key.split("|")
        result[key] = StrategyStats(
            strategy      = parts[0],
            regime        = parts[1] if len(parts) > 1 else "ALL",
            n             = n,
            wins          = len(wins),
            win_rate      = round(wr * 100, 1),
            avg_pnl_r     = round(avg, 3),
            profit_factor = round(pf, 3),
        )
    return result


# ── Synthetic comparison reference ───────────────────────────────────────────

# From OPTIONS_AUDIT_001 — these are the numbers being validated
SYNTHETIC_BENCHMARK: Dict[str, dict] = {
    "BULL_PUT_SPREAD": {"win_rate": 70.3, "profit_factor": 1.74, "best_regime": "TRENDING"},
    "BEAR_CALL_SPREAD": {"win_rate": 63.1, "profit_factor": 1.45, "best_regime": "TRENDING"},
    "IRON_CONDOR":     {"win_rate": 62.0, "profit_factor": 2.20, "best_regime": "RANGING"},
    "SHORT_STRANGLE":  {"win_rate": 58.4, "profit_factor": 1.98, "best_regime": "RANGING"},
    "LONG_STRANGLE":   {"win_rate": 38.7, "profit_factor": 1.12, "best_regime": "HIGH_VOL"},
    "COVERED_CALL":    {"win_rate": 65.0, "profit_factor": 1.55, "best_regime": "RANGING"},
    "PROTECTIVE_PUT":  {"win_rate": 45.3, "profit_factor": 2.85, "best_regime": "HIGH_VOL"},
    "LONG_CALL":       {"win_rate": 42.0, "profit_factor": 1.30, "best_regime": "TRENDING"},
    "LONG_PUT":        {"win_rate": 39.5, "profit_factor": 1.22, "best_regime": "HIGH_VOL"},
}


def compare_to_synthetic(
    real_stats: Dict[str, StrategyStats],
) -> Dict[str, str]:
    """
    Returns a verdict string per strategy:
        CONFIRMED   — real WR within ±10pp of synthetic
        OVERSTATED  — synthetic was too optimistic (real < synthetic − 10pp)
        UNDERSTATED — real is better than synthetic
        INSUFFICIENT— fewer than 20 real observations
    """
    verdicts = {}
    for key, st in real_stats.items():
        strat = st.strategy
        syn   = SYNTHETIC_BENCHMARK.get(strat)
        if syn is None:
            verdicts[key] = "NO_SYNTHETIC_BASELINE"
            continue
        if st.n < 20:
            verdicts[key] = "INSUFFICIENT_DATA"
            continue
        diff = st.win_rate - syn["win_rate"]
        if abs(diff) <= 10:
            verdicts[key] = "CONFIRMED"
        elif diff < -10:
            verdicts[key] = f"OVERSTATED (synthetic {syn['win_rate']:.1f}% vs real {st.win_rate:.1f}%)"
        else:
            verdicts[key] = f"UNDERSTATED (real {st.win_rate:.1f}% beats synthetic {syn['win_rate']:.1f}%)"
    return verdicts
