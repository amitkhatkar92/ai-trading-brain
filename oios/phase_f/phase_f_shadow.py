"""
oios/phase_f/phase_f_shadow.py
Phase F Step F6.1 — Research Shadow Engine

Reads all Phase F research tables and produces structured output:
  - Suggested common factors in winners (hypothesis, not action)
  - Suggested hidden factors not captured in OIOS signals
  - Suggested failure factors in control stocks

OUTPUT CONSTRAINT
-----------------
This module NEVER writes to any database table.
It reads and returns Python dicts / strings.
It emits NO events, calls NO execution engine functions, and
does NOT touch any A–E table.

If you see a write call in this file: it is a bug.
"""

from __future__ import annotations

import logging
import sqlite3
from collections import Counter, defaultdict
from datetime import date, timedelta
from typing import Optional

log = logging.getLogger(__name__)

# How many days to look back for research aggregation
DEFAULT_LOOKBACK_DAYS = 30
TOP_N = 5


# ── Public API ────────────────────────────────────────────────────────────────

def run_shadow(
    as_of_date: str,
    conn: sqlite3.Connection,
    lookback_days: int = DEFAULT_LOOKBACK_DAYS,
) -> dict:
    """
    Aggregate Phase F research findings and return structured suggestions.

    Returns
    -------
    dict with keys:
        winner_common_factors   : list[dict]
        hidden_factors          : list[dict]
        failure_factors         : list[dict]
        persistence_summary     : dict
        as_of_date              : str
        lookback_days           : int
        WARNING                 : str  (isolation reminder)
    """
    start_date = (date.fromisoformat(as_of_date) - timedelta(days=lookback_days)).isoformat()

    winner_factors  = _winner_common_factors(start_date, as_of_date, conn)
    failure_factors = _failure_common_factors(start_date, as_of_date, conn)
    hidden_factors  = _hidden_factor_suggestions(start_date, as_of_date, conn)
    persistence     = _persistence_summary(start_date, as_of_date, conn)

    return {
        "as_of_date":            as_of_date,
        "lookback_days":         lookback_days,
        "start_date":            start_date,
        "winner_common_factors": winner_factors,
        "failure_factors":       failure_factors,
        "hidden_factors":        hidden_factors,
        "persistence_summary":   persistence,
        "WARNING": (
            "Phase F Shadow Engine — research output only. "
            "No OIOS tables were modified. No trades implied."
        ),
    }


def format_shadow_report(result: dict) -> str:
    """Convert run_shadow() output to human-readable Markdown."""
    lines = [
        "# Phase F Research Shadow Report",
        f"**As of:** {result['as_of_date']}  |  **Lookback:** {result['lookback_days']} days",
        "",
        "> ⚠️ " + result["WARNING"],
        "",
    ]

    # Winner factors
    lines.append("## Suggested Common Winner Factors")
    lines.append("")
    wf = result.get("winner_common_factors", [])
    if wf:
        lines.append("| Feature | Avg Value | Frequency | Hypothesis |")
        lines.append("|---|---|---|---|")
        for f in wf:
            lines.append(f"| {f['feature']} | {f['avg_value']:.2f} | {f['frequency']:.0%} | {f['hypothesis']} |")
    else:
        lines.append("*Not enough winner data yet.*")
    lines.append("")

    # Failure factors
    lines.append("## Suggested Failure Factors")
    lines.append("")
    ff = result.get("failure_factors", [])
    if ff:
        lines.append("| Reason | Count | Avg Confidence |")
        lines.append("|---|---|---|")
        for f in ff:
            lines.append(f"| {f['reason']} | {f['count']} | {f['avg_confidence']:.2f} |")
    else:
        lines.append("*No failure attributions in window.*")
    lines.append("")

    # Hidden factors
    lines.append("## Suggested Hidden Factors")
    lines.append("")
    hf = result.get("hidden_factors", [])
    if hf:
        for f in hf:
            lines.append(f"- **{f['factor']}**: {f['observation']}")
    else:
        lines.append("*Insufficient data for hidden factor detection.*")
    lines.append("")

    # Persistence
    lines.append("## Persistence Summary")
    lines.append("")
    ps = result.get("persistence_summary", {})
    if ps:
        lines.append("| Class | Count | 5D Win% | 20D Win% |")
        lines.append("|---|---|---|---|")
        for cls, data in ps.items():
            lines.append(
                f"| {cls} | {data['count']} | "
                f"{data.get('win_pct_5d', 0):.0%} | "
                f"{data.get('win_pct_20d', 0):.0%} |"
            )
    else:
        lines.append("*No outcome data yet.*")
    lines.append("")

    return "\n".join(lines)


