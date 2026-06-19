"""
analysis/learning_engine.py
================================
LEARNING_ENGINE_001 — Master orchestrator.

Loads all audit databases, mines patterns, detects edges,
generates governance recommendations, and writes a dated markdown report.

Usage
-----
    python analysis/learning_engine.py

    # Re-generate even if run already exists today
    python analysis/learning_engine.py --force

    # Custom DB and output dirs
    python analysis/learning_engine.py --db-dir data/ --out reports/learning/

CLI options
-----------
    --force               Overwrite today's report if it exists
    --db-dir PATH         Directory containing all audit .db files (default: data/)
    --out    PATH         Directory to write the markdown report (default: reports/learning/)
    --no-db               Skip storing recommendations in the tracker DB
    --summary             Print a brief summary to stdout instead of full report path

SAFETY GUARANTEE
----------------
This module NEVER modifies:
    decision_engine.py, risk_control.py, execution_engine.py, risk_guardian.py
    Any file listed as protected in copilot-instructions.md

All recommendations require human approval before implementation.
"""

from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from datetime import datetime, timezone
from typing import Dict, List, Optional

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from analysis.pattern_miner import (
    mine_quality_patterns,
    mine_news_patterns,
    mine_rejection_patterns,
    mine_options_patterns,
)
from analysis.edge_detector import (
    detect_rejection_edges,
    detect_quality_tier_edges,
    detect_news_signal_edges,
    summarise_edges,
)
from analysis.governance_recommender import (
    generate_recommendations,
    recommend_from_pattern,
    Recommendation,
)
from analysis.recommendation_tracker import get_recommendation_tracker


# ── Default paths ─────────────────────────────────────────────────────────────

DB_DIR   = os.path.join(ROOT, "data")
OUT_DIR  = os.path.join(ROOT, "reports", "learning")


# ── Database helpers ──────────────────────────────────────────────────────────

def _connect(db_path: str) -> Optional[sqlite3.Connection]:
    if not os.path.exists(db_path):
        return None
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def _rows(conn: sqlite3.Connection, sql: str, params: tuple = ()) -> List[dict]:
    if conn is None:
        return []
    return [dict(r) for r in conn.execute(sql, params).fetchall()]


# ── Load audit data ───────────────────────────────────────────────────────────

def _load_trade_quality(db_dir: str) -> dict:
    path = os.path.join(db_dir, "trade_quality.db")
    conn = _connect(path)
    if conn is None:
        return {"records": [], "tier_stats": {}}

    records  = _rows(conn, "SELECT * FROM trade_quality_log")
    tier_raw = _rows(conn,
        """SELECT quality_tier, COUNT(*) AS total,
                  SUM(CASE WHEN outcome='WIN' THEN 1 ELSE 0 END) AS wins
           FROM trade_quality_log WHERE outcome IN ('WIN','LOSS')
           GROUP BY quality_tier"""
    )
    tier_stats: Dict[str, dict] = {}
    for r in tier_raw:
        closed   = r["total"]
        wins     = r["wins"]
        tier_stats[r["quality_tier"]] = {
            "closed":   closed,
            "win_rate": round(wins / closed * 100, 1) if closed else 0.0,
        }
    conn.close()
    return {"records": records, "tier_stats": tier_stats}


def _load_rejection(db_dir: str) -> dict:
    path = os.path.join(db_dir, "rejection_audit.db")
    conn = _connect(path)
    if conn is None:
        return {"records": [], "by_reason": {}}

    records  = _rows(conn, "SELECT * FROM rejection_log")
    by_reason_raw = _rows(conn,
        """SELECT rejected_reason AS reason,
                  COUNT(*) AS total,
                  SUM(CASE WHEN rejection_outcome='CORRECT' THEN 1 ELSE 0 END) AS correct
           FROM rejection_log
           WHERE rejection_outcome IN ('CORRECT','FALSE_REJECTION')
           GROUP BY rejected_reason"""
    )
    by_reason: Dict[str, dict] = {}
    for r in by_reason_raw:
        total   = r["total"]
        correct = r["correct"]
        by_reason[r["reason"]] = {
            "classified":    total,
            "accuracy_pct":  round(correct / total * 100, 1) if total else 0.0,
        }
    conn.close()
    return {"records": records, "by_reason": by_reason}


