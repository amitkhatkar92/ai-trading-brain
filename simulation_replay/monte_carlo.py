"""
Monte Carlo Equity Simulation
==============================
Bootstrap-resamples the replay's trade PnL list N times to stress-test the
equity curve.  Answers three questions:

  1. What is the realistic *range* of outcomes (5th–95th percentile equity)?
  2. What is the worst-case drawdown at the 95th-percentile (conservative)?
  3. What is the probability of ruin (equity falling below 50 % of capital)?

No external dependencies — pure Python + random module.

Usage (standalone):
    from simulation_replay.monte_carlo import run_monte_carlo, format_mc_report
    result = run_monte_carlo(pnl_list, capital=1_000_000)
    print(format_mc_report(result))
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import List


# ── Constants ─────────────────────────────────────────────────────────────────

N_SIMS            = 1_000    # number of bootstrap iterations
RUIN_THRESHOLD    = 0.50     # equity < 50 % of starting capital → ruin
SEED              = 42       # reproducible results


# ── Data classes ──────────────────────────────────────────────────────────────

@dataclass
class MonteCarloResult:
    n_sims:               int   = N_SIMS
    n_trades_per_sim:     int   = 0
    starting_capital:     float = 0.0

    # Final-equity distribution (gross, before costs)
    median_final_equity:  float = 0.0
    p5_final_equity:      float = 0.0     # worst 5 % outcome
    p95_final_equity:     float = 0.0     # best 5 % outcome
    median_return_pct:    float = 0.0
    p5_return_pct:        float = 0.0
    p95_return_pct:       float = 0.0

    # Drawdown distribution (peak-to-trough, % of capital)
    median_max_dd:        float = 0.0
    p95_max_dd:           float = 0.0    # conservative (worst 5 %) drawdown
    p99_max_dd:           float = 0.0

    # Risk of ruin
    ruin_probability:     float = 0.0    # P(equity < 50 % capital) in pct
    probability_of_loss:  float = 0.0    # P(final_equity < starting_capital) in pct

    # Sharpe estimate (median equity path)
    sharpe_estimate:      float = 0.0

    # Raw distributions for charting (omitted from text report)
    _final_equities:      List[float] = field(default_factory=list, repr=False)
    _max_drawdowns:       List[float] = field(default_factory=list, repr=False)

    @property
    def verdict(self) -> str:
        if self.p95_max_dd <= 10 and self.ruin_probability < 1 and self.p5_return_pct >= -5:
            return "ROBUST"
        if self.p95_max_dd <= 20 and self.ruin_probability < 5:
            return "ACCEPTABLE"
        if self.p95_max_dd <= 30 and self.ruin_probability < 15:
            return "MARGINAL"
        return "HIGH_RISK"

    @property
    def verdict_note(self) -> str:
        notes = {
            "ROBUST":      "Equity curve is stable across 95 % of simulations — suitable for live paper trading.",
            "ACCEPTABLE":  "Drawdowns are manageable.  Run a full 6-month replay before paper trading.",
            "MARGINAL":    "Significant tail risk detected.  Tighten position sizing before paper trading.",
            "HIGH_RISK":   "Ruin probability or drawdown exceeds safe thresholds.  DO NOT paper trade yet.",
        }
        return notes[self.verdict]


# ── Core simulation ───────────────────────────────────────────────────────────

def run_monte_carlo(
    pnl_list: List[float],
    capital:   float = 1_000_000.0,
    n_sims:    int   = N_SIMS,
    seed:      int   = SEED,
) -> MonteCarloResult:
    """
    Bootstrap-resample *pnl_list* `n_sims` times.

    Each simulation draws len(pnl_list) trades with replacement and computes
    the resulting equity curve, max drawdown, and final equity.
    """
    result = MonteCarloResult(
        n_sims            = n_sims,
        n_trades_per_sim  = len(pnl_list),
        starting_capital  = capital,
    )

    if not pnl_list:
        return result   # nothing to simulate

    rng = random.Random(seed)
    final_equities: List[float] = []
    max_drawdowns:  List[float] = []
    daily_returns:  List[float] = []   # for Sharpe estimate

    for _ in range(n_sims):
        sample = rng.choices(pnl_list, k=len(pnl_list))
        equity   = capital
        peak     = capital
        max_dd   = 0.0
        for pnl in sample:
            equity += pnl
            if equity > peak:
                peak = equity
            dd = (peak - equity) / peak * 100 if peak > 0 else 0.0
            if dd > max_dd:
                max_dd = dd
        final_equities.append(equity)
        max_drawdowns.append(max_dd)
        daily_returns.append((equity - capital) / capital * 100)

    final_equities.sort()
    max_drawdowns.sort()

    n = len(final_equities)
    p5_idx  = max(0, int(0.05 * n) - 1)
    p50_idx = int(0.50 * n) - 1
    p95_idx = min(n - 1, int(0.95 * n))
    p99_idx = min(n - 1, int(0.99 * n))

    result._final_equities = final_equities
    result._max_drawdowns  = max_drawdowns

    result.median_final_equity = final_equities[p50_idx]
    result.p5_final_equity     = final_equities[p5_idx]
    result.p95_final_equity    = final_equities[p95_idx]

    result.median_return_pct = (result.median_final_equity - capital) / capital * 100
    result.p5_return_pct     = (result.p5_final_equity     - capital) / capital * 100
    result.p95_return_pct    = (result.p95_final_equity    - capital) / capital * 100

    result.median_max_dd = max_drawdowns[p50_idx]
    result.p95_max_dd    = max_drawdowns[p95_idx]
    result.p99_max_dd    = max_drawdowns[p99_idx]

    ruin_count = sum(1 for e in final_equities if e < capital * RUIN_THRESHOLD)
    loss_count = sum(1 for e in final_equities if e < capital)
    result.ruin_probability  = ruin_count / n * 100
    result.probability_of_loss = loss_count / n * 100

    # Sharpe estimate: annualise assuming 252 trading days.
    # We have (n_trades / target_days) trades/day on the median path.
    mean_r = sum(daily_returns) / n
    if n > 1:
        variance = sum((r - mean_r) ** 2 for r in daily_returns) / (n - 1)
        std_r    = math.sqrt(variance) if variance > 0 else 1e-9
        result.sharpe_estimate = round((mean_r / std_r) * math.sqrt(252), 2)

    return result


# ── Formatting ────────────────────────────────────────────────────────────────

def format_mc_report(r: MonteCarloResult, capital: float = 1_000_000.0) -> str:
    """Render MC results as a markdown section."""
    verdict_emoji = {
        "ROBUST": "✅", "ACCEPTABLE": "⚠️", "MARGINAL": "⚠️", "HIGH_RISK": "❌"
    }.get(r.verdict, "")

    lines = [
        "## Section 4a — Monte Carlo Equity Simulation\n",
        f"> {r.n_sims:,} bootstrap simulations · {r.n_trades_per_sim} trades each  "
        f"· Starting capital ₹{capital:,.0f}\n",
        "### Equity Distribution\n",
        "| Scenario | Final Equity | Return |",
        "|----------|-------------|--------|",
        f"| Best 5% (p95) | ₹{r.p95_final_equity:,.0f} | {r.p95_return_pct:+.1f}% |",
        f"| Median (p50)  | ₹{r.median_final_equity:,.0f} | {r.median_return_pct:+.1f}% |",
        f"| Worst 5% (p5) | ₹{r.p5_final_equity:,.0f} | {r.p5_return_pct:+.1f}% |",
        "",
        "### Drawdown & Risk\n",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Median max drawdown | {r.median_max_dd:.1f}% |",
        f"| 95th-pct max drawdown (conservative) | {r.p95_max_dd:.1f}% |",
        f"| 99th-pct max drawdown (extreme) | {r.p99_max_dd:.1f}% |",
        f"| Probability of loss (final < capital) | {r.probability_of_loss:.1f}% |",
        f"| Probability of ruin (equity < 50%) | {r.ruin_probability:.1f}% |",
        f"| Sharpe estimate (annualised) | {r.sharpe_estimate:.2f} |",
        "",
        f"### Verdict: {verdict_emoji} {r.verdict}\n",
        f"> {r.verdict_note}",
        "",
    ]
    return "\n".join(lines)
