"""
oios/reporting/weekly_report.py

Weekly Report — Saturday end-of-week summary covering:
  - Opportunity statistics
  - Archetype firing frequencies
  - Invalidation breakdown
  - Sector conviction summary
  - Phase D recommendation performance
  - Phase E cause/propagation performance
  - Pipeline health metrics

Covers the 7 calendar days ending on week_end_date (inclusive).
Read-only SELECT queries only. No writes.
"""
from __future__ import annotations

import sqlite3
import statistics as _st
from datetime import date, timedelta

from .base import (hr, section, kv, kv_warn, fmt, fmt_int, pct,
                   quartile_win_rate, stats_line, report_header, shadow_mode_footer)


def _week_bounds(week_end_date: str) -> tuple[str, str]:
    end = date.fromisoformat(week_end_date)
    start = end - timedelta(days=6)
    return start.isoformat(), end.isoformat()


def _trading_days_in_week(conn: sqlite3.Connection, start: str, end: str) -> list[str]:
    rows = conn.execute("""
        SELECT trade_date FROM trading_calendar
        WHERE trade_date BETWEEN ? AND ? AND is_trading_day = 1
        ORDER BY trade_date
    """, (start, end)).fetchall()
    return [r[0] for r in rows]


def generate_weekly_report(conn: sqlite3.Connection, week_end_date: str) -> str:
    week_start, week_end = _week_bounds(week_end_date)
    try:
        trading_days = _trading_days_in_week(conn, week_start, week_end)
    except Exception:
        trading_days = []

    lines: list[str] = [
        report_header(
            f"WEEKLY REPORT — Week ending {week_end_date}",
            week_end_date,
        )
    ]
    lines.append(kv("Reporting period:", f"{week_start}  to  {week_end}"))
    lines.append(kv("Trading days in period:", len(trading_days)))

    # ── Opportunity Statistics ────────────────────────────────────────────
    lines.append(section("OPPORTUNITY STATISTICS"))
    try:
        # Born this week
        born = conn.execute(
            "SELECT COUNT(*) FROM opportunities WHERE DATE(created_at) BETWEEN ? AND ?",
            (week_start, week_end)
        ).fetchone()[0]
        lines.append(kv("New opportunities born this week:", fmt_int(born)))

        # Closed this week (transitions to terminal state)
        closed_rows = conn.execute("""
            SELECT to_state, COUNT(*) AS n
            FROM signal_state_transitions
            WHERE DATE(transitioned_at) BETWEEN ? AND ?
              AND to_state IN ('ZOMBIE_CAP','TTL_EXHAUSTED','INVALID')
            GROUP BY to_state
        """, (week_start, week_end)).fetchall()
        closed_map = {r[0]: r[1] for r in closed_rows}
        total_closed = sum(closed_map.values())
        lines.append(kv("Opportunities closed this week:", fmt_int(total_closed)))
        for st in ("TTL_EXHAUSTED", "INVALID", "ZOMBIE_CAP"):
            if closed_map.get(st, 0) > 0:
                lines.append(f"    → {st:<22} {closed_map[st]}")

        win_rate = closed_map.get("TTL_EXHAUSTED", 0)
        lines.append(kv("Week win rate (TTL_EXHAUSTED / closed):",
                        f"{pct(win_rate, total_closed)}  ({win_rate}/{total_closed})"))

        # End-of-week state snapshot
        lines.append("\n  State snapshot (end of week):")
        state_rows = conn.execute("""
            SELECT current_state, COUNT(*) AS n FROM opportunities
            GROUP BY current_state ORDER BY n DESC
        """).fetchall()
        total_opps = sum(r[1] for r in state_rows)
        for r in state_rows:
            lines.append(f"    {r[0]:<22} {r[1]:>5}  ({pct(r[1], total_opps)})")
        lines.append(f"    {'TOTAL':<22} {total_opps:>5}")

        # Direction breakdown
        dir_rows = conn.execute(
            "SELECT direction, COUNT(*) FROM opportunities GROUP BY direction"
        ).fetchall()
        dir_str = "  ".join(f"{r[0]}: {r[1]}" for r in dir_rows)
        lines.append(kv("\n  Direction (all opps):", dir_str))

        # Sector breakdown
        sec_rows = conn.execute("""
            SELECT sector, COUNT(*) AS n FROM opportunities
            WHERE current_state IN ('ACTIVE','WATCHING','DISCOVERED')
            GROUP BY sector ORDER BY n DESC LIMIT 8
        """).fetchall()
        if sec_rows:
            lines.append("\n  Sector breakdown (live opps):")
            for r in sec_rows:
                lines.append(f"    {r[0]:<28} {r[1]}")
    except Exception as e:
        lines.append(f"  ERROR: {e}")

    # ── Archetype Firing Frequencies ──────────────────────────────────────
    lines.append(section("ARCHETYPE FIRING FREQUENCIES (this week)"))
    try:
        arch_rows = conn.execute("""
            SELECT sb.archetype_id,
                   COUNT(*) AS signals,
                   SUM(CASE WHEN o.opportunity_id IS NOT NULL THEN 1 ELSE 0 END) AS opps,
                   SUM(CASE WHEN sb.final_state = 'TTL_EXHAUSTED' THEN 1 ELSE 0 END) AS wins,
                   SUM(CASE WHEN sb.final_state = 'INVALID' THEN 1 ELSE 0 END) AS losses
            FROM signal_births sb
            LEFT JOIN opportunities o ON o.first_signal_id = sb.signal_id
            WHERE DATE(sb.detected_at) BETWEEN ? AND ?
            GROUP BY sb.archetype_id ORDER BY signals DESC
        """, (week_start, week_end)).fetchall()

        if arch_rows:
            hdr = f"  {'Archetype':<40} {'Signals':>7} {'Opps':>5} {'Wins':>5} {'WR':>7}"
            lines.append(hdr)
            lines.append("  " + "-" * 66)
            for r in arch_rows:
                closed = (r[3] or 0) + (r[4] or 0)
                wr_str = pct(r[3] or 0, closed) if closed else "N/A"
                lines.append(
                    f"  {r[0]:<40} {r[1]:>7} {r[2] or 0:>5} {r[3] or 0:>5} {wr_str:>7}"
                )
        else:
            lines.append("  No signal births recorded this week.")
    except Exception as e:
        lines.append(f"  ERROR: {e}")

    # ── Invalidation Breakdown ────────────────────────────────────────────
    lines.append(section("INVALIDATION BREAKDOWN (this week)"))
    try:
        inv_rows = conn.execute("""
            SELECT trigger_cause, to_state, COUNT(*) AS n
            FROM signal_state_transitions
            WHERE DATE(transitioned_at) BETWEEN ? AND ?
              AND to_state IN ('INVALID','ZOMBIE_CAP','TTL_EXHAUSTED')
            GROUP BY trigger_cause, to_state ORDER BY n DESC
        """, (week_start, week_end)).fetchall()
        total_inv = sum(r[2] for r in inv_rows)

        if inv_rows:
            hdr = f"  {'Cause':<36} {'State':<18} {'Count':>5}  {'%':>6}"
            lines.append(hdr)
            lines.append("  " + "-" * 68)
            for r in inv_rows:
                cause = r[0] or "(no trigger logged)"
                lines.append(f"  {cause:<36} {r[1]:<18} {r[2]:>5}  {pct(r[2], total_inv):>6}")
            lines.append(f"  {'TOTAL':<36} {'':>18} {total_inv:>5}")
        else:
            lines.append("  No closures recorded this week.")
    except Exception as e:
        lines.append(f"  ERROR: {e}")

    # ── Sector Conviction Summary ─────────────────────────────────────────
    lines.append(section("SECTOR CONVICTION SUMMARY (this week)"))
    try:
        sc_rows = conn.execute("""
            SELECT sector,
                   AVG(sector_conviction_score) AS avg_score,
                   SUM(stocks_with_data)        AS total_signals,
                   COUNT(*)                     AS trading_days
            FROM sector_conviction_daily
            WHERE record_date BETWEEN ? AND ?
            GROUP BY sector ORDER BY avg_score DESC
            LIMIT 15
        """, (week_start, week_end)).fetchall()

        if sc_rows:
            hdr = f"  {'Sector':<28} {'7-Day Avg':>10} {'Signals':>8} {'Days':>5}"
            lines.append(hdr)
            lines.append("  " + "-" * 56)
            for r in sc_rows:
                lines.append(
                    f"  {r[0]:<28} {fmt(r[1]):>10} {fmt_int(r[2] or 0):>8} {r[3]:>5}"
                )
        else:
            lines.append("  No sector conviction data for this week.")
    except Exception as e:
        lines.append(f"  ERROR: {e}")

    # ── Phase D Recommendation Performance ───────────────────────────────
    lines.append(section("PHASE D RECOMMENDATION PERFORMANCE (this week)"))
    try:
        new_d = conn.execute(
            "SELECT COUNT(*) FROM pending_adjustments "
            "WHERE DATE(proposed_at) BETWEEN ? AND ?",
            (week_start, week_end)
        ).fetchone()[0]
        lines.append(kv("New proposals generated this week:", fmt_int(new_d)))

        # Breakdown by type (new this week)
        dtype_rows = conn.execute("""
            SELECT adjustment_type, COUNT(*) AS n,
                   AVG(ABS(change_pct)) AS avg_change
            FROM pending_adjustments
            WHERE DATE(proposed_at) BETWEEN ? AND ?
            GROUP BY adjustment_type ORDER BY n DESC
        """, (week_start, week_end)).fetchall()
        if dtype_rows:
            for r in dtype_rows:
                avg_chg = f"{fmt(r[2], 1)}%" if r[2] is not None else "N/A"
                lines.append(f"    {r[0]:<28} {r[1]:>3} new  avg change: {avg_chg}")

        reviewed = conn.execute(
            "SELECT COUNT(*) FROM pending_adjustments "
            "WHERE status IN ('APPROVED','REJECTED') "
            "AND DATE(proposed_at) BETWEEN ? AND ?",
            (week_start, week_end)
        ).fetchone()[0]
        lines.append(kv("Proposals reviewed (approved or rejected):", fmt_int(reviewed)))

        total_pending = conn.execute(
            "SELECT COUNT(*) FROM pending_adjustments WHERE status = 'PENDING'"
        ).fetchone()[0]
        lines.append(kv("Total cumulative unreviewed PENDING:", fmt_int(total_pending)))
        lines.append("\n  [SHADOW MODE] No proposals applied. Manual review required.")
    except Exception as e:
        lines.append(f"  ERROR: {e}")

    # ── Phase E Cause/Propagation Performance ────────────────────────────
    lines.append(section("PHASE E CAUSE / PROPAGATION PERFORMANCE (this week)"))
    try:
        # Events
        evt_total = conn.execute(
            "SELECT COUNT(*) FROM daily_events WHERE event_date BETWEEN ? AND ?",
            (week_start, week_end)
        ).fetchone()[0]
        lines.append(kv("Events ingested this week:", fmt_int(evt_total)))

        # Cause cycles (proxy: distinct score_date in cause_scores)
        cycle_days = conn.execute(
            "SELECT COUNT(DISTINCT score_date) FROM cause_scores "
            "WHERE score_date BETWEEN ? AND ?",
            (week_start, week_end)
        ).fetchone()[0]
        lines.append(kv("Cause scoring days:", fmt_int(cycle_days) +
                        f"  / {len(trading_days)} trading days"))

        # Opps with cause data this week
        cs_rows = conn.execute("""
            SELECT COUNT(DISTINCT opportunity_id) AS n,
                   AVG(CASE WHEN cause_score > 0 THEN cause_score END) AS avg_pos
            FROM cause_scores WHERE score_date BETWEEN ? AND ?
        """, (week_start, week_end)).fetchone()
        lines.append(kv("Opportunities with cause scores:", fmt_int(cs_rows[0])))
        lines.append(kv("Average cause score (where > 0):", fmt(cs_rows[1])))

        # Propagation
        prop_evt = conn.execute("""
            SELECT COUNT(DISTINCT source_event_id)
            FROM propagation_paths WHERE DATE(computed_at) BETWEEN ? AND ?
        """, (week_start, week_end)).fetchone()[0]
        prop_paths = conn.execute("""
            SELECT COUNT(*) FROM propagation_paths
            WHERE DATE(computed_at) BETWEEN ? AND ?
        """, (week_start, week_end)).fetchone()[0]
        prop_opps = conn.execute("""
            SELECT COUNT(DISTINCT opportunity_id)
            FROM propagation_scores WHERE score_date BETWEEN ? AND ?
        """, (week_start, week_end)).fetchone()[0]
        lines.append(kv("\n  Events propagated:", fmt_int(prop_evt)))
        lines.append(kv("  Paths discovered:", fmt_int(prop_paths)))
        lines.append(kv("  Downstream opportunities scored:", fmt_int(prop_opps)))

        # Shadow OS delta this week
        delta_row = conn.execute("""
            SELECT AVG(shadow_os - live_os) AS avg_d,
                   MAX(shadow_os - live_os) AS max_d,
                   MIN(shadow_os - live_os) AS min_d
            FROM shadow_cause_outcomes
            WHERE outcome_date BETWEEN ? AND ?
        """, (week_start, week_end)).fetchone()
        if delta_row[0] is not None:
            lines.append(kv("\n  Shadow OS delta (avg / max / min):",
                            f"{fmt(delta_row[0])} / {fmt(delta_row[1])} / {fmt(delta_row[2])}"))

        # Predictive value (all-time closed data)
        cause_wl = conn.execute("""
            SELECT cause_score, final_state
            FROM shadow_cause_outcomes
            WHERE cause_score IS NOT NULL AND final_state IS NOT NULL AND cause_score > 0
            ORDER BY cause_score ASC
        """).fetchall()
        lines.append(f"\n  Predictive value (all-time, {len(cause_wl)} closed obs):")
        for lne in quartile_win_rate(cause_wl):
            lines.append(lne)

        lines.append("\n  [SHADOW MODE] E1 outputs not influencing live decisions.")
    except Exception as e:
        lines.append(f"  ERROR: {e}")

    # ── Pipeline Health Metrics ───────────────────────────────────────────
    lines.append(section("PIPELINE HEALTH METRICS"))
    try:
        # OHLCV completeness
        active_syms = conn.execute(
            "SELECT COUNT(DISTINCT symbol) FROM opportunities "
            "WHERE current_state IN ('ACTIVE','WATCHING','DISCOVERED')"
        ).fetchone()[0]
        covered_syms = conn.execute(
            "SELECT COUNT(DISTINCT symbol) FROM ohlcv_daily "
            "WHERE trade_date = ?", (week_end,)
        ).fetchone()[0]
        lines.append(kv("OHLCV completeness (end of week):",
                        f"{pct(covered_syms, active_syms)}  ({covered_syms}/{active_syms} symbols)"))

        # Events per trading day
        if trading_days and evt_total is not None:
            epd = evt_total / len(trading_days) if trading_days else 0
            lines.append(kv("Events per trading day (avg):", fmt(epd, 1)))

        # Cause cycle completion rate
        if trading_days:
            lines.append(kv("Cause scoring coverage:",
                            f"{cycle_days}/{len(trading_days)} trading days  "
                            f"({pct(cycle_days, len(trading_days))})"))

        # Shadow scoring days
        shadow_days = conn.execute(
            "SELECT COUNT(DISTINCT outcome_date) FROM shadow_cause_outcomes "
            "WHERE outcome_date BETWEEN ? AND ?",
            (week_start, week_end)
        ).fetchone()[0]
        if trading_days:
            lines.append(kv("Shadow scoring coverage:",
                            f"{shadow_days}/{len(trading_days)} trading days  "
                            f"({pct(shadow_days, len(trading_days))})"))

        # RE snapshot coverage
        snap_days = conn.execute(
            "SELECT COUNT(DISTINCT snapshot_date) FROM opportunity_re_snapshots "
            "WHERE snapshot_date BETWEEN ? AND ?",
            (week_start, week_end)
        ).fetchone()[0]
        if trading_days:
            lines.append(kv("RE snapshot coverage:",
                            f"{snap_days}/{len(trading_days)} trading days  "
                            f"({pct(snap_days, len(trading_days))})"))

        # DB record counts
        total_opps_db = conn.execute("SELECT COUNT(*) FROM opportunities").fetchone()[0]
        total_sbs_db = conn.execute("SELECT COUNT(*) FROM signal_births").fetchone()[0]
        total_trans_db = conn.execute(
            "SELECT COUNT(*) FROM signal_state_transitions"
        ).fetchone()[0]
        lines.append(kv("\n  signal_births (total):", fmt_int(total_sbs_db)))
        lines.append(kv("  opportunities (total):", fmt_int(total_opps_db)))
        lines.append(kv("  signal_state_transitions (total):", fmt_int(total_trans_db)))
        lines.append(kv("  opportunity_re_snapshots (total):",
                        fmt_int(conn.execute(
                            "SELECT COUNT(*) FROM opportunity_re_snapshots"
                        ).fetchone()[0])))
        lines.append(kv("  shadow_cause_outcomes (total):",
                        fmt_int(conn.execute(
                            "SELECT COUNT(*) FROM shadow_cause_outcomes"
                        ).fetchone()[0])))
    except Exception as e:
        lines.append(f"  ERROR: {e}")

    lines.append(shadow_mode_footer("Phase D", "Phase E"))
    lines.append("\n" + hr("="))
    lines.append(f"  END OF WEEKLY REPORT — {week_end_date}")
    lines.append(hr("="))
    return "\n".join(lines)
