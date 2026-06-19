"""
analysis/filter_scorecard.py
================================
FILTER SCORECARD — Governance dashboard for all AI filters.

Aggregates accuracy data from all three audit modules:
    - REJECTION_AUDIT_001  (filter effectiveness)
    - TRADE_QUALITY_AUDIT_001 (quality tier win rates)
    - NEWS_AUDIT_001 (news signal strength)

Governance rules applied automatically:
    accuracy >= 70%  → KEEP    (filter is earning its place)
    accuracy >= 55%  → WATCH   (monitor, no change yet)
    accuracy >= 45%  → REVIEW  (evidence of underperformance)
    accuracy  < 45%  → REMOVE  (candidate for removal)

Usage:
    python analysis/filter_scorecard.py
    python analysis/filter_scorecard.py --out reports/filter_scorecard/
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from typing import Dict, List, Optional

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


# ── Governance thresholds ─────────────────────────────────────────────────────

KEEP_THRESHOLD   = 70.0
WATCH_THRESHOLD  = 55.0
REVIEW_THRESHOLD = 45.0

# Minimum observations before a governance decision is made
MIN_OBS_FOR_DECISION = 10


def governance_status(accuracy_pct: float, n_obs: int) -> tuple[str, str]:
    """
    Returns (status, action) for a filter based on accuracy and observation count.
    """
    if n_obs < MIN_OBS_FOR_DECISION:
        return "COLLECTING", "Wait for more data"
    if accuracy_pct >= KEEP_THRESHOLD:
        return "KEEP", "Filter is working — no change needed"
    elif accuracy_pct >= WATCH_THRESHOLD:
        return "WATCH", "Monitor for 4 more weeks before deciding"
    elif accuracy_pct >= REVIEW_THRESHOLD:
        return "REVIEW", "Schedule parameter review this week"
    return "REMOVE", "Candidate for removal — blocking more winners than losers"


def _status_icon(status: str) -> str:
    return {
        "KEEP":      "✅",
        "WATCH":     "🟢",
        "REVIEW":    "⚠️",
        "REMOVE":    "❌",
        "COLLECTING": "—",
    }.get(status, "—")


# ── Data collectors ───────────────────────────────────────────────────────────

def _collect_rejection_filters(db_path: str) -> List[dict]:
    """Read rejection accuracy per reason from rejection_audit.db."""
    if not os.path.exists(db_path):
        return []
    try:
        from analysis.rejection_tracker import RejectionTracker
        tracker   = RejectionTracker(db_path)
        by_reason = tracker.accuracy_by_reason()
        rows = []
        for reason, stats in by_reason.items():
            n   = stats.get("classified", 0)
            acc = stats.get("accuracy_pct", 0.0)
            status, action = governance_status(acc, n)
            rows.append({
                "category":    "REJECTION_FILTER",
                "filter_name": reason,
                "accuracy_pct": acc,
                "n_obs":        n,
                "status":       status,
                "action":       action,
                "source":       "rejection_audit.db",
            })
        return rows
    except Exception:
        return []


def _collect_quality_tier_filters(db_path: str) -> List[dict]:
    """Read tier win rates from trade_quality.db."""
    if not os.path.exists(db_path):
        return []
    try:
        from analysis.trade_quality_tracker import TradeQualityTracker
        tracker    = TradeQualityTracker(db_path)
        tier_stats = tracker.get_tier_statistics()
        rows = []
        for tier, stats in tier_stats.items():
            n   = stats.get("closed", 0)
            wr  = stats.get("win_rate", 0.0)
            status, action = governance_status(wr, n)
            rows.append({
                "category":    "QUALITY_TIER",
                "filter_name": f"TIER_{tier}",
                "accuracy_pct": wr,
                "n_obs":        n,
                "status":       status,
                "action":       action,
                "source":       "trade_quality.db",
            })
        return rows
    except Exception:
        return []


def _collect_news_signal_filters(db_path: str) -> List[dict]:
    """Read news type win rates from news_audit.db."""
    if not os.path.exists(db_path):
        return []
    try:
        from analysis.news_impact_tracker import NewsImpactTracker
        tracker = NewsImpactTracker(db_path)
        by_type = tracker.impact_by_type()
        rows = []
        for ntype, data in by_type.items():
            n   = data.get("closed", 0)
            wr  = data.get("win_rate", 0.0)
            # For news: a signal is "working" if win rate >= 60%
            # Repurpose accuracy_pct field for win rate here
            status, action = governance_status(wr, n)
            rows.append({
                "category":    "NEWS_SIGNAL",
                "filter_name": f"NEWS_{ntype}",
                "accuracy_pct": wr,
                "n_obs":        n,
                "status":       status,
                "action":       action,
                "source":       "news_audit.db",
            })
        return rows
    except Exception:
        return []


# ── Report generator ──────────────────────────────────────────────────────────

def generate_scorecard_report(
    all_filters: List[dict],
    output_path: str,
) -> str:
    """Build and write the FILTER SCORECARD markdown report."""

    removes = [f for f in all_filters if f["status"] == "REMOVE"]
    reviews = [f for f in all_filters if f["status"] == "REVIEW"]
    watches = [f for f in all_filters if f["status"] == "WATCH"]
    keeps   = [f for f in all_filters if f["status"] == "KEEP"]
    coll    = [f for f in all_filters if f["status"] == "COLLECTING"]

    lines = [
        "# FILTER SCORECARD",
        "",
        f"**Generated:** {datetime.now(timezone.utc).isoformat()}",
        "**Governance Dashboard — Evidence-Driven Filter Management**",
        "",
        f"| Status | Count |",
        f"|---|---|",
        f"| ✅ KEEP   (≥ 70%) | {len(keeps)} |",
        f"| 🟢 WATCH  (55–70%) | {len(watches)} |",
        f"| ⚠️ REVIEW (45–55%) | {len(reviews)} |",
        f"| ❌ REMOVE (< 45%) | {len(removes)} |",
        f"| — COLLECTING (< {MIN_OBS_FOR_DECISION} obs) | {len(coll)} |",
        "",
        "---",
        "",
    ]

    # ── Full scorecard table ──────────────────────────────────────────────────
    lines += [
        "## Full Filter Scorecard",
        "",
        "```",
        f"{'Filter':<32s}  {'Accuracy':>8s}  {'N':>5s}  {'Status':>12s}  Action",
        "─" * 80,
    ]

    categories = ["REJECTION_FILTER", "QUALITY_TIER", "NEWS_SIGNAL"]
    cat_labels  = {
        "REJECTION_FILTER": "Rejection Filters",
        "QUALITY_TIER":     "Quality Tier Gates",
        "NEWS_SIGNAL":      "News Signal Filters",
    }

    for cat in categories:
        cat_filters = sorted(
            [f for f in all_filters if f["category"] == cat],
            key=lambda x: -x["accuracy_pct"],
        )
        if not cat_filters:
            continue
        lines.append(f"\n{cat_labels[cat]}:")
        for f in cat_filters:
            icon = _status_icon(f["status"])
            lines.append(
                f"  {f['filter_name']:<30s}  {f['accuracy_pct']:>7.1f}%  "
                f"{f['n_obs']:>5d}  {icon} {f['status']:>10s}  {f['action']}"
            )

    lines += ["```", ""]

    # ── Action items ──────────────────────────────────────────────────────────
    if removes:
        lines += [
            "---",
            "",
            "## ❌ Immediate Action — REMOVE Candidates",
            "",
            "These filters are blocking more winners than losers.",
            "Consider removing or relaxing until recalibrated.",
            "",
        ]
        for f in removes:
            lines.append(
                f"- **{f['filter_name']}**  "
                f"(accuracy={f['accuracy_pct']:.1f}%, n={f['n_obs']})  "
                f"— {f['action']}"
            )
        lines.append("")

    if reviews:
        lines += [
            "---",
            "",
            "## ⚠️ Schedule Review This Week",
            "",
        ]
        for f in reviews:
            lines.append(
                f"- **{f['filter_name']}**  "
                f"(accuracy={f['accuracy_pct']:.1f}%, n={f['n_obs']})"
            )
        lines.append("")

    # ── Governance rules (printed once for reference) ─────────────────────────
    lines += [
        "---",
        "",
        "## Governance Rules",
        "",
        "| Accuracy | Status | Rule |",
        "|---|---|---|",
        "| ≥ 70% | ✅ KEEP | Filter is working — no change |",
        "| 55–70% | 🟢 WATCH | Monitor for 4 more weeks |",
        "| 45–55% | ⚠️ REVIEW | Schedule parameter review |",
        f"| < 45% | ❌ REMOVE | Candidate for removal |",
        f"| < {MIN_OBS_FOR_DECISION} obs | — COLLECTING | Wait for more data |",
        "",
        "> A filter's accuracy score is computed from:",
        "> - **Rejection filters:** % of rejected trades that would have lost (correct rejections)",
        "> - **Quality tier gates:** % of trades in that tier that resulted in a WIN",
        "> - **News signal filters:** % of news-tagged trades that resulted in a WIN",
        "",
        "---",
        "",
        "*Filter Scorecard generated from live audit databases. "
        "Accuracy figures update every time the audit modules are re-run.*",
    ]

    report = "\n".join(lines)
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report)
    return report


# ── Orchestrator ──────────────────────────────────────────────────────────────

def run_filter_scorecard(
    reports_dir:  str = os.path.join(ROOT, "reports", "filter_scorecard"),
    rejection_db: str = os.path.join(ROOT, "data", "rejection_audit.db"),
    quality_db:   str = os.path.join(ROOT, "data", "trade_quality.db"),
    news_db:      str = os.path.join(ROOT, "data", "news_audit.db"),
) -> None:
    print("=" * 70)
    print("FILTER SCORECARD — Governance Dashboard")
    print("=" * 70)

    all_filters: List[dict] = []

    print("\n[1/4] Reading rejection filter accuracy...")
    rej_rows = _collect_rejection_filters(rejection_db)
    print(f"      {len(rej_rows)} rejection filters loaded")
    all_filters.extend(rej_rows)

    print("[2/4] Reading quality tier win rates...")
    qual_rows = _collect_quality_tier_filters(quality_db)
    print(f"      {len(qual_rows)} quality tiers loaded")
    all_filters.extend(qual_rows)

    print("[3/4] Reading news signal accuracy...")
    news_rows = _collect_news_signal_filters(news_db)
    print(f"      {len(news_rows)} news filters loaded")
    all_filters.extend(news_rows)

    print("\n[4/4] Building scorecard...")

    # Console output
    print("\n" + "─" * 70)
    print(f"  {'Filter':<32s}  {'Acc%':>6s}  {'N':>5s}  {'Status':<14s}")
    print("  " + "─" * 64)

    categories = [
        ("REJECTION_FILTER", "Rejection Filters"),
        ("QUALITY_TIER",     "Quality Tier Gates"),
        ("NEWS_SIGNAL",      "News Signals"),
    ]
    removes = []
    reviews = []
    for cat, label in categories:
        print(f"\n  {label}:")
        cat_f = sorted(
            [f for f in all_filters if f["category"] == cat],
            key=lambda x: -x["accuracy_pct"],
        )
        for f in cat_f:
            icon = _status_icon(f["status"])
            print(
                f"    {f['filter_name']:<30s}  "
                f"{f['accuracy_pct']:>5.1f}%  {f['n_obs']:>5d}  "
                f"{icon} {f['status']}"
            )
            if f["status"] == "REMOVE":
                removes.append(f["filter_name"])
            elif f["status"] == "REVIEW":
                reviews.append(f["filter_name"])

    date_str    = datetime.now().strftime("%Y%m%d")
    report_path = os.path.join(reports_dir, f"FILTER_SCORECARD_{date_str}.md")
    generate_scorecard_report(all_filters, report_path)

    print(f"\n  Report: {report_path}")
    print("\n" + "=" * 70)
    if removes:
        print(f"❌ REMOVE candidates:  {', '.join(removes)}")
    if reviews:
        print(f"⚠️  REVIEW this week:   {', '.join(reviews)}")
    if not removes and not reviews:
        print("✅ All filters within acceptable range.")
    print("=" * 70)


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="FILTER SCORECARD — Governance Dashboard")
    parser.add_argument("--out",          default=os.path.join(ROOT, "reports", "filter_scorecard"),
                        help="Reports output directory")
    parser.add_argument("--rejection-db", default=os.path.join(ROOT, "data", "rejection_audit.db"))
    parser.add_argument("--quality-db",   default=os.path.join(ROOT, "data", "trade_quality.db"))
    parser.add_argument("--news-db",      default=os.path.join(ROOT, "data", "news_audit.db"))
    args = parser.parse_args()

    run_filter_scorecard(
        reports_dir  = args.out,
        rejection_db = args.rejection_db,
        quality_db   = args.quality_db,
        news_db      = args.news_db,
    )
