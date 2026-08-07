"""predictive_gap/pga_reporter.py — Generate 9 PGA-001 Markdown reports."""
from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import List

from .pga_analyzer import (
    StockAnalysis,
    MISS_CORRECT, MISS_MISSED_WINNER, MISS_MISSED_LOSER,
    MISS_WRONG_DIRECTION, MISS_NO_DATA,
    PRED_YES, PRED_PART, PRED_NO,
    WP_YES, WP_PARTIALLY, WP_NO,
)
from .pga_collector import DailyData
from .pga_config import LEARNING_CATEGORIES
from .pga_learning import LearningAction
from .pga_root_cause import RootCause

log = logging.getLogger(__name__)

_W = 90   # report width


def _hr(c: str = "─", w: int = _W) -> str:
    return c * w


def _move_badge(ret: float) -> str:
    if ret >= 3:   return "🚀"
    if ret >= 1.5: return "▲"
    if ret >= 0:   return "▶"
    if ret >= -1.5: return "▼"
    if ret >= -3:  return "🔻"
    return "💥"


def _pred_badge(wp: str) -> str:
    return {"YES": "✅", "PARTIALLY": "⚡", "NO": "❌"}.get(wp, "?")


def _predictable_badge(pred: str) -> str:
    return {
        "PREDICTABLE": "🟢",
        "PARTIALLY_PREDICTABLE": "🟡",
        "NOT_PREDICTABLE": "🔴",
    }.get(pred, "?")


def _miss_badge(mt: str) -> str:
    return {
        MISS_CORRECT:         "✅ CORRECT",
        MISS_MISSED_WINNER:   "❌ MISSED WINNER",
        MISS_MISSED_LOSER:    "❌ MISSED LOSER",
        MISS_WRONG_DIRECTION: "⚠️  WRONG DIRECTION",
        MISS_NO_DATA:         "── NO DATA",
    }.get(mt, mt)


def _analysis_table(analyses: List[StockAnalysis], title: str = "") -> str:
    lines = []
    if title:
        lines.append(f"### {title}")
        lines.append("")
    hdr = f"{'Symbol':<12} {'Return':>7} {'Predicted':>10} {'Predictable':>22} {'DNA':>4} {'Outcome'}"
    lines.append(hdr)
    lines.append(_hr("-", len(hdr)))
    for a in analyses:
        ret_str  = f"{a.stock_move.daily_return_pct:+.1f}%"
        lines.append(
            f"{a.symbol:<12} {ret_str:>7} "
            f"{_pred_badge(a.was_predicted)+a.was_predicted:>14} "
            f"{_predictable_badge(a.was_predictable)+' '+a.was_predictable:>28} "
            f"{a.dna_coverage:>4}  {_miss_badge(a.miss_type)}"
        )
    return "\n".join(lines)


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    log.debug("[PGA] Written: %s", path)


# ────────────────────────────────────────────────────────────────────
# Individual report builders
# ────────────────────────────────────────────────────────────────────

