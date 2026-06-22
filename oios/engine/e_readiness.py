"""
oios/engine/e_readiness.py

Phase E1 (Shadow Mode) — E-Readiness Checker.

Three gates that must all pass before E1 cause/propagation scores may
influence any live decision parameter.

E-Ready-1: >= 500 opportunities with cause candidates + final outcomes recorded
E-Ready-2: >= 50 successful AND >= 50 unsuccessful cause-attributed opportunities
E-Ready-3: Top-quartile cause score win rate > bottom-quartile by >= 10 pp

Gate values are intentionally conservative — the engine is designed to observe
for months before any gate can pass.

Shadow mode: this module is READ-ONLY (SELECT only on all tables).
"""

from __future__ import annotations

import logging
import sqlite3
from datetime import date

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Gate thresholds
# ---------------------------------------------------------------------------

E_READY_1_MIN_OBSERVATIONS = 500   # opportunities with cause data + closed outcome
E_READY_2_MIN_SUCCESS      = 50    # closed cause-attributed opps that succeeded
E_READY_2_MIN_FAILURE      = 50    # closed cause-attributed opps that failed
E_READY_3_WIN_RATE_GAP     = 0.10  # top Q1 vs bottom Q4 win rate spread required

# A "succeeded" opportunity has final_state in {ACTIVE, TTL_EXHAUSTED, ZOMBIE_CAP}
# where peak_move_pct >= expected_move_pct (thesis confirmed).
# A "failed" opportunity has final_state = INVALID with peak_move_pct < expected_move_pct.
_SUCCESS_STATES = ("ACTIVE",)        # still alive counts as success-in-progress
_TERMINAL_WIN   = frozenset({"TTL_EXHAUSTED"})   # reached TTL with positive return
_TERMINAL_LOSS  = frozenset({"INVALID"})


def check_e_ready_1(conn: sqlite3.Connection) -> dict:
    """
    E-Ready-1: At least 500 opportunities have BOTH:
      (a) at least one cause candidate in opportunity_causes
      (b) a closed outcome in shadow_cause_outcomes (final_state IS NOT NULL)
    """
    n = conn.execute("""
        SELECT COUNT(DISTINCT sco.opportunity_id) AS cnt
        FROM shadow_cause_outcomes sco
        JOIN opportunity_causes oc ON oc.opportunity_id = sco.opportunity_id
        WHERE sco.final_state IS NOT NULL
    """).fetchone()["cnt"]

    return {
        "gate":          "E-Ready-1",
        "threshold":     E_READY_1_MIN_OBSERVATIONS,
        "current":       n,
        "pass":          n >= E_READY_1_MIN_OBSERVATIONS,
        "description":   "500 opportunities with cause data + final outcome",
    }


def check_e_ready_2(conn: sqlite3.Connection) -> dict:
    """
    E-Ready-2: At least 50 successful AND 50 unsuccessful cause-attributed opps.

    "Successful": final_state = TTL_EXHAUSTED  (positive return)
    "Unsuccessful": final_state = INVALID
    Both must have cause_score > 0 (i.e., actual cause candidates identified).
    """
    row = conn.execute("""
        SELECT
            SUM(CASE WHEN sco.final_state = 'TTL_EXHAUSTED' THEN 1 ELSE 0 END) AS successes,
            SUM(CASE WHEN sco.final_state = 'INVALID' THEN 1 ELSE 0 END)       AS failures
        FROM shadow_cause_outcomes sco
        WHERE sco.cause_score > 0 AND sco.final_state IS NOT NULL
    """).fetchone()

    successes = row["successes"] or 0
    failures  = row["failures"]  or 0

    return {
        "gate":               "E-Ready-2",
        "threshold_success":  E_READY_2_MIN_SUCCESS,
        "threshold_failure":  E_READY_2_MIN_FAILURE,
        "current_success":    successes,
        "current_failure":    failures,
        "pass":               successes >= E_READY_2_MIN_SUCCESS and failures >= E_READY_2_MIN_FAILURE,
        "description":        "50 successful + 50 unsuccessful cause-attributed opportunities",
    }


def check_e_ready_3(conn: sqlite3.Connection) -> dict:
    """
    E-Ready-3: Top-quartile cause score win rate > bottom-quartile win rate by >= 10 pp.

    Win = final_state = 'TTL_EXHAUSTED'.
    Only include opportunities that are fully closed (final_state IS NOT NULL).
    Quartile split is by cause_score at the time of recording.
    """
    # Fetch all closed outcomes that have a cause score
    rows = conn.execute("""
        SELECT sco.cause_score, sco.final_state
        FROM shadow_cause_outcomes sco
        WHERE sco.cause_score IS NOT NULL
          AND sco.final_state IS NOT NULL
          AND sco.cause_score > 0
        ORDER BY sco.cause_score ASC
    """).fetchall()

    n = len(rows)
    if n < 40:   # need at least 40 to form meaningful quartiles (10 per Q)
        return {
            "gate":          "E-Ready-3",
            "pass":          False,
            "current_n":     n,
            "insufficient_data": True,
            "description":   "Top Q1 cause score win rate > bottom Q4 by 10pp",
        }

    q1_cutoff = int(n * 0.25)
    q4_start  = int(n * 0.75)

    bottom_q  = rows[:q1_cutoff]
    top_q     = rows[q4_start:]

    def _win_rate(group) -> float:
        wins = sum(1 for r in group if r["final_state"] == "TTL_EXHAUSTED")
        return wins / len(group) if group else 0.0

    top_wr    = round(_win_rate(top_q), 4)
    bottom_wr = round(_win_rate(bottom_q), 4)
    gap       = round(top_wr - bottom_wr, 4)

    return {
        "gate":             "E-Ready-3",
        "threshold_gap":    E_READY_3_WIN_RATE_GAP,
        "top_quartile_wr":  top_wr,
        "bottom_quartile_wr": bottom_wr,
        "win_rate_gap":     gap,
        "n_top":            len(top_q),
        "n_bottom":         len(bottom_q),
        "pass":             gap >= E_READY_3_WIN_RATE_GAP,
        "description":      "Top Q1 cause score win rate > bottom Q4 by >= 10pp",
    }


def check_e_ready(conn: sqlite3.Connection) -> dict:
    """
    Run all three E-Ready gates and return combined result.
    overall_pass = True only when ALL three gates pass.
    """
    g1 = check_e_ready_1(conn)
    g2 = check_e_ready_2(conn)
    g3 = check_e_ready_3(conn)

    overall = g1["pass"] and g2["pass"] and g3["pass"]
    n_passing = sum(1 for g in (g1, g2, g3) if g["pass"])

    summary = {
        "overall_pass":  overall,
        "gates_passing": n_passing,
        "gates_total":   3,
        "checked_at":    date.today().isoformat(),
        "e_ready_1":     g1,
        "e_ready_2":     g2,
        "e_ready_3":     g3,
    }
    if overall:
        summary["message"] = (
            "All E-Ready gates PASS. "
            "E1 may be authorized to influence decisions after explicit approval."
        )
    else:
        summary["message"] = (
            f"E-Ready gates: {n_passing}/3 passing. "
            "E1 remains in shadow mode — continue data collection."
        )
    return summary
