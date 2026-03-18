"""
Replay Metrics
==============
Calculates quantitative performance metrics from a completed 7-day replay run.

Metrics computed
----------------
  • total_signals         — raw opportunities generated across all days
  • trades_executed       — positions opened by the execution engine
  • trades_approved_pct   — trades / signals (how many cleared all gates)
  • win_rate              — % of closed trades with PnL > 0
  • avg_r_multiple        — mean reward-to-risk multiple across all trades
  • max_drawdown_pct       — peak-to-trough loss as % of starting capital
  • profit_factor         — gross profits / gross losses
  • per_strategy          — breakdown of each strategy's trade count + win rate
  • per_regime            — trade distribution by regime label
  • risk_compliance       — checks SL set, RR > 1, Guardian not bypassed
  • regime_alignment_pct  — % trades whose strategy matched the day's regime

All inputs come from DayCycleResult objects returned by the replay engine.
"""

from __future__ import annotations

import csv
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

PAPER_TRADES_CSV = Path(__file__).resolve().parent.parent / "data" / "paper_trades.csv"

# Minimum acceptable RR ratio
MIN_RR = 1.0

# Strategy ↔ Regime alignment table (which strategies suit which regimes)
STRATEGY_REGIME_FIT: Dict[str, List[str]] = {
    "MomentumBreakout":      ["BULL_TREND", "VOLATILE"],
    "TrendFollowing":        ["BULL_TREND", "BEAR_MARKET"],
    "MeanReversion":         ["RANGE_MARKET"],
    "Scalping":              ["RANGE_MARKET", "VOLATILE"],
    "VolatilityBreakout":    ["VOLATILE", "BULL_TREND"],
    "SwingTrading":          ["BULL_TREND", "RANGE_MARKET"],
    "RiskReversal":          ["VOLATILE", "BEAR_MARKET"],
    "GapFill":               ["RANGE_MARKET"],
    "SupportResistance":     ["RANGE_MARKET", "BULL_TREND"],
    "EventDriven":           ["VOLATILE"],
}


# ── Indian-market cost constants ─────────────────────────────────────────────
_BROKERAGE_PER_SIDE = 20.0       # Zerodha flat ₹20 per leg
_STT_RATE          = 0.001       # 0.1 % — sell side, intraday equity
_EXCHANGE_RATE     = 0.0000325   # NSE + BSE transaction charge (both sides)
_SEBI_RATE         = 0.000001    # SEBI charge (both sides)
_GST_RATE          = 0.18        # GST on brokerage + exchange + SEBI
_SLIPPAGE_RATE     = 0.001       # 0.1 % of trade value (NSE large-cap estimate)


@dataclass
class TradeCosts:
    """Itemised transaction costs for one round-trip trade (INR)."""
    brokerage:  float = 0.0   # ₹20 buy + ₹20 sell
    stt:        float = 0.0   # 0.1 % on sell value
    exchange:   float = 0.0   # both legs
    sebi:       float = 0.0   # both legs
    gst:        float = 0.0   # 18 % on (brokerage + exchange + sebi)
    slippage:   float = 0.0   # estimated market-impact
    total:      float = 0.0


def compute_trade_costs(entry: float, qty: int) -> TradeCosts:
    """Compute full round-trip trading costs for an NSE intraday equity trade."""
    if entry <= 0 or qty <= 0:
        return TradeCosts()
    value    = entry * qty
    brok     = _BROKERAGE_PER_SIDE * 2          # buy + sell leg
    stt      = value * _STT_RATE                 # sell side only
    exch     = value * 2 * _EXCHANGE_RATE        # both legs
    sebi     = value * 2 * _SEBI_RATE            # both legs
    gst      = (brok + exch + sebi) * _GST_RATE
    slippage = value * _SLIPPAGE_RATE
    total    = brok + stt + exch + sebi + gst + slippage
    return TradeCosts(
        brokerage = round(brok, 2),
        stt       = round(stt,  2),
        exchange  = round(exch, 2),
        sebi      = round(sebi, 2),
        gst       = round(gst,  2),
        slippage  = round(slippage, 2),
        total     = round(total, 2),
    )


@dataclass
class StrategyStats:
    name:        str
    trades:      int = 0
    wins:        int = 0
    total_pnl:   float = 0.0
    total_r:     float = 0.0

    @property
    def win_rate(self) -> float:
        return self.wins / self.trades * 100 if self.trades else 0.0

    @property
    def avg_r(self) -> float:
        return self.total_r / self.trades if self.trades else 0.0