def _r1_daily_report(
    data: DailyData,
    analyses: List[StockAnalysis],
    causes: List[RootCause],
    actions: List[LearningAction],
    report_dir: Path,
) -> None:
    """PGA_DAILY_REPORT.md — master summary."""
    ts   = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    date = data.date

    n_correct     = sum(1 for r in causes if r.miss_type == MISS_CORRECT)
    n_missed_w    = sum(1 for r in causes if r.miss_type == MISS_MISSED_WINNER)
    n_missed_l    = sum(1 for r in causes if r.miss_type == MISS_MISSED_LOSER)
    n_wrong_dir   = sum(1 for r in causes if r.miss_type == MISS_WRONG_DIRECTION)
    n_predictable = sum(1 for a in analyses if a.was_predictable == PRED_YES)
    n_part_pred   = sum(1 for a in analyses if a.was_predictable == PRED_PART)
    n_not_pred    = sum(1 for a in analyses if a.was_predictable == PRED_NO)
    n_actions     = sum(1 for a in actions if a.category)
    cat_counts    = {c: sum(1 for a in actions if a.category == c) for c in "ABCDEFG"}
    n_hyp         = sum(1 for a in actions if a.category == "C" and a.scheduled)

    lines = [
        f"# PGA-001 Daily Predictive Gap Analysis",
        f"**Date:** {date}  |  **Generated:** {ts}",
        _hr("═"),
        "",
        "## Executive Summary",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Stocks Analysed | {len(analyses)} |",
        f"| Correct Predictions | {n_correct} |",
        f"| Missed Winners | {n_missed_w} |",
        f"| Missed Losers | {n_missed_l} |",
        f"| Wrong Direction | {n_wrong_dir} |",
        f"| Predictable Misses | {n_predictable} |",
        f"| Partially Predictable | {n_part_pred} |",
        f"| Not Predictable | {n_not_pred} |",
        f"| Learning Actions | {n_actions} |",
        f"| Hypotheses Created | {n_hyp} |",
        "",
        _hr("─"),
        "",
        "## Market Context",
        "",
        f"- **Regime:** {data.market_stats.get('regime', 'UNKNOWN')}",
        f"- **VIX:** {data.market_stats.get('vix', 0):.1f}",
        f"- **Breadth:** {data.market_stats.get('breadth', 0.5):.2f}",
        f"- **Universe:** {len(data.universe_symbols)} symbols",
        f"- **Scanned Today:** {len(data.scanned_today)}",
        f"- **Approved Trades:** {len(data.approved_today)}",
        f"- **Rejected Trades:** {len(data.rejected_today)}",
        f"- **Executed Trades:** {len(data.executed_trades)}",
        "",
        _hr("─"),
        "",
        "## Top 5 Gainers",
        "",
        _analysis_table([a for a in analyses if a.symbol in [m.symbol for m in data.gainers]]),
        "",
        "## Top 5 Losers",
        "",
        _analysis_table([a for a in analyses if a.symbol in [m.symbol for m in data.losers]]),
        "",
        _hr("─"),
        "",
        "## Learning Actions Summary",
        "",
    ]
    for cat, desc in LEARNING_CATEGORIES.items():
        count = cat_counts.get(cat, 0)
        if count:
            syms = [a.symbol for a in actions if a.category == cat]
            lines.append(f"- **Cat {cat} — {desc}:** {count} action(s) for {', '.join(syms)}")
    if not any(cat_counts.values()):
        lines.append("- No learning actions identified today.")
    lines += ["", _hr("─"), "", "## What Did IIOS Learn Today?", ""]

    learned = [a for a in actions if a.scheduled and a.outcome not in ("DRY_RUN", "LOGGED_FOR_REVIEW", "")]
    if learned:
        for a in learned:
            lines.append(f"- **{a.symbol}** ({a.category}): {a.description} → `{a.outcome}`")
    else:
        lines.append("- No live system updates executed today (actions logged for review).")

    lines += ["", "## What Remains Unexplained?", ""]
    unexplained = [
        r for r in causes
        if not r.can_improve and r.miss_type not in (MISS_CORRECT, MISS_NO_DATA)
    ]
    if unexplained:
        for r in unexplained:
            lines.append(f"- **{r.symbol}** ({r.miss_type}): {r.reason_not_improvable or r.explanation}")
    else:
        lines.append("- All analysed misses have improvable root causes.")

    lines += ["", "## New Hypotheses Generated", ""]
    hyp_actions = [a for a in actions if a.category == "C"]
    if hyp_actions:
        for a in hyp_actions:
            status = "✅ Created" if a.scheduled else "⏳ Pending"
            lines.append(f"- **{a.symbol}**: {a.payload.get('title', '')} — {status}")
    else:
        lines.append("- No new hypotheses generated today.")

    lines += ["", "## Research Scheduled", ""]
    research = [a for a in actions if a.category == "D"]
    if research:
        for a in research:
            lines.append(f"- **{a.symbol}**: {a.description}")
    else:
        lines.append("- No new research studies scheduled today.")

    lines += ["", "## Knowledge Reinforced", ""]
    reinforced = [a for a in actions if a.category == "B" and a.scheduled]
    if reinforced:
        for a in reinforced:
            lines.append(f"- **{a.symbol}**: {a.description}")
    else:
        lines.append("- No knowledge reinforcement executed today.")

    lines += ["", "## DNA / Edge Changes", ""]
    dna_actions = [a for a in actions if a.category in ("E",)]
    edge_actions = [a for a in actions if a.category == "G"]
    if dna_actions:
        lines.append("**DNA Candidates Identified:**")
        for a in dna_actions:
            lines.append(f"- **{a.symbol}**: {a.description}")
    if edge_actions:
        lines.append("**Edge Discovery Scheduled:**")
        for a in edge_actions:
            lines.append(f"- **{a.symbol}**: {a.description}")
    if not dna_actions and not edge_actions:
        lines.append("- No DNA or edge changes today.")

    lines += ["", "## Future Prediction Capability", ""]
    lines.append(
        f"- Predictable coverage: **{n_predictable}/{len(analyses)}** stocks "
        f"({100*n_predictable//max(len(analyses),1)}%)"
    )
    improvement_syms = list({a.symbol for a in actions})
    if improvement_syms:
        lines.append(f"- Improvement actions for: **{', '.join(improvement_syms[:10])}**")
    lines += ["", _hr("═"), f"*Report generated by PGA-001 at {ts}*"]

    _write(report_dir / "PGA_DAILY_REPORT.md", "\n".join(lines))


