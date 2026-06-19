"""
analysis/rejection_reporter.py
==================================
REJECTION_AUDIT_001 — Markdown report generator.

No database writes. No live-system imports.
Reads from RejectionTracker, writes one markdown report.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Optional

from analysis.rejection_tracker import RejectionTracker
from analysis.rejection_classifier import REASON_EXPECTED_ACCURACY


# ── Helpers ───────────────────────────────────────────────────────────────────

def _pct_bar(pct: float, width: int = 20) -> str:
    """ASCII bar for a percentage 0–100."""
    filled = max(0, min(width, int(round(pct / 100 * width))))
    return "█" * filled + "░" * (width - filled)


def _accuracy_icon(accuracy_pct: float) -> str:
    if accuracy_pct >= 70:
        return "✅"
    elif accuracy_pct >= 55:
        return "⚠️"
    return "❌"


# ── Report sections ───────────────────────────────────────────────────────────

def _section_header(total: int, classified: int) -> list:
    return [
        "# REJECTION AUDIT REPORT",
        "",
        f"**Generated:** {datetime.now(timezone.utc).isoformat()}",
        "**Module:** REJECTION_AUDIT_001",
        "**Mode:** Shadow analysis — no live trading",
        f"**Total rejections logged:** {total}",
        f"**Classified (5d follow-through available):** {classified}",
        "",
        "---",
        "",
    ]


def _section_overall(stats: dict) -> list:
    if stats.get("classified", 0) == 0:
        return [
            "## Overall Rejection Accuracy",
            "",
            "_No classified rejections yet. Ensure price follow-through data is loaded._",
            "",
        ]

    acc   = stats["accuracy_pct"]
    fn    = stats["false_negative_pct"]
    icon  = _accuracy_icon(acc)

    if acc >= 70:
        verdict = "**Rejection system is working. More rejections than false alarms.**"
    elif acc >= 55:
        verdict = "**Marginal accuracy. Monitor — system may be too aggressive.**"
    else:
        verdict = "**Rejection system may be rejecting too many winners. Investigate.**"

    return [
        "## Overall Rejection Accuracy",
        "",
        f"{icon} **Accuracy: {acc:.1f}%**  |  False Negatives: {fn:.1f}%",
        "",
        "```",
        f"Rejected Trades:        {stats['total']:>6d}",
        f"Classified:             {stats['classified']:>6d}",
        f"  Correct Rejections:   {stats['correct']:>6d}   {_pct_bar(acc)}  {acc:.1f}%",
        f"  False Rejections:     {stats['false_rejections']:>6d}   (missed winners)",
        f"  Neutral:              {stats['neutral']:>6d}   (move too small)",
        "```",
        "",
        verdict,
        "",
    ]


def _section_by_reason(reason_stats: dict) -> list:
    if not reason_stats:
        return []

    lines = [
        "---",
        "",
        "## Accuracy by Rejection Reason",
        "",
        "| Rejection Reason | Total | Correct | False | Accuracy | Expected | Verdict |",
        "|---|---|---|---|---|---|---|",
    ]

    reason_order = [
        "LOW_SFT", "HIGH_VOL_REGIME", "LOW_DECISION_SCORE",
        "LOW_QUALITY_SCORE", "LOW_CONVICTION",
        "CORRELATED_POSITION", "MAX_POSITIONS",
        "DAILY_LOSS_LIMIT", "MANUAL_OVERRIDE", "UNKNOWN",
    ]
    all_reasons = list(reason_stats.keys())
    ordered = [r for r in reason_order if r in all_reasons] + \
              [r for r in all_reasons if r not in reason_order]

    for reason in ordered:
        s = reason_stats[reason]
        if s.get("classified", 0) == 0:
            continue
        acc_icon = _accuracy_icon(s["accuracy_pct"])
        verdict_display = {
            "OUTPERFORMING":      "✅ OUTPERFORMING",
            "ON_TARGET":          "🟢 ON TARGET",
            "UNDERPERFORMING":    "⚠️ UNDERPERFORMING",
            "BROKEN":             "❌ BROKEN",
            "INSUFFICIENT_DATA":  "— INSUFFICIENT",
        }.get(s.get("verdict", ""), s.get("verdict", "—"))

        lines.append(
            f"| {reason} | {s['classified']} | {s['correct']} "
            f"| {s['false_rejections']} "
            f"| {acc_icon} {s['accuracy_pct']:.1f}% "
            f"| {s.get('expected_pct', 0):.1f}% "
            f"| {verdict_display} |"
        )

    lines += [""]
    return lines


def _section_by_quality_tier(tier_stats: dict) -> list:
    if not tier_stats:
        return []

    lines = [
        "---",
        "",
        "## Accuracy by Quality Tier of Rejected Trade",
        "",
        "_High-quality trades being rejected (PREMIUM/HIGH tier) with low accuracy = system too aggressive_",
        "",
        "| Quality Tier | Rejected | Correct | False | Accuracy |",
        "|---|---|---|---|---|",
    ]

    for tier in ["PREMIUM", "HIGH", "MEDIUM", "LOW", "UNKNOWN"]:
        if tier not in tier_stats:
            continue
        s = tier_stats[tier]
        if s.get("classified", 0) == 0:
            continue
        acc_icon = _accuracy_icon(s["accuracy_pct"])
        lines.append(
            f"| {tier} | {s['classified']} | {s['correct']} "
            f"| {s['false_rejections']} "
            f"| {acc_icon} {s['accuracy_pct']:.1f}% |"
        )

    lines += [
        "",
        "> If PREMIUM/HIGH tier rejections show accuracy < 55%, the system is likely using "
        "a threshold that is too conservative.",
        "",
    ]
    return lines


def _section_missed_winners(analysis: dict, hyp_pnl: float) -> list:
    if not analysis.get("count"):
        return []

    lines = [
        "---",
        "",
        "## Missed Winners — False Rejection Analysis",
        "",
        f"**{analysis['count']} trades rejected that would likely have been winners.**",
        "",
        f"| Metric | Value |",
        f"|---|---|",
        f"| Missed winner count | {analysis['count']} |",
        f"| Avg quality score of missed | {analysis.get('avg_quality', 0):.2f} |",
        f"| Avg 5-day move (favourable) | {analysis.get('avg_move_pct', 0):+.2f}% |",
        f"| Best missed move | {analysis.get('max_move_pct', 0):+.2f}% |",
        f"| Hypothetical total PnL (all rejections) | ₹{hyp_pnl:,.0f} |",
        "",
    ]

    if hyp_pnl < 0:
        lines += [
            "> Hypothetical PnL is **negative** — the rejection system is saving money overall.",
            "> The missed winners are outweighed by the losses correctly avoided.",
            "",
        ]
    elif hyp_pnl > 0:
        lines += [
            "> ⚠️ Hypothetical PnL is **positive** — the system is rejecting more winners "
            "than losers overall.",
            "> Consider reviewing rejection thresholds.",
            "",
        ]

    by_reason = analysis.get("by_reason", {})
    if by_reason:
        lines += [
            "**Missed winners by rejection reason:**",
            "",
            "| Reason | Count |",
            "|---|---|",
        ]
        for reason, cnt in sorted(by_reason.items(), key=lambda x: -x[1]):
            lines.append(f"| {reason} | {cnt} |")
        lines.append("")

    return lines


def _section_conclusion(overall: dict, reason_stats: dict, hyp_pnl: float) -> list:
    classified = overall.get("classified", 0)
    acc        = overall.get("accuracy_pct", 0.0)
    false_r    = overall.get("false_rejections", 0)

    lines = ["---", "", "## Conclusion", ""]

    if classified < 20:
        lines += [
            f"Only {classified} classified rejections. Need at least 20 for reliable signal.",
            "",
            "Continue logging. Re-run after 100 classified observations.",
        ]
    elif acc >= 70:
        lines += [
            f"**Rejection system is working correctly. ({acc:.1f}% accuracy)**",
            "",
            "The system rejects more genuine losers than winners.",
            f"{false_r} false negatives (missed winners) — acceptable rate.",
            "",
            "**Recommended Action:** No change needed. Continue observation.",
        ]
    elif acc >= 55:
        lines += [
            f"**Marginal accuracy ({acc:.1f}%). System is borderline.**",
            "",
            f"{false_r} trades were rejected but would have been winners.",
            "",
            "**Recommended Action:** Review which rejection reasons have lowest accuracy "
            "(see table above). Consider relaxing those specific criteria.",
        ]
    else:
        # Find worst-performing reason
        broken = [
            r for r, s in reason_stats.items()
            if s.get("verdict") in ("BROKEN", "UNDERPERFORMING") and s.get("classified", 0) >= 5
        ]
        broken_str = ", ".join(broken) if broken else "unknown"
        lines += [
            f"❌ **Rejection accuracy is low ({acc:.1f}%).**",
            "",
            f"The system is rejecting too many winners. {false_r} false negatives.",
            "",
            f"Worst-performing rejection reasons: **{broken_str}**",
            "",
            "**Recommended Action:** Audit those rejection criteria immediately.",
            "Consider temporarily lowering the rejection threshold or removing "
            "the broken criteria until recalibrated.",
        ]

    lines += ["", "---", "", "*Shadow analysis only. No trades placed or modified.*"]
    return lines


# ── Main entry point ──────────────────────────────────────────────────────────

def generate_rejection_report(
    tracker:     RejectionTracker,
    output_path: str,
) -> str:
    """
    Build and write the REJECTION AUDIT REPORT markdown file.

    Args:
        tracker:     Populated RejectionTracker instance.
        output_path: Absolute path for the output .md file.

    Returns:
        The markdown string written to disk.
    """
    total      = tracker.count_total()
    classified = len(tracker.get_classified())
    overall    = tracker.overall_accuracy()
    by_reason  = tracker.accuracy_by_reason()
    by_tier    = tracker.accuracy_by_quality_tier()
    missed     = tracker.missed_winner_analysis()
    hyp_pnl    = tracker.hypothetical_total_pnl()

    sections = (
        _section_header(total, classified)
        + _section_overall(overall)
        + _section_by_reason(by_reason)
        + _section_by_quality_tier(by_tier)
        + _section_missed_winners(missed, hyp_pnl)
        + _section_conclusion(overall, by_reason, hyp_pnl)
    )

    report = "\n".join(sections)
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report)
    return report
