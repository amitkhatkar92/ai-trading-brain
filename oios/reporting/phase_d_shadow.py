"""
oios/reporting/phase_d_shadow.py

Phase D Shadow Report — RE snapshots, velocity, pending adjustments,
archetype outcome distributions, transition probability cache.

Shadow mode: reads pending_adjustments and Phase D tables.
No writes. No parameter applications.
"""
from __future__ import annotations

import sqlite3
from datetime import date, timedelta

from .base import (hr, section, kv, kv_warn, fmt, fmt_int, pct,
                   report_header, shadow_mode_footer)

_VELOCITY_CLASSES = [
    "THESIS_WORKING", "REGIME_PRESSURE", "CROWDING", "MECHANICAL_DECAY"
]
_ADJ_TYPES = ["TTL_CHANGE", "HALF_LIFE_CHANGE", "WEIGHT_CHANGE", "ARCHETYPE_RETIRE"]


def generate_phase_d_shadow_report(conn: sqlite3.Connection, report_date: str) -> str:
    lines: list[str] = [report_header("PHASE D SHADOW REPORT", report_date)]

    # ── RE Snapshot Recording ─────────────────────────────────────────────
    lines.append(section("RE SNAPSHOT RECORDING"))
    try:
        snap_today = conn.execute(
            "SELECT COUNT(*) FROM opportunity_re_snapshots WHERE snapshot_date = ?",
            (report_date,)
        ).fetchone()[0]
        lines.append(kv("Snapshots recorded today:", fmt_int(snap_today)))

        snap_total = conn.execute(
            "SELECT COUNT(*) FROM opportunity_re_snapshots"
        ).fetchone()[0]
        lines.append(kv("Total snapshots in database:", fmt_int(snap_total)))

        # Active/Watching opps that didn't get a snapshot today
        missing_snaps = conn.execute("""
            SELECT COUNT(*) FROM opportunities
            WHERE current_state IN ('ACTIVE','WATCHING')
              AND opportunity_id NOT IN (
                  SELECT opportunity_id FROM opportunity_re_snapshots
                  WHERE snapshot_date = ?
              )
        """, (report_date,)).fetchone()[0]
        if missing_snaps > 0:
            lines.append(kv_warn("Active/Watching opps missing today's snapshot:", missing_snaps))
        else:
            lines.append(kv("Active/Watching opps missing today's snapshot:", 0))

        # Daily state snapshot
        ds_row = conn.execute("""
            SELECT SUM(opp_count) FROM opportunity_daily_state_snapshot
            WHERE snapshot_date = ?
        """, (report_date,)).fetchone()
        ds_total = ds_row[0] or 0
        lines.append(kv("Daily state snapshot total opps recorded:", fmt_int(ds_total)))
    except Exception as e:
        lines.append(f"  [Phase D snapshot tables not available: {e}]")

    # ── Velocity Distribution ─────────────────────────────────────────────
    lines.append(section("VELOCITY DISTRIBUTION (ACTIVE opportunities)"))
    try:
        vel_rows = conn.execute("""
            SELECT velocity_class, COUNT(*) AS n
            FROM opportunities
            WHERE current_state = 'ACTIVE' AND velocity_class IS NOT NULL
            GROUP BY velocity_class ORDER BY n DESC
        """).fetchall()
        vel_map = {r[0]: r[1] for r in vel_rows}
        total_vel = sum(vel_map.values())
        unclassified = conn.execute(
            "SELECT COUNT(*) FROM opportunities "
            "WHERE current_state = 'ACTIVE' AND velocity_class IS NULL"
        ).fetchone()[0]

        for vc in _VELOCITY_CLASSES:
            n = vel_map.get(vc, 0)
            lines.append(kv(f"  {vc}:", f"{n:>4}  ({pct(n, total_vel + unclassified)})"))
        lines.append(kv("  Not yet classified:", f"{unclassified:>4}"))

        # Average velocity magnitude
        v3d_vals = conn.execute(
            "SELECT velocity_3d FROM opportunities "
            "WHERE current_state = 'ACTIVE' AND velocity_3d IS NOT NULL"
        ).fetchall()
        if v3d_vals:
            vals = [r[0] for r in v3d_vals]
            import statistics as _st
            mean_v = _st.mean(vals)
            lines.append(kv("  Mean velocity_3d (ACTIVE):", fmt(mean_v, 3)))
    except Exception as e:
        lines.append(f"  [velocity columns not available: {e}]")

    # ── Pending Adjustments ───────────────────────────────────────────────
    lines.append(section("PENDING ADJUSTMENTS (status = PENDING)"))
    try:
        pa_rows = conn.execute("""
            SELECT adjustment_type, COUNT(*) AS n
            FROM pending_adjustments WHERE status = 'PENDING'
            GROUP BY adjustment_type ORDER BY n DESC
        """).fetchall()
        total_pa = sum(r[1] for r in pa_rows)
        lines.append(kv("Total unreviewed proposals:", fmt_int(total_pa)))
        for r in pa_rows:
            lines.append(f"    {r[0]:<32} {r[1]:>4}")
        if not pa_rows:
            lines.append("    (none)")

        new_today = conn.execute(
            "SELECT COUNT(*) FROM pending_adjustments WHERE DATE(proposed_at) = ?",
            (report_date,)
        ).fetchone()[0]
        lines.append(kv("New proposals today:", fmt_int(new_today)))

        needs_approval = conn.execute(
            "SELECT COUNT(*) FROM pending_adjustments "
            "WHERE status = 'PENDING' AND requires_approval = 1"
        ).fetchone()[0]
        lines.append(kv("Proposals requiring explicit approval:", fmt_int(needs_approval)))

        oldest = conn.execute(
            "SELECT MIN(proposed_at) FROM pending_adjustments WHERE status = 'PENDING'"
        ).fetchone()[0]
        if oldest:
            try:
                from datetime import date as _date
                d = _date.fromisoformat(oldest[:10])
                age_days = (date.fromisoformat(report_date) - d).days
                lines.append(kv("Oldest unreviewed proposal:", f"{oldest[:10]}  ({age_days} days old)"))
            except Exception:
                lines.append(kv("Oldest unreviewed proposal:", oldest[:10]))

        # Proposals by archetype
        arch_rows = conn.execute("""
            SELECT archetype_id, COUNT(*) AS n
            FROM pending_adjustments WHERE status = 'PENDING'
            GROUP BY archetype_id ORDER BY n DESC LIMIT 8
        """).fetchall()
        if arch_rows:
            lines.append("\n  By archetype (top 8):")
            for r in arch_rows:
                lines.append(f"    {r[0]:<40} {r[1]:>3}")
    except Exception as e:
        lines.append(f"  ERROR: {e}")

    # ── Archetype Outcome Distributions ───────────────────────────────────
    lines.append(section("ARCHETYPE OUTCOME DISTRIBUTIONS"))
    try:
        aod_total = conn.execute(
            "SELECT COUNT(*) FROM archetype_outcome_distributions"
        ).fetchone()[0]
        lines.append(kv("Distribution records computed:", fmt_int(aod_total)))

        aod_active = conn.execute(
            "SELECT COUNT(*) FROM archetype_outcome_distributions "
            "WHERE is_distribution_active = 1"
        ).fetchone()[0]
        if aod_active > 0:
            lines.append(kv_warn("Active distributions (non-zero in shadow mode!):", aod_active))
        else:
            lines.append(kv("Active distributions (shadow mode enforced = 0):", 0))

        aod_pairs = conn.execute(
            "SELECT COUNT(DISTINCT archetype_id || '|' || regime) "
            "FROM archetype_outcome_distributions"
        ).fetchone()[0]
        lines.append(kv("Distinct archetype/regime pairs computed:", fmt_int(aod_pairs)))

        latest_aod = conn.execute(
            "SELECT MAX(computed_at) FROM archetype_outcome_distributions"
        ).fetchone()[0]
        lines.append(kv("Most recent computation:", latest_aod[:10] if latest_aod else "N/A"))
    except Exception as e:
        lines.append(f"  [archetype_outcome_distributions not available: {e}]")

    # ── Transition Probability Cache ──────────────────────────────────────
    lines.append(section("TRANSITION PROBABILITY CACHE"))
    try:
        cache_row = conn.execute(
            "SELECT COUNT(*), MAX(computed_at) FROM transition_probability_cache"
        ).fetchone()
        lines.append(kv("Cache entries:", fmt_int(cache_row[0])))
        lines.append(kv("Most recent refresh:",
                        cache_row[1][:10] if cache_row[1] else "N/A"))

        empirical = conn.execute(
            "SELECT COUNT(*) FROM transition_probability_cache WHERE is_empirical = 1"
        ).fetchone()[0]
        prior_only = (cache_row[0] or 0) - empirical
        lines.append(kv("Entries using empirical data:", fmt_int(empirical)))
        lines.append(kv("Entries using priors only:", fmt_int(prior_only)))
    except Exception as e:
        lines.append(f"  [transition_probability_cache not available: {e}]")

    lines.append(shadow_mode_footer("Phase D"))
    lines.append(
        "  All proposals remain PENDING. No D output modifies thresholds or parameters.\n" +
        hr()
    )
    return "\n".join(lines)
