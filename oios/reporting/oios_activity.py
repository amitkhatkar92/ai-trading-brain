"""
oios/reporting/oios_activity.py

OIOS Activity Report — state distribution, transitions, score summaries,
decision log activity for a given trading day.
Read-only SELECT queries only. No writes.
"""
from __future__ import annotations

import sqlite3

from .base import (hr, section, kv, fmt, fmt_int, pct,
                   stats_line, report_header, shadow_mode_footer)

# States in display order
_STATES = ["DISCOVERED", "WATCHING", "ACTIVE", "ZOMBIE_CAP",
           "TTL_EXHAUSTED", "INVALID"]
_TERMINAL = {"ZOMBIE_CAP", "TTL_EXHAUSTED", "INVALID"}


def generate_oios_activity_report(conn: sqlite3.Connection, report_date: str) -> str:
    lines: list[str] = [report_header("OIOS ACTIVITY REPORT", report_date)]

    # ── Opportunity State Distribution ────────────────────────────────────
    lines.append(section("OPPORTUNITY STATE DISTRIBUTION"))
    try:
        state_rows = conn.execute("""
            SELECT current_state, COUNT(*) AS n
            FROM opportunities GROUP BY current_state
        """).fetchall()
        state_map = {r[0]: r[1] for r in state_rows}
        total_opps = sum(state_map.values())

        for s in _STATES:
            n = state_map.get(s, 0)
            lines.append(kv(f"  {s}:", f"{n:>6}   ({pct(n, total_opps)})"))
        # Catch any unexpected states
        for s, n in state_map.items():
            if s not in _STATES:
                lines.append(kv(f"  {s} (unexpected):", f"{n:>6}"))
        lines.append(kv("  TOTAL:", f"{total_opps:>6}"))
    except Exception as e:
        lines.append(f"  ERROR: {e}")

    # ── Today's Activity ──────────────────────────────────────────────────
    lines.append(section(f"ACTIVITY TODAY ({report_date})"))
    try:
        new_today = conn.execute(
            "SELECT COUNT(*) FROM opportunities WHERE DATE(created_at) = ?",
            (report_date,)
        ).fetchone()[0]
        lines.append(kv("New opportunities born:", fmt_int(new_today)))

        closed_today = conn.execute("""
            SELECT current_state, COUNT(*) AS n
            FROM opportunities
            WHERE current_state IN ('ZOMBIE_CAP','TTL_EXHAUSTED','INVALID')
              AND DATE(created_at) <= ?
            GROUP BY current_state
        """, (report_date,)).fetchall()
        # Use transitions to count closures today
        closed_trans = conn.execute("""
            SELECT to_state, COUNT(*) AS n
            FROM signal_state_transitions
            WHERE to_state IN ('ZOMBIE_CAP','TTL_EXHAUSTED','INVALID')
              AND DATE(transitioned_at) = ?
            GROUP BY to_state
        """, (report_date,)).fetchall()
        closed_map = {r[0]: r[1] for r in closed_trans}
        total_closed = sum(closed_map.values())
        lines.append(kv("Opportunities closed today:", fmt_int(total_closed)))
        for st, n in sorted(closed_map.items()):
            lines.append(f"    → {st:<22} {n}")

        # All transitions today
        trans_rows = conn.execute("""
            SELECT from_state, to_state, COUNT(*) AS n
            FROM signal_state_transitions
            WHERE DATE(transitioned_at) = ?
            GROUP BY from_state, to_state
            ORDER BY from_state, to_state
        """, (report_date,)).fetchall()
        lines.append(kv("State transitions today:", fmt_int(len(trans_rows)) + " distinct pairs"))
        for r in trans_rows:
            lines.append(f"    {r[0]:<18} → {r[1]:<18} {r[2]:>4}")
        if not trans_rows:
            lines.append("    (none)")
    except Exception as e:
        lines.append(f"  ERROR: {e}")

    # ── Score Distributions ───────────────────────────────────────────────
    lines.append(section("SCORE DISTRIBUTIONS (ACTIVE opportunities)"))
    try:
        active_rows = conn.execute("""
            SELECT conviction_score, re_score, NULL as maturity_score,
                   age_trading_days, effective_ttl_days
            FROM opportunities
            WHERE current_state = 'ACTIVE'
        """).fetchall()

        if active_rows:
            n_active = len(active_rows)
            lines.append(kv("Active count:", fmt_int(n_active)))

            lines.append("\n  Conviction Score:")
            lines.append(stats_line([r[0] for r in active_rows if r[0] is not None]))

            lines.append("\n  RE Score:")
            lines.append(stats_line([r[1] for r in active_rows if r[1] is not None]))

            lines.append("\n  Maturity Score:")
            lines.append(stats_line([r[2] for r in active_rows if r[2] is not None]))

            lines.append("\n  Age (trading days):")
            lines.append(stats_line([r[3] for r in active_rows if r[3] is not None]))

            # TTL utilization %
            ttl_util = [
                100 * r[3] / r[4]
                for r in active_rows
                if r[3] is not None and r[4] and r[4] > 0
            ]
            if ttl_util:
                lines.append("\n  TTL Utilization (age / effective_ttl × 100):")
                lines.append(stats_line(ttl_util))
        else:
            lines.append("  No ACTIVE opportunities.")
    except Exception as e:
        lines.append(f"  ERROR: {e}")

    # ── Decision Log ──────────────────────────────────────────────────────
    lines.append(section(f"DECISION LOG ({report_date})"))
    try:
        dec_rows = conn.execute("""
            SELECT action, COUNT(*) AS n
            FROM decision_log
            WHERE DATE(decided_at) = ?
            GROUP BY action ORDER BY n DESC
        """, (report_date,)).fetchall()
        total_dec = sum(r[1] for r in dec_rows)
        lines.append(kv("Total decisions today:", fmt_int(total_dec)))
        for r in dec_rows:
            lines.append(f"  {r[0]:<36} {r[1]:>5}")
        if not dec_rows:
            lines.append("  (none logged today)")
    except Exception as e:
        lines.append(f"  ERROR: {e}")

    # ── Signal Birth Summary ──────────────────────────────────────────────
    lines.append(section("SIGNAL BIRTHS"))
    try:
        sb_today = conn.execute(
            "SELECT COUNT(*), COUNT(DISTINCT archetype_id) "
            "FROM signal_births WHERE DATE(detected_at) = ?",
            (report_date,)
        ).fetchone()
        lines.append(kv("Signal births today:", fmt_int(sb_today[0])))
        lines.append(kv("Distinct archetypes firing today:", fmt_int(sb_today[1])))

        arch_rows = conn.execute("""
            SELECT archetype_id, COUNT(*) AS n
            FROM signal_births WHERE DATE(detected_at) = ?
            GROUP BY archetype_id ORDER BY n DESC
        """, (report_date,)).fetchall()
        for r in arch_rows:
            lines.append(f"    {r[0]:<40} {r[1]:>4}")
        if not arch_rows:
            lines.append("    (none today)")
    except Exception as e:
        lines.append(f"  ERROR: {e}")

    lines.append(shadow_mode_footer("Phase D", "Phase E"))
    return "\n".join(lines)