def _load_news(db_dir: str) -> dict:
    path = os.path.join(db_dir, "news_audit.db")
    conn = _connect(path)
    if conn is None:
        return {"records": [], "by_type": {}}

    records  = _rows(conn, "SELECT * FROM news_impact_log")
    by_type_raw = _rows(conn,
        """SELECT news_type,
                  COUNT(*) AS total,
                  SUM(CASE WHEN outcome='WIN' THEN 1 ELSE 0 END) AS wins
           FROM news_impact_log WHERE outcome IN ('WIN','LOSS')
           GROUP BY news_type"""
    )
    by_type: Dict[str, dict] = {}
    for r in by_type_raw:
        total = r["total"]
        wins  = r["wins"]
        by_type[r["news_type"]] = {
            "closed":   total,
            "win_rate": round(wins / total * 100, 1) if total else 0.0,
        }
    conn.close()
    return {"records": records, "by_type": by_type}


def _load_options(db_dir: str) -> dict:
    path = os.path.join(db_dir, "options_audit.db")
    conn = _connect(path)
    if conn is None:
        return {"records": []}
    records = _rows(conn, "SELECT * FROM option_trade_audit")
    conn.close()
    return {"records": records}


def _load_sft(db_dir: str) -> dict:
    path = os.path.join(db_dir, "phase_d_sft.db")
    conn = _connect(path)
    if conn is None:
        return {"records": []}
    try:
        records = _rows(conn, "SELECT * FROM sft_log")
    except Exception:
        records = []
    conn.close()
    return {"records": records}


# ── Report generation ─────────────────────────────────────────────────────────

def _fmt_pct(v: float) -> str:
    return f"{v:.1f}%"


def _rec_table(recs: List[Recommendation]) -> str:
    if not recs:
        return "_None._\n"
    lines = [
        "| Rec ID | Type | Target | Accuracy | Confidence | Suggestion |",
        "|--------|------|--------|----------|------------|------------|",
    ]
    for r in recs:
        acc = f"{r.current_accuracy:.1f}%"
        lines.append(
            f"| {r.rec_id} | {r.rec_type} | `{r.target}` "
            f"| {acc} ({r.n_obs}n) | {r.confidence} "
            f"| {r.suggestion[:80]}... |"
            if len(r.suggestion) > 80
            else f"| {r.rec_id} | {r.rec_type} | `{r.target}` "
                 f"| {acc} ({r.n_obs}n) | {r.confidence} | {r.suggestion} |"
        )
    return "\n".join(lines) + "\n"


def _edge_table(edges) -> str:
    if not edges:
        return "_None detected._\n"
    lines = [
        "| Filter | Category | Accuracy | N | Edge Score | Strength | Action |",
        "|--------|----------|----------|---|------------|----------|--------|",
    ]
    for e in edges[:20]:  # cap at 20 rows
        lines.append(
            f"| `{e.name}` | {e.category} | {e.accuracy*100:.1f}% "
            f"| {e.n_obs} | {e.edge_score:+.2f} "
            f"| {e.strength} | {e.action} |"
        )
    return "\n".join(lines) + "\n"


