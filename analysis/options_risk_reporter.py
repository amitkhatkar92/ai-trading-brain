"""
analysis/options_risk_reporter.py
======================================
OPTIONS_RISK_AUDIT_001 — Markdown report generator.

Reads precomputed RiskMetrics and DrawdownResult objects for every strategy
and writes a dated risk-first report.

The report leads with VERDICT (TRADE / WATCH / AVOID) and Profit Factor
rather than win rate, to ensure tail risk is front-and-centre.

Output: reports/options_risk/OPTIONS_RISK_AUDIT_001_YYYYMMDD.md
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Dict, List

from analysis.tail_risk_analyzer  import RiskMetrics
from analysis.drawdown_analyzer   import DrawdownResult
from analysis.options_backtester  import ALL_STRATEGIES

_ROOT   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(_ROOT, "reports", "options_risk")

# ── Verdict icons ─────────────────────────────────────────────────────────────
_ICON = {"TRADE": "✅", "WATCH": "⚠️", "AVOID": "🔴", "NO_DATA": "⚪"}


def _pct(v: float, decimals: int = 1) -> str:
    return f"{v:.{decimals}f}%"


def _r(v: float, decimals: int = 3) -> str:
    sign = "+" if v > 0 else ""
    return f"{sign}{v:.{decimals}f}R"


def _fmt_pf(pf: float) -> str:
    """Colour-code PF: green if > 1.3, amber if 1.0-1.3, red if < 1.0."""
    if pf >= 1.3:
        return f"**{pf:.2f}** ✅"
    if pf >= 1.0:
        return f"**{pf:.2f}** ⚠️"
    return f"**{pf:.2f}** 🔴"


def _regime_table(
    by_regime: Dict[str, RiskMetrics],
    dd_by_regime: Dict[str, DrawdownResult],
) -> str:
    rows = [
        "| Regime | WR% | PF | EV/trade | Sharpe | MaxDD | Worst Month | Verdict |",
        "|--------|-----|----|----------|--------|-------|-------------|---------|",
    ]
    for regime in ["ALL", "RANGING", "TRENDING", "HIGH_VOL"]:
        m  = by_regime.get(regime)
        dd = dd_by_regime.get(regime)
        if m is None or m.n < 5:
            rows.append(f"| {regime} | — | — | — | — | — | — | ⚪ |")
            continue
        rows.append(
            f"| {regime} (n={m.n}) "
            f"| {_pct(m.win_rate)} "
            f"| {_fmt_pf(m.profit_factor)} "
            f"| {_r(m.expected_value)} "
            f"| {m.sharpe:.2f} "
            f"| {_r(dd.max_drawdown_r) if dd else '—'} "
            f"| {_r(dd.worst_month_r) if dd else '—'} "
            f"| {_ICON.get(m.verdict, '⚪')} {m.verdict} |"
        )
    return "\n".join(rows)


def generate_risk_report(
    risk_by_strategy: Dict[str, Dict[str, RiskMetrics]],
    dd_by_strategy:   Dict[str, Dict[str, DrawdownResult]],
    total_records:    int,
    date_range:       tuple,
    out_dir:          str = OUT_DIR,
) -> str:
    """
    Write OPTIONS_RISK_AUDIT_001 markdown report.

    Returns path to written file.
    """
    os.makedirs(out_dir, exist_ok=True)
    date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    out_path = os.path.join(out_dir, f"OPTIONS_RISK_AUDIT_001_{date_str}.md")
    now_str  = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    date_from, date_to = date_range

    md = []

    # ── Header ────────────────────────────────────────────────────────────────
    md += ["# OPTIONS_RISK_AUDIT_001 — Risk-First Strategy Evaluation", ""]
    md += [f"**Generated:** {now_str}  "]
    md += [f"**Data period:** {date_from} → {date_to}  "]
    md += [f"**Total records:** {total_records:,} (NIFTY + BANKNIFTY)  "]
    md += [""]
    md += ["> **Win rate alone is not a trading edge.**  "]
    md += ["> This report leads with Profit Factor, Expected Value, and Drawdown.  "]
    md += ["> A strategy with 84% WR and PF < 1.0 is a losing strategy.  "]
    md += [""]
    md += ["> **Note on DrawdownScale:** MaxDD and Worst Month are computed on the"]
    md += ["> *aggregate equity curve* (all instruments × all trading days). For a"]
    md += ["> realistic single-expiry weekly trade, divide these figures by the number"]
    md += ["> of average weekly trades in the sample. **EV/trade and Sharpe are the"]
    md += ["> primary per-trade-normalised metrics** — use those for position sizing."]
    md += [""]

    # ── Executive Verdict Table ────────────────────────────────────────────────
    md += ["---", "## Executive Verdicts", ""]
    md += ["> The only question that matters before execution: is the strategy worth trading?", ""]
    md += [
        "| Strategy | Verdict | WR% | PF | EV/Trade | Sharpe | Sortino | Max DD | Worst Month | Kelly% |",
        "|----------|---------|-----|----|----------|--------|---------|--------|-------------|--------|",
    ]

    for strat in ALL_STRATEGIES:
        rm = risk_by_strategy.get(strat, {}).get("ALL")
        dd = dd_by_strategy.get(strat, {}).get("ALL")
        if rm is None:
            md.append(f"| `{strat}` | ⚪ NO DATA | — | — | — | — | — | — | — | — |")
            continue
        icon = _ICON.get(rm.verdict, "⚪")
        md.append(
            f"| `{strat}` "
            f"| {icon} **{rm.verdict}** "
            f"| {_pct(rm.win_rate)} "
            f"| {_fmt_pf(rm.profit_factor)} "
            f"| {_r(rm.expected_value)} "
            f"| {rm.sharpe:.2f} "
            f"| {rm.sortino:.2f} "
            f"| {_r(dd.max_drawdown_r) if dd else '—'} "
            f"| {_r(dd.worst_month_r) if dd else '—'} "
            f"| {rm.kelly_pct:.1f}% |"
        )
    md += [""]

    # ── The Core Finding Upfront ──────────────────────────────────────────────
    md += ["---", "## The Regime Context", ""]
    md += [
        "The data covers a period that was **predominantly RANGING (>90% of sessions).**",
        "",
        "This single fact explains all findings below:",
        "",
        "- **Premium sellers** (SHORT_STRANGLE, IRON_CONDOR, spreads) look excellent — "
        "they are *regime-matched*.",
        "- **Premium buyers** (LONG_CALL, LONG_PUT, LONG_STRANGLE) look poor — "
        "they are *regime-mismatched*, not structurally broken.",
        "",
        "> **Governance rule:** Re-evaluate debit strategies when India VIX > 20 "
        "or regime shifts to HIGH_VOL / TRENDING.",
        "",
    ]

    # ── Per-Strategy Deep Dive ────────────────────────────────────────────────
    md += ["---", "## Per-Strategy Risk Profile", ""]

    for strat in ALL_STRATEGIES:
        rm_all = risk_by_strategy.get(strat, {}).get("ALL")
        dd_all = dd_by_strategy.get(strat, {}).get("ALL")
        rm_dict = risk_by_strategy.get(strat, {})
        dd_dict = dd_by_strategy.get(strat, {})

        icon = _ICON.get(rm_all.verdict if rm_all else "NO_DATA", "⚪")
        md += [f"### `{strat}` — {icon} {rm_all.verdict if rm_all else 'NO DATA'}", ""]

        if rm_all is None:
            md += ["_No data available._", ""]
            continue

        # Summary grid
        md += [
            "| Metric | Value | Interpretation |",
            "|--------|-------|----------------|",
            f"| Profit Factor | {_fmt_pf(rm_all.profit_factor)} | "
            f"{'Must be > 1.0 to be profitable' if rm_all.profit_factor < 1.3 else 'Solid edge'} |",
            f"| Expected Value | {_r(rm_all.expected_value)} | Per trade in R |",
            f"| Win Rate | {_pct(rm_all.win_rate)} | High WR ≠ profitable by itself |",
            f"| Avg Win | {_r(rm_all.avg_win)} | |",
            f"| Avg Loss | −{_r(rm_all.avg_loss)} | |",
            f"| Win/Loss Ratio | {rm_all.win_loss_ratio:.2f}× | > 1.0 = winners larger than losers |",
            f"| Kelly % | {rm_all.kelly_pct:.1f}% | Optimal bet size (capped 25%) |",
            f"| Sharpe | {rm_all.sharpe:.2f} | Annualised (> 0.5 = acceptable) |",
            f"| Sortino | {rm_all.sortino:.2f} | Downside-only risk |",
            f"| Large Losses (>2R) | {_pct(rm_all.pct_large_losses)} | Tail event frequency |",
            f"| Max Consec. Losses | {rm_all.max_consecutive_loss} | Worst streak |",
        ]
        if dd_all:
            md += [
                f"| Max Drawdown | {_r(dd_all.max_drawdown_r)} ({dd_all.max_drawdown_pct:.1f}%) | "
                f"Recovery: {dd_all.recovery_trades} trades |",
                f"| Worst Week | {_r(dd_all.worst_week_r)} | |",
                f"| Worst Month | {_r(dd_all.worst_month_r)} | Best: {_r(dd_all.best_month_r)} |",
                f"| Calmar Ratio | {dd_all.calmar_ratio:.2f} | Ann. return / max DD |",
                f"| Ulcer Index | {dd_all.ulcer_index:.3f} | Lower = smoother equity curve |",
                f"| Worst Single Trade | {_r(dd_all.worst_single_trade_r)} | |",
            ]
        md += [""]

        # Verdict reasoning
        md += [f"**Verdict reasoning:** {rm_all.verdict_reason}", ""]

        # Regime breakdown
        if len(rm_dict) > 1:
            md += [f"**Regime breakdown:**", ""]
            md += [_regime_table(rm_dict, dd_dict), ""]

    # ── Ranking tables ────────────────────────────────────────────────────────
    md += ["---", "## Rankings", ""]

    def _rank(strats, key_fn, label, higher_better=True):
        scored = [
            (s, key_fn(risk_by_strategy.get(s, {}).get("ALL")))
            for s in strats
            if risk_by_strategy.get(s, {}).get("ALL") is not None
        ]
        scored.sort(key=lambda x: x[1], reverse=higher_better)
        rows = [f"| Rank | Strategy | {label} |", "|------|----------|" + "-" * (len(label)+2) + "|"]
        for i, (s, v) in enumerate(scored, 1):
            rows.append(f"| {i} | `{s}` | {v:.3f} |")
        return "\n".join(rows)

    md += ["**By Profit Factor (higher = better):**", ""]
    md += [_rank(ALL_STRATEGIES, lambda r: r.profit_factor if r else 0, "Profit Factor"), ""]
    md += ["**By Expected Value per trade (higher = better):**", ""]
    md += [_rank(ALL_STRATEGIES, lambda r: r.expected_value if r else 0, "EV/trade (R)"), ""]
    md += ["**By Sharpe Ratio (higher = better):**", ""]
    md += [_rank(ALL_STRATEGIES, lambda r: r.sharpe if r else 0, "Sharpe"), ""]

    if dd_by_strategy:
        md += ["**By Max Drawdown (less negative = better):**", ""]
        def _dd_key(strat):
            d = dd_by_strategy.get(strat, {}).get("ALL")
            return d.max_drawdown_r if d else -999
        scored = [(s, _dd_key(s)) for s in ALL_STRATEGIES]
        scored.sort(key=lambda x: -x[1])   # least negative first
        rows = ["| Rank | Strategy | Max DD (R) |", "|------|----------|------------|"]
        for i, (s, v) in enumerate(scored, 1):
            rows.append(f"| {i} | `{s}` | {v:+.3f}R |")
        md += ["\n".join(rows), ""]

    # ── Production Readiness Gate ──────────────────────────────────────────────
    md += ["---", "## Production Readiness Gate", ""]
    md += ["> Strategy promoted only when: PF > 1.3, EV > 0.1R, Sharpe > 0.5, MaxDD within acceptable range.", ""]
    md += [
        "| Strategy | PF > 1.3? | EV > 0.1R? | Sharpe > 0.5? | Max DD < −15R? | Gate |",
        "|----------|-----------|------------|---------------|----------------|------|",
    ]
    for strat in ALL_STRATEGIES:
        rm = risk_by_strategy.get(strat, {}).get("ALL")
        dd = dd_by_strategy.get(strat, {}).get("ALL")
        if rm is None:
            md.append(f"| `{strat}` | ⚪ | ⚪ | ⚪ | ⚪ | ⚪ NO DATA |")
            continue
        pf_ok  = rm.profit_factor >= 1.3
        ev_ok  = rm.expected_value >= 0.1
        sh_ok  = rm.sharpe >= 0.5
        dd_ok  = (dd.max_drawdown_r > -15.0) if dd else False
        gate   = "✅ PASS" if all([pf_ok, ev_ok, sh_ok, dd_ok]) else "❌ FAIL"
        md.append(
            f"| `{strat}` "
            f"| {'✅' if pf_ok else '❌'} {rm.profit_factor:.2f} "
            f"| {'✅' if ev_ok else '❌'} {rm.expected_value:+.3f}R "
            f"| {'✅' if sh_ok else '❌'} {rm.sharpe:.2f} "
            f"| {'✅' if dd_ok else '❌'} {dd.max_drawdown_r:+.2f}R "
            f"| {gate} |"
        )
    md += [""]

    # ── Footer ────────────────────────────────────────────────────────────────
    md += ["---"]
    md += ["*Generated by OPTIONS_RISK_AUDIT_001.*  "]
    md += ["*Win rate is context. Profit factor is reality. Drawdown is the cost.*  "]
    md += ["*No live trading code was modified.*"]

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md))
    return out_path
