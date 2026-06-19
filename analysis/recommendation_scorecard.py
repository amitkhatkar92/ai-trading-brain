"""
analysis/recommendation_scorecard.py
=============================================
RECOMMENDATION_VALIDATION_001 — Evidence accumulation scorecard.

Reads from:
    data/recommendations.db   — 62 pending recommendations
    data/live_observations.db — live trade evidence accumulating over time

For each recommendation, answers:
    "How much live evidence do we have for or against this recommendation?"
    "Is there enough data to validate it yet?"
    "What does the current live data suggest?"

This is the system that will tell you WHEN a recommendation is ready
to be moved from PENDING → APPROVED or PENDING → REJECTED.

Validation readiness thresholds
--------------------------------
INSUFFICIENT    : < 10 live observations matching the recommendation's target
EMERGING        : 10–29 observations — early signal, direction may not be stable
READY           : ≥ 30 observations — statistical minimum for a decision
CONCLUSIVE      : ≥ 50 observations with effect size ≥ 0.10 — promote or reject

Effect size = |observed_win_rate − baseline|  (same as edge_detector logic)
"""

from __future__ import annotations

import os
import sqlite3
import sys
from datetime import datetime, timezone
from typing import Dict, List, Optional

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)

REC_DB  = os.path.join(_ROOT, "data", "recommendations.db")
LIVE_DB = os.path.join(_ROOT, "data", "live_observations.db")
OUT_DIR = os.path.join(_ROOT, "reports", "validation")

BASELINE           = 0.50
READY_THRESHOLD    = 30
CONCLUSIVE_THRESHOLD = 50
MIN_EFFECT_SIZE    = 0.10


# ── Data loading helpers ──────────────────────────────────────────────────────

def _load_recs(db_path: str) -> List[dict]:
    if not os.path.exists(db_path):
        return []
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM recommendations ORDER BY priority, confidence"
        ).fetchall()
    return [dict(r) for r in rows]


def _load_live(db_path: str) -> List[dict]:
    if not os.path.exists(db_path):
        return []
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM live_observations WHERE outcome IN ('WIN','LOSS')"
        ).fetchall()
    return [dict(r) for r in rows]


# ── Evidence matching ─────────────────────────────────────────────────────────

def _matches(rec: dict, trade: dict) -> bool:
    """
    Does this live trade provide evidence for/against this recommendation?

    Matching rules (broad — a trade can match multiple recs):
    - REJECTION_FILTER rec   → match if strategy or quality_tier contains the filter name
    - QUALITY_TIER rec       → match if quality_tier contains the tier
    - NEWS_SIGNAL rec        → match if news_type contains the news type
    - PATTERN rec            → match if relevant fields are present
    - OPTIONS rec            → match if strategy is an options strategy
    """
    target   = rec.get("target", "").upper()
    category = rec.get("category", "").upper()

    if "TIER_" in target:
        tier = target.replace("TIER_", "")
        return trade.get("quality_tier", "").upper() == tier

    if "NEWS_" in target:
        news_type = target.replace("NEWS_", "")
        return trade.get("news_type", "").upper() == news_type

    if category == "REJECTION_FILTER":
        # Match trades that would have been rejected for this reason
        return trade.get("strategy", "").upper() in target or target in trade.get("strategy", "").upper()

    if "PATTERN_" in category:
        # Patterns: broad match — if the trade has the same regime or strategy
        if "RANGING" in target and trade.get("market_regime") == "RANGING":
            return True
        if "TRENDING" in target and trade.get("market_regime") == "TRENDING":
            return True
        if "HIGH_VOL" in target and trade.get("market_regime") == "HIGH_VOL":
            return True

    # Default: any trade is mild evidence for aggregate recs
    return False


def _evidence_for_rec(rec: dict, live_trades: List[dict]) -> dict:
    """Compute evidence metrics for one recommendation."""
    matching = [t for t in live_trades if _matches(rec, t)]
    n        = len(matching)
    wins     = sum(1 for t in matching if t["outcome"] == "WIN")
    wr       = wins / n if n else 0.0
    effect   = abs(wr - BASELINE)

    if n >= CONCLUSIVE_THRESHOLD and effect >= MIN_EFFECT_SIZE:
        readiness = "CONCLUSIVE"
    elif n >= READY_THRESHOLD:
        readiness = "READY"
    elif n >= 10:
        readiness = "EMERGING"
    else:
        readiness = "INSUFFICIENT"

    # Direction: does the live data support or contradict the recommendation?
    rec_type = rec.get("rec_type", "")
    if n < 10:
        direction = "UNKNOWN"
    elif rec_type in ("REMOVE_FILTER", "DECREASE_WEIGHT") and wr < BASELINE:
        direction = "SUPPORTS_REC"     # live data confirms filter is hurting
    elif rec_type == "INCREASE_WEIGHT" and wr > BASELINE + 0.05:
        direction = "SUPPORTS_REC"
    elif rec_type == "KEEP_FILTER" and wr >= BASELINE + 0.10:
        direction = "SUPPORTS_REC"
    elif effect < 0.05:
        direction = "NEUTRAL"
    else:
        direction = "CONTRADICTS_REC"

    return {
        "rec_id":    rec["rec_id"],
        "target":    rec["target"],
        "rec_type":  rec_type,
        "priority":  rec["priority"],
        "confidence": rec["confidence"],
        "n_matched": n,
        "win_rate":  round(wr * 100, 1),
        "effect_size": round(effect, 3),
        "readiness": readiness,
        "direction": direction,
        "status":    rec["status"],
    }