def _pattern_section(title: str, patterns, baseline: float, rec_id_offset: int) -> tuple:
    """Returns (markdown_text, list_of_recs, next_rec_id_offset)."""
    lines   = [f"### {title}\n"]
    recs    : List[Recommendation] = []
    counter = rec_id_offset

    if not patterns:
        lines.append("_No patterns with sufficient observations._\n")
        return "\n".join(lines), recs, counter

    top_pos = patterns.positive(5)
    top_neg = patterns.negative(3)

    if top_pos:
        lines.append("**Top positive patterns:**\n")
        lines.append("| Pattern | WR% | N | Edge |")
        lines.append("|---------|-----|---|------|")
        for p in top_pos:
            lines.append(
                f"| {p.description} | {p.win_rate*100:.1f}% "
                f"| {p.n} | {p.strength:+.2f} |"
            )
            recs.append(recommend_from_pattern(
                p.description, p.win_rate, p.n, baseline,
                p.source, f"PAT-{counter:03d}",
            ))
            counter += 1
        lines.append("")

    if top_neg:
        lines.append("**Top negative patterns (avoid):**\n")
        lines.append("| Pattern | WR% | N | Edge |")
        lines.append("|---------|-----|---|------|")
        for p in top_neg:
            lines.append(
                f"| {p.description} | {p.win_rate*100:.1f}% "
                f"| {p.n} | {p.strength:+.2f} |"
            )
            recs.append(recommend_from_pattern(
                p.description, p.win_rate, p.n, baseline,
                p.source, f"PAT-{counter:03d}",
            ))
            counter += 1
        lines.append("")

    return "\n".join(lines), recs, counter