# ── Internal aggregators ──────────────────────────────────────────────────────

def _winner_common_factors(
    start_date: str, end_date: str, conn: sqlite3.Connection
) -> list[dict]:
    """
    Find features that appear more frequently in WINNER rows than expected.
    Returns top-N features with hypothesis strings.
    """
    rows = conn.execute("""
        SELECT mlf.feature_name, mlf.feature_value
        FROM market_leader_features mlf
        JOIN market_leaders_daily mld ON mlf.leader_id = mld.leader_id
        WHERE mld.leader_type = 'WINNER'
          AND mld.trade_date BETWEEN ? AND ?
          AND mlf.feature_value IS NOT NULL
    """, (start_date, end_date)).fetchall()

    total_leaders = conn.execute("""
        SELECT COUNT(DISTINCT leader_id) FROM market_leaders_daily
        WHERE leader_type = 'WINNER' AND trade_date BETWEEN ? AND ?
    """, (start_date, end_date)).fetchone()[0]

    if not rows or not total_leaders:
        return []

    sums:   dict[str, float] = defaultdict(float)
    counts: dict[str, int]   = defaultdict(int)
    for fname, fval in rows:
        sums[fname]   += fval
        counts[fname] += 1

    _HYPOTHESES = {
        "above_20dma":      "Price above 20 DMA → trend aligned, not extended",
        "above_50dma":      "Above medium-term trend → institutional support",
        "volume_ratio":     "Elevated volume → institutional participation",
        "rs_score":         "Outperforming universe → relative momentum edge",
        "atr_expansion":    "ATR expanding → breakout energy present",
        "sector_conviction":"High sector conviction → theme is active",
        "theme_phase_score":"Early theme phase → runway remaining",
        "active_archetypes":"Multiple OIOS archetypes active → confluence",
        "cause_score":      "Identifiable catalyst present in knowledge graph",
        "sector_purity":    "High sector purity → clean sector exposure",
    }

    result = []
    for feat in sorted(sums, key=lambda f: counts[f], reverse=True)[:TOP_N]:
        result.append({
            "feature":   feat,
            "avg_value": round(sums[feat] / counts[feat], 3),
            "frequency": round(counts[feat] / total_leaders, 3),
            "hypothesis": _HYPOTHESES.get(feat, "No hypothesis defined"),
        })
    return result


def _failure_common_factors(
    start_date: str, end_date: str, conn: sqlite3.Connection
) -> list[dict]:
    rows = conn.execute("""
        SELECT candidate_reason, COUNT(*) as cnt, AVG(confidence) as avg_conf
        FROM failure_attribution
        WHERE trade_date BETWEEN ? AND ?
        GROUP BY candidate_reason
        ORDER BY cnt DESC, avg_conf DESC
        LIMIT ?
    """, (start_date, end_date, TOP_N)).fetchall()

    return [
        {"reason": r[0], "count": r[1], "avg_confidence": round(r[2], 3)}
        for r in rows
    ]