# ── Report generator ──────────────────────────────────────────────────────────

def _readiness_icon(r: str) -> str:
    return {"CONCLUSIVE": "✅", "READY": "🟡", "EMERGING": "🔵", "INSUFFICIENT": "⚪"}[r]


def auto_advance_evidence_stages(
    rec_db:  str = REC_DB,
    live_db: str = LIVE_DB,
) -> dict:
    """
    Write current evidence stage into reviewer_notes for every PENDING rec.

    Does NOT change status to APPROVED/REJECTED — human-only gate.
    Allows reviewers to sort by stage: INSUFFICIENT < EMERGING < READY < CONCLUSIVE.

    Returns {stage: count_updated}.
    """
    recs        = _load_recs(rec_db)
    live_trades = _load_live(live_db)
    evidence    = [_evidence_for_rec(r, live_trades) for r in recs]
    updates: dict = {}

    if not os.path.exists(rec_db):
        return updates

    with sqlite3.connect(rec_db) as conn:
        for e in evidence:
            stage = e["readiness"]
            note  = (
                f"[EVIDENCE {datetime.now(timezone.utc).strftime('%Y-%m-%d')}] "
                f"Stage={stage} n={e['n_matched']} WR={e['win_rate']:.1f}% "
                f"Effect={e['effect_size']:.3f} Direction={e['direction']}"
            )
            conn.execute(
                "UPDATE recommendations SET reviewer_notes=? "
                "WHERE rec_id=? AND status='PENDING'",
                (note, e["rec_id"]),
            )
            updates[stage] = updates.get(stage, 0) + 1
        conn.commit()
    return updates


