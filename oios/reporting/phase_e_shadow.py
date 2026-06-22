"""
oios/reporting/phase_e_shadow.py

Phase E Shadow Report — event ingestion, cause intelligence, propagation,
shadow OS delta, cumulative outcome tracking, and E-Readiness snapshot.

Shadow mode: outputs never influence live OS, RE, TTL, or conviction.
Read-only SELECT queries only. No writes.
"""
from __future__ import annotations

import sqlite3
import statistics as _st

from .base import (hr, section, kv, kv_warn, fmt, fmt_int, pct,
                   quartile_win_rate, report_header, shadow_mode_footer)


def generate_phase_e_shadow_report(conn: sqlite3.Connection, report_date: str) -> str:
    lines: list[str] = [report_header("PHASE E SHADOW REPORT", report_date)]

    # ── Event Ingestion (E0) ──────────────────────────────────────────────
    lines.append(section("EVENT INGESTION (Phase E0)"))
    try:
        evt_rows = conn.execute("""
            SELECT event_type, COUNT(*) AS n
            FROM daily_events WHERE event_date = ?
            GROUP BY event_type ORDER BY n DESC
        """, (report_date,)).fetchall()
        total_evt = sum(r[1] for r in evt_rows)
        lines.append(kv("Events ingested today:", fmt_int(total_evt)))
        for r in evt_rows:
            lines.append(f"    {r[0]:<28} {r[1]}")
        if not evt_rows:
            lines.append("    (none)")

        total_evt_all = conn.execute(
            "SELECT COUNT(*) FROM daily_events"
        ).fetchone()[0]
        lines.append(kv("Total events in database:", fmt_int(total_evt_all)))

        # High-confidence events today
        hc_today = conn.execute(
            "SELECT COUNT(*) FROM daily_events "
            "WHERE event_date = ? AND confidence >= 0.8",
            (report_date,)
        ).fetchone()[0]
        lines.append(kv("High-confidence events (≥ 0.80) today:", fmt_int(hc_today)))
    except Exception as e:
        lines.append(f"  [Phase E0 tables not available: {e}]")

    # ── Cause Intelligence (E1) ───────────────────────────────────────────
    lines.append(section("CAUSE INTELLIGENCE (Phase E1)"))
    try:
        cs_row = conn.execute("""
            SELECT COUNT(*) AS n,
                   SUM(CASE WHEN cause_score > 0 THEN 1 ELSE 0 END) AS positive,
                   AVG(CASE WHEN cause_score > 0 THEN cause_score END) AS avg_pos
            FROM cause_scores WHERE score_date = ?
        """, (report_date,)).fetchone()

        n_scored = cs_row[0] or 0
        n_positive = cs_row[1] or 0
        avg_pos = cs_row[2]

        lines.append(kv("Opportunities with cause scores today:", fmt_int(n_scored)))
        lines.append(kv("Opportunities with cause_score > 0:", fmt_int(n_positive) +
                        f"  ({pct(n_positive, n_scored)})"))
        lines.append(kv("Average cause score (where > 0):", fmt(avg_pos)))

        # Primary cause types
        pct_rows = conn.execute("""
            SELECT primary_cause_type, COUNT(*) AS n
            FROM cause_scores
            WHERE score_date = ? AND primary_cause_type IS NOT NULL
            GROUP BY primary_cause_type ORDER BY n DESC
        """, (report_date,)).fetchall()
        if pct_rows:
            lines.append("\n  Primary cause types today:")
            for r in pct_rows:
                lines.append(f"    {r[0]:<28} {r[1]}")

        # Total causes stored
        total_causes = conn.execute(
            "SELECT COUNT(*) FROM opportunity_causes"
        ).fetchone()[0]
        lines.append(kv("\n  Total cause candidates in database:", fmt_int(total_causes)))
    except Exception as e:
        lines.append(f"  [cause_scores / opportunity_causes not available: {e}]")

    # ── Propagation Engine (E1) ───────────────────────────────────────────
    lines.append(section("PROPAGATION ENGINE (Phase E1)"))
    try:
        prop_events = conn.execute("""
            SELECT COUNT(DISTINCT source_event_id)
            FROM propagation_paths WHERE DATE(computed_at) = ?
        """, (report_date,)).fetchone()[0]
        lines.append(kv("Events propagated today:", fmt_int(prop_events)))

        prop_paths = conn.execute("""
            SELECT COUNT(*) FROM propagation_paths WHERE DATE(computed_at) = ?
        """, (report_date,)).fetchone()[0]
        lines.append(kv("Propagation paths built today:", fmt_int(prop_paths)))

        prop_opps = conn.execute("""
            SELECT COUNT(DISTINCT opportunity_id)
            FROM propagation_scores WHERE score_date = ?
        """, (report_date,)).fetchone()[0]
        lines.append(kv("Downstream opportunities scored:", fmt_int(prop_opps)))

        total_paths = conn.execute(
            "SELECT COUNT(*) FROM propagation_paths"
        ).fetchone()[0]
        lines.append(kv("Total propagation paths in database:", fmt_int(total_paths)))

        # Hops distribution
        hop_rows = conn.execute("""
            SELECT path_hops, COUNT(*) AS n
            FROM propagation_paths
            WHERE DATE(computed_at) = ?
            GROUP BY path_hops ORDER BY path_hops
        """, (report_date,)).fetchall()
        if hop_rows:
            lines.append("\n  Hop distance distribution (today):")
            for r in hop_rows:
                lines.append(f"    {r[0]}-hop paths:              {r[1]}")
    except Exception as e:
        lines.append(f"  [propagation tables not available: {e}]")

    # ── Shadow OS vs Live OS ──────────────────────────────────────────────
    lines.append(section("SHADOW OS vs LIVE OS (today)"))
    try:
        sco_row = conn.execute("""
            SELECT COUNT(*) AS n,
                   AVG(shadow_os - live_os)   AS avg_delta,
                   MAX(shadow_os - live_os)   AS max_delta,
                   MIN(shadow_os - live_os)   AS min_delta,
                   SUM(CASE WHEN shadow_os > live_os THEN 1 ELSE 0 END) AS shadow_higher,
                   SUM(CASE WHEN shadow_os = live_os THEN 1 ELSE 0 END) AS shadow_equal
            FROM shadow_cause_outcomes WHERE outcome_date = ?
        """, (report_date,)).fetchone()

        n_sco = sco_row[0] or 0
        lines.append(kv("Opportunities scored today:", fmt_int(n_sco)))
        if n_sco > 0:
            lines.append(kv("Mean shadow delta (shadow − live):",
                            f"+{fmt(sco_row[1])}" if (sco_row[1] or 0) >= 0 else fmt(sco_row[1])))
            lines.append(kv("Max shadow delta:", fmt(sco_row[2])))
            lines.append(kv("Min shadow delta:", fmt(sco_row[3])))
            higher = sco_row[4] or 0
            equal  = sco_row[5] or 0
            lines.append(kv("shadow_os > live_os:",
                            f"{higher}  ({pct(higher, n_sco)})"))
            lines.append(kv("shadow_os = live_os (no cause data):",
                            f"{equal}  ({pct(equal, n_sco)})"))
        else:
            lines.append("  No shadow scores recorded today.")
    except Exception as e:
        lines.append(f"  [shadow_cause_outcomes not available: {e}]")

    # ── Cumulative Outcome Tracking ───────────────────────────────────────
    lines.append(section("CUMULATIVE SHADOW OUTCOMES"))
    try:
        cum_row = conn.execute("""
            SELECT COUNT(*) AS total,
                   SUM(CASE WHEN final_state IS NOT NULL THEN 1 ELSE 0 END) AS closed,
                   SUM(CASE WHEN final_state = 'TTL_EXHAUSTED' THEN 1 ELSE 0 END) AS wins,
                   SUM(CASE WHEN final_state = 'INVALID' THEN 1 ELSE 0 END) AS losses
            FROM shadow_cause_outcomes
        """).fetchone()
        total_cum = cum_row[0] or 0
        closed_cum = cum_row[1] or 0
        wins_cum = cum_row[2] or 0
        losses_cum = cum_row[3] or 0

        lines.append(kv("Total shadow outcome records:", fmt_int(total_cum)))
        lines.append(kv("Records with final outcome:", fmt_int(closed_cum)))
        lines.append(kv("Closed wins (TTL_EXHAUSTED):", fmt_int(wins_cum) +
                        f"  ({pct(wins_cum, closed_cum)})"))
        lines.append(kv("Closed losses (INVALID):", fmt_int(losses_cum) +
                        f"  ({pct(losses_cum, closed_cum)})"))

        # Cause attribution win rate split
        cause_wl = conn.execute("""
            SELECT cause_score, final_state
            FROM shadow_cause_outcomes
            WHERE cause_score IS NOT NULL
              AND final_state IS NOT NULL
              AND cause_score > 0
            ORDER BY cause_score ASC
        """).fetchall()
        if len(cause_wl) >= 40:
            lines.append("\n  Predictive value analysis (quartile split):")
            for lne in quartile_win_rate(cause_wl):
                lines.append(lne)
        else:
            lines.append(f"\n  Predictive analysis: Insufficient data "
                         f"({len(cause_wl)} closed obs with cause score, need ≥ 40)")
    except Exception as e:
        lines.append(f"  [shadow_cause_outcomes not available: {e}]")

    # ── E-Readiness Snapshot ──────────────────────────────────────────────
    lines.append(section("E-READINESS SNAPSHOT"))
    try:
        from oios.engine.e_readiness import check_e_ready
        gates = check_e_ready(conn)
        g1 = gates["e_ready_1"]
        g2 = gates["e_ready_2"]
        g3 = gates["e_ready_3"]

        lines.append(kv("E-Ready-1 (500 closed+cause obs):",
                        f"{g1['current']} / {g1['threshold']}   "
                        f"{'PASS ✓' if g1['pass'] else 'FAIL ✗'}"))
        lines.append(kv("E-Ready-2 success (50):",
                        f"{g2['current_success']} / {g2['threshold_success']}   "
                        f"{'✓' if g2['current_success'] >= g2['threshold_success'] else '✗'}"))
        lines.append(kv("E-Ready-2 failure (50):",
                        f"{g2['current_failure']} / {g2['threshold_failure']}   "
                        f"{'✓' if g2['current_failure'] >= g2['threshold_failure'] else '✗'}"))
        if g3.get("insufficient_data"):
            lines.append(kv("E-Ready-3 (10pp gap):",
                            f"Insufficient data ({g3.get('current_n', 0)} obs)   FAIL ✗"))
        else:
            lines.append(kv("E-Ready-3 gap:",
                            f"{(g3.get('win_rate_gap', 0) * 100):.1f}pp  "
                            f"{'PASS ✓' if g3['pass'] else 'FAIL ✗'}"))

        overall = "ALL PASS ✓  E1 authorization pending explicit approval." \
            if gates["overall_pass"] else \
            f"NOT READY — {3 - gates['gates_passing']}/3 gate(s) failing."
        lines.append(f"\n  Overall: {overall}")
    except Exception as e:
        lines.append(f"  [e_readiness module not available: {e}]")

    lines.append(shadow_mode_footer("Phase E"))
    lines.append(
        "  E1 cause/propagation scores are observed and stored only.\n" +
        "  No E1 output changes live OS, RE, TTL, conviction, or any decision.\n" +
        hr()
    )
    return "\n".join(lines)
