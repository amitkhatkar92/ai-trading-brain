"""
oios/reporting/readiness_gates.py

Readiness Gate Summary — comprehensive gate status for Phase D and Phase E.
Reports current status, trends, and issues. Never auto-authorizes anything.
Read-only. No writes.
"""
from __future__ import annotations

import sqlite3
from datetime import date

from .base import hr, section, kv, kv_warn, fmt, fmt_int, pct, report_header


def generate_readiness_gate_summary(conn: sqlite3.Connection, report_date: str) -> str:
    lines: list[str] = [report_header("READINESS GATE SUMMARY", report_date)]

    # ── Phase D Readiness ─────────────────────────────────────────────────
    lines.append(section("PHASE D READINESS"))
    try:
        from oios.engine.shadow_mode import (
            SHADOW_MODE, MIN_OBS_FOR_PROPOSAL, TTL_FLOORS,
            MAX_TTL_CHANGE_PCT, MAX_WEIGHT_CHANGE_PCT, MAX_HL_CHANGE_PCT,
        )
        lines.append(kv("Shadow mode active:", "YES (SHADOW_MODE = True)" if SHADOW_MODE else
                        "*** NO — SHADOW MODE IS OFF ***"))
        lines.append(kv("Min observations for any proposal:", MIN_OBS_FOR_PROPOSAL))
        lines.append(kv("TTL floors (1A / 1B / 1.5 days):",
                        f"{TTL_FLOORS.get('1A')} / {TTL_FLOORS.get('1B')} / {TTL_FLOORS.get('1.5')}"))
        lines.append(kv("Max TTL / HL change per cycle:",
                        f"±{MAX_TTL_CHANGE_PCT * 100:.0f}% / ±{MAX_HL_CHANGE_PCT * 100:.0f}%"))
        lines.append(kv("Max weight change per cycle:",
                        f"±{MAX_WEIGHT_CHANGE_PCT * 100:.0f}%"))
    except Exception as e:
        lines.append(f"  [shadow_mode module not available: {e}]")
        SHADOW_MODE = True  # assume shadow

    try:
        # Quarter start (current quarter)
        today = date.fromisoformat(report_date)
        qm = ((today.month - 1) // 3) * 3 + 1
        quarter_start = date(today.year, qm, 1).isoformat()

        pa_quarter = conn.execute(
            "SELECT COUNT(*) FROM pending_adjustments WHERE proposed_at >= ?",
            (quarter_start,)
        ).fetchone()[0]
        pa_pending = conn.execute(
            "SELECT COUNT(*) FROM pending_adjustments WHERE status = 'PENDING'"
        ).fetchone()[0]
        pa_approved = conn.execute(
            "SELECT COUNT(*) FROM pending_adjustments WHERE status = 'APPROVED'"
        ).fetchone()[0]
        pa_rejected = conn.execute(
            "SELECT COUNT(*) FROM pending_adjustments WHERE status = 'REJECTED'"
        ).fetchone()[0]
        pa_approval_needed = conn.execute(
            "SELECT COUNT(*) FROM pending_adjustments "
            "WHERE status = 'PENDING' AND requires_approval = 1"
        ).fetchone()[0]

        lines.append(kv("\n  Proposals this quarter:", fmt_int(pa_quarter)))
        lines.append(kv("  PENDING (unreviewed):", fmt_int(pa_pending)))
        lines.append(kv("  APPROVED:", fmt_int(pa_approved)))
        lines.append(kv("  REJECTED:", fmt_int(pa_rejected)))
        lines.append(kv("  Requiring explicit approval:", fmt_int(pa_approval_needed)))

        # D-Ready: No formal gate thresholds defined — summarize qualitatively
        lines.append("\n  D-READY STATUS:")
        lines.append("    No quantitative D-Ready gates are currently defined.")
        lines.append("    Pending proposals accumulate until manually reviewed.")
        lines.append("    SHADOW_MODE = True enforces no auto-application.")
        lines.append("    To authorize any proposal: change status to APPROVED in")
        lines.append("    pending_adjustments after manual review (out-of-band).")

        # Warn about expired proposals
        expired = conn.execute(
            "SELECT COUNT(*) FROM pending_adjustments "
            "WHERE status = 'PENDING' AND expires_at < ?",
            (report_date,)
        ).fetchone()[0]
        if expired > 0:
            lines.append(kv_warn("  Expired PENDING proposals:", expired))
    except Exception as e:
        lines.append(f"  ERROR: {e}")

    # ── Phase E Readiness ─────────────────────────────────────────────────
    lines.append(section("PHASE E READINESS"))
    try:
        from oios.engine.e_readiness import (
            check_e_ready_1, check_e_ready_2, check_e_ready_3,
            check_e_ready,
            E_READY_1_MIN_OBSERVATIONS, E_READY_2_MIN_SUCCESS,
            E_READY_2_MIN_FAILURE, E_READY_3_WIN_RATE_GAP,
        )

        g1 = check_e_ready_1(conn)
        g2 = check_e_ready_2(conn)
        g3 = check_e_ready_3(conn)
        summary = check_e_ready(conn)

        # E-Ready-1
        p1 = g1["current"]
        t1 = g1["threshold"]
        pct1 = 100 * p1 / t1 if t1 else 0
        lines.append(f"\n  E-Ready-1: {p1} / {t1}  ({pct1:.1f}% complete)")
        lines.append(f"    {'PASS ✓' if g1['pass'] else 'FAIL ✗'}  — 500 closed observations with cause data + final outcome")

        # E-Ready-2
        s2 = g2["current_success"]
        f2 = g2["current_failure"]
        lines.append(f"\n  E-Ready-2:")
        lines.append(f"    Success (TTL_EXHAUSTED, cause_score > 0): {s2} / {E_READY_2_MIN_SUCCESS}  "
                     f"{'✓' if s2 >= E_READY_2_MIN_SUCCESS else '✗'}")
        lines.append(f"    Failure (INVALID, cause_score > 0):       {f2} / {E_READY_2_MIN_FAILURE}  "
                     f"{'✓' if f2 >= E_READY_2_MIN_FAILURE else '✗'}")
        lines.append(f"    {'PASS ✓' if g2['pass'] else 'FAIL ✗'}")

        # E-Ready-3
        lines.append(f"\n  E-Ready-3: Top-Q cause win rate > Bottom-Q by ≥ 10pp")
        if g3.get("insufficient_data"):
            lines.append(f"    FAIL ✗  — Insufficient data ({g3.get('current_n', 0)} closed, need ≥ 40)")
        else:
            gap = g3.get("win_rate_gap", 0)
            twr = g3.get("top_quartile_wr", 0)
            bwr = g3.get("bottom_quartile_wr", 0)
            lines.append(f"    Top-Q win rate:    {pct(twr, 1)}")
            lines.append(f"    Bottom-Q win rate: {pct(bwr, 1)}")
            lines.append(f"    Gap: {gap * 100:.1f}pp  (need ≥ {E_READY_3_WIN_RATE_GAP * 100:.0f}pp)")
            lines.append(f"    {'PASS ✓' if g3['pass'] else 'FAIL ✗'}")

        # Overall
        lines.append(f"\n  OVERALL E-READY: {'PASS ✓' if summary['overall_pass'] else 'FAIL ✗'}")
        lines.append(f"  Gates passing: {summary['gates_passing']}/3")
        lines.append(f"  {summary['message']}")

        # Trend: if all gates pass, gate transition alert
        if summary["overall_pass"]:
            lines.append("\n  *** GATE TRANSITION ALERT ***")
            lines.append("  All three E-Ready gates are currently PASSING.")
            lines.append("  E1 authorization is NOT automatic.")
            lines.append("  A deliberate, manual approval is required before E1")
            lines.append("  outputs can influence any live parameter.")
            lines.append("  Review shadow_cause_outcomes and pending_adjustments")
            lines.append("  before any authorization decision.")
    except Exception as e:
        lines.append(f"  [e_readiness module not available: {e}]")

    # ── Authorization Policy ───────────────────────────────────────────────
    lines.append(section("AUTHORIZATION POLICY"))
    lines.append("  Any readiness gate transition is REPORTED here, never auto-authorized.")
    lines.append("  Phase D proposals: require manual review of pending_adjustments.")
    lines.append("  Phase E activation: requires all three E-Ready gates to pass,")
    lines.append("    plus explicit human review of shadow_cause_outcomes and")
    lines.append("    deliberate change of SHADOW_MODE = False in shadow_mode.py.")
    lines.append("  No automated process may change SHADOW_MODE.")
    lines.append(f"\n  Checked at: {report_date}")

    lines.append("\n" + hr())
    return "\n".join(lines)
