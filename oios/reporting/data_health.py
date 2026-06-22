"""
oios/reporting/data_health.py

Data Health Report — OHLCV coverage, trading calendar, event graph integrity.
Read-only SELECT queries only. No writes.
"""
from __future__ import annotations

import sqlite3

from .base import hr, section, kv, kv_warn, fmt_int, report_header, shadow_mode_footer


def generate_data_health_report(conn: sqlite3.Connection, report_date: str) -> str:
    lines: list[str] = [report_header("DATA HEALTH REPORT", report_date)]

    # ── OHLCV Coverage ────────────────────────────────────────────────────
    lines.append(section("OHLCV DATA COVERAGE"))
    missing_syms: list[str] = []
    try:
        n_today = conn.execute(
            "SELECT COUNT(DISTINCT symbol) FROM ohlcv_daily WHERE trade_date = ?",
            (report_date,)
        ).fetchone()[0]
        lines.append(kv("Symbols with OHLCV today:", fmt_int(n_today)))

        missing_rows = conn.execute("""
            SELECT DISTINCT o.symbol
            FROM opportunities o
            WHERE o.current_state IN ('ACTIVE','WATCHING','DISCOVERED')
              AND o.symbol NOT IN (
                  SELECT symbol FROM ohlcv_daily WHERE trade_date = ?
              )
            ORDER BY o.symbol
        """, (report_date,)).fetchall()
        missing_syms = [r[0] for r in missing_rows]
        lines.append(kv("Active/Watching opps missing OHLCV today:", len(missing_syms)))

        hist = conn.execute(
            "SELECT MIN(trade_date), MAX(trade_date), COUNT(DISTINCT trade_date) "
            "FROM ohlcv_daily"
        ).fetchone()
        lines.append(kv("OHLCV history (distinct trading days):", fmt_int(hist[2])))
        lines.append(kv("Date range:", f"{hist[0] or 'N/A'} to {hist[1] or 'N/A'}"))

        n_total_opps = conn.execute(
            "SELECT COUNT(DISTINCT symbol) FROM opportunities "
            "WHERE current_state IN ('ACTIVE','WATCHING','DISCOVERED')"
        ).fetchone()[0]
        lines.append(kv("Active/Watching distinct symbols tracked:", fmt_int(n_total_opps)))
    except Exception as e:
        lines.append(f"  ERROR (ohlcv): {e}")

    # ── Trading Calendar ──────────────────────────────────────────────────
    lines.append(section("TRADING CALENDAR"))
    try:
        is_trading = conn.execute(
            "SELECT COUNT(*) FROM trading_calendar "
            "WHERE trade_date = ? AND is_trading_day = 1",
            (report_date,)
        ).fetchone()[0]
        lines.append(kv("Today is a trading day:", "YES" if is_trading else "NO (Holiday / Weekend)"))

        next_td = conn.execute("""
            SELECT trade_date FROM trading_calendar
            WHERE trade_date > ? AND is_trading_day = 1
            ORDER BY trade_date LIMIT 1
        """, (report_date,)).fetchone()
        lines.append(kv("Next trading day:", next_td[0] if next_td else "N/A"))

        prev_td = conn.execute("""
            SELECT trade_date FROM trading_calendar
            WHERE trade_date < ? AND is_trading_day = 1
            ORDER BY trade_date DESC LIMIT 1
        """, (report_date,)).fetchone()
        lines.append(kv("Previous trading day:", prev_td[0] if prev_td else "N/A"))

        total_cal = conn.execute(
            "SELECT COUNT(*) FROM trading_calendar WHERE is_trading_day = 1"
        ).fetchone()[0]
        lines.append(kv("Total trading days in calendar:", fmt_int(total_cal)))
    except Exception as e:
        lines.append(f"  ERROR (calendar): {e}")

    # ── Phase E0 Event Knowledge Graph ────────────────────────────────────
    lines.append(section("EVENT KNOWLEDGE GRAPH (Phase E0)"))
    try:
        evt_rows = conn.execute("""
            SELECT event_type, COUNT(*) AS n
            FROM daily_events WHERE event_date = ?
            GROUP BY event_type ORDER BY n DESC
        """, (report_date,)).fetchall()
        total_events = sum(r[1] for r in evt_rows)
        lines.append(kv("Events ingested today:", fmt_int(total_events)))
        for row in evt_rows:
            lines.append(f"    {row[0]:<28} {row[1]}")
        if not evt_rows:
            lines.append("    (none)")

        total_all = conn.execute(
            "SELECT COUNT(*) FROM daily_events"
        ).fetchone()[0]
        lines.append(kv("Total events in database:", fmt_int(total_all)))

        n_rels = conn.execute(
            "SELECT COUNT(*) FROM company_relationships WHERE is_active = 1"
        ).fetchone()[0]
        lines.append(kv("Active company relationships:", fmt_int(n_rels)))

        n_kg = conn.execute(
            "SELECT COUNT(*) FROM knowledge_graph_metadata"
        ).fetchone()[0]
        lines.append(kv("Knowledge graph metadata entries:", fmt_int(n_kg)))

        n_links = conn.execute(
            "SELECT COUNT(*) FROM event_entity_links"
        ).fetchone()[0]
        lines.append(kv("Event-entity links (total):", fmt_int(n_links)))
    except Exception as e:
        lines.append(f"  [Phase E0 tables not available: {e}]")

    # ── Data Quality Flags ────────────────────────────────────────────────
    lines.append(section("DATA QUALITY FLAGS"))
    try:
        warnings: list[str] = []
        if missing_syms:
            warnings.append(
                f"{len(missing_syms)} active symbol(s) missing today's OHLCV: "
                f"{', '.join(missing_syms[:8])}{'...' if len(missing_syms) > 8 else ''}"
            )

        stale = conn.execute("""
            SELECT COUNT(*) FROM opportunities
            WHERE current_state = 'ACTIVE'
              AND age_trading_days > 2 * effective_ttl_days
              AND effective_ttl_days > 0
        """).fetchone()[0]
        if stale > 0:
            warnings.append(
                f"{stale} ACTIVE opportunity(ies) have age > 2× effective TTL"
            )

        expired_pending = conn.execute("""
            SELECT COUNT(*) FROM pending_adjustments
            WHERE status = 'PENDING' AND expires_at < ?
        """, (report_date,)).fetchone()[0]
        if expired_pending > 0:
            warnings.append(
                f"{expired_pending} PENDING proposal(s) are past their expiry date"
            )

        if warnings:
            for w in warnings:
                lines.append(kv_warn("WARNING:", w))
        else:
            lines.append("  No data quality issues detected.")
    except Exception as e:
        lines.append(f"  ERROR (quality): {e}")

    lines.append(shadow_mode_footer("Phase D", "Phase E"))
    return "\n".join(lines)
