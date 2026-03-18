"""
Edge Distribution Map (EDM) Analyzer
======================================
Shows how the system's profits are actually generated across trades by
mapping R-multiple frequency — revealing whether the edge comes from
many small wins, few large wins, or a balanced distribution.

Why this matters
----------------
Two systems can share the same Profit Factor but have radically different
risk profiles:

    Profile        | Win rate | Win size | Loss size | Risk approach
    ---------------|----------|----------|-----------|---------------
    Mean-Reversion | High     | Small    | Moderate  | Tight SL critical
    Trend-Follow   | Low      | Large    | Small     | Wide SL tolerable
    Balanced       | Moderate | Moderate | Moderate  | Standard sizing

Profile classification drives:
  - Whether to use tight or wide stop-losses
  - Kelly fraction for position sizing
  - Whether drawdowns come from frequency (mean-rev) or size (trend-follow)

Metrics derived
---------------
    R-multiple         = trade PnL / (risk per unit × quantity)
    Payoff ratio       = avg winning R / avg |losing R|
    Win/Loss ratio     = win count / loss count
    Tail profit ratio  = 95th pct R / |5th pct R|  (>3 = tail-dependent)
    Loss concentration = losses from worst-25% trades / total gross loss

Profile thresholds
------------------
    Mean-Reversion : win_rate > 58 %  AND  payoff_ratio < 1.8
    Trend-Following: win_rate < 45 %  AND  payoff_ratio > 2.5
    Balanced       : all other cases
"""

from __future__ import annotations

import math
import statistics
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

# ── Bin configuration ─────────────────────────────────────────────────────────
_BIN_STEP  = 0.5      # R-multiple bin width
_BIN_MIN   = -3.0     # left edge of first bin (trades below go into overflow)
_BIN_MAX   =  5.0     # right edge of last bin (trades above go into overflow)
_BAR_SCALE =  30      # max ASCII bar width in characters

# ── Profile detection thresholds ─────────────────────────────────────────────
_MEAN_REV_WIN_RATE_MIN  = 58.0   # %
_MEAN_REV_PAYOFF_MAX    =  1.8
_TREND_WIN_RATE_MAX     = 45.0   # %
_TREND_PAYOFF_MIN       =  2.5

# ── Tail ratio threshold ──────────────────────────────────────────────────────
_TAIL_DEPENDENT_THRESHOLD = 3.0  # 95th / |5th| > 3 → tail-dependent


# ─────────────────────────────────────────────────────────────────────────────
# Data classes
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class BinEntry:
    """One bucket in the R-multiple histogram."""
    label:       str    # display label, e.g. "+1.0R"
    lower:       float  # inclusive lower bound
    upper:       float  # exclusive upper bound (except the overflow bins)
    count:       int    = 0
    is_overflow: bool   = False   # True for the tail catch-all bins


@dataclass
class StrategyEdgeProfile:
    """Per-strategy profile detail."""
    strategy:     str
    trades:       int
    win_rate:     float
    payoff_ratio: float
    avg_r:        float
    profile:      str   # "Mean-Reversion" / "Trend-Following" / "Balanced"


@dataclass
class EdmResult:
    """Full EDM analysis result."""
    bins:                List[BinEntry]  = field(default_factory=list)
    r_multiples:         List[float]    = field(default_factory=list)  # raw list

    # Aggregate statistics
    total_trades:        int   = 0
    win_count:           int   = 0
    loss_count:          int   = 0
    breakeven_count:     int   = 0

    win_rate:            float = 0.0   # %
    avg_r:               float = 0.0
    avg_win_r:           float = 0.0   # mean R of winning trades
    avg_loss_r:          float = 0.0   # mean |R| of losing trades
    payoff_ratio:        float = 0.0   # avg_win_r / avg_loss_r

    tail_profit_ratio:   float = 0.0   # 95th pct R / |5th pct R|
    loss_concentration:  float = 0.0   # % of total loss from worst-25% of losers

    profile:             str   = "Unknown"   # edge profile classification
    profile_description: str   = ""

    per_strategy:        Dict[str, StrategyEdgeProfile] = field(default_factory=dict)


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _make_bins() -> List[BinEntry]:
    """Build the fixed bin list from _BIN_MIN to _BIN_MAX with overflow buckets."""
    bins: List[BinEntry] = []

    # Underflow: < _BIN_MIN
    bins.append(BinEntry(
        label=f"<{_BIN_MIN:+.1f}R",
        lower=float("-inf"),
        upper=_BIN_MIN,
        is_overflow=True,
    ))

    lo = _BIN_MIN
    while lo < _BIN_MAX:
        hi = round(lo + _BIN_STEP, 10)
        # Format label: centre of bin, e.g. "-1.0R", "+0.5R"
        mid = (lo + hi) / 2.0
        label = f"{mid:+.1f}R"
        bins.append(BinEntry(label=label, lower=lo, upper=hi))
        lo = hi

    # Overflow: >= _BIN_MAX
    bins.append(BinEntry(
        label=f">={_BIN_MAX:+.1f}R",
        lower=_BIN_MAX,
        upper=float("inf"),
        is_overflow=True,
    ))

    return bins


