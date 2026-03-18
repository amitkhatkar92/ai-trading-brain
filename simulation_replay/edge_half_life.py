"""
Edge Half-Life (EHL) Analyzer
==============================
Measures how long a trading signal keeps its statistical advantage after
it appears, expressed as the number of 5-minute candles before the average
R-multiple falls to half its initial (immediate-entry) value.

Why this matters
----------------
All three of the system's execution timing parameters should be calibrated
against the edge half-life of the strategy:

    Parameter               | Current value | Should be
    ------------------------|---------------|----------
    LIMIT_CANDLE_EXPIRY     | 3 candles     | = half-life
    AET_MAX_WAIT_CANDLES    | 2 candles     | <= half-life // 2
    REENTRY_WINDOW_CANDLES  | 10 candles    | <= half-life * 2

If the parameters are already tighter than EHL → system is well-calibrated.
If looser → the system is placing/holding orders after the edge is gone.

Drift model
-----------
When entry is delayed by *d* candles, the market has moved adversely by:

    adverse_drift(d) = entry_price × per_candle_drift_pct × d

where:

    per_candle_drift_pct = (avg_|Nifty_daily_change| / 100) / CANDLES_PER_DAY

This is empirically derived from the replay data (or falls back to a VIX-
implied estimate when fewer than 5 days are available).

For each delay d the adjusted PnL is:

    adjusted_pnl(d) = raw_pnl - adverse_drift(d) × quantity

and the R-multiple is:

    R(d) = adjusted_pnl(d) / (|entry - sl| × quantity)

Half-life is the smallest delay where avg_R(d) <= avg_R(0) × 0.5.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

# ── Constants ─────────────────────────────────────────────────────────────────
CANDLES_PER_DAY  = 75     # NSE 5-min session: 09:15–15:30 = 375 min / 5
MAX_DELAY_CANDLES = 6     # analyse delays 0 → 6

# Current execution parameter values (for calibration report)
_CURRENT_EXPIRY      = 3    # LIMIT_CANDLE_EXPIRY
_CURRENT_AET_WAIT    = 2    # AET_MAX_WAIT_CANDLES
_CURRENT_REENTRY_WIN = 10   # REENTRY_WINDOW_CANDLES

# Fallback VIX if not derivable from replay
_FALLBACK_VIX = 15.0


# ─────────────────────────────────────────────────────────────────────────────
# Data classes
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class StrategyHalfLife:
    """Per-strategy EHL detail."""
    strategy:         str
    trades:           int
    r_at_delays:      List[float]   # avg R at delay 0,1,2,...
    half_life:        float         # candles (may be fractional via interpolation)
    r_at_zero:        float         # baseline


@dataclass
class EhlResult:
    """Full Edge Half-Life analysis output."""
    # Core result
    delays:              List[int]    # [0, 1, 2, 3, 4, 5, 6]
    avg_r_at_delay:      List[float]  # mean R-multiple across all trades
    half_life_candles:   float        # fractional; NaN if edge never reaches 50%
    r_at_zero:           float        # R@delay=0 (baseline)
    r_half:              float        # = r_at_zero * 0.5

    # Per-strategy
    per_strategy:        Dict[str, StrategyHalfLife] = field(default_factory=dict)

    # Drift model info
    per_candle_drift_pct: float = 0.0  # empirical % per candle

    # Calibration recommendations
    recommended_expiry:      int = _CURRENT_EXPIRY
    recommended_aet_wait:    int = _CURRENT_AET_WAIT
    recommended_reentry_win: int = _CURRENT_REENTRY_WIN

    # Input counts
    total_trades:        int = 0
    days_used:           int = 0


# ─────────────────────────────────────────────────────────────────────────────
# Core analysis function
# ─────────────────────────────────────────────────────────────────────────────

def analyze_edge_half_life(
    day_results: list,                         # List[DayCycleResult]
    max_delay:   int   = MAX_DELAY_CANDLES,
    vix_override: Optional[float] = None,
) -> EhlResult:
    """
    Compute Edge Half-Life from replay DayCycleResult objects.

    Parameters
    ----------
    day_results:
        DayCycleResult list from the replay engine.
    max_delay:
        Maximum candle delay to simulate (default 6 = 30 min after signal).
    vix_override:
        If supplied, use this VIX instead of deriving from day data.
        Useful for sensitivity analysis.

    Returns
    -------
    EhlResult — safe to consume even when no trades were recorded.
    """
    delays = list(range(max_delay + 1))

    # ── Step 1: derive per-candle drift from replay market data ───────────────
    daily_moves: List[float] = []
    avg_vix = vix_override or 0.0

    for dr in day_results:
        daily_moves.append(abs(float(dr.nifty_change or 0.0)))
        if not vix_override:
            avg_vix += float(dr.vix or _FALLBACK_VIX)

    if len(daily_moves) >= 5:
        per_candle_drift_pct = (sum(daily_moves) / len(daily_moves)) / CANDLES_PER_DAY / 100.0
    else:
        # VIX-implied fallback: annualised vol / sqrt(252 * CANDLES_PER_DAY)
        if not vix_override and day_results:
            avg_vix /= len(day_results)
        vix = avg_vix if avg_vix > 0 else _FALLBACK_VIX
        daily_vol = vix / math.sqrt(252) / 100.0
        per_candle_drift_pct = daily_vol / CANDLES_PER_DAY

    # ── Step 2: collect trades ────────────────────────────────────────────────
    all_trades: List[Dict[str, Any]] = []
    for dr in day_results:
        for t in dr.executed_trades:
            all_trades.append(dict(t))

    empty = EhlResult(
        delays               = delays,
        avg_r_at_delay       = [0.0] * len(delays),
        half_life_candles    = float("nan"),
        r_at_zero            = 0.0,
        r_half               = 0.0,
        per_candle_drift_pct = round(per_candle_drift_pct * 100, 6),
        total_trades         = 0,
        days_used            = len(day_results),
    )

    if not all_trades:
        return empty

    # ── Step 3: simulate R-multiples at each delay ───────────────────────────
    # Bucket: strategy -> [[R@d0, R@d1, ...], ...]
    strat_buckets: Dict[str, List[List[float]]] = {}
    global_r_lists: Dict[int, List[float]] = {d: [] for d in delays}

    for t in all_trades:
        pnl    = float(t.get("pnl", 0.0) or 0.0)
        entry  = float(t.get("entry", 0.0) or t.get("entry_price", 0.0) or 0.0)
        sl     = float(t.get("sl", 0.0) or t.get("stop_loss", 0.0) or 0.0)
        qty    = float(t.get("qty", 0.0) or t.get("quantity", 1.0) or 1.0)
        strat  = str(t.get("strategy", t.get("strategy_name", "unknown")) or "unknown")

        if entry <= 0:
            continue   # can't model without entry price

        # risk per unit (SL-based; fall back to 1% of entry)
        risk_per_unit = abs(entry - sl) if sl > 0 else entry * 0.01
        if risk_per_unit <= 0:
            risk_per_unit = entry * 0.01

        r_series: List[float] = []
        for d in delays:
            adverse_move = entry * per_candle_drift_pct * d
            adj_pnl      = pnl - adverse_move * qty
            r_mult       = adj_pnl / (risk_per_unit * qty)
            r_series.append(round(r_mult, 4))
            global_r_lists[d].append(r_mult)

        if strat not in strat_buckets:
            strat_buckets[strat] = []
        strat_buckets[strat].append(r_series)

    # ── Step 4: aggregate ─────────────────────────────────────────────────────
    avg_r_at_delay = [
        (sum(global_r_lists[d]) / len(global_r_lists[d])) if global_r_lists[d] else 0.0
        for d in delays
    ]
    avg_r_at_delay = [round(v, 4) for v in avg_r_at_delay]

    r0    = avg_r_at_delay[0]
    r_50  = r0 * 0.5
    ehl   = _interpolate_half_life(avg_r_at_delay, delays, r_50)

    # ── Step 5: per-strategy ──────────────────────────────────────────────────
    per_strategy: Dict[str, StrategyHalfLife] = {}
    for strat, series_list in strat_buckets.items():
        n_trades = len(series_list)
        avg_r_strat = []
        for d_idx in range(len(delays)):
            vals = [s[d_idx] for s in series_list]
            avg_r_strat.append(round(sum(vals) / len(vals), 4))
        r0_s  = avg_r_strat[0]
        ehl_s = _interpolate_half_life(avg_r_strat, delays, r0_s * 0.5)
        per_strategy[strat] = StrategyHalfLife(
            strategy    = strat,
            trades      = n_trades,
            r_at_delays = avg_r_strat,
            half_life   = ehl_s,
            r_at_zero   = r0_s,
        )

    # ── Step 6: calibration recommendations ──────────────────────────────────
    if not math.isnan(ehl) and ehl > 0:
        rec_expiry      = max(1, round(ehl))
        rec_aet_wait    = max(1, round(ehl / 2))
        rec_reentry_win = max(2, round(ehl * 2))
    else:
        rec_expiry      = _CURRENT_EXPIRY
        rec_aet_wait    = _CURRENT_AET_WAIT
        rec_reentry_win = _CURRENT_REENTRY_WIN

    return EhlResult(
        delays                = delays,
        avg_r_at_delay        = avg_r_at_delay,
        half_life_candles     = round(ehl, 2) if not math.isnan(ehl) else float("nan"),
        r_at_zero             = round(r0, 4),
        r_half                = round(r_50, 4),
        per_strategy          = per_strategy,
        per_candle_drift_pct  = round(per_candle_drift_pct * 100, 6),
        recommended_expiry    = rec_expiry,
        recommended_aet_wait  = rec_aet_wait,
        recommended_reentry_win = rec_reentry_win,
        total_trades          = len(all_trades),
        days_used             = len(day_results),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Report formatter
# ─────────────────────────────────────────────────────────────────────────────

def format_ehl_report(result: EhlResult) -> str:
    """
    Return the Markdown block for the EHL section (Section 4e) of the report.
    """
    lines: List[str] = [
        "## Section 4e -- Edge Half-Life (EHL) Analysis",
        "",
        "> **What this measures:** How many 5-minute candles after a signal the"
        " strategy retains at least half of its original R-multiple edge."
        " The result directly calibrates three execution timing parameters.",
        "",
    ]

    if result.total_trades == 0:
        lines += [
            "_No trades recorded -- EHL analysis skipped._",
            "",
            f"_Drift model: {result.per_candle_drift_pct:.4f}% per candle"
            f" (based on {result.days_used} replay days)._",
            "",
        ]
        return "\n".join(lines)

    ehl_str = (
        f"{result.half_life_candles:.1f} candles"
        if not math.isnan(result.half_life_candles)
        else "beyond max delay tested (>{} candles)".format(result.delays[-1])
    )

    lines += [
        "### Summary",
        "",
        f"| Item | Value |",
        f"|------|-------|",
        f"| Baseline edge (R at delay=0) | {result.r_at_zero:+.3f}R |",
        f"| Half-life threshold (50% of baseline) | {result.r_half:+.3f}R |",
        f"| **Edge Half-Life** | **{ehl_str}** |",
        f"| Per-candle adverse drift modelled | {result.per_candle_drift_pct:.4f}% of entry price |",
        f"| Trades analysed | {result.total_trades} |",
        "",
    ]

    # ── Decay table ───────────────────────────────────────────────────────────
    lines += [
        "### R-Multiple Decay by Entry Delay",
        "",
        "| Candles Delayed | Avg R | % of Baseline | Edge Status |",
        "|-----------------|-------|---------------|-------------|",
    ]
    for d, r in zip(result.delays, result.avg_r_at_delay):
        if result.r_at_zero != 0.0:
            pct_of_base = r / result.r_at_zero * 100.0
        else:
            pct_of_base = 0.0
        status = _edge_status(pct_of_base)
        marker = "  **<-- half-life**" if (
            not math.isnan(result.half_life_candles)
            and abs(d - result.half_life_candles) < 0.75
        ) else ""
        lines.append(
            f"| {d} candles ({d*5} min) "
            f"| {r:+.3f}R "
            f"| {pct_of_base:.0f}% "
            f"| {status}{marker} |"
        )
    lines.append("")

    # ── Per-strategy breakdown ────────────────────────────────────────────────
    if result.per_strategy:
        lines += [
            "### Per-Strategy Half-Life",
            "",
            "| Strategy | Trades | R@0 | Half-Life | Interpretation |",
            "|----------|--------|-----|-----------|----------------|",
        ]
        for s in sorted(result.per_strategy.values(), key=lambda x: -x.trades):
            if math.isnan(s.half_life):
                hl_str = ">{}c".format(result.delays[-1])
            else:
                hl_str = f"{s.half_life:.1f}c"
            interp = _strategy_interp(s.half_life, result.delays[-1])
            lines.append(
                f"| {s.strategy} | {s.trades} | {s.r_at_zero:+.3f}R"
                f" | {hl_str} | {interp} |"
            )
        lines.append("")

    # ── Calibration recommendations ───────────────────────────────────────────
    lines += [
        "### Calibration vs Current Execution Parameters",
        "",
        "| Parameter | Current Value | EHL-Derived Recommendation | Status |",
        "|-----------|--------------|---------------------------|--------|",
    ]
    lines.append(
        f"| `LIMIT_CANDLE_EXPIRY` "
        f"| {_CURRENT_EXPIRY} candles "
        f"| {result.recommended_expiry} candles "
        f"| {_calibration_status(_CURRENT_EXPIRY, result.recommended_expiry, 'expiry')} |"
    )
    lines.append(
        f"| `AET_MAX_WAIT_CANDLES` "
        f"| {_CURRENT_AET_WAIT} candles "
        f"| {result.recommended_aet_wait} candles "
        f"| {_calibration_status(_CURRENT_AET_WAIT, result.recommended_aet_wait, 'wait')} |"
    )
    lines.append(
        f"| `REENTRY_WINDOW_CANDLES` "
        f"| {_CURRENT_REENTRY_WIN} candles "
        f"| {result.recommended_reentry_win} candles "
        f"| {_calibration_status(_CURRENT_REENTRY_WIN, result.recommended_reentry_win, 'reentry')} |"
    )
    lines.append("")

    # ── Overall verdict ───────────────────────────────────────────────────────
    lines.append("### Verdict")
    lines.append("")
    if math.isnan(result.half_life_candles):
        lines.append(
            "> Edge persists beyond the max tested delay "
            f"({result.delays[-1]} candles / {result.delays[-1]*5} min). "
            "This is characteristic of slow-decay strategies (trend-following). "
            "Current timing parameters are conservative -- no urgent tuning needed."
        )
    elif result.half_life_candles <= 2.0:
        lines.append(
            f"> **Short half-life ({result.half_life_candles:.1f} candles = "
            f"{result.half_life_candles*5:.0f} min).** "
            "Classic mean-reversion / liquidity-bounce profile. "
            "The AI must enter quickly -- orders that wait more than "
            f"{result.recommended_expiry} candles are likely to find "
            "the edge already gone. Confirm that `LIMIT_CANDLE_EXPIRY` "
            f"is <= {result.recommended_expiry}."
        )
    elif result.half_life_candles <= 4.0:
        lines.append(
            f"> **Medium half-life ({result.half_life_candles:.1f} candles = "
            f"{result.half_life_candles*5:.0f} min).** "
            "The current execution parameters look well-calibrated for this decay rate. "
            "A short adaptive-timing delay is acceptable."
        )
    else:
        lines.append(
            f"> **Long half-life ({result.half_life_candles:.1f} candles = "
            f"{result.half_life_candles*5:.0f} min).** "
            "The signal retains edge over multiple candles -- consistent with "
            "trend or momentum signals. Wider re-entry and longer limit expiry are justified."
        )
    lines.append("")

    lines += [
        "> **Drift model note:** adverse drift per candle is empirically derived"
        " from average |Nifty daily change| across the replay period divided by"
        f" {CANDLES_PER_DAY} intraday candles. Actual slippage may vary.",
        "",
    ]

    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _interpolate_half_life(r_series: List[float], delays: List[int], target: float) -> float:
    """
    Return the delay (possibly fractional) where the R-series crosses *target*
    on the way down. Returns NaN if R never falls to target within the series.
    """
    if not r_series or r_series[0] <= 0:
        return float("nan")

    for i in range(1, len(r_series)):
        prev_r = r_series[i - 1]
        curr_r = r_series[i]
        # Crossed going downward
        if prev_r >= target >= curr_r:
            if prev_r == curr_r:
                return float(delays[i - 1])
            # Linear interpolation
            frac = (prev_r - target) / (prev_r - curr_r)
            return delays[i - 1] + frac
    return float("nan")


def _edge_status(pct_of_base: float) -> str:
    if pct_of_base >= 90:  return "Full strength"
    if pct_of_base >= 70:  return "Strong"
    if pct_of_base >= 50:  return "Half"
    if pct_of_base >= 25:  return "Weak"
    if pct_of_base > 0:    return "Marginal"
    return "Gone / negative"


def _strategy_interp(half_life: float, max_delay: int) -> str:
    if math.isnan(half_life):
        return f"Slow decay -- persist beyond {max_delay} candles"
    if half_life <= 1.5:
        return "Very fast -- enter immediately"
    if half_life <= 3.0:
        return "Fast -- short delays only"
    if half_life <= 5.0:
        return "Moderate -- adaptive timing OK"
    return "Slow -- longer expiry tolerated"


def _calibration_status(current: int, recommended: int, kind: str) -> str:
    diff = current - recommended
    if diff == 0:
        return "OK -- exact match"
    if kind == "expiry":
        # expiry should ideally equal half-life; tighter is safer
        if diff > 0:
            return f"OK -- current is {diff} candle(s) looser than EHL (acceptable)"
        return f"WARNING -- current is {abs(diff)} candle(s) tighter than EHL (may under-fill)"
    if kind == "wait":
        # AET wait should be <= half-life // 2; tighter is safer
        if diff >= 0:
            return f"OK -- current is within EHL budget"
        return f"WARNING -- current waits {abs(diff)} candle(s) longer than recommended"
    if kind == "reentry":
        # re-entry window should be <= 2x half-life; tighter is safer
        if diff >= 0:
            return f"OK -- current window is within 2x EHL"
        return f"INFO -- current window extends {abs(diff)} candles beyond 2x EHL"
    return "OK"
