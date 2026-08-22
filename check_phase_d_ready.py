"""
check_phase_d_ready.py

Phase D Readiness Check — answers D-Ready-1 through D-Ready-5.

Run this after Phase C has been live for a meaningful period.
NOT a progress report — a hard gate.

Usage:
    python check_phase_d_ready.py
    python check_phase_d_ready.py --db data/market_behavior.db

Output:
    READY / NOT READY per criterion, with diagnostic counts and notes.

Criteria:
    D-Ready-1  >= 100 ACTIVE-to-WATCHING-or-INVALID state transitions
    D-Ready-2  >= 60 calendar days of RE trajectory data
    D-Ready-3  >= 30 completed opportunities (terminal state reached)
    D-Ready-4  >= 3 distinct invalidation reasons represented
    D-Ready-5  No single lifecycle state > 80% for 30 consecutive days

Recommended reading order when results arrive:
    1. D-Ready-5 (State Concentration)
       30-consecutive-day concentration means Phase C's State Machine is not
       cycling opportunities correctly. Fix the state machine before adding
       any Phase D learning layer on top of a stuck population.

    2. D-Ready-4 (Invalidation Diversity)
       Fewer than 3 reasons means most opportunities exit via the same path.
       If NEVER_MATURED dominates: activation threshold is too strict.
       If TTL_EXHAUSTED dominates: TTL assumptions are wrong for this regime.
       If EC_THRESHOLD dominates: expected-move assumptions are too optimistic.
       Calibrate Phase C thresholds before teaching Phase D to classify them.

    3. D-Ready-3 (Completed Opportunities)
       The minimum population for meaningful outcome distribution learning.
       Low count = Phase C has not had enough time, not a Phase D problem.

    4. D-Ready-1 (Transition Volume)
       Validates that the ACTIVE-WATCHING cycle is actually functioning.
       Zero WATCHING entries means ACTIVE opportunities are never re-evaluated.

    5. D-Ready-2 (RE Trajectory Coverage)
       60 days spans roughly 2–3 regime windows. Less than that means the
       RE decay curves have not been observed across different regimes yet.
       Phase D velocity attribution needs multi-regime RE data to be credible.

Phase D discipline:
    Phase D implements Velocity Attribution + Transition Probabilities +
    the first Adaptive Intelligence layer (outcome-conditioned weights).
    Nothing in Phase D should alter Phase C's deterministic RE computation
    or State Machine transition logic.
    Phase D adds probability estimates on top of a working deterministic base.
    If Phase D learning produces strange results, Phase C outputs remain valid
    and can be used as the fallback without breaking anything downstream.
"""

import argparse
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path


# ---------------------------------------------------------------------------
# Thresholds
# ---------------------------------------------------------------------------

READY_TRANSITIONS          = 100  # D-Ready-1: state transitions ACTIVE->WATCHING or ACTIVE->INVALID
READY_RE_DAYS              = 60   # D-Ready-2: calendar days with RE snapshot data
READY_COMPLETED_OPPS       = 30   # D-Ready-3: opportunities that reached a terminal state
READY_INVALIDATION_REASONS = 3    # D-Ready-4: distinct invalidation_reason values
CONCENTRATION_WINDOW_DAYS  = 30   # D-Ready-5: rolling window
CONCENTRATION_MAX          = 0.80 # D-Ready-5: no single state above this fraction

# States that Phase C considers terminal
TERMINAL_STATES = {"INVALID", "COMPLETED", "EXPIRED"}

# The state transition Phase D needs to see cycling
ACTIVE_EXIT_STATES = {"WATCHING", "INVALID", "COMPLETED", "EXPIRED"}


def _banner(title):
    print(f"\n{'─'*60}")
    print(f"  {title}")
    print(f"{'─'*60}")


def _ready(label, ok, detail=""):
    icon = "✓ READY    " if ok else "✗ NOT READY"
    print(f"  {icon}  {label}")
    if detail:
        print(f"             {detail}")
    return ok


def _table_exists(conn, table_name):
    row = conn.execute(
        "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,),
    ).fetchone()
    return row[0] > 0