def _classify_r(r: float, bins: List[BinEntry]) -> int:
    """Return index of the bin that r falls into."""
    for i, b in enumerate(bins):
        if b.lower <= r < b.upper:
            return i
    # edge case: exactly _BIN_MAX goes into overflow
    return len(bins) - 1


def _classify_profile(win_rate: float, payoff_ratio: float) -> Tuple[str, str]:
    """
    Return (profile_name, description) based on win-rate / payoff characteristics.
    """
    if win_rate > _MEAN_REV_WIN_RATE_MIN and payoff_ratio < _MEAN_REV_PAYOFF_MAX:
        return (
            "Mean-Reversion",
            "High-frequency small wins. Stop-loss discipline is critical — losses "
            "must be contained tightly or they will erase many small winners. "
            "Kelly fraction should be conservative (f < 0.20).",
        )
    if win_rate < _TREND_WIN_RATE_MAX and payoff_ratio > _TREND_PAYOFF_MIN:
        return (
            "Trend-Following",
            "Low win-rate with large winners. Drawdown periods are long but "
            "recoverable. Avoid exiting winners early — the edge lies in the tail. "
            "Kelly fraction can be moderate (f 0.15–0.30).",
        )
    return (
        "Balanced",
        "Moderate win-rate and payoff ratio. Equal emphasis on stop-loss control "
        "and letting winners run. Kelly fraction: standard sizing (f ~ 0.20). "
        "Review per-strategy profiles for more granular guidance.",
    )


def _tail_ratio(r_list: List[float]) -> float:
    """95th pct R / |5th pct R|.  Returns 0 if insufficient data."""
    if len(r_list) < 5:
        return 0.0
    p95 = statistics.quantiles(r_list, n=20)[18]   # 19/20 = 95th pct
    p05 = statistics.quantiles(r_list, n=20)[0]    # 1/20  =  5th pct
    if p05 >= 0.0:
        return 0.0   # no left tail
    return round(p95 / abs(p05), 3) if abs(p05) > 1e-9 else 0.0


