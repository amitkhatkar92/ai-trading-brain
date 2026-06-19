"""
analysis/trade_quality_reporter.py
======================================
TRADE_QUALITY_AUDIT_001 — Markdown report generator.

No database writes. No live-system imports.
Reads from TradeQualityTracker and writes one markdown file.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Optional

from analysis.trade_quality_tracker import TradeQualityTracker
from analysis.trade_quality_scoring import QualityTier, OutcomeComparison


# ── Helper ────────────────────────────────────────────────────────────────────

def _score_bar(value: float, max_v: float = 10.0, width: int = 15) -> str:
    """ASCII progress bar: ████░░░░"""
    filled = max(0, min(width, int(round(value / max_v * width))))
    return "█" * filled + "░" * (width - filled)


# ── Core report block: Win vs Loss comparison ─────────────────────────────────

def _section_win_loss(comp: Optional[OutcomeComparison]) -> list:
    if comp is None:
        return [
            "## Win vs Loss — Score Comparison",
            "",
            "_No closed trades yet. Ingest at least 1 WIN and 1 LOSS to enable comparison._",
            "",
        ]

    edge_tag = (
        "✅ QUALITY PREDICTS OUTCOME"
        if comp.quality_edge >= 1.0
        else ("⚠️ MARGINAL SIGNAL" if comp.quality_edge >= 0.5 else "❌ INCONCLUSIVE")
    )

    lines = [
        "## Win vs Loss — Score Comparison",
        "",
        f"**{edge_tag}**  |  Quality Edge: `{comp.quality_edge:+.2f}` pts  |  "
        f"N = {comp.n_wins} wins, {comp.n_losses} losses",
        "",
        "```",
        "Winning Trades",
        "",
        f"  Avg Quality Score   = {comp.win_avg_quality:.1f}  {_score_bar(comp.win_avg_quality)}",
        f"  Avg Decision Score  = {comp.win_avg_decision:.1f}  {_score_bar(comp.win_avg_decision)}",
        f"  Avg Technical Score = {comp.win_avg_technical:.1f}  {_score_bar(comp.win_avg_technical)}",
        f"  Avg Macro Score     = {comp.win_avg_macro:.1f}  {_score_bar(comp.win_avg_macro)}",
        f"  SFT = HIGH rate     = {comp.win_sft_high_pct:.1f}%",
        "",
        "Losing Trades",
        "",
        f"  Avg Quality Score   = {comp.loss_avg_quality:.1f}  {_score_bar(comp.loss_avg_quality)}",
        f"  Avg Decision Score  = {comp.loss_avg_decision:.1f}  {_score_bar(comp.loss_avg_decision)}",
        f"  Avg Technical Score = {comp.loss_avg_technical:.1f}  {_score_bar(comp.loss_avg_technical)}",
        f"  Avg Macro Score     = {comp.loss_avg_macro:.1f}  {_score_bar(comp.loss_avg_macro)}",
        f"  SFT = HIGH rate     = {comp.loss_sft_high_pct:.1f}%",
        "```",
        "",
    ]
    return lines


def _section_tier_win_rates(tier_stats: dict) -> list:
    if not tier_stats:
        return []

    lines = [
        "---",
        "",
        "## Quality Tier → Win Rate",
        "",
        "| Tier | Trades | Closed | WR% | Avg PnL | Expected WR |",
        "|---|---|---|---|---|---|",
    ]

    from analysis.trade_quality_scoring import TIER_EXPECTED_WIN_RATES
    tier_order = [
        QualityTier.PREMIUM.value,
        QualityTier.HIGH.value,
        QualityTier.MEDIUM.value,
        QualityTier.LOW.value,
        "UNKNOWN",
    ]
    for tier in tier_order:
        if tier not in tier_stats:
            continue
        s    = tier_stats[tier]
        exp  = TIER_EXPECTED_WIN_RATES.get(tier)
        exp_s = f"{exp*100:.0f}%" if exp else "—"
        gap   = ""
        if exp and s["closed"] > 0:
            actual_wr = s["win_rate"] / 100
            diff = actual_wr - exp
            gap = f" ({'+' if diff >= 0 else ''}{diff*100:.1f}% vs expected)"
        lines.append(
            f"| {tier} | {s['total']} | {s['closed']} | "
            f"{s['win_rate']:.1f}%{gap} | ₹{s['avg_pnl']:,.0f} | {exp_s} |"
        )

    lines.append("")
    return lines


def _section_regime_breakdown(regime_data: dict) -> list:
    if not regime_data:
        return []

    lines = [
        "---",
        "",
        "## Performance by Market Regime",
        "",
        "| Regime | Trades | WR% | Avg Quality Score |",
        "|---|---|---|---|",
    ]
    for regime, data in sorted(regime_data.items()):
        lines.append(
            f"| {regime} | {data['trades']} | {data['win_rate']:.1f}% "
            f"| {data['avg_quality']:.2f} |"
        )
    lines.append("")
    return lines


def _section_high_conviction(hc_stats: dict) -> list:
    hc  = hc_stats.get("high_conviction", {})
    nc  = hc_stats.get("normal", {})
    if not hc.get("trades") and not nc.get("trades"):
        return []

    lines = [
        "---",
        "",
        "## High-Conviction vs Normal Trades",
        "",
        "High-conviction = quality_score ≥ 7.5 AND margin > 0.5",
        "",
        "| Type | Trades | WR% | Avg PnL |",
        "|---|---|---|---|",
        f"| High-Conviction | {hc.get('trades',0)} | {hc.get('win_rate',0):.1f}% "
        f"| ₹{hc.get('avg_pnl',0):,.0f} |",
        f"| Normal | {nc.get('trades',0)} | {nc.get('win_rate',0):.1f}% "
        f"| ₹{nc.get('avg_pnl',0):,.0f} |",
        "",
    ]
    return lines


def _section_anomalies(all_trades: list) -> list:
    """Flag low-quality wins and high-quality losses for investigation."""
    low_q_wins = sorted(
        [t for t in all_trades
         if t.get("outcome") == "WIN" and (t.get("quality_score") or 10.0) < 6.5],
        key=lambda x: x.get("quality_score", 0),
    )[:5]

    high_q_losses = sorted(
        [t for t in all_trades
         if t.get("outcome") == "LOSS" and (t.get("quality_score") or 0.0) >= 7.5],
        key=lambda x: -(x.get("quality_score") or 0),
    )[:5]

    lines = []

    if low_q_wins:
        lines += [
            "---",
            "",
            "## Low-Quality Wins — False Negatives",
            "_Scored < 6.5 but still won. May indicate missing signal sources._",
            "",
            "| Symbol | Strategy | Quality | Decision | PnL |",
            "|---|---|---|---|---|",
        ]
        for t in low_q_wins:
            lines.append(
                f"| {t['symbol']} | {t['strategy']} | {t['quality_score']:.2f} "
                f"| {t['decision_score']:.2f} | ₹{t['pnl']:,.0f} |"
            )
        lines.append("")

    if high_q_losses:
        lines += [
            "---",
            "",
            "## High-Quality Losses — Probe for System Error",
            "_Scored ≥ 7.5 but still lost. Review for slippage, news shock, or scoring error._",
            "",
            "| Symbol | Strategy | Quality | Decision | PnL |",
            "|---|---|---|---|---|",
        ]
        for t in high_q_losses:
            lines.append(
                f"| {t['symbol']} | {t['strategy']} | {t['quality_score']:.2f} "
                f"| {t['decision_score']:.2f} | ₹{t['pnl']:,.0f} |"
            )
        lines.append("")

    return lines


def _section_conclusion(comp: Optional[OutcomeComparison], total: int, closed: int) -> list:
    lines = [
        "---",
        "",
        "## Conclusion",
        "",
    ]

    if comp is None or closed < 10:
        lines += [
            f"Only {closed} closed trades so far. Need at least 10 for meaningful comparison.",
            "",
            "Continue logging trades. Revisit after 50 closed.",
        ]
    elif comp.quality_edge >= 1.0:
        lines += [
            "Quality scoring is **working**.",
            "",
            f"A {comp.quality_edge:.2f}-point quality gap separates winning trades "
            f"(avg {comp.win_avg_quality:.1f}) from losing trades (avg {comp.loss_avg_quality:.1f}).",
            "",
            "**Recommended Action:** Raise minimum quality gate to 7.0+.",
            "Filter any trade with quality_score < 6.5.",
            "Prioritise HIGH-SFT symbols.",
        ]
    elif comp.quality_edge >= 0.5:
        lines += [
            "Quality scoring shows a **marginal signal**.",
            "",
            f"Edge of {comp.quality_edge:.2f} points is positive but not yet decisive.",
            "",
            "**Recommended Action:** Collect 100+ closed trades before adjusting thresholds.",
            "Monitor whether edge grows with more data.",
        ]
    else:
        lines += [
            "Quality scoring shows **no clear signal** yet.",
            "",
            "This is normal under 50 closed trades. Continue collecting.",
            "",
            "If still inconclusive at 100 trades, review score calibration.",
        ]

    lines += ["", "---", "", "*Shadow analysis only. No trades placed or modified.*"]
    return lines


# ── Main entry point ──────────────────────────────────────────────────────────

def generate_full_report(
    tracker:     TradeQualityTracker,
    output_path: str,
) -> str:
    """
    Generate and write the full trade quality audit markdown report.

    Args:
        tracker:     Populated TradeQualityTracker instance.
        output_path: Absolute path for the markdown output file.

    Returns:
        The markdown string that was written.
    """
    total  = tracker.count_total()
    closed = tracker.count_closed()

    header = [
        "# TRADE QUALITY AUDIT REPORT",
        "",
        f"**Generated:** {datetime.now(timezone.utc).isoformat()}",
        "**Module:** TRADE_QUALITY_AUDIT_001",
        "**Mode:** Shadow analysis — no live trading",
        f"**Total trades logged:** {total}",
        f"**Closed trades analysed:** {closed}",
        "",
        "---",
        "",
    ]

    comp        = tracker.get_comparison()
    tier_stats  = tracker.get_tier_statistics()
    regime_data = tracker.get_regime_breakdown()
    hc_stats    = tracker.get_high_conviction_stats()
    all_trades  = tracker.get_all_trades()

    sections = (
        header
        + _section_win_loss(comp)
        + _section_tier_win_rates(tier_stats)
        + _section_regime_breakdown(regime_data)
        + _section_high_conviction(hc_stats)
        + _section_anomalies(all_trades)
        + _section_conclusion(comp, total, closed)
    )

    report = "\n".join(sections)

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report)

    return report