def check_phase_d_ready(db_path: str) -> bool:
    if not Path(db_path).exists():
        print(f"\n[ERROR] Database not found: {db_path}")
        print("  Phase C has not been initialised yet.")
        print("  Phase D cannot be evaluated without Phase C data.")
        sys.exit(1)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    results = []

    # -----------------------------------------------------------------------
    # D-Ready-1: State transition volume  ACTIVE -> WATCHING | INVALID
    # -----------------------------------------------------------------------
    _banner("D-Ready-1: State Transition Volume")

    if not _table_exists(conn, "signal_state_transitions"):
        print("  signal_state_transitions table does not exist.")
        print("  Phase A schema must be applied before simulation can run.")
        ok1 = _ready(
            f">= {READY_TRANSITIONS} ACTIVE->WATCHING/INVALID transitions",
            False,
            "table missing — apply Phase A schema and run simulation",
        )
    else:
        # Count records where previous state was ACTIVE and new state is an exit.
        # signal_state_transitions is the Phase A schema table for all state changes.
        active_exits = conn.execute("""
            SELECT to_state, COUNT(*) AS n
            FROM signal_state_transitions
            WHERE from_state = 'ACTIVE'
              AND to_state IN ('WATCHING', 'INVALID', 'COMPLETED', 'EXPIRED')
            GROUP BY to_state
            ORDER BY n DESC
        """).fetchall()

        total_exits = sum(r["n"] for r in active_exits)
        print(f"  Total ACTIVE->exit transitions: {total_exits}")
        if active_exits:
            print("  Breakdown by destination state:")
            for r in active_exits:
                print(f"    ACTIVE -> {r['to_state']:<12}  {r['n']}")
        else:
            print("  No ACTIVE exit transitions recorded yet.")

        # Also show all-pairs for context
        all_pairs = conn.execute("""
            SELECT from_state, to_state, COUNT(*) AS n
            FROM signal_state_transitions
            GROUP BY from_state, to_state
            ORDER BY n DESC
            LIMIT 15
        """).fetchall()
        if all_pairs:
            print(f"\n  All observed transitions (top 15):")
            for r in all_pairs:
                print(f"    {r['from_state']:<12} -> {r['to_state']:<12}  {r['n']}")

        ok1 = _ready(
            f">= {READY_TRANSITIONS} ACTIVE->WATCHING/INVALID transitions",
            total_exits >= READY_TRANSITIONS,
            f"actual={total_exits}, need={READY_TRANSITIONS}",
        )

    results.append(ok1)

    # -----------------------------------------------------------------------
    # D-Ready-2: RE trajectory coverage (calendar days)
    # -----------------------------------------------------------------------
    _banner("D-Ready-2: RE Trajectory Coverage")

    if not _table_exists(conn, "opportunity_re_snapshots"):
        print("  opportunity_re_snapshots table does not exist.")
        print("  This table is written by Phase C RE Calculator (not yet built).")
        print("  D-Ready-2 cannot be evaluated until Phase C is authorized and deployed.")
        ok2 = _ready(
            f">= {READY_RE_DAYS} calendar days of RE data",
            False,
            "table missing — Phase C RE Calculator not yet deployed",
        )
    else:
        re_range = conn.execute("""
            SELECT MIN(snapshot_date) AS earliest,
                   MAX(snapshot_date) AS latest,
                   COUNT(DISTINCT snapshot_date) AS trading_days,
                   COUNT(DISTINCT opportunity_id) AS opportunities_tracked
            FROM opportunity_re_snapshots
        """).fetchone()

        earliest     = re_range["earliest"]
        latest       = re_range["latest"]
        trading_days = re_range["trading_days"] or 0
        tracked      = re_range["opportunities_tracked"] or 0

        # Approximate calendar days from earliest/latest dates
        calendar_days = 0
        if earliest and latest:
            from datetime import date
            try:
                d0 = date.fromisoformat(earliest[:10])
                d1 = date.fromisoformat(latest[:10])
                calendar_days = (d1 - d0).days
            except ValueError:
                calendar_days = trading_days  # fallback: use trading days

        print(f"  RE snapshots date range: {earliest} -> {latest}")
        print(f"  Calendar days spanned:   {calendar_days}")
        print(f"  Trading days with data:  {trading_days}")
        print(f"  Distinct opportunities tracked: {tracked}")

        # Show RE distribution at latest snapshot date
        if latest:
            re_dist = conn.execute("""
                SELECT
                    SUM(CASE WHEN re_score >= 0.7 THEN 1 ELSE 0 END) AS high_re,
                    SUM(CASE WHEN re_score >= 0.4 AND re_score < 0.7 THEN 1 ELSE 0 END) AS mid_re,
                    SUM(CASE WHEN re_score < 0.4 THEN 1 ELSE 0 END) AS low_re,
                    AVG(re_score) AS avg_re
                FROM opportunity_re_snapshots
                WHERE snapshot_date = ?
            """, (latest,)).fetchone()
            if re_dist and re_dist["avg_re"] is not None:
                print(f"\n  RE distribution on {latest}:")
                print(f"    High (>=0.7):  {re_dist['high_re']}")
                print(f"    Mid  (0.4-0.7):{re_dist['mid_re']}")
                print(f"    Low  (<0.4):   {re_dist['low_re']}")
                print(f"    Average RE:    {re_dist['avg_re']:.3f}")

        ok2 = _ready(
            f">= {READY_RE_DAYS} calendar days of RE trajectory data",
            calendar_days >= READY_RE_DAYS,
            f"actual={calendar_days} days, need={READY_RE_DAYS}",
        )

    results.append(ok2)

    # -----------------------------------------------------------------------
    # D-Ready-3: Completed opportunities
    # -----------------------------------------------------------------------
    _banner("D-Ready-3: Completed Opportunities")

    if not _table_exists(conn, "opportunities"):
        print("  opportunities table does not exist.")
        ok3 = _ready(
            f">= {READY_COMPLETED_OPPS} completed opportunities",
            False,
            "table missing — Phase C not yet deployed",
        )
    else:
        completed = conn.execute(f"""
            SELECT current_state, COUNT(*) AS n
            FROM opportunities
            WHERE current_state IN ({', '.join('?' * len(TERMINAL_STATES))})
            GROUP BY current_state
            ORDER BY n DESC
        """, list(TERMINAL_STATES)).fetchall()

        total_completed = sum(r["n"] for r in completed)
        total_all       = conn.execute("SELECT COUNT(*) AS n FROM opportunities").fetchone()["n"]

        print(f"  Total opportunities created: {total_all}")
        print(f"  Terminal-state opportunities: {total_completed}")
        if completed:
            for r in completed:
                print(f"    {r['current_state']:<12}  {r['n']}")

        completion_rate = total_completed / total_all * 100 if total_all > 0 else 0
        print(f"  Completion rate: {completion_rate:.1f}%")

        if total_all > 0 and total_completed == 0:
            print("\n  NOTE: No opportunities have reached a terminal state.")
            print("        Either the system has not run long enough, or the TTL")
            print("        defaults are very long relative to the collection period.")

        ok3 = _ready(
            f">= {READY_COMPLETED_OPPS} completed opportunities",
            total_completed >= READY_COMPLETED_OPPS,
            f"actual={total_completed}, need={READY_COMPLETED_OPPS}",
        )

    results.append(ok3)

    # -----------------------------------------------------------------------
    # D-Ready-4: Invalidation reason diversity
    # -----------------------------------------------------------------------
    _banner("D-Ready-4: Invalidation Reason Diversity")

    if not _table_exists(conn, "opportunities"):
        ok4 = _ready(
            f">= {READY_INVALIDATION_REASONS} distinct invalidation reasons",
            False,
            "table missing — Phase C not yet deployed",
        )
    else:
        inv_reasons = conn.execute("""
            SELECT invalidation_reason,
                   COUNT(*) AS n,
                   ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 1) AS pct
            FROM opportunities
            WHERE invalidation_reason IS NOT NULL
            GROUP BY invalidation_reason
            ORDER BY n DESC
        """).fetchall()

        distinct_reasons = len(inv_reasons)
        total_invalidated = sum(r["n"] for r in inv_reasons)

        print(f"  Total invalidated opportunities: {total_invalidated}")
        print(f"  Distinct invalidation reasons: {distinct_reasons}")

        if inv_reasons:
            print("\n  Breakdown:")
            for r in inv_reasons:
                bar = "█" * int(r["pct"] / 3)
                print(f"    {r['invalidation_reason']:<30}  {r['n']:>4}  ({r['pct']:4.1f}%)  {bar}")

            # Warn if one reason dominates overwhelmingly
            top_pct = inv_reasons[0]["pct"] if inv_reasons else 0
            if top_pct > 70:
                print(f"\n  NOTE: {inv_reasons[0]['invalidation_reason']} accounts for "
                      f"{top_pct}% of all invalidations.")
                print("        Calibrate Phase C thresholds before Phase D learns from this")
                print("        distribution — Phase D will amplify whatever pattern is here.")
        else:
            print("\n  No invalidation data yet.")

        ok4 = _ready(
            f">= {READY_INVALIDATION_REASONS} distinct invalidation reasons",
            distinct_reasons >= READY_INVALIDATION_REASONS,
            f"actual={distinct_reasons}, need={READY_INVALIDATION_REASONS}",
        )

    results.append(ok4)

    # -----------------------------------------------------------------------
    # D-Ready-5: Sustained state concentration check
    # -----------------------------------------------------------------------
    _banner(f"D-Ready-5: State Concentration (no state > {int(CONCENTRATION_MAX*100)}% "
            f"for {CONCENTRATION_WINDOW_DAYS} consecutive days)")

    if not _table_exists(conn, "opportunity_daily_state_snapshot"):
        # Fallback: approximate from opportunities.current_state only
        # This is a coarse check — without daily snapshots we only see today's view
        print("  opportunity_daily_state_snapshot table not found.")
        print("  Falling back to current-state distribution only.")
        print(f"  (Full 30-day concentration check requires daily snapshots from Phase C.)")

        if _table_exists(conn, "opportunities"):
            state_rows = conn.execute("""
                SELECT current_state, COUNT(*) AS n
                FROM opportunities GROUP BY current_state ORDER BY n DESC
            """).fetchall()
            total_opps = sum(r["n"] for r in state_rows)
            if total_opps > 0:
                dominant_frac = state_rows[0]["n"] / total_opps if state_rows else 0
                dominant_state = state_rows[0]["current_state"] if state_rows else "N/A"
                print(f"\n  Current state distribution (snapshot only):")
                for r in state_rows:
                    pct = r["n"] / total_opps * 100
                    print(f"    {r['current_state']:<12}  {r['n']:>5}  ({pct:5.1f}%)")
                if dominant_frac > CONCENTRATION_MAX:
                    ok5 = _ready(
                        f"no state > {int(CONCENTRATION_MAX*100)}% for "
                        f"{CONCENTRATION_WINDOW_DAYS} consecutive days",
                        False,
                        f"{dominant_state} is at {dominant_frac*100:.1f}% today — "
                        "investigate even without 30-day history",
                    )
                else:
                    ok5 = _ready(
                        f"no state > {int(CONCENTRATION_MAX*100)}% for "
                        f"{CONCENTRATION_WINDOW_DAYS} consecutive days",
                        False,
                        "daily snapshot table missing — cannot verify 30-day window",
                    )
            else:
                ok5 = _ready(
                    f"no state > {int(CONCENTRATION_MAX*100)}% for "
                    f"{CONCENTRATION_WINDOW_DAYS} consecutive days",
                    False,
                    "no opportunities yet",
                )
        else:
            ok5 = _ready(
                f"no state > {int(CONCENTRATION_MAX*100)}% for "
                f"{CONCENTRATION_WINDOW_DAYS} consecutive days",
                False,
                "opportunities table missing",
            )
    else:
        # Full check: find any 30-consecutive-day window where one state > 80%
        daily_rows = conn.execute("""
            SELECT snapshot_date, current_state,
                   COUNT(*) AS n,
                   SUM(COUNT(*)) OVER (PARTITION BY snapshot_date) AS day_total
            FROM opportunity_daily_state_snapshot
            GROUP BY snapshot_date, current_state
            ORDER BY snapshot_date
        """).fetchall()

        # Group by date, find dominant fraction per day
        days_concentrated: list = []
        day_map: dict = defaultdict(dict)
        for r in daily_rows:
            day_map[r["snapshot_date"]][r["current_state"]] = (r["n"], r["day_total"])

        for day, states in sorted(day_map.items()):
            day_total = sum(v[0] for v in states.values())
            if day_total == 0:
                continue
            max_state = max(states, key=lambda s: states[s][0])
            max_frac  = states[max_state][0] / day_total
            if max_frac > CONCENTRATION_MAX:
                days_concentrated.append((day, max_state, max_frac))

        # Check for any consecutive run >= CONCENTRATION_WINDOW_DAYS
        consecutive_run = 0
        max_run = 0
        max_run_detail = ""
        for i, (day, state, frac) in enumerate(days_concentrated):
            if i == 0:
                consecutive_run = 1
            else:
                prev_day = days_concentrated[i - 1][0]
                try:
                    from datetime import date as _date
                    d0 = _date.fromisoformat(prev_day[:10])
                    d1 = _date.fromisoformat(day[:10])
                    gap = (d1 - d0).days
                    # Allow up to 4 calendar days gap (weekend + holiday)
                    if gap <= 4:
                        consecutive_run += 1
                    else:
                        consecutive_run = 1
                except ValueError:
                    consecutive_run = 1

            if consecutive_run > max_run:
                max_run = consecutive_run
                max_run_detail = f"{state} > {int(CONCENTRATION_MAX*100)}% for {max_run} days (ending {day})"

        total_days_tracked = len(day_map)
        print(f"  Trading days with snapshot data: {total_days_tracked}")
        print(f"  Days where any state > {int(CONCENTRATION_MAX*100)}%: {len(days_concentrated)}")
        if max_run_detail:
            print(f"  Longest concentrated run: {max_run_detail}")
        if days_concentrated:
            print(f"\n  Concentrated days (sample, last 10):")
            for day, state, frac in days_concentrated[-10:]:
                print(f"    {day}  {state:<12}  {frac*100:.1f}%")

        if total_days_tracked < CONCENTRATION_WINDOW_DAYS:
            ok5 = _ready(
                f"no state > {int(CONCENTRATION_MAX*100)}% for "
                f"{CONCENTRATION_WINDOW_DAYS} consecutive days",
                False,
                f"only {total_days_tracked} days of snapshot data — "
                f"need {CONCENTRATION_WINDOW_DAYS} to evaluate 30-day window",
            )
        else:
            ok5 = _ready(
                f"no state > {int(CONCENTRATION_MAX*100)}% for "
                f"{CONCENTRATION_WINDOW_DAYS} consecutive days",
                max_run < CONCENTRATION_WINDOW_DAYS,
                max_run_detail if max_run >= CONCENTRATION_WINDOW_DAYS else
                f"longest concentrated run = {max_run} days (threshold={CONCENTRATION_WINDOW_DAYS})",
            )

    results.append(ok5)

    # -----------------------------------------------------------------------
    # Bonus: Phase C health summary
    # -----------------------------------------------------------------------
    _banner("Bonus: Phase C Health Summary")

    if _table_exists(conn, "opportunities"):
        opp_summary = conn.execute("""
            SELECT
                COUNT(*) AS total,
                SUM(CASE WHEN current_state = 'DISCOVERED' THEN 1 ELSE 0 END) AS discovered,
                SUM(CASE WHEN current_state = 'ACTIVE'     THEN 1 ELSE 0 END) AS active,
                SUM(CASE WHEN current_state = 'WATCHING'   THEN 1 ELSE 0 END) AS watching,
                SUM(CASE WHEN current_state = 'INVALID'    THEN 1 ELSE 0 END) AS invalid,
                MIN(first_seen_at) AS oldest,
                MAX(first_seen_at) AS newest
            FROM opportunities
        """).fetchone()
        print(f"  Opportunities:  total={opp_summary['total']}  "
              f"DISCOVERED={opp_summary['discovered']}  "
              f"ACTIVE={opp_summary['active']}  "
              f"WATCHING={opp_summary['watching']}  "
              f"INVALID={opp_summary['invalid']}")
        print(f"  Date range: {opp_summary['oldest']} -> {opp_summary['newest']}")
    else:
        print("  Phase C tables not yet present.")

    # -----------------------------------------------------------------------
    # Summary
    # -----------------------------------------------------------------------
    _banner("PHASE D READINESS SUMMARY")

    labels = [
        "D-Ready-1: >= 100 ACTIVE->WATCHING/INVALID transitions",
        "D-Ready-2: >= 60 calendar days of RE trajectory data",
        "D-Ready-3: >= 30 completed opportunities",
        "D-Ready-4: >= 3 distinct invalidation reasons",
        "D-Ready-5: no state > 80% for 30 consecutive days",
    ]
    all_ready = all(results)
    for label, ok in zip(labels, results):
        icon = "✓ READY" if ok else "✗ NOT READY"
        print(f"  {icon}  {label}")

    print()
    if all_ready:
        print("  -> PHASE D MAY BEGIN")
    else:
        not_ready = sum(1 for r in results if not r)
        print(f"  -> PHASE D BLOCKED -- {not_ready} prerequisite(s) not yet met.")
        print("  -> Continue running Phase C. Re-check after more data accumulates.")

    conn.close()
    return all_ready


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Phase D Readiness Check")
    parser.add_argument(
        "--db",
        default="data/market_behavior.db",
        help="Path to SQLite database (default: data/market_behavior.db)",
    )
    args = parser.parse_args()
    ready = check_phase_d_ready(args.db)
    sys.exit(0 if ready else 1)