def _loss_concentration(r_list: List[float]) -> float:
    """
    Percentage of total gross loss accounted for by the worst 25 % of losing trades.
    High value (>60 %) indicates clustered/catastrophic drawdown risk.
    """
    losses = sorted([r for r in r_list if r < 0.0])  # most-negative first
    if not losses:
        return 0.0
    total_loss = sum(losses)   # negative number
    n_worst = max(1, len(losses) // 4)
    worst_loss = sum(losses[:n_worst])  # most negative subset
    return round(worst_loss / total_loss * 100, 1) if total_loss < 0 else 0.0


# ─────────────────────────────────────────────────────────────────────────────
# Core analysis function
# ─────────────────────────────────────────────────────────────────────────────

def analyze_edge_distribution(
    day_results: list,   # List[DayCycleResult]
) -> EdmResult:
    """
    Build the Edge Distribution Map from a completed replay run.

    Parameters
    ----------
    day_results:
        List of ``DayCycleResult`` objects produced by ``ReplayOrchestrator``.

    Returns
    -------
    EdmResult — safe to consume even when no trades were executed.
    """
    result = EdmResult()
    bins = _make_bins()
    result.bins = bins

    if not day_results:
        return result

    # ── Collect trades and compute R-multiples ────────────────────────────────
    strat_trades: Dict[str, List[float]] = {}

    for dr in day_results:
        for t in dr.executed_trades:
            td = dict(t)
            pnl   = float(td.get("pnl", 0.0) or 0.0)
            entry = float(td.get("entry", 0.0) or td.get("entry_price", 0.0) or 0.0)
            sl    = float(td.get("sl", 0.0) or td.get("stop_loss", 0.0) or 0.0)
            qty   = float(td.get("qty", 0.0) or td.get("quantity", 1.0) or 1.0)
            strat = str(td.get("strategy", td.get("strategy_name", "unknown")) or "unknown")

            if entry <= 0:
                continue

            risk_per_unit = abs(entry - sl) if sl > 0 else entry * 0.01
            if risk_per_unit <= 0:
                risk_per_unit = entry * 0.01

            r_mult = round(pnl / (risk_per_unit * qty), 4)
            result.r_multiples.append(r_mult)

            # slot into bin
            idx = _classify_r(r_mult, bins)
            bins[idx].count += 1

            # per-strategy bucket
            if strat not in strat_trades:
                strat_trades[strat] = []
            strat_trades[strat].append(r_mult)

    if not result.r_multiples:
        return result

    # ── Aggregate statistics ──────────────────────────────────────────────────
    r_list = result.r_multiples
    result.total_trades = len(r_list)

    winners = [r for r in r_list if r > 0.0]
    losers  = [r for r in r_list if r < 0.0]
    breakev = [r for r in r_list if r == 0.0]

    result.win_count       = len(winners)
    result.loss_count      = len(losers)
    result.breakeven_count = len(breakev)
    result.win_rate        = round(len(winners) / len(r_list) * 100, 1) if r_list else 0.0
    result.avg_r           = round(statistics.mean(r_list), 4)
    result.avg_win_r       = round(statistics.mean(winners), 4) if winners else 0.0
    result.avg_loss_r      = round(abs(statistics.mean(losers)), 4) if losers else 0.0
    result.payoff_ratio    = round(result.avg_win_r / result.avg_loss_r, 3) if result.avg_loss_r > 0 else 0.0

    result.tail_profit_ratio  = _tail_ratio(r_list)
    result.loss_concentration = _loss_concentration(r_list)

    result.profile, result.profile_description = _classify_profile(
        result.win_rate, result.payoff_ratio
    )

    # ── Per-strategy profiles ─────────────────────────────────────────────────
    for strat, rs in strat_trades.items():
        w = [r for r in rs if r > 0.0]
        l = [r for r in rs if r < 0.0]
        wr  = round(len(w) / len(rs) * 100, 1) if rs else 0.0
        avg_w_r = round(statistics.mean(w),       4) if w else 0.0
        avg_l_r = round(abs(statistics.mean(l)),  4) if l else 0.0
        pay = round(avg_w_r / avg_l_r, 3) if avg_l_r > 0 else 0.0
        avg_r = round(statistics.mean(rs), 4)
        prof, _ = _classify_profile(wr, pay)
        result.per_strategy[strat] = StrategyEdgeProfile(
            strategy=strat,
            trades=len(rs),
            win_rate=wr,
            payoff_ratio=pay,
            avg_r=avg_r,
            profile=prof,
        )

    return result


# ─────────────────────────────────────────────────────────────────────────────
# ASCII bar chart helper
# ─────────────────────────────────────────────────────────────────────────────

def _ascii_bar(count: int, max_count: int, width: int = _BAR_SCALE) -> str:
    """Return an ASCII bar of '#' chars scaled to width."""
    if max_count == 0 or count == 0:
        return ""
    bar_len = max(1, round(count / max_count * width))
    return "#" * bar_len


# ─────────────────────────────────────────────────────────────────────────────
# Report formatter
# ─────────────────────────────────────────────────────────────────────────────

def format_edm_report(result: EdmResult) -> str:
    """Return a Markdown string for Section 4f — Edge Distribution Map."""
    lines: List[str] = []
    lines.append("## Section 4f -- Edge Distribution Map (EDM)")
    lines.append("")

    if result.total_trades == 0:
        lines.append("_No trades recorded — EDM skipped._")
        lines.append("")
        return "\n".join(lines)

    # ── Summary statistics table ──────────────────────────────────────────────
    tail_note = (
        "tail-dependent" if result.tail_profit_ratio >= _TAIL_DEPENDENT_THRESHOLD
        else "distributed"
    )
    lines.append("### Summary Statistics")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|--------|-------|")
    lines.append(f"| Total trades | {result.total_trades} |")
    lines.append(f"| Win / Loss / Even | {result.win_count} / {result.loss_count} / {result.breakeven_count} |")
    lines.append(f"| Win rate | {result.win_rate:.1f}% |")
    lines.append(f"| Avg R (all trades) | {result.avg_r:+.3f}R |")
    lines.append(f"| Avg winning R | +{result.avg_win_r:.3f}R |")
    lines.append(f"| Avg losing R | -{result.avg_loss_r:.3f}R |")
    lines.append(f"| Payoff ratio | {result.payoff_ratio:.2f}x |")
    lines.append(f"| Tail profit ratio | {result.tail_profit_ratio:.2f}x  ({tail_note}) |")
    lines.append(f"| Loss concentration (worst 25%) | {result.loss_concentration:.1f}% of gross loss |")
    lines.append("")

    # ── Profile classification ────────────────────────────────────────────────
    lines.append("### Edge Profile")
    lines.append("")
    lines.append(f"**Profile: {result.profile}**")
    lines.append("")
    lines.append(result.profile_description)
    lines.append("")

    # ── Histogram ──────────────────────────────────────────────────────────────
    lines.append("### R-Multiple Distribution")
    lines.append("")
    lines.append("```")
    lines.append(f"{'Bin':<12}  {'Trades':>6}  {'Bar'}")
    lines.append("-" * 55)

    max_count = max((b.count for b in result.bins), default=1)
    max_count = max(max_count, 1)

    for b in result.bins:
        if b.count == 0:
            continue   # skip empty bins for cleaner output
        bar = _ascii_bar(b.count, max_count)
        lines.append(f"{b.label:<12}  {b.count:>6}  {bar}")

    lines.append("```")
    lines.append("")
    lines.append(
        "_Bins: each bucket spans 0.5R.  "
        "Overflow bins (<-3R and >=+5R) capture extreme outliers._"
    )
    lines.append("")

    # ── Interpretation ────────────────────────────────────────────────────────
    lines.append("### Interpretation")
    lines.append("")

    if result.profile == "Mean-Reversion":
        lines.append(
            "- Profits are broadly distributed across many small winners — desirable for stability."
        )
        lines.append(
            "- Tail profit ratio {:.2f}x — {}.".format(
                result.tail_profit_ratio,
                "system relies partly on rare large wins; monitor outlier dependency"
                if result.tail_profit_ratio >= _TAIL_DEPENDENT_THRESHOLD
                else "profits are not concentrated in outliers"
            )
        )
        lines.append(
            "- Loss concentration {:.0f}% — {}.".format(
                result.loss_concentration,
                "risk is spread evenly across losses" if result.loss_concentration < 60
                else "WARNING: most losses cluster in a few bad trades — review stop-loss logic"
            )
        )
    elif result.profile == "Trend-Following":
        lines.append(
            "- Profits are concentrated in a small number of large winners."
        )
        lines.append(
            "- Wide stop-losses are acceptable given the high payoff ratio ({:.2f}x).".format(
                result.payoff_ratio
            )
        )
        lines.append(
            "- Loss concentration {:.0f}% — {}.".format(
                result.loss_concentration,
                "losses are spread — healthy for trend system"
                if result.loss_concentration < 50
                else "high concentration — check if a single regime is dominating losses"
            )
        )
    else:
        lines.append(
            "- Balanced distribution — both win frequency and win size contribute to PnL."
        )
        lines.append(
            "- Standard risk management applies. Review per-strategy profiles below "
            "for strategy-specific guidance."
        )
    lines.append("")

    # ── Per-strategy breakdown ────────────────────────────────────────────────
    if result.per_strategy:
        lines.append("### Per-Strategy Profiles")
        lines.append("")
        lines.append(
            "| Strategy | Trades | Win% | AvgR | Payoff | Profile |"
        )
        lines.append(
            "|----------|--------|------|------|--------|---------|"
        )
        for sp in sorted(result.per_strategy.values(), key=lambda x: -x.trades):
            lines.append(
                f"| {sp.strategy} | {sp.trades} | {sp.win_rate:.1f}% "
                f"| {sp.avg_r:+.3f}R | {sp.payoff_ratio:.2f}x | {sp.profile} |"
            )
        lines.append("")

    return "\n".join(lines)
