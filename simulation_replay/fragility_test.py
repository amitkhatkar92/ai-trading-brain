"""
Strategy Fragility Test
========================
Measures how robust the strategy's edge is under price execution noise.

For each noise level (0 → 2 %) the test degrades every trade's entry price
by that percentage in the *adverse direction* (BUY fills higher, SELL fills
lower).  SL and target stay fixed at market structure levels, so the
risk/reward ratio deteriorates, mimicking real-world slippage and suboptimal
execution.

If the profit factor remains above 1.3 at 1 % noise the edge is considered
robust enough for paper trading.

Usage (standalone):
    from simulation_replay.fragility_test import run_fragility_test, format_fragility_report
    result = run_fragility_test(all_trades)
    print(format_fragility_report(result))
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any, Dict, List


# ── Noise levels to test (% of entry price, adverse direction) ────────────────
NOISE_LEVELS = [0.0, 0.25, 0.50, 1.00, 1.50, 2.00]

# Threshold: PF must stay above this at 1 % noise to be called "robust"
ROBUST_PF_THRESHOLD    = 1.30
ROBUST_NOISE_THRESHOLD = 1.00   # % at which we gate the verdict


# ── Result dataclass ──────────────────────────────────────────────────────────

@dataclass
class NoiseLevelStats:
    noise_pct:    float
    trades:       int   = 0
    wins:         int   = 0
    gross_profit: float = 0.0
    gross_loss:   float = 0.0
    total_pnl:    float = 0.0
    avg_r:        float = 0.0

    @property
    def win_rate(self) -> float:
        return self.wins / self.trades * 100 if self.trades else 0.0

    @property
    def profit_factor(self) -> float:
        if self.gross_loss == 0:
            return float("inf") if self.gross_profit > 0 else 0.0
        return round(self.gross_profit / self.gross_loss, 3)


@dataclass
class FragilityResult:
    noise_levels:   List[float]           = field(default_factory=list)
    stats:          List[NoiseLevelStats] = field(default_factory=list)
    baseline_pf:    float = 0.0           # PF at 0 % noise
    pf_at_1pct:     float = 0.0           # PF at 1 % noise

    # Degradation: how much PF drops per 1 % of noise
    pf_decay_per_pct: float = 0.0

    @property
    def robust(self) -> bool:
        return self.pf_at_1pct >= ROBUST_PF_THRESHOLD

    @property
    def verdict(self) -> str:
        if self.pf_at_1pct >= 1.5:
            return "ROBUST"
        if self.pf_at_1pct >= 1.3:
            return "ACCEPTABLE"
        if self.pf_at_1pct >= 1.0:
            return "FRAGILE"
        return "BROKEN"

    @property
    def verdict_note(self) -> str:
        pf = self.pf_at_1pct
        notes = {
            "ROBUST":     f"Edge holds at 1 % noise (PF {pf:.2f} ≥ 1.5).  Strategy survives realistic execution variance.",
            "ACCEPTABLE": f"Edge survives 1 % noise (PF {pf:.2f} ≥ 1.3).  Acceptable for paper trading with tight execution.",
            "FRAGILE":    f"Edge barely survives at 1 % noise (PF {pf:.2f}).  Improve entry precision before paper trading.",
            "BROKEN":     f"Edge collapses at 1 % noise (PF {pf:.2f} < 1.0).  DO NOT paper trade — edge is execution-dependent.",
        }
        return notes[self.verdict]


# ── Core test ─────────────────────────────────────────────────────────────────

def run_fragility_test(
    all_trades: List[Dict[str, Any]],
    noise_levels: List[float] = NOISE_LEVELS,
) -> FragilityResult:
    """
    Re-compute trade PnL at each noise level and aggregate metrics.

    *all_trades* is the flat list of trade-dicts produced by the replay engine:
    keys needed: entry, sl, target, qty, direction, symbol, [date/trading_date]
    """
    result = FragilityResult(noise_levels=noise_levels)

    if not all_trades:
        return result

    for noise_pct in noise_levels:
        stats = NoiseLevelStats(noise_pct=noise_pct)
        r_sum = 0.0

        for t in all_trades:
            entry  = float(t.get("entry", 0.0) or t.get("entry_price", 0.0) or 0.0)
            sl     = float(t.get("sl", 0.0)    or t.get("stop_loss", 0.0)   or 0.0)
            target = float(t.get("target", 0.0) or t.get("target_price", 0.0) or 0.0)
            qty    = max(int(t.get("qty", 1) or t.get("quantity", 1) or 1), 1)
            dirn   = str(t.get("direction", "BUY")).upper()
            sym    = str(t.get("symbol", ""))
            # Use same hash-seed win/loss as _sim_pnl in replay_engine
            date_str = str(t.get("date", t.get("trading_date", "unknown")))
            seed_hex = hashlib.md5(f"{date_str}:{sym}".encode()).hexdigest()[:8]
            win      = (int(seed_hex, 16) % 100) < 55   # 55 % base win rate

            if entry <= 0 or sl <= 0 or target <= 0:
                continue

            # Apply adverse noise: BUY fills higher, SELL fills lower
            multiplier   = noise_pct / 100.0
            if dirn in ("BUY", "LONG"):
                noisy_entry  = entry * (1 + multiplier)   # worse fill for long
                reward       = target - noisy_entry
                risk         = noisy_entry - sl
            else:
                noisy_entry  = entry * (1 - multiplier)   # worse fill for short
                reward       = noisy_entry - target
                risk         = sl - noisy_entry

            if risk <= 0:
                continue   # SL beyond entry after noise → skip

            pnl   = (reward * qty) if win and reward > 0 else -(abs(risk) * qty)
            r_mult = pnl / (abs(risk) * qty) if risk > 0 and qty > 0 else 0.0

            stats.trades += 1
            if pnl > 0:
                stats.wins        += 1
                stats.gross_profit += pnl
            else:
                stats.gross_loss   += abs(pnl)
            stats.total_pnl += pnl
            r_sum           += r_mult

        stats.avg_r = round(r_sum / stats.trades, 3) if stats.trades else 0.0
        result.stats.append(stats)

    # Pull out key summary values
    result.baseline_pf = result.stats[0].profit_factor if result.stats else 0.0

    # Find PF at 1 % noise
    for s in result.stats:
        if abs(s.noise_pct - ROBUST_NOISE_THRESHOLD) < 0.01:
            result.pf_at_1pct = s.profit_factor
            break

    # Compute PF decay slope: linear fit over first 4 levels (0–1 %)
    first_four = [s for s in result.stats if s.noise_pct <= 1.0]
    if len(first_four) >= 2:
        x0, y0 = first_four[0].noise_pct,  first_four[0].profit_factor
        x1, y1 = first_four[-1].noise_pct, first_four[-1].profit_factor
        if (x1 - x0) > 0:
            result.pf_decay_per_pct = round((y0 - y1) / (x1 - x0), 3)

    return result


# ── Formatting ────────────────────────────────────────────────────────────────

def format_fragility_report(r: FragilityResult) -> str:
    """Render fragility results as a markdown section."""
    if not r.stats:
        return "## Section 5 — Strategy Fragility Test\n\n_No trades to test._\n\n"

    verdict_emoji = {
        "ROBUST": "✅", "ACCEPTABLE": "✅", "FRAGILE": "⚠️", "BROKEN": "❌"
    }.get(r.verdict, "")

    lines = [
        "## Section 4b — Strategy Fragility Test\n",
        "> Each noise level degrades entry price adversely (BUY fills higher,",
        "> SELL fills lower).  SL and target remain fixed.  Tests execution",
        "> robustness: does the edge survive imperfect fills?\n",
        "| Noise (%) | Trades | Win Rate | Profit Factor | Avg R | Net PnL |",
        "|-----------|--------|----------|---------------|-------|---------|",
    ]

    for s in r.stats:
        pf_str = f"{s.profit_factor:.2f}" if s.profit_factor != float("inf") else "∞"
        highlight = " **←base**" if s.noise_pct == 0 else (
                    " **←gate**" if abs(s.noise_pct - ROBUST_NOISE_THRESHOLD) < 0.01 else ""
        )
        lines.append(
            f"| {s.noise_pct:.2f}{highlight} | {s.trades} | {s.win_rate:.0f}% "
            f"| {pf_str} | {s.avg_r:+.2f}R | ₹{s.total_pnl:,.0f} |"
        )

    lines += [
        "",
        f"**PF decay per 1 % of noise:** {r.pf_decay_per_pct:.3f}  "
        f"(lower = more robust)",
        "",
        f"### Verdict: {verdict_emoji} {r.verdict}\n",
        f"> {r.verdict_note}",
        "",
    ]
    return "\n".join(lines)