def generate_report(
    db_dir:    str = DB_DIR,
    out_dir:   str = OUT_DIR,
    store_recs: bool = True,
    run_id:    str = "",
) -> str:
    """
    Run the full learning engine cycle and write a markdown report.

    Returns the path to the written report.
    """
    now       = datetime.now(timezone.utc)
    date_str  = now.strftime("%Y%m%d")
    run_id    = run_id or f"{date_str}-{now.strftime('%H%M')}"
    os.makedirs(out_dir, exist_ok=True)
    out_path  = os.path.join(out_dir, f"LEARNING_REPORT_{date_str}.md")

    # ── 1. Load all audit data ────────────────────────────────────────────────
    tq   = _load_trade_quality(db_dir)
    rej  = _load_rejection(db_dir)
    news = _load_news(db_dir)
    opts = _load_options(db_dir)

    # ── 2. Mine patterns ──────────────────────────────────────────────────────
    qp    = mine_quality_patterns(tq["records"])
    np_   = mine_news_patterns(news["records"])
    rp    = mine_rejection_patterns(rej["records"])
    op    = mine_options_patterns(opts["records"])

    # ── 3. Detect edges ───────────────────────────────────────────────────────
    rej_edges  = detect_rejection_edges(rej["by_reason"])
    qual_edges = detect_quality_tier_edges(tq["tier_stats"])
    news_edges = detect_news_signal_edges(news["by_type"])
    all_edges  = rej_edges + qual_edges + news_edges
    summary    = summarise_edges(all_edges)

    # ── 4. Generate recommendations ───────────────────────────────────────────
    all_recs: List[Recommendation] = generate_recommendations(
        all_edges, rec_id_start=1
    )

    # ── 5. Pattern-based recs (appended after edge recs) ──────────────────────
    pat_recs   : List[Recommendation] = []
    pat_id_next = 1
    pat_sections: List[tuple] = []  # (title, patterns, baseline)

    _secs = [
        ("Quality Patterns",    qp,  0.50),
        ("News Patterns",       np_, 0.50),
        ("Rejection Patterns",  rp,  0.50),
        ("Options Patterns",    op,  0.50),
    ]
    for title, mined, base in _secs:
        _, p_recs, pat_id_next = _pattern_section(
            title, mined, base, pat_id_next
        )
        pat_recs.extend(p_recs)
        pat_sections.append((title, mined, base))

    # Combined prioritised list
    all_final_recs = all_recs + pat_recs

    # ── 6. Store in tracker ───────────────────────────────────────────────────
    tracker = get_recommendation_tracker(
        os.path.join(db_dir, "recommendations.db")
    )
    stored_count = tracker.store_batch(all_final_recs, run_id=run_id) if store_recs else 0
    existing_pending = tracker.count_by_status()

    # ── 7. Build markdown ─────────────────────────────────────────────────────
    md  = []
    md += [f"# LEARNING_ENGINE_001 — Learning Report", ""]
    md += [f"**Run ID:** `{run_id}`  "]
    md += [f"**Generated:** {now.strftime('%Y-%m-%d %H:%M UTC')}  "]
    md += [f"**Databases:** `{db_dir}/`  "]
    md += [f"**Recommendations stored:** {stored_count} new"]
    md += [""]
    md += ["> ⚠️ SAFETY NOTICE: All recommendations below require **human approval**",
           "> before implementation. This engine NEVER modifies live trading code.",
           ""]

    # ── Executive summary ──────────────────────────────────────────────────────
    md += ["---", "## Executive Summary", ""]
    md += ["| Metric | Value |"]
    md += ["|--------|-------|"]
    md += [f"| Total filters analysed | {summary['total']} |"]
    md += [f"| Positive edges (filter works) | {summary['positive']} |"]
    md += [f"| Negative edges (filter hurts) | {summary['negative']} |"]
    md += [f"| Neutral | {summary['neutral']} |"]
    md += [f"| Insufficient data | {summary['collecting']} |"]
    md += [f"| Strong positive signals | {summary['strong_positive']} |"]
    if summary.get("top_edge"):
        e = summary["top_edge"]
        md += [f"| Strongest signal | `{e.name}` ({e.accuracy*100:.1f}%, edge={e.edge_score:+.2f}) |"]
    if summary.get("worst_edge"):
        e = summary["worst_edge"]
        md += [f"| Weakest signal | `{e.name}` ({e.accuracy*100:.1f}%, edge={e.edge_score:+.2f}) |"]
    md += [f"| Pending recommendations (all time) | {existing_pending.get('PENDING', 0)} |"]
    md += [f"| Approved (awaiting implementation) | {existing_pending.get('APPROVED', 0)} |"]
    md += [f"| Implemented | {existing_pending.get('IMPLEMENTED', 0)} |"]
    md += [""]

    # ── Top recommendations ────────────────────────────────────────────────────
    md += ["---", "## Priority Recommendations", ""]
    md += ["These are sorted by priority (1=critical) then confidence."]
    md += ["> All require explicit human approval before any change is made.", ""]

    p1 = [r for r in all_final_recs if r.priority == 1]
    p2 = [r for r in all_final_recs if r.priority == 2]
    p3 = [r for r in all_final_recs if r.priority == 3]

    if p1:
        md += ["### P1 — Critical (Remove or Investigate)"]
        md += [_rec_table(p1)]
    if p2:
        md += ["### P2 — High (Weight Adjustments)"]
        md += [_rec_table(p2)]
    if p3:
        md += ["### P3 — Medium (Increase Weight)"]
        md += [_rec_table(p3)]

    # ── Edge strength ranking ──────────────────────────────────────────────────
    md += ["---", "## Filter Edge Strength Ranking", ""]
    md += ["All filters ranked by absolute edge score. Baseline = 50% (random)."]
    md += ["Edge score ≈ z-score direction. Positive = filter works. Negative = filter hurts.", ""]

    ranked = sorted(all_edges, key=lambda e: -abs(e.edge_score))
    md += [_edge_table(ranked)]

    # ── Pattern mining ────────────────────────────────────────────────────────
    md += ["---", "## Pattern Mining Results", ""]
    md += ["Multi-factor combinations with highest and lowest win rates.", ""]

    for title, mined, base in pat_sections:
        _, _, _ = (None, None, None)  # already processed above
        md += [f"### {title}", ""]
        if mined is None:
            md += ["_No data._", ""]
            continue
        top_pos = mined.positive(5) if mined else []
        top_neg = mined.negative(3) if mined else []
        if top_pos:
            md += ["**High-performing combinations:**", ""]
            md += ["| Pattern | WR% | N | Direction |"]
            md += ["|---------|-----|---|-----------|"]
            for p in top_pos:
                md += [f"| {p.description} | {p.win_rate*100:.1f}% | {p.n} | {p.direction} |"]
            md += [""]
        if top_neg:
            md += ["**Underperforming combinations (consider avoiding):**", ""]
            md += ["| Pattern | WR% | N | Direction |"]
            md += ["|---------|-----|---|-----------|"]
            for p in top_neg:
                md += [f"| {p.description} | {p.win_rate*100:.1f}% | {p.n} | {p.direction} |"]
            md += [""]
        if not top_pos and not top_neg:
            md += ["_Insufficient data for significant patterns._", ""]

    # ── Pending tracker status ────────────────────────────────────────────────
    md += ["---", "## Recommendation Tracker Status", ""]
    outcome = tracker.outcome_summary()
    pending_recs = tracker.get_pending()[:10]
    md += ["| Status | Count |"]
    md += ["|--------|-------|"]
    for status, cnt in existing_pending.items():
        md += [f"| {status} | {cnt} |"]
    md += [""]
    if outcome["with_outcome"] > 0:
        md += [
            f"**Implementation track record:** "
            f"{outcome['improved']}/{outcome['with_outcome']} improved "
            f"({outcome['accuracy']}% success rate)", ""
        ]
    if pending_recs:
        md += ["**Oldest pending recommendations:**", ""]
        md += ["| Rec ID | Target | Priority | Confidence | Generated |"]
        md += ["|--------|--------|----------|------------|-----------|"]
        for r in pending_recs:
            md += [
                f"| {r['rec_id']} | `{r['target']}` "
                f"| {r['priority']} | {r['confidence']} "
                f"| {r['generated_at'][:10]} |"
            ]
        md += [""]

    # ── Footer ────────────────────────────────────────────────────────────────
    md += ["---", ""]
    md += ["*Generated by LEARNING_ENGINE_001.*  "]
    md += ["*No live trading code was modified in the production of this report.*"]

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md))

    return out_path