def _r2_gainer_analysis(data: DailyData, analyses: List[StockAnalysis], report_dir: Path) -> None:
    """TOP_GAINER_ANALYSIS.md."""
    gainer_syms = {m.symbol for m in data.gainers}
    gainer_analyses = [a for a in analyses if a.symbol in gainer_syms]

    lines = [
        "# Top Gainer Analysis — PGA-001",
        f"**Date:** {data.date}",
        _hr("═"), "",
        "## Summary", "",
        _analysis_table(gainer_analyses),
        "",
    ]
    for a in gainer_analyses:
        move = a.stock_move
        lines += [
            _hr("─"), "",
            f"### {_move_badge(move.daily_return_pct)} {a.symbol}  "
            f"({move.daily_return_pct:+.1f}%  {move.open_price:.2f} → {move.close_price:.2f})",
            "",
            f"- **IIOS Predicted:** {_pred_badge(a.was_predicted)} {a.was_predicted}",
            f"- **Was Predictable:** {_predictable_badge(a.was_predictable)} {a.was_predictable}",
            f"- **Outcome:** {_miss_badge(a.miss_type)}",
            f"- **DNA Coverage:** {a.dna_coverage}  |  **Edge Coverage:** {a.edge_coverage}",
            f"- **Prediction Detail:** {a.prediction_detail}",
            f"- **Predictability Detail:** {a.predictability_detail}",
            "",
        ]
        if a.iios_decision:
            d = a.iios_decision
            lines += [
                f"**IIOS Decision:** {d.direction}  conf={d.confidence:.1f}  "
                f"approved={d.approved}  strategy={d.strategy}",
                f"- Rejection reason: {d.rejection_reason or '—'}",
                "",
            ]

    _write(report_dir / "TOP_GAINER_ANALYSIS.md", "\n".join(lines))


def _r3_loser_analysis(data: DailyData, analyses: List[StockAnalysis], report_dir: Path) -> None:
    """TOP_LOSER_ANALYSIS.md."""
    loser_syms = {m.symbol for m in data.losers}
    loser_analyses = [a for a in analyses if a.symbol in loser_syms]

    lines = [
        "# Top Loser Analysis — PGA-001",
        f"**Date:** {data.date}",
        _hr("═"), "",
        "## Summary", "",
        _analysis_table(loser_analyses),
        "",
    ]
    for a in loser_analyses:
        move = a.stock_move
        lines += [
            _hr("─"), "",
            f"### {_move_badge(move.daily_return_pct)} {a.symbol}  "
            f"({move.daily_return_pct:+.1f}%  {move.open_price:.2f} → {move.close_price:.2f})",
            "",
            f"- **IIOS Predicted:** {_pred_badge(a.was_predicted)} {a.was_predicted}",
            f"- **Was Predictable:** {_predictable_badge(a.was_predictable)} {a.was_predictable}",
            f"- **Outcome:** {_miss_badge(a.miss_type)}",
            f"- **DNA Coverage:** {a.dna_coverage}  |  **Edge Coverage:** {a.edge_coverage}",
            f"- **Prediction Detail:** {a.prediction_detail}",
            f"- **Predictability Detail:** {a.predictability_detail}",
            "",
        ]
        if a.iios_decision:
            d = a.iios_decision
            lines += [
                f"**IIOS Decision:** {d.direction}  conf={d.confidence:.1f}  "
                f"approved={d.approved}  strategy={d.strategy}",
                f"- Rejection reason: {d.rejection_reason or '—'}",
                "",
            ]

    _write(report_dir / "TOP_LOSER_ANALYSIS.md", "\n".join(lines))