def generate_scorecard(
    rec_db:   str = REC_DB,
    live_db:  str = LIVE_DB,
    out_dir:  str = OUT_DIR,
) -> str:
    os.makedirs(out_dir, exist_ok=True)
    date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    out_path = os.path.join(out_dir, f"RECOMMENDATION_SCORECARD_{date_str}.md")
    now_str  = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    recs        = _load_recs(rec_db)
    live_trades = _load_live(live_db)
    evidence    = [_evidence_for_rec(r, live_trades) for r in recs]

    # Auto-update evidence stages in DB (non-destructive — notes only)
    auto_advance_evidence_stages(rec_db, live_db)

    total_live  = len(live_trades)
    conclusive  = [e for e in evidence if e["readiness"] == "CONCLUSIVE"]
    ready       = [e for e in evidence if e["readiness"] == "READY"]
    emerging    = [e for e in evidence if e["readiness"] == "EMERGING"]
    insufficient= [e for e in evidence if e["readiness"] == "INSUFFICIENT"]

    by_status = {}
    for r in recs:
        s = r.get("status", "PENDING")
        by_status[s] = by_status.get(s, 0) + 1

    md = []
    md += ["# RECOMMENDATION_VALIDATION_001 — Evidence Scorecard", ""]
    md += [f"**Generated:** {now_str}  "]
    md += [f"**Total recommendations:** {len(recs)}  "]
    md += [f"**Live closed trades:** {total_live}  "]
    md += [""]

    # Progress to decision
    needs = max(0, READY_THRESHOLD - total_live)
    if total_live < READY_THRESHOLD:
        pct = int(total_live / READY_THRESHOLD * 100)
        bar = "█" * (pct // 5) + "░" * (20 - pct // 5)
        md += [f"> **Progress to first validation decision:** [{bar}] {pct}%  "]
        md += [f"> Need {needs} more closed trades (target: {READY_THRESHOLD})."]
    else:
        md += [f"> ✅ **Sufficient live data for initial validation decisions.**"]
    md += [""]

    # Status table
    md += ["---", "## Recommendation Status Summary", ""]
    md += ["| Status | Count |"]
    md += ["|--------|-------|"]
    for status, n in sorted(by_status.items()):
        md += [f"| {status} | {n} |"]
    md += [""]

    # Evidence accumulation
    md += ["---", "## Evidence Readiness", ""]
    md += ["| Readiness | Count | Meaning |"]
    md += ["|-----------|-------|---------|"]
    md += [f"| ✅ CONCLUSIVE | {len(conclusive)} | ≥50 obs, effect ≥10pp — ready to decide |"]
    md += [f"| 🟡 READY | {len(ready)} | ≥30 obs — statistical minimum reached |"]
    md += [f"| 🔵 EMERGING | {len(emerging)} | 10–29 obs — signal forming |"]
    md += [f"| ⚪ INSUFFICIENT | {len(insufficient)} | <10 matching obs — too early |"]
    md += [""]

    # Priority P1 recs with most evidence
    md += ["---", "## P1 Recommendations — Critical (Remove/Decrease)", ""]
    p1 = sorted([e for e in evidence if e["priority"] == 1],
                key=lambda x: -x["n_matched"])
    if p1:
        md += [
            "| Rec ID | Target | Live n | WR% | Effect | Readiness | Direction |",
            "|--------|--------|--------|-----|--------|-----------|-----------|",
        ]
        for e in p1[:15]:
            icon = _readiness_icon(e["readiness"])
            md += [
                f"| {e['rec_id']} | `{e['target']}` "
                f"| {e['n_matched']} "
                f"| {e['win_rate']:.1f}% "
                f"| {e['effect_size']:.3f} "
                f"| {icon} {e['readiness']} "
                f"| {e['direction']} |"
            ]
        md += [""]
    else:
        md += ["_No P1 recommendations found._", ""]

    # Approval candidates (CONCLUSIVE + SUPPORTS_REC)
    candidates = [e for e in evidence if e["readiness"] in ("CONCLUSIVE", "READY")
                  and e["direction"] == "SUPPORTS_REC"]
    md += ["---", "## Approval Candidates", ""]
    if candidates:
        md += ["> These recommendations have enough live evidence pointing in the right direction.", ""]
        md += [
            "| Rec ID | Target | Type | Live n | WR% | Readiness | Action |",
            "|--------|--------|------|--------|-----|-----------|--------|",
        ]
        for e in candidates:
            action = ("Consider APPROVING" if e["readiness"] == "CONCLUSIVE"
                      else "Watch closely")
            md += [
                f"| {e['rec_id']} | `{e['target']}` "
                f"| {e['rec_type']} "
                f"| {e['n_matched']} "
                f"| {e['win_rate']:.1f}% "
                f"| {_readiness_icon(e['readiness'])} {e['readiness']} "
                f"| {action} |"
            ]
        md += [""]
    else:
        md += [f"_None yet — collecting evidence. {total_live} closed trades so far._", ""]

    # Contradictions
    contradictions = [e for e in evidence if e["direction"] == "CONTRADICTS_REC"
                      and e["n_matched"] >= 10]
    if contradictions:
        md += ["---", "## ⚠️ Contradictions — Live Data Opposes Recommendation", ""]
        md += ["> These recommendations may need reconsideration.", ""]
        md += ["| Rec ID | Target | Type | Live WR% | Expected Direction |"]
        md += ["|--------|--------|------|----------|--------------------|"]
        for e in contradictions:
            md += [
                f"| {e['rec_id']} | `{e['target']}` "
                f"| {e['rec_type']} "
                f"| {e['win_rate']:.1f}% "
                f"| Contradicts rec (n={e['n_matched']}) |"
            ]
        md += [""]

    # Collection progress per priority
    md += ["---", "## Collection Progress by Priority", ""]
    md += [f"_Target: {READY_THRESHOLD} closed trades per recommendation group_", ""]
    md += [f"**Current live closed trades: {total_live}**", ""]
    md += [f"Needed for READY: {max(0, READY_THRESHOLD - total_live)} more  "]
    md += [f"Needed for CONCLUSIVE: {max(0, CONCLUSIVE_THRESHOLD - total_live)} more  "]
    md += [""]

    md += ["---"]
    md += ["*Generated by RECOMMENDATION_VALIDATION_001.*  "]
    md += ["*All recommendations remain PENDING until explicitly approved by a human.*"]

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md))
    return out_path


def main() -> None:
    import argparse
    p = argparse.ArgumentParser(description="RECOMMENDATION_VALIDATION_001 scorecard")
    p.add_argument("--rec-db",  default=REC_DB,  help="recommendations.db path")
    p.add_argument("--live-db", default=LIVE_DB, help="live_observations.db path")
    p.add_argument("--out",     default=OUT_DIR, help="Output directory")
    args = p.parse_args()

    path = generate_scorecard(args.rec_db, args.live_db, args.out)
    print(f"Scorecard written: {path}")


if __name__ == "__main__":
    main()
