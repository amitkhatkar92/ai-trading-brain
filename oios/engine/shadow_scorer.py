"""
oios/engine/shadow_scorer.py

Phase E1 (Shadow Mode) — Shadow OS Computation and Outcome Tracking.

Computes OS_shadow = Phase C live OS + cause contribution + propagation contribution.
Records the shadow score alongside the live score for every active opportunity.
Records final outcomes (actual return, days_to_peak, final_state) when
opportunities close — this becomes E-readiness training material.

Shadow mode contract (absolute, non-negotiable):
  - OS_shadow is NEVER written to opportunities.conviction_score
  - OS_shadow is NEVER written to opportunities.re_score
  - OS_shadow is NEVER passed to the state machine
  - OS_shadow is NEVER visible to the execution engine
  - All output goes to shadow_cause_outcomes ONLY
"""

from __future__ import annotations

import logging
import sqlite3
import uuid
from datetime import date

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# How much a cause_score contributes to shadow OS
# Formula: shadow_os = live_os + CAUSE_WEIGHT × normalized_cause_score
#          + PROP_WEIGHT × normalized_prop_score
# Both cause_score and prop_score are on [0, 10]; live_os is also [0, 10].
_CAUSE_WEIGHT: float = 0.20   # 20% additive contribution max
_PROP_WEIGHT:  float = 0.10   # 10% additive contribution max
_MAX_OS:       float = 10.0


def _compute_shadow_os(
    live_os: float,
    cause_score: float | None,
    propagation_score: float | None,
) -> float:
    """
    Compute OS_shadow from live OS + cause/propagation deltas.
    Both scores are already on [0, 10].
    shadow_os is capped at _MAX_OS.
    """
    c = (cause_score or 0.0) / 10.0       # normalize to [0, 1]
    p = (propagation_score or 0.0) / 10.0 # normalize to [0, 1]
    shadow = live_os + _CAUSE_WEIGHT * c * live_os + _PROP_WEIGHT * p * live_os
    return round(min(_MAX_OS, shadow), 4)


# ---------------------------------------------------------------------------
# Daily shadow score recording
# ---------------------------------------------------------------------------

def record_shadow_score(
    conn: sqlite3.Connection,
    opportunity_id: str,
    today: str,
    live_os: float,
) -> dict:
    """
    Pull today's cause_score and propagation_score, compute shadow_os,
    and upsert into shadow_cause_outcomes.

    Returns the shadow outcome dict written.
    Shadow mode: NEVER writes to opportunities table.
    """
    # Read cause score
    cs_row = conn.execute("""
        SELECT cause_score FROM cause_scores
        WHERE opportunity_id = ? AND score_date = ?
        ORDER BY computed_at DESC LIMIT 1
    """, (opportunity_id, today)).fetchone()
    cause_score = cs_row["cause_score"] if cs_row else None

    # Read best propagation score
    ps_row = conn.execute("""
        SELECT MAX(propagation_score) AS best_prop
        FROM propagation_scores
        WHERE opportunity_id = ? AND score_date = ?
    """, (opportunity_id, today)).fetchone()
    prop_score = ps_row["best_prop"] if ps_row and ps_row["best_prop"] is not None else None

    shadow_os = _compute_shadow_os(live_os, cause_score, prop_score)

    conn.execute("""
        INSERT INTO shadow_cause_outcomes
            (outcome_id, opportunity_id, outcome_date,
             cause_score, propagation_score,
             shadow_os, live_os,
             recorded_at)
        VALUES (?,?,?,?,?,?,?,datetime('now'))
        ON CONFLICT(opportunity_id, outcome_date) DO UPDATE SET
            cause_score         = excluded.cause_score,
            propagation_score   = excluded.propagation_score,
            shadow_os           = excluded.shadow_os,
            live_os             = excluded.live_os,
            recorded_at         = excluded.recorded_at
    """, (
        str(uuid.uuid4()), opportunity_id, today,
        cause_score, prop_score,
        shadow_os, live_os,
    ))

    return {
        "opportunity_id":    opportunity_id,
        "outcome_date":      today,
        "live_os":           live_os,
        "cause_score":       cause_score,
        "propagation_score": prop_score,
        "shadow_os":         shadow_os,
    }


def backfill_outcomes(
    conn: sqlite3.Connection,
    today: str,
) -> int:
    """
    For every shadow_cause_outcomes row where actual_return_pct is NULL,
    check if the linked opportunity has closed (signal_birth has final_state set).
    If so, fill in actual_return_pct, days_to_peak, and final_state.

    Returns number of rows updated.
    """
    # Find closed opportunities not yet back-filled
    rows = conn.execute("""
        SELECT sco.outcome_id, sco.opportunity_id, o.first_signal_id
        FROM shadow_cause_outcomes sco
        JOIN opportunities o ON o.opportunity_id = sco.opportunity_id
        WHERE sco.actual_return_pct IS NULL
    """).fetchall()

    updated = 0
    for row in rows:
        oid    = row["opportunity_id"]
        sid    = row["first_signal_id"]
        if not sid:
            continue
        sb = conn.execute("""
            SELECT final_state, days_to_peak, peak_move_pct
            FROM signal_births WHERE signal_id = ? AND final_state IS NOT NULL
        """, (sid,)).fetchone()
        if not sb:
            continue
        conn.execute("""
            UPDATE shadow_cause_outcomes
               SET actual_return_pct = ?,
                   days_to_peak      = ?,
                   final_state       = ?
             WHERE outcome_id = ?
        """, (sb["peak_move_pct"], sb["days_to_peak"], sb["final_state"],
               row["outcome_id"]))
        updated += 1

    return updated


def run_shadow_scoring_cycle(
    conn: sqlite3.Connection,
    today: str,
) -> dict:
    """
    Daily shadow scoring cycle:
      1. For each ACTIVE / WATCHING opportunity with a live OS in opportunities,
         call record_shadow_score().
      2. backfill_outcomes() for closed opportunities.

    Returns summary.
    """
    opps = conn.execute("""
        SELECT opportunity_id, conviction_score
        FROM opportunities
        WHERE current_state IN ('ACTIVE', 'WATCHING', 'DISCOVERED')
    """).fetchall()

    recorded = 0
    for row in opps:
        try:
            record_shadow_score(conn, row["opportunity_id"], today,
                                float(row["conviction_score"] or 0.0))
            recorded += 1
        except Exception:
            log.exception("[E1] shadow_scoring error for opp %s", row["opportunity_id"])

    backfilled = backfill_outcomes(conn, today)

    return {
        "shadow_scores_recorded": recorded,
        "outcomes_backfilled":    backfilled,
    }