def _hidden_factor_suggestions(
    start_date: str, end_date: str, conn: sqlite3.Connection
) -> list[dict]:
    """
    Look for patterns that correlate with LONG_TREND_WINNER but are NOT
    currently in the standard feature set.  Currently implements 3 heuristics:
      1. Volume spike before the capture day (momentum buildup)
      2. Sector rank < 3 (top-conviction sector)
      3. Cause score present (catalyst detected in E1)
    """
    suggestions = []

    # Heuristic 1: volume_ratio > 2.0 correlates with longer trend?
    trend_with_high_vol = conn.execute("""
        SELECT COUNT(*) FROM market_leader_features mlf
        JOIN market_leaders_daily mld ON mlf.leader_id = mld.leader_id
        JOIN market_leader_outcomes mlo ON mld.leader_id = mlo.leader_id
        WHERE mlf.feature_name = 'volume_ratio'
          AND mlf.feature_value > 2.0
          AND mlo.outcome_class = 'LONG_TREND_WINNER'
          AND mld.trade_date BETWEEN ? AND ?
    """, (start_date, end_date)).fetchone()[0]

    total_trend = conn.execute("""
        SELECT COUNT(*) FROM market_leaders_daily mld
        JOIN market_leader_outcomes mlo ON mld.leader_id = mlo.leader_id
        WHERE mlo.outcome_class = 'LONG_TREND_WINNER'
          AND mld.trade_date BETWEEN ? AND ?
    """, (start_date, end_date)).fetchone()[0]

    if total_trend and trend_with_high_vol / max(1, total_trend) > 0.50:
        suggestions.append({
            "factor": "HIGH_VOLUME_BURST",
            "observation": (
                f"{trend_with_high_vol}/{total_trend} long-trend winners had volume_ratio > 2.0. "
                "Suggests volume burst day is a meaningful leading indicator for sustained moves."
            ),
        })

    # Heuristic 2: cause_score present
    cause_in_winners = conn.execute("""
        SELECT COUNT(*) FROM market_leader_features mlf
        JOIN market_leaders_daily mld ON mlf.leader_id = mld.leader_id
        WHERE mlf.feature_name = 'cause_score'
          AND mlf.feature_value IS NOT NULL
          AND mlf.feature_value > 0
          AND mld.leader_type = 'WINNER'
          AND mld.trade_date BETWEEN ? AND ?
    """, (start_date, end_date)).fetchone()[0]

    total_winners = conn.execute("""
        SELECT COUNT(*) FROM market_leaders_daily
        WHERE leader_type = 'WINNER' AND trade_date BETWEEN ? AND ?
    """, (start_date, end_date)).fetchone()[0]

    if total_winners and cause_in_winners / max(1, total_winners) > 0.40:
        suggestions.append({
            "factor": "CATALYST_PRESENT",
            "observation": (
                f"{cause_in_winners}/{total_winners} winners had a detected cause/catalyst. "
                "Strengthening E1 cause detection may improve winner prediction."
            ),
        })

    # Heuristic 3: sector_rank ≤ 3
    top_sector = conn.execute("""
        SELECT COUNT(*) FROM market_leader_features mlf
        JOIN market_leaders_daily mld ON mlf.leader_id = mld.leader_id
        JOIN market_leader_outcomes mlo ON mld.leader_id = mlo.leader_id
        WHERE mlf.feature_name = 'sector_rank'
          AND mlf.feature_value <= 3
          AND mlo.outcome_class IN ('MULTI_WEEK_WINNER', 'LONG_TREND_WINNER')
          AND mld.trade_date BETWEEN ? AND ?
    """, (start_date, end_date)).fetchone()[0]

    if top_sector > 2:
        suggestions.append({
            "factor": "TOP_SECTOR_RANK",
            "observation": (
                f"{top_sector} multi-week+ winners came from a top-3 sector by conviction. "
                "Sector rank ≤ 3 appears to be a persistent edge filter."
            ),
        })

    return suggestions


def _persistence_summary(
    start_date: str, end_date: str, conn: sqlite3.Connection
) -> dict:
    """Return {outcome_class: {count, win_pct_5d, win_pct_20d}} for WINNER rows."""
    rows = conn.execute("""
        SELECT mlo.outcome_class,
               COUNT(*) as cnt,
               SUM(CASE WHEN mlo.return_5d > 0 THEN 1 ELSE 0 END) * 1.0 / COUNT(*),
               SUM(CASE WHEN mlo.return_20d > 0 THEN 1 ELSE 0 END) * 1.0 / COUNT(*)
        FROM market_leaders_daily mld
        JOIN market_leader_outcomes mlo ON mld.leader_id = mlo.leader_id
        WHERE mld.leader_type = 'WINNER'
          AND mld.trade_date BETWEEN ? AND ?
          AND mlo.outcome_class != 'UNKNOWN'
        GROUP BY mlo.outcome_class
    """, (start_date, end_date)).fetchall()

    return {
        r[0]: {
            "count":       r[1],
            "win_pct_5d":  round(r[2], 3) if r[2] is not None else 0.0,
            "win_pct_20d": round(r[3], 3) if r[3] is not None else 0.0,
        }
        for r in rows
    }
