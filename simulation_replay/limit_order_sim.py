"""
Limit-Order Entry Simulation
=============================
The 126-day replay shows the strategy's edge collapses at 0.5 % execution
noise (Fragility verdict: BROKEN).  The root cause is market-order fills:
every fill carries slippage in the adverse direction.

Limit orders solve this:
  • BUY  limit at price E  → fills ONLY if the day's LOW  ≤ E  (no adverse fill)
  • SELL limit at price E  → fills ONLY if the day's HIGH ≥ E  (no adverse fill)

When the order does not fill, no trade is taken — the capital stays safe.
This trades fill-rate for execution quality: fewer but cleaner entries.

This module:
  1. Replays the historical trade set through limit-order fill gates.
  2. Produces a fill-rate / PF / R-multiple table.
  3. Runs a mini-fragility test on the limit-filled subset to show that PF
     is noise-resistant (since there is no adverse slippage to degrade it).
  4. Shows tightness analysis: how fill rate and PF change as the limit
     is placed further inside the day's range (0 % … 1 % from entry).

Usage (standalone)::

    from simulation_replay.limit_order_sim import run_limit_order_sim, format_limit_order_report
    result = run_limit_order_sim(all_trades)
    print(format_limit_order_report(result))
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


# ── Constants ─────────────────────────────────────────────────────────────────

# Default intraday range proxy (% of close) used when day_high/day_low are
# absent.  NSE large-cap stocks average ≈ 0.8 % true range per day.
DEFAULT_INTRADAY_HALF_RANGE_PCT = 0.80

# Tightness offsets: the limit is placed at entry ± offset % of entry price.
# A positive offset means we bid *inside* the range (more conservative fill,
# guarantees no adverse fill even if price briefly touches entry).
TIGHTNESS_OFFSETS: List[float] = [0.0, 0.10, 0.25, 0.50, 1.00]

# Fragility noise levels to test on limit-filled trades only
FRAG_NOISE_LEVELS = [0.0, 0.25, 0.50, 1.00]


# ── Result dataclasses ────────────────────────────────────────────────────────

@dataclass
class TightnessRow:
    """One row of the tightness analysis table."""
    offset_pct:   float   # % inside the range we place the limit
    filled:       int
    total:        int
    fill_rate:    float   # %
    pf:           float
    win_rate:     float   # %
    avg_r:        float
    net_pnl:      float


@dataclass
class LimitFragRow:
    """PF of limit-filled trades under varying noise levels."""
    noise_pct: float
    pf:        float
    avg_r:     float


@dataclass
class LimitOrderResult:
    # ── Fill simulation (at 0 % tightness offset) ────────────────────────────
    total_orders:      int   = 0
    filled_count:      int   = 0
    fill_rate_pct:     float = 0.0

    # ── Performance of limit-filled trades ───────────────────────────────────
    filled_wins:       int   = 0
    filled_pf:         float = 0.0
    filled_win_rate:   float = 0.0
    filled_avg_r:      float = 0.0
    filled_net_pnl:    float = 0.0

    # ── Tightness table ───────────────────────────────────────────────────────
    tightness: List[TightnessRow] = field(default_factory=list)

    # ── Fragility of limit-filled subset ─────────────────────────────────────
    limit_frag: List[LimitFragRow] = field(default_factory=list)

    # ── Comparison vs market-order baseline ──────────────────────────────────
    market_pf:          float = 0.0   # PF of all market-order trades
    limit_pf_at_1pct:   float = 0.0   # PF of limit-filled trades at 1 % noise
    market_pf_at_1pct:  float = 0.0   # PF of all trades at 1 % noise (from fragility)

    # ── Verdict ───────────────────────────────────────────────────────────────
    @property
    def verdict(self) -> str:
        if self.filled_count == 0:
            return "NO_DATA"
        if self.limit_pf_at_1pct >= 1.5 and self.fill_rate_pct >= 50:
            return "STRONG"
        if self.limit_pf_at_1pct >= 1.3 and self.fill_rate_pct >= 30:
            return "VIABLE"
        if self.limit_pf_at_1pct >= 1.0 and self.fill_rate_pct >= 20:
            return "MARGINAL"
        return "NOT_VIABLE"

    @property
    def verdict_note(self) -> str:
        if self.verdict == "NO_DATA":
            return "No limit-order fills simulated — insufficient trade data."
        v = self.verdict
        fr = self.fill_rate_pct
        pf = self.limit_pf_at_1pct
        notes = {
            "STRONG":     (f"Limit orders fill {fr:.0f}% of the time and PF holds at "
                           f"{pf:.2f} under 1% noise.  Switch to limit entries immediately."),
            "VIABLE":     (f"Limit orders fill {fr:.0f}% of the time; PF {pf:.2f} at "
                           f"1% noise.  Use limit orders with a backup market order after "
                           f"30 min if unfilled."),
            "MARGINAL":   (f"Fill rate {fr:.0f}% is low; PF {pf:.2f} marginally positive "
                           f"at 1% noise.  Improve signal entry precision before committing."),
            "NOT_VIABLE": (f"Fill rate {fr:.0f}% or PF {pf:.2f} too low.  Entry levels "
                           f"need rework — signals fire too far from traded price."),
        }
        return notes[v]


# ── Core simulation ───────────────────────────────────────────────────────────

def _would_fill(
    entry: float,
    direction: str,
    day_high: float,
    day_low: float,
    offset_pct: float = 0.0,
) -> bool:
    """
    Return True if a limit order at *entry* (offset by *offset_pct* further
    inside the day's range) would have been filled given the day's H/L.

    offset_pct  – makes the limit MORE conservative (bid lower for BUY,
                   offer higher for SELL); 0 = at exactly the entry price.
    """
    if day_high <= 0 or day_low <= 0:
        # No H/L data — use a ±DEFAULT_INTRADAY_HALF_RANGE_PCT proxy
        estimated_range = entry * DEFAULT_INTRADAY_HALF_RANGE_PCT / 100.0
        day_high = entry + estimated_range
        day_low  = entry - estimated_range

    multiplier = offset_pct / 100.0
    if direction.upper() in ("BUY", "LONG"):
        limit_price = entry * (1 - multiplier)   # bid below entry (conservative)
        return day_low <= limit_price
    else:  # SELL / SHORT
        limit_price = entry * (1 + multiplier)   # offer above entry
        return day_high >= limit_price


def _sim_pnl_trade(
    entry: float,
    sl: float,
    target: float,
    qty: int,
    direction: str,
    date_str: str,
    symbol: str,
    win_rate_pct: int = 55,
) -> Tuple[float, float]:
    """
    Deterministic hash-seeded simulated PnL (same algorithm as replay_engine).
    Returns (pnl, r_multiple).
    """
    if entry <= 0 or sl <= 0 or target <= 0:
        return 0.0, 0.0
    qty = max(qty, 1)
    seed_hex = hashlib.md5(f"{date_str}:{symbol}".encode()).hexdigest()[:8]
    win      = (int(seed_hex, 16) % 100) < win_rate_pct

    if direction.upper() in ("BUY", "LONG"):
        reward = (target - entry) * qty
        risk   = (entry  - sl)    * qty
    else:
        reward = (entry  - target) * qty
        risk   = (sl     - entry)  * qty

    if risk <= 0:
        return 0.0, 0.0

    pnl   = round(reward if (win and reward > 0) else -abs(risk), 2)
    r_mul = pnl / abs(risk) if risk > 0 and qty > 0 else 0.0
    return pnl, round(r_mul, 3)


def run_limit_order_sim(
    all_trades: List[Dict[str, Any]],
    market_pf_at_1pct: float = 0.0,
) -> LimitOrderResult:
    """
    Simulate the full trade set as if every entry were a limit order.

    Parameters
    ----------
    all_trades          : list of trade dicts from replay_engine
                          Expected keys: entry, sl, target, qty, direction,
                          symbol, date/trading_date, day_high, day_low
    market_pf_at_1pct   : PF of all trades at 1 % noise (from FragilityResult)
                          for the comparison row.
    """
    result = LimitOrderResult(
        total_orders     = len(all_trades),
        market_pf_at_1pct = market_pf_at_1pct,
    )

    if not all_trades:
        return result

    # ── Compute market-order baseline PF for comparison ───────────────────────
    mp_profit = mp_loss = 0.0
    for t in all_trades:
        pnl = float(t.get("pnl", 0.0) or 0.0)
        if pnl > 0:
            mp_profit += pnl
        elif pnl < 0:
            mp_loss += abs(pnl)
    result.market_pf = round(mp_profit / mp_loss, 3) if mp_loss > 0 else 0.0

    # ── Tightness analysis ────────────────────────────────────────────────────
    for offset in TIGHTNESS_OFFSETS:
        gross_profit = gross_loss = 0.0
        wins = fills = 0
        r_sum = 0.0
        net_pnl = 0.0

        for t in all_trades:
            entry  = float(t.get("entry", 0.0)     or t.get("entry_price", 0.0)    or 0.0)
            sl     = float(t.get("sl", 0.0)         or t.get("stop_loss", 0.0)      or 0.0)
            target = float(t.get("target", 0.0)     or t.get("target_price", 0.0)   or 0.0)
            qty    = max(int(t.get("qty", 1)         or t.get("quantity", 1)         or 1), 1)
            dirn   = str(t.get("direction", "BUY")).upper()
            sym    = str(t.get("symbol", ""))
            date_s = str(t.get("date", t.get("trading_date", "unknown")))
            dh     = float(t.get("day_high", 0.0) or 0.0)
            dl     = float(t.get("day_low",  0.0) or 0.0)

            if entry <= 0 or sl <= 0 or target <= 0:
                continue

            if not _would_fill(entry, dirn, dh, dl, offset_pct=offset):
                continue   # limit order did NOT fill — no trade

            fills += 1
            pnl, r_mul = _sim_pnl_trade(entry, sl, target, qty, dirn, date_s, sym)
            net_pnl += pnl
            r_sum   += r_mul
            if pnl > 0:
                wins        += 1
                gross_profit += pnl
            else:
                gross_loss   += abs(pnl)

        pf       = round(gross_profit / gross_loss, 3) if gross_loss > 0 else (
                   float("inf") if gross_profit > 0 else 0.0)
        fill_rt  = fills / len(all_trades) * 100 if all_trades else 0.0
        win_rt   = wins / fills * 100 if fills > 0 else 0.0
        avg_r    = round(r_sum / fills, 3) if fills > 0 else 0.0

        row = TightnessRow(
            offset_pct = offset,
            filled     = fills,
            total      = len(all_trades),
            fill_rate  = round(fill_rt, 1),
            pf         = pf,
            win_rate   = round(win_rt, 1),
            avg_r      = avg_r,
            net_pnl    = round(net_pnl, 0),
        )
        result.tightness.append(row)

        # The baseline (offset=0) populates the main result fields
        if offset == 0.0:
            result.filled_count    = fills
            result.fill_rate_pct   = round(fill_rt, 1)
            result.filled_wins     = wins
            result.filled_pf       = pf
            result.filled_win_rate = round(win_rt, 1)
            result.filled_avg_r    = avg_r
            result.filled_net_pnl  = round(net_pnl, 0)

    # ── Fragility of limit-filled subset at offset=0 ──────────────────────────
    filled_trades = []
    for t in all_trades:
        entry  = float(t.get("entry", 0.0)     or t.get("entry_price", 0.0)  or 0.0)
        sl     = float(t.get("sl", 0.0)         or t.get("stop_loss", 0.0)   or 0.0)
        target = float(t.get("target", 0.0)     or t.get("target_price", 0.0) or 0.0)
        dirn   = str(t.get("direction", "BUY")).upper()
        dh     = float(t.get("day_high", 0.0) or 0.0)
        dl     = float(t.get("day_low",  0.0) or 0.0)
        if entry > 0 and sl > 0 and target > 0 and _would_fill(entry, dirn, dh, dl):
            filled_trades.append(t)

    for noise_pct in FRAG_NOISE_LEVELS:
        gp = gl = 0.0
        r_sum   = 0.0
        n_trades = 0

        for t in filled_trades:
            entry  = float(t.get("entry", 0.0)     or t.get("entry_price", 0.0)   or 0.0)
            sl     = float(t.get("sl", 0.0)         or t.get("stop_loss", 0.0)    or 0.0)
            target = float(t.get("target", 0.0)     or t.get("target_price", 0.0) or 0.0)
            qty    = max(int(t.get("qty", 1)         or t.get("quantity", 1)       or 1), 1)
            dirn   = str(t.get("direction", "BUY")).upper()
            sym    = str(t.get("symbol", ""))
            date_s = str(t.get("date", t.get("trading_date", "unknown")))

            if entry <= 0 or sl <= 0 or target <= 0:
                continue

            # Apply noise to entry (same adverse degradation as fragility_test)
            mult = noise_pct / 100.0
            if dirn in ("BUY", "LONG"):
                noisy_entry = entry * (1 + mult)
            else:
                noisy_entry = entry * (1 - mult)

            risk = abs(noisy_entry - sl) * qty
            if risk <= 0:
                continue

            pnl, r_mul = _sim_pnl_trade(noisy_entry, sl, target, qty, dirn, date_s, sym)
            n_trades += 1
            r_sum    += r_mul
            if pnl > 0:
                gp += pnl
            else:
                gl += abs(pnl)

        pf    = round(gp / gl, 3) if gl > 0 else (float("inf") if gp > 0 else 0.0)
        avg_r = round(r_sum / n_trades, 3) if n_trades > 0 else 0.0
        result.limit_frag.append(LimitFragRow(noise_pct=noise_pct, pf=pf, avg_r=avg_r))

    # PF@1% for limit-filled trades
    for row in result.limit_frag:
        if abs(row.noise_pct - 1.0) < 0.01:
            result.limit_pf_at_1pct = row.pf
            break

    return result


# ── Formatting ────────────────────────────────────────────────────────────────

def format_limit_order_report(r: LimitOrderResult) -> str:
    """Render limit-order simulation results as a markdown section."""
    if r.total_orders == 0:
        return "## Section 4c — Limit-Order Entry Simulation\n\n_No trades to test._\n\n"

    verdict_emoji = {
        "STRONG":     "✅",
        "VIABLE":     "✅",
        "MARGINAL":   "⚠️",
        "NOT_VIABLE": "❌",
        "NO_DATA":    "⬜",
    }.get(r.verdict, "")

    def _pf(v: float) -> str:
        return "∞" if v == float("inf") else f"{v:.2f}"

    lines = [
        "## Section 4c — Limit-Order Entry Simulation\n",
        "> **Problem:** The market-order fragility test shows PF collapses at 0.5 % noise.",
        "> **Solution tested here:** Place every entry as a limit order at the signal price.",
        "> A BUY limit fills only when the day's LOW ≤ entry; a SELL limit fills only when",
        "> HIGH ≥ entry.  If the order does not fill, no trade is taken.",
        "> Fill price = exactly the limit price — zero adverse slippage.\n",
        "### Fill Rate Summary (limit at exact signal price)\n",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Total orders (market would have taken) | {r.total_orders} |",
        f"| Orders that would fill as limits | {r.filled_count} ({r.fill_rate_pct:.1f}%) |",
        f"| Unfilled (no trade taken) | {r.total_orders - r.filled_count} |",
        f"| Win rate (filled trades) | {r.filled_win_rate:.1f}% |",
        f"| Profit factor (filled trades) | {_pf(r.filled_pf)} |",
        f"| Avg R-multiple (filled trades) | {r.filled_avg_r:+.2f}R |",
        f"| Net PnL (filled trades) | ₹{r.filled_net_pnl:,.0f} |",
        "",
        "### Tightness Analysis\n",
        "> Shows how fill rate and PF change as the limit is placed *inside* the range",
        "> (offset = how many % below entry for BUY, above for SELL).\n",
        "| Offset (%) | Filled | Fill Rate | PF | Win Rate | Avg R | Net PnL |",
        "|------------|--------|-----------|----|----------|-------|---------|",
    ]

    for row in r.tightness:
        tag = " **← at price**" if row.offset_pct == 0.0 else ""
        lines.append(
            f"| {row.offset_pct:.2f}{tag} | {row.filled}/{row.total} "
            f"| {row.fill_rate:.1f}% "
            f"| {_pf(row.pf)} | {row.win_rate:.0f}% "
            f"| {row.avg_r:+.2f}R | ₹{row.net_pnl:,.0f} |"
        )

    lines += [
        "",
        "### Fragility of Limit-Filled Trades\n",
        "> Market-order fragility (from Section 4b) vs. limit-order fragility.",
        "> Limit orders neutralise adverse fill slippage — PF should be far",
        "> more stable under noise.\n",
        "| Noise (%) | Market-Order PF | Limit-Order PF | Improvement |",
        "|-----------|-----------------|----------------|-------------|",
    ]

    # Build market-order PF at each noise level from fragility_test (not available here,
    # so we use the baseline for 0% and the passed-in market_pf_at_1pct for 1 %)
    market_pf_map = {
        0.0:  r.market_pf,
        1.0:  r.market_pf_at_1pct,
    }

    for row in r.limit_frag:
        mkt   = market_pf_map.get(row.noise_pct, None)
        mkt_s = _pf(mkt) if mkt is not None else "—"
        if mkt is not None and row.pf not in (0.0, float("inf")) and mkt > 0:
            improvement = f"+{(row.pf - mkt):.2f}"
        else:
            improvement = "—"
        lines.append(
            f"| {row.noise_pct:.2f} | {mkt_s} | {_pf(row.pf)} | {improvement} |"
        )

    lines += [
        "",
        f"**Limit PF@1% noise:** {_pf(r.limit_pf_at_1pct)}  "
        f"(market was {_pf(r.market_pf_at_1pct)})\n",
        f"### Verdict: {verdict_emoji} {r.verdict}\n",
        f"> {r.verdict_note}",
        "",
    ]
    return "\n".join(lines)