@dataclass
class ReplayMetrics:
    # Volume
    total_signals:       int   = 0
    trades_executed:     int   = 0
    trades_approved_pct: float = 0.0   # trades / signals * 100

    # Returns
    win_rate:            float = 0.0
    avg_r_multiple:      float = 0.0
    total_pnl:           float = 0.0
    profit_factor:       float = 0.0
    max_drawdown_pct:    float = 0.0

    # Days
    days_with_trades:    int   = 0
    days_total:          int   = 0
    cycle_errors:        int   = 0

    # Strategy / Regime breakdown
    per_strategy:        Dict[str, StrategyStats] = field(default_factory=dict)
    per_regime:          Dict[str, int]            = field(default_factory=dict)

    # Risk compliance
    sl_missing_count:    int   = 0   # trades with SL == 0
    rr_below_1_count:    int   = 0   # trades with RR < 1.0
    regime_alignment_pct:float = 0.0 # % trades whose strategy fits the day's regime

    # Trading costs (INR)
    total_brokerage:     float = 0.0
    total_stt:           float = 0.0
    total_slippage:      float = 0.0
    total_costs:         float = 0.0
    net_pnl:             float = 0.0  # total_pnl − total_costs
    avg_cost_per_trade:  float = 0.0


def calculate_metrics(
    day_results: list,          # List[DayCycleResult]
    capital: float = 1_000_000.0,
) -> ReplayMetrics:
    """
    Build a ReplayMetrics from DayCycleResult objects.

    Re-reads data/paper_trades.csv (if it exists) for closed PnL;
    also uses in-memory position data from DayCycleResult.executed_trades.
    """
    m = ReplayMetrics()
    m.days_total  = len(day_results)

    # Aggregate from day results
    all_trades: List[Dict[str, Any]] = []
    alignment_numerator   = 0
    alignment_denominator = 0

    for dr in day_results:
        m.total_signals += dr.signals_found
        m.cycle_errors  += len(dr.errors)
        if dr.executed_trades:
            m.days_with_trades += 1
        # Strip "RegimeLabel." prefix for per-regime key
        regime_key = dr.regime.replace("RegimeLabel.", "")
        m.per_regime[regime_key] = m.per_regime.get(regime_key, 0) + len(dr.executed_trades)

        for t in dr.executed_trades:
            all_trades.append({**t, "_regime": regime_key})

    # ── Use in-memory data only (skip CSV to avoid stale data contamination) ─
    # all_trades is already populated from DayCycleResult.executed_trades

    m.trades_executed = len(all_trades)
    m.trades_approved_pct = (
        m.trades_executed / max(m.total_signals, 1) * 100
    )

    if not all_trades:
        return m   # no trades — return with defaults

    # ── PnL / RR metrics ─────────────────────────────────────────────────────
    pnls:     List[float] = []
    r_multiples: List[float] = []
    gross_profit = 0.0
    gross_loss   = 0.0

    for t in all_trades:
        pnl    = float(t.get("pnl", 0.0) or 0.0)
        entry  = float(t.get("entry", 0.0) or t.get("entry_price", 0.0) or 0.0)
        sl     = float(t.get("sl", 0.0) or t.get("stop_loss", 0.0) or 0.0)
        target = float(t.get("target", 0.0) or t.get("target_price", 0.0) or 0.0)
        qty    = float(t.get("qty", 0.0) or t.get("quantity", 1.0) or 1.0)
        strat  = str(t.get("strategy", t.get("strategy_name", "unknown")) or "unknown")

        # Risk compliance checks
        if sl <= 0.0:
            m.sl_missing_count += 1
        risk   = abs(entry - sl) if entry > 0 and sl > 0 else 1.0
        reward = abs(target - entry) if entry > 0 and target > 0 else 0.0
        rr     = reward / risk if risk > 0 else 0.0
        if rr < MIN_RR and entry > 0 and target > 0:
            m.rr_below_1_count += 1

        # R-multiple: actual PnL / risk_per_unit
        r_risk = risk * qty if risk > 0 and qty > 0 else 1.0
        r_mult = pnl / r_risk if r_risk != 0 else 0.0
        r_multiples.append(r_mult)
        pnls.append(pnl)

        if pnl > 0:
            gross_profit += pnl
        else:
            gross_loss   += abs(pnl)

        # Strategy stats
        if strat not in m.per_strategy:
            m.per_strategy[strat] = StrategyStats(name=strat)
        s = m.per_strategy[strat]
        s.trades    += 1
        s.wins      += 1 if pnl > 0 else 0
        s.total_pnl += pnl
        s.total_r   += r_mult

        # Regime alignment
        regime = str(t.get("_regime", "UNKNOWN")).replace("RegimeLabel.", "")
        if strat in STRATEGY_REGIME_FIT:
            alignment_denominator += 1
            if any(r in regime for r in STRATEGY_REGIME_FIT[strat]):
                alignment_numerator += 1

    # ── Trading costs ─────────────────────────────────────────────────────────
    cost_totals = TradeCosts()
    for t in all_trades:
        entry = float(t.get("entry", 0.0) or t.get("entry_price", 0.0) or 0.0)
        qty   = int(t.get("qty", 0) or t.get("quantity", 1) or 1)
        c = compute_trade_costs(entry, qty)
        cost_totals.brokerage += c.brokerage
        cost_totals.stt       += c.stt
        cost_totals.slippage  += c.slippage
        cost_totals.total     += c.total

    m.total_brokerage    = round(cost_totals.brokerage, 2)
    m.total_stt          = round(cost_totals.stt,       2)
    m.total_slippage     = round(cost_totals.slippage,  2)
    m.total_costs        = round(cost_totals.total,     2)
    m.avg_cost_per_trade = round(cost_totals.total / len(all_trades), 2) if all_trades else 0.0

    # ── Aggregate stats ───────────────────────────────────────────────────────
    wins = sum(1 for p in pnls if p > 0)
    m.win_rate       = wins / len(pnls) * 100 if pnls else 0.0
    m.avg_r_multiple = sum(r_multiples) / len(r_multiples) if r_multiples else 0.0
    m.total_pnl      = sum(pnls)
    m.net_pnl        = round(m.total_pnl - m.total_costs, 2)
    m.profit_factor  = gross_profit / gross_loss if gross_loss > 0 else float("inf") if gross_profit > 0 else 0.0
    m.max_drawdown_pct = _max_drawdown(pnls, capital)
    m.regime_alignment_pct = (
        alignment_numerator / alignment_denominator * 100
        if alignment_denominator > 0 else 0.0
    )

    return m