# ── CLI ───────────────────────────────────────────────────────────────────────

def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="LEARNING_ENGINE_001 — generate learning report")
    p.add_argument("--db-dir",  default=DB_DIR,  help="Directory containing audit .db files")
    p.add_argument("--out",     default=OUT_DIR,  help="Output directory for the report")
    p.add_argument("--force",   action="store_true", help="Overwrite existing report for today")
    p.add_argument("--no-db",   action="store_true", help="Skip storing recommendations in tracker")
    p.add_argument("--summary", action="store_true", help="Print brief summary instead of report path")
    return p.parse_args()


def main() -> None:
    args    = _parse_args()
    db_dir  = os.path.abspath(args.db_dir)
    out_dir = os.path.abspath(args.out)

    date_str   = datetime.now().strftime("%Y%m%d")
    out_path_c = os.path.join(out_dir, f"LEARNING_REPORT_{date_str}.md")

    if not args.force and os.path.exists(out_path_c):
        print(f"Report already exists for today: {out_path_c}")
        print("Use --force to regenerate.")
        return

    report_path = generate_report(
        db_dir     = db_dir,
        out_dir    = out_dir,
        store_recs = not args.no_db,
    )

    if args.summary:
        tracker = get_recommendation_tracker(os.path.join(db_dir, "recommendations.db"))
        counts  = tracker.count_by_status()
        print(f"\nLEARNING_ENGINE_001 run complete.")
        print(f"  Report : {report_path}")
        print(f"  Pending: {counts.get('PENDING', 0)}")
        print(f"  Approved (not yet implemented): {counts.get('APPROVED', 0)}")
    else:
        print(f"Report written: {report_path}")


if __name__ == "__main__":
    main()