def _r4_missed_winners(data: DailyData, analyses: List[StockAnalysis], report_dir: Path) -> None:
    """MISSED_WINNER_ANALYSIS.md."""
    missed = [a for a in analyses if a.miss_type == MISS_MISSED_WINNER]
    lines = [
        "# Missed Winner Analysis — PGA-001",
        f"**Date:** {data.date}  |  **Count:** {len(missed)}",
        _hr("═"), "",
    ]
    if not missed:
        lines.append("**No missed winners today.** IIOS captured all significant upside moves.")
    else:
        lines += ["## Summary", "", _analysis_table(missed), ""]
        for a in missed:
            move = a.stock_move
            lines += [
                _hr("─"), "",
                f"### {a.symbol}  ({move.daily_return_pct:+.1f}%)",
                f"- Predictable: {_predictable_badge(a.was_predictable)} {a.was_predictable}",
                f"- DNA: {a.dna_coverage}  Edges: {a.edge_coverage}",
                f"- {a.prediction_detail}",
                f"- {a.predictability_detail}",
                "",
            ]
    _write(report_dir / "MISSED_WINNER_ANALYSIS.md", "\n".join(lines))


def _r5_missed_losers(data: DailyData, analyses: List[StockAnalysis], report_dir: Path) -> None:
    """MISSED_LOSER_ANALYSIS.md."""
    missed = [a for a in analyses if a.miss_type == MISS_MISSED_LOSER]
    lines = [
        "# Missed Loser Analysis — PGA-001",
        f"**Date:** {data.date}  |  **Count:** {len(missed)}",
        _hr("═"), "",
    ]
    if not missed:
        lines.append("**No missed losers today.** IIOS either avoided downside or correctly stayed out.")
    else:
        lines += ["## Summary", "", _analysis_table(missed), ""]
        for a in missed:
            move = a.stock_move
            lines += [
                _hr("─"), "",
                f"### {a.symbol}  ({move.daily_return_pct:+.1f}%)",
                f"- Predictable: {_predictable_badge(a.was_predictable)} {a.was_predictable}",
                f"- DNA: {a.dna_coverage}  Edges: {a.edge_coverage}",
                f"- {a.prediction_detail}",
                f"- {a.predictability_detail}",
                "",
            ]
    _write(report_dir / "MISSED_LOSER_ANALYSIS.md", "\n".join(lines))


def _r6_root_cause(causes: List[RootCause], report_dir: Path, report_date: str) -> None:
    """ROOT_CAUSE_REPORT.md."""
    actionable = [c for c in causes if c.miss_type not in (MISS_CORRECT, MISS_NO_DATA)]
    cause_dist: dict = {}
    for c in actionable:
        cause_dist[c.primary_cause] = cause_dist.get(c.primary_cause, 0) + 1
    top_cause = max(cause_dist, key=cause_dist.get) if cause_dist else "None"

    lines = [
        "# Root Cause Report — PGA-001",
        f"**Date:** {report_date}  |  **Misses Analysed:** {len(actionable)}",
        _hr("═"), "",
        "## Cause Distribution", "",
        f"| Cause | Count |",
        f"|-------|-------|",
    ]
    for cause, count in sorted(cause_dist.items(), key=lambda x: -x[1]):
        lines.append(f"| {cause} | {count} |")

    lines += [
        "",
        f"**Dominant Root Cause Today:** `{top_cause}`",
        "", _hr("─"), "",
        "## Detailed Root Causes", "",
    ]
    for c in actionable:
        can_str = "✅ Yes" if c.can_improve else f"❌ No — {c.reason_not_improvable}"
        lines += [
            f"### {c.symbol}  ({c.miss_type})",
            f"- **Primary Cause:** {c.primary_cause}",
            f"- **Secondary Cause:** {c.secondary_cause or '—'}",
            f"- **Can Improve:** {can_str}",
            f"- **Category:** {c.improvement_category or '—'}",
            f"- **Explanation:** {c.explanation}",
        ]
        if c.evidence:
            lines.append(f"- **Evidence:** {'; '.join(c.evidence)}")
        lines.append("")
    _write(report_dir / "ROOT_CAUSE_REPORT.md", "\n".join(lines))


def _r7_predictability(analyses: List[StockAnalysis], report_dir: Path, report_date: str) -> None:
    """PREDICTABILITY_REPORT.md."""
    pred = [a for a in analyses if a.was_predictable == "PREDICTABLE"]
    part = [a for a in analyses if a.was_predictable == "PARTIALLY_PREDICTABLE"]
    no   = [a for a in analyses if a.was_predictable == "NOT_PREDICTABLE"]

    lines = [
        "# Predictability Report — PGA-001",
        f"**Date:** {report_date}",
        _hr("═"), "",
        f"| Category | Count | Pct |",
        f"|----------|-------|-----|",
        f"| 🟢 PREDICTABLE | {len(pred)} | {100*len(pred)//max(len(analyses),1)}% |",
        f"| 🟡 PARTIALLY_PREDICTABLE | {len(part)} | {100*len(part)//max(len(analyses),1)}% |",
        f"| 🔴 NOT_PREDICTABLE | {len(no)} | {100*len(no)//max(len(analyses),1)}% |",
        "", _hr("─"), "",
        "## Predictable Stocks (IIOS had sufficient intelligence)", "",
    ]
    for a in pred:
        lines.append(f"- **{a.symbol}**: {a.predictability_detail}")
    lines += ["", "## Partially Predictable", ""]
    for a in part:
        lines.append(f"- **{a.symbol}**: {a.predictability_detail}")
    lines += ["", "## Not Predictable (External Events / No Data)", ""]
    for a in no:
        lines.append(f"- **{a.symbol}** ({a.stock_move.daily_return_pct:+.1f}%): {a.predictability_detail}")

    _write(report_dir / "PREDICTABILITY_REPORT.md", "\n".join(lines))