# ── Helpers ───────────────────────────────────────────────────────────────────

def _pf_label(pf: float) -> str:
    """Human-readable tier for a profit factor value."""
    if pf == float("inf") or pf > 2.5:
        return "Excellent ( >2.5 )"
    if pf >= 1.5:
        return "Strong ( >=1.5 )"
    if pf >= 1.3:
        return "Acceptable ( 1.3-1.5 )"
    if pf >= 1.0:
        return "Breakeven ( 1.0-1.3 )"
    return "Below breakeven ( <1.0 )"


def _max_drawdown(pnls: List[float], capital: float) -> float:
    """Peak-to-trough drawdown as % of starting capital."""
    if not pnls:
        return 0.0
    running = capital
    peak    = capital
    max_dd  = 0.0
    for p in pnls:
        running += p
        if running > peak:
            peak = running
        dd = (peak - running) / peak * 100
        if dd > max_dd:
            max_dd = dd
    return round(max_dd, 2)


def _load_csv_trades() -> List[Dict[str, Any]]:
    """Read closed trades from data/paper_trades.csv (if present)."""
    if not PAPER_TRADES_CSV.exists():
        return []
    trades = []
    try:
        with open(PAPER_TRADES_CSV, newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                # Normalise numeric fields
                for num_field in ("entry_price", "stop_loss", "target_price",
                                  "fill_price", "pnl", "quantity"):
                    v = row.get(num_field, "")
                    try:
                        row[num_field] = float(v) if v and v != "None" else 0.0
                    except (ValueError, TypeError):
                        row[num_field] = 0.0
                trades.append(row)
    except Exception as exc:
        pass   # corrupt CSV — fall back to in-memory
    return trades


def format_metrics_table(m: ReplayMetrics) -> str:
    """Render a metrics summary as a markdown table string."""
    lines = [
        "## Quantitative Metrics\n",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Total signals generated | {m.total_signals} |",
        f"| Trades executed | {m.trades_executed} |",
        f"| Trade approval rate | {m.trades_approved_pct:.1f}% |",
        f"| Win rate | {m.win_rate:.1f}% |",
        f"| Avg R-multiple | {m.avg_r_multiple:+.2f}R |",
        f"| Gross PnL (simulated) | ₹{m.total_pnl:,.0f} |",
        f"| Total trading costs | ₹{m.total_costs:,.0f} |",
        f"| Net PnL (after costs) | ₹{m.net_pnl:,.0f} |",
        f"| Avg cost per trade | ₹{m.avg_cost_per_trade:,.0f} |",
        f"| Profit factor | {m.profit_factor:.2f}  —  {_pf_label(m.profit_factor)} |",
        f"| Max drawdown | {m.max_drawdown_pct:.2f}% |",
        f"| Days with trades | {m.days_with_trades} / {m.days_total} |",
        f"| Cycle errors | {m.cycle_errors} |",
        f"| SL missing count | {m.sl_missing_count} |",
        f"| RR < 1.0 count | {m.rr_below_1_count} |",
        f"| Strategy-regime alignment | {m.regime_alignment_pct:.1f}% |",
        "",
    ]

    if m.per_strategy:
        lines += [
            "## Per-Strategy Breakdown\n",
            "| Strategy | Trades | Win Rate | Avg R | Total PnL |",
            "|----------|--------|----------|-------|-----------|",
        ]
        for s in sorted(m.per_strategy.values(), key=lambda x: -x.trades):
            lines.append(
                f"| {s.name} | {s.trades} | {s.win_rate:.0f}% | "
                f"{s.avg_r:+.2f}R | ₹{s.total_pnl:,.0f} |"
            )
        lines.append("")

    if m.per_regime:
        lines += [
            "## Trade Distribution by Regime\n",
            "| Regime | Trades |",
            "|--------|--------|",
        ]
        for regime, count in sorted(m.per_regime.items(), key=lambda x: -x[1]):
            lines.append(f"| {regime} | {count} |")
        lines.append("")

    return "\n".join(lines)
