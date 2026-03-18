"""
Market Capture Ratio (MCR) Analyzer
=====================================
Measures how much of the available market movement the AI trading system
actually captures, broken down by regime.

Why this matters
----------------
Two systems can report the same PnL but behave very differently:
  • System A earns ₹10k capturing 40 % of range-market moves   → regime-aligned
  • System B earns ₹10k capturing  5 % of trend moves          → lucky, fragile

MCR answers the institutional question:
  "Did the AI make money **in the environment it was designed for**?"

Formulas
--------
Regime-level capture:
    market_move   = sum |nifty_change %| for all days classified into that regime
    system_return = sum trade_PnL / initial_capital x 100     (regime's trades only)
    capture_ratio = system_return / market_move x 100

Trade-level capture (complementary):
    offered_range  = |target_price - entry_price| / entry_price x 100
    trade_return   = trade_PnL / (entry_price x qty) x 100
    trade_capture  = trade_return / offered_range x 100     (if offered_range > 0)

Both metrics are aggregated per regime and averaged.

Interpretation thresholds
--------------------------
  ≥ 40 %   →  DOMINANT   — strong alpha in this regime
  15–40 %  →  MODERATE   — positive edge, room to improve
  0–15 %   →  WEAK       — marginal capture, consider disabling strategies
  < 0 %    →  NEGATIVE   — AI loses money when market moves in this regime
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

# ── Thresholds ────────────────────────────────────────────────────────────────
_DOMINANT_THRESHOLD  = 40.0   #  %
_MODERATE_THRESHOLD  = 15.0   #  %
_INITIAL_CAPITAL     = 1_000_000.0   # ₹ — matches replay default


# ─────────────────────────────────────────────────────────────────────────────
# Data classes
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class RegimeCaptureStats:
    """MCR result for a single market regime."""
    regime:             str
    days_count:         int   = 0   # days the system saw this regime
    trades_count:       int   = 0   # trades executed in this regime
    wins_count:         int   = 0   # winning trades
    market_move_pct:    float = 0.0 # Σ |nifty_change %| for regime days
    system_return_pct:  float = 0.0 # Σ PnL / capital × 100
    capture_ratio_pct:  float = 0.0 # system_return_pct / market_move_pct × 100
    avg_trade_capture:  float = 0.0 # mean trade-level capture ratio (%)
    win_rate:           float = 0.0 # % of trades that were profitable

    @property
    def assessment(self) -> str:
        if self.capture_ratio_pct >= _DOMINANT_THRESHOLD:
            return "DOMINANT"
        if self.capture_ratio_pct >= _MODERATE_THRESHOLD:
            return "MODERATE"
        if self.capture_ratio_pct >= 0.0:
            return "WEAK"
        return "NEGATIVE"

    @property
    def assessment_emoji(self) -> str:
        return {
            "DOMINANT":  "🟢",
            "MODERATE":  "🟡",
            "WEAK":      "🟠",
            "NEGATIVE":  "🔴",
        }.get(self.assessment, "⚪")


@dataclass
class MarketCaptureResult:
    """Aggregate MCR output returned by ``analyze_market_capture()``."""
    regime_stats:         Dict[str, RegimeCaptureStats] = field(default_factory=dict)
    overall_capture_pct:  float = 0.0
    total_market_move:    float = 0.0   # Σ |nifty_change %| across all days
    total_system_return:  float = 0.0   # Σ PnL / capital × 100 across all trades
    primary_regime:       str   = ""    # regime with highest capture_ratio_pct
    avoid_regime:         str   = ""    # regime with lowest (most negative) ratio
    total_trades:         int   = 0
    capital:              float = _INITIAL_CAPITAL


# ─────────────────────────────────────────────────────────────────────────────
# Core analysis function
# ─────────────────────────────────────────────────────────────────────────────

def analyze_market_capture(
    day_results:  list,                 # List[DayCycleResult]
    capital:      float = _INITIAL_CAPITAL,
) -> MarketCaptureResult:
    """
    Compute Market Capture Ratio from a completed replay run.

    Parameters
    ----------
    day_results:
        List of ``DayCycleResult`` objects produced by ``ReplayOrchestrator``.
    capital:
        Starting capital used for normalising system returns.
        Defaults to ₹10,00,000 (matches replay default).

    Returns
    -------
    MarketCaptureResult
        Fully populated; safe to consume even when no trades were executed.
    """
    res = MarketCaptureResult(capital=capital)

    if not day_results:
        return res

    # ── Step 1: Aggregate per-regime stats ───────────────────────────────────
    regime_buckets: Dict[str, _RegimeBucket] = {}

    for dr in day_results:
        regime_key = _normalise_regime(dr.regime)
        if regime_key not in regime_buckets:
            regime_buckets[regime_key] = _RegimeBucket(regime=regime_key)
        bkt = regime_buckets[regime_key]

        bkt.days_count    += 1
        bkt.market_move   += abs(float(dr.nifty_change or 0.0))

        for t in dr.executed_trades:
            pnl    = float(t.get("pnl",         0.0) or 0.0)
            entry  = float(t.get("entry",        0.0) or t.get("entry_price",  0.0) or 0.0)
            target = float(t.get("target",       0.0) or t.get("target_price", 0.0) or 0.0)
            qty    = float(t.get("qty",          0.0) or t.get("quantity",     1.0) or 1.0)

            bkt.trades_count  += 1
            bkt.total_pnl     += pnl
            if pnl > 0:
                bkt.wins_count += 1

            # Trade-level capture: offered_range vs actual_return
            if entry > 0 and target > 0:
                offered_pct = abs(target - entry) / entry * 100.0
                if offered_pct > 0.0:
                    trade_return_pct = (pnl / (entry * qty) * 100.0) if qty > 0 else 0.0
                    bkt.trade_captures.append(trade_return_pct / offered_pct * 100.0)

    # ── Step 2: Build RegimeCaptureStats ────────────────────────────────────
    for regime_key, bkt in regime_buckets.items():
        sys_return_pct = bkt.total_pnl / capital * 100.0
        capture = (
            sys_return_pct / bkt.market_move * 100.0
            if bkt.market_move > 0.0 else 0.0
        )
        avg_tc = (
            sum(bkt.trade_captures) / len(bkt.trade_captures)
            if bkt.trade_captures else 0.0
        )
        win_rate = (
            bkt.wins_count / bkt.trades_count * 100.0
            if bkt.trades_count > 0 else 0.0
        )
        res.regime_stats[regime_key] = RegimeCaptureStats(
            regime             = regime_key,
            days_count         = bkt.days_count,
            trades_count       = bkt.trades_count,
            wins_count         = bkt.wins_count,
            market_move_pct    = round(bkt.market_move,   2),
            system_return_pct  = round(sys_return_pct,    4),
            capture_ratio_pct  = round(capture,           2),
            avg_trade_capture  = round(avg_tc,            2),
            win_rate           = round(win_rate,          1),
        )

        res.total_market_move    += bkt.market_move
        res.total_system_return  += sys_return_pct
        res.total_trades         += bkt.trades_count

    # ── Step 3: Overall capture ──────────────────────────────────────────────
    res.total_market_move   = round(res.total_market_move,   2)
    res.total_system_return = round(res.total_system_return, 4)
    res.overall_capture_pct = round(
        res.total_system_return / res.total_market_move * 100.0
        if res.total_market_move > 0.0 else 0.0,
        2,
    )

    # ── Step 4: Primary / Avoid regimes ────────────────────────────────────
    if res.regime_stats:
        # Only consider regimes WITH trades for ranking
        traded = {k: v for k, v in res.regime_stats.items() if v.trades_count > 0}
        if traded:
            res.primary_regime = max(traded, key=lambda k: traded[k].capture_ratio_pct)
            res.avoid_regime   = min(traded, key=lambda k: traded[k].capture_ratio_pct)
        else:
            # no trades at all — rank by market move seen
            res.primary_regime = max(res.regime_stats,
                                     key=lambda k: res.regime_stats[k].market_move_pct)
            res.avoid_regime   = ""

    return res


# ─────────────────────────────────────────────────────────────────────────────
# Report formatter
# ─────────────────────────────────────────────────────────────────────────────

def format_mcr_report(result: MarketCaptureResult) -> str:
    """
    Return the Markdown block for the MCR section of the replay report.
    Heading is designed to sit as **Section 4d** after the LIMIT section.
    """
    lines: List[str] = [
        "## Section 4d — Market Capture Ratio (MCR)",
        "",
        "> **What this measures:** How much of the available market movement the AI"
        " captures in each regime.  A high capture ratio in your primary regime"
        " confirms the strategy is genuinely aligned — not just profitable by chance.",
        "",
    ]

    if not result.regime_stats:
        lines.append("_No trades executed — MCR analysis skipped._")
        lines.append("")
        return "\n".join(lines)

    # ── Overall banner ────────────────────────────────────────────────────────
    overall_label = _capture_label(result.overall_capture_pct)
    lines += [
        "### Overall",
        "",
        f"| Item | Value |",
        f"|------|-------|",
        f"| Total market movement (sum of |Nifty chg %|) | {result.total_market_move:+.2f}% |",
        f"| Total system return (PnL / capital) | {result.total_system_return:+.4f}% |",
        f"| **Overall capture ratio** | **{result.overall_capture_pct:+.1f}%** — {overall_label} |",
        f"| Total trades across all regimes | {result.total_trades} |",
        "",
    ]

    if result.primary_regime:
        lines.append(
            f"> 🏆 **Primary regime edge:** `{result.primary_regime}` "
            f"— highest capture ratio."
        )
    if result.avoid_regime and result.avoid_regime != result.primary_regime:
        avoid_stats = result.regime_stats.get(result.avoid_regime)
        if avoid_stats and avoid_stats.capture_ratio_pct < 5.0:
            lines.append(
                f"> ⚠ **Consider avoiding:** `{result.avoid_regime}` "
                f"— lowest capture ratio ({avoid_stats.capture_ratio_pct:+.1f}%)."
            )
    lines.append("")

    # ── Per-regime table ──────────────────────────────────────────────────────
    lines += [
        "### Regime-by-Regime Breakdown",
        "",
        "| Regime | Days | Trades | Market Move | System Return | "
        "Capture Ratio | Avg Trade Capture | Win Rate | Assessment |",
        "|--------|------|--------|-------------|---------------|"
        "--------------|-------------------|----------|------------|",
    ]
    # Sort: traded regimes first (by capture desc), then untradeable by market_move
    def _sort_key(s: RegimeCaptureStats) -> Tuple[int, float]:
        return (-s.trades_count, -s.capture_ratio_pct)

    for stats in sorted(result.regime_stats.values(), key=_sort_key):
        lines.append(
            f"| {stats.regime} "
            f"| {stats.days_count} "
            f"| {stats.trades_count} "
            f"| {stats.market_move_pct:+.2f}% "
            f"| {stats.system_return_pct:+.4f}% "
            f"| {stats.capture_ratio_pct:+.1f}% "
            f"| {stats.avg_trade_capture:+.1f}% "
            f"| {stats.win_rate:.0f}% "
            f"| {stats.assessment_emoji} {stats.assessment} |"
        )
    lines.append("")

    # ── Interpretation guide ──────────────────────────────────────────────────
    lines += [
        "### Interpretation",
        "",
        "| Capture Ratio | Label | Meaning |",
        "|---------------|-------|---------|",
        "| ≥ 40% | 🟢 DOMINANT | Strong alpha — this regime is your sweet spot |",
        "| 15–40% | 🟡 MODERATE | Positive edge — room to optimise |",
        "| 0–15% | 🟠 WEAK | Marginal capture — consider disabling strategies |",
        "| < 0% | 🔴 NEGATIVE | AI loses when market moves — avoid this regime |",
        "",
    ]

    # ── Regime-specific guidance ──────────────────────────────────────────────
    if any(s.capture_ratio_pct >= _DOMINANT_THRESHOLD
           for s in result.regime_stats.values() if s.trades_count > 0):
        dominant_regimes = [
            s.regime for s in result.regime_stats.values()
            if s.trades_count > 0 and s.capture_ratio_pct >= _DOMINANT_THRESHOLD
        ]
        lines.append(
            f"✅ **Strategy-regime alignment confirmed** in: "
            + ", ".join(f"`{r}`" for r in dominant_regimes)
        )
        lines.append("")

    negative_regimes = [
        s for s in result.regime_stats.values()
        if s.trades_count > 0 and s.capture_ratio_pct < 0
    ]
    if negative_regimes:
        lines.append("### Regime Avoidance Recommendations")
        lines.append("")
        for s in negative_regimes:
            lines.append(
                f"- **Disable mean-reversion/liquidity strategies when regime = `{s.regime}`**"
                f"  (capture {s.capture_ratio_pct:+.1f}%, {s.trades_count} trade(s))."
            )
        lines.append("")

    # ── MCR vs hedge-fund standard ───────────────────────────────────────────
    lines += [
        "### MCR vs Institutional Standard",
        "",
        "> Institutional quant desks require strategy capture ≥ 20–30% of the market"
        " move in the strategy's target regime before allocating capital.",
        "",
    ]
    if result.total_trades == 0:
        lines.append(
            "_MCR benchmark cannot be assessed with zero trades.  "
            "Supply individual stock OHLCV data to generate trade flow._"
        )
    elif result.overall_capture_pct >= 20.0:
        lines.append(
            f"✅ Overall capture **{result.overall_capture_pct:.1f}%** meets the"
            f" ≥ 20% institutional threshold."
        )
    else:
        lines.append(
            f"⚠ Overall capture **{result.overall_capture_pct:.1f}%** is below"
            f" the 20% institutional threshold.  Focus on the highest-capture"
            f" regime(s) and restrict trading in low-capture environments."
        )
    lines.append("")

    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class _RegimeBucket:
    """Accumulator used internally during analysis."""
    regime:         str
    days_count:     int   = 0
    trades_count:   int   = 0
    wins_count:     int   = 0
    market_move:    float = 0.0
    total_pnl:      float = 0.0
    trade_captures: List[float] = field(default_factory=list)


def _normalise_regime(raw: str) -> str:
    """Strip 'RegimeLabel.' prefix and title-case for consistent keys."""
    cleaned = str(raw or "UNKNOWN").replace("RegimeLabel.", "").strip()
    return cleaned if cleaned else "UNKNOWN"


def _capture_label(capture_pct: float) -> str:
    if capture_pct >= _DOMINANT_THRESHOLD:
        return "🟢 DOMINANT"
    if capture_pct >= _MODERATE_THRESHOLD:
        return "🟡 MODERATE"
    if capture_pct >= 0.0:
        return "🟠 WEAK"
    return "🔴 NEGATIVE"