def _r8_research_recommendations(
    actions: List[LearningAction],
    causes: List[RootCause],
    report_dir: Path,
    report_date: str,
) -> None:
    """RESEARCH_RECOMMENDATIONS.md."""
    research = [a for a in actions if a.category in ("C", "D", "F", "G")]
    lines = [
        "# Research Recommendations — PGA-001",
        f"**Date:** {report_date}  |  **Recommendations:** {len(research)}",
        _hr("═"), "",
    ]
    if not research:
        lines.append("No research recommendations today.")
    else:
        for cat in ("C", "D", "F", "G"):
            cat_items = [a for a in research if a.category == cat]
            if not cat_items:
                continue
            lines += [
                f"## Category {cat} — {LEARNING_CATEGORIES.get(cat, '')}",
                f"**{len(cat_items)} recommendation(s)**", "",
            ]
            for a in cat_items:
                lines += [
                    f"### {a.symbol} — `{a.action_type}`",
                    f"{a.description}",
                    f"- **Target System:** {a.target_system}",
                    f"- **Status:** {a.outcome or 'Pending'}",
                    "",
                ]
    _write(report_dir / "RESEARCH_RECOMMENDATIONS.md", "\n".join(lines))


def _r9_learning_actions(
    actions: List[LearningAction],
    report_dir: Path,
    report_date: str,
) -> None:
    """LEARNING_ACTIONS.md — operational action plan."""
    lines = [
        "# Learning Actions — PGA-001",
        f"**Date:** {report_date}  |  **Total Actions:** {len(actions)}",
        _hr("═"), "",
        "| ID | Cat | Symbol | Target | Description | Status |",
        "|-----|-----|--------|--------|-------------|--------|",
    ]
    for a in actions:
        desc_short = (a.description[:50] + "…") if len(a.description) > 50 else a.description
        status = "✅" if a.scheduled else ("⏳" if a.outcome == "LOGGED_FOR_REVIEW" else a.outcome[:10])
        lines.append(
            f"| {a.action_id} | {a.category} | {a.symbol} | {a.target_system} "
            f"| {desc_short} | {status} |"
        )
    if not actions:
        lines.append("| — | — | — | — | No learning actions today | — |")

    lines += [
        "", _hr("─"), "",
        "## Action Breakdown by Category", "",
    ]
    for cat, desc in LEARNING_CATEGORIES.items():
        cat_items = [a for a in actions if a.category == cat]
        if cat_items:
            lines.append(f"**{cat} — {desc} ({len(cat_items)})**")
            for a in cat_items:
                lines.append(f"  - {a.symbol}: {a.description}")
    _write(report_dir / "LEARNING_ACTIONS.md", "\n".join(lines))


# ────────────────────────────────────────────────────────────────────
# Master entry point
# ────────────────────────────────────────────────────────────────────

def write_all_reports(
    data: DailyData,
    analyses: List[StockAnalysis],
    causes: List[RootCause],
    actions: List[LearningAction],
    report_dir: Path,
) -> None:
    """Write all 9 PGA reports to report_dir."""
    report_dir.mkdir(parents=True, exist_ok=True)
    date = data.date

    _r1_daily_report(data, analyses, causes, actions, report_dir)
    _r2_gainer_analysis(data, analyses, report_dir)
    _r3_loser_analysis(data, analyses, report_dir)
    _r4_missed_winners(data, analyses, report_dir)
    _r5_missed_losers(data, analyses, report_dir)
    _r6_root_cause(causes, report_dir, date)
    _r7_predictability(analyses, report_dir, date)
    _r8_research_recommendations(actions, causes, report_dir, date)
    _r9_learning_actions(actions, report_dir, date)

    log.info("[PGA] All 9 reports written → %s", report_dir)
