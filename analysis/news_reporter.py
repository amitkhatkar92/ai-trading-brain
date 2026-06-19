"""
analysis/news_reporter.py
============================
NEWS_AUDIT_001 — Markdown report generator.

No database writes. No live-system imports.
Reads from NewsImpactTracker and writes one markdown report.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import List, Optional

from analysis.news_impact_tracker import NewsImpactTracker
from analysis.news_classifier import NEWS_TYPE_PRIORS, NewsType


# ── Helpers ───────────────────────────────────────────────────────────────────

def _verdict_icon(verdict: str) -> str:
    return {
        "STRONG_SIGNAL":    "✅",
        "MODERATE_SIGNAL":  "🟢",
        "WEAK_SIGNAL":      "⚠️",
        "NO_SIGNAL":        "❌",
        "INSUFFICIENT_DATA": "—",
    }.get(verdict, "—")


def _wr_icon(win_rate: float) -> str:
    if win_rate >= 65:
        return "✅"
    elif win_rate >= 50:
        return "🟢"
    elif win_rate >= 40:
        return "⚠️"
    return "❌"


# ── Sections ──────────────────────────────────────────────────────────────────

def _section_header(total: int, closed: int) -> list:
    return [
        "# NEWS AUDIT REPORT",
        "",
        f"**Generated:** {datetime.now(timezone.utc).isoformat()}",
        "**Module:** NEWS_AUDIT_001",
        "**Mode:** Shadow analysis — no live trading",
        f"**Total observations:** {total}",
        f"**Observations with outcomes:** {closed}",
        "",
        "---",
        "",
    ]


def _section_summary_table(by_type: dict) -> list:
    if not by_type:
        return []

    lines = [
        "## News Type Impact Summary",
        "",
        "| News Type | Observations | WR% | Avg Move | Dir Accuracy | Strategy Impact | Verdict |",
        "|---|---|---|---|---|---|---|",
    ]

    # Order by win rate descending
    ordered = sorted(
        [(k, v) for k, v in by_type.items() if v.get("closed", 0) > 0],
        key=lambda x: -x[1].get("win_rate", 0),
    )

    for ntype, data in ordered:
        icon     = _verdict_icon(data.get("verdict", ""))
        wr_icon  = _wr_icon(data.get("win_rate", 0))
        lines.append(
            f"| {ntype} | {data['total']} | "
            f"{wr_icon} {data['win_rate']:.1f}% | "
            f"{data['avg_move_pct']:+.2f}% | "
            f"{data['direction_accuracy']:.1f}% | "
            f"{data.get('strategy_impact','?')} | "
            f"{icon} {data.get('verdict', '—')} |"
        )

    lines += [""]
    return lines


def _section_top_catalysts(top: List[dict]) -> list:
    if not top:
        return []

    lines = [
        "---",
        "",
        "## Top 5 Positive Catalysts",
        "",
        "_(News types with highest win rates — prioritise trading when these occur)_",
        "",
    ]
    for i, r in enumerate(top, 1):
        prior = NEWS_TYPE_PRIORS.get(r["news_type"], {})
        lines += [
            f"### #{i} {r['news_type']}",
            f"- **Win Rate:** {r['win_rate']:.1f}%  ({r['wins']}/{r['closed']} trades)",
            f"- **Avg 5-day move:** {r['avg_move_pct']:+.2f}%",
            f"- **Direction Accuracy:** {r['direction_accuracy']:.1f}%",
            f"- **Note:** {prior.get('note', '—')}",
            "",
        ]
    return lines


def _section_no_signal(no_signal: List[str]) -> list:
    if not no_signal:
        return []

    lines = [
        "---",
        "",
        "## No-Signal News Types",
        "",
        "_(These news types show no predictive value for trade outcomes)_",
        "",
        "| News Type | Recommendation |",
        "|---|---|",
    ]
    for ntype in no_signal:
        lines.append(
            f"| {ntype} | Consider ignoring in trade filters — no edge found |"
        )
    lines += [
        "",
        "> **Action:** Do NOT use these event types as trade signals.",
        "> Continue tracking for at least 50 more observations before removing from system.",
        "",
    ]
    return lines


def _section_questions_answered(by_type: dict) -> list:
    """The key questions the user asked — answered directly."""

    def _answer(ntype: str) -> str:
        data = by_type.get(ntype)
        if not data or data.get("closed", 0) < 5:
            return "INSUFFICIENT DATA"
        wr  = data["win_rate"]
        dir_acc = data["direction_accuracy"]
        verdict = data.get("verdict", "")
        if verdict == "STRONG_SIGNAL":
            return f"YES — WR={wr:.1f}%, direction accuracy={dir_acc:.1f}%"
        elif verdict in ("MODERATE_SIGNAL", "WEAK_SIGNAL"):
            return f"PARTIAL — WR={wr:.1f}%, direction accuracy={dir_acc:.1f}%"
        return f"NO — WR={wr:.1f}%, direction accuracy={dir_acc:.1f}%"

    lines = [
        "---",
        "",
        "## Questions Answered",
        "",
        "| Question | Answer |",
        "|---|---|",
        f"| Do EARNINGS matter? | {_answer(NewsType.EARNINGS.value)} |",
        f"| Do CORPORATE ACTIONS matter? | {_answer(NewsType.CORPORATE_ACTION.value)} |",
        f"| Do ANALYST calls matter? | {_answer(NewsType.UPGRADE_DOWNGRADE.value)} |",
        f"| Does SECTOR NEWS matter? | {_answer(NewsType.SECTOR_NEWS.value)} |",
        f"| Do RBI decisions matter? | {_answer(NewsType.RBI_POLICY.value)} |",
        f"| Do Fed meetings matter? | {_answer(NewsType.FED_MEETING.value)} |",
        f"| Does ECB meeting matter? | {_answer(NewsType.ECB_MEETING.value)} |",
        f"| Does BUDGET matter? | {_answer(NewsType.BUDGET.value)} |",
        f"| Does TAX POLICY matter? | {_answer(NewsType.TAX_POLICY.value)} |",
        f"| Do ELECTIONS matter? | {_answer(NewsType.ELECTION.value)} |",
        f"| Do POLITICAL EVENTS matter? | {_answer(NewsType.POLITICAL_EVENT.value)} |",
        f"| Does WAR matter? | {_answer(NewsType.WAR.value)} |",
        f"| Does GEOPOLITICAL TENSION matter? | {_answer(NewsType.GEOPOLITICAL_TENSION.value)} |",
        f"| Do SANCTIONS matter? | {_answer(NewsType.SANCTIONS.value)} |",
        f"| Does TRADE WAR matter? | {_answer(NewsType.TRADE_WAR.value)} |",
        f"| Do CRUDE OIL SHOCKS matter? | {_answer(NewsType.CRUDE_OIL_SHOCK.value)} |",
        f"| Do CURRENCY SHOCKS matter? | {_answer(NewsType.CURRENCY_SHOCK.value)} |",
        f"| Are BLACK SWAN events tradeable? | {_answer(NewsType.BLACK_SWAN.value)} |",
        "",
    ]
    return lines


def _section_conclusion(by_type: dict, total: int, closed: int) -> list:
    lines = ["---", "", "## Conclusion", ""]

    if closed < 30:
        lines += [
            f"Only {closed} observations with outcomes. Need at least 30 per news type.",
            "Continue collecting. Re-run after 100 total observations.",
        ]
        lines += ["", "---", "", "*Shadow analysis only. No trades placed or modified.*"]
        return lines

    strong = [k for k, v in by_type.items() if v.get("verdict") == "STRONG_SIGNAL"]
    no_sig = [k for k, v in by_type.items()
              if v.get("verdict") in ("NO_SIGNAL", "WEAK_SIGNAL") and v.get("closed", 0) >= 5]

    if strong:
        lines += [
            f"**{len(strong)} news type(s) show strong signal:** {', '.join(strong)}",
            "",
            "These are your most reliable catalysts. When these events occur with "
            "positive sentiment and a trade is aligned, win probability is elevated.",
            "",
        ]
    if no_sig:
        lines += [
            f"**{len(no_sig)} news type(s) show no signal:** {', '.join(no_sig)}",
            "",
            "These events are noise. Consider removing them from the decision pipeline.",
            "",
        ]

    lines += ["---", "", "*Shadow analysis only. No trades placed or modified.*"]
    return lines


# ── Main entry point ──────────────────────────────────────────────────────────

def generate_news_report(
    tracker:     NewsImpactTracker,
    output_path: str,
) -> str:
    """
    Build and write the NEWS AUDIT REPORT markdown file.

    Returns the markdown string written.
    """
    total     = tracker.count_total()
    closed    = len(tracker.get_closed())
    by_type   = tracker.impact_by_type()
    top       = tracker.top_catalysts()
    no_signal = tracker.no_signal_types()

    sections = (
        _section_header(total, closed)
        + _section_summary_table(by_type)
        + _section_top_catalysts(top)
        + _section_no_signal(no_signal)
        + _section_questions_answered(by_type)
        + _section_conclusion(by_type, total, closed)
    )

    report = "\n".join(sections)
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report)
    return report
