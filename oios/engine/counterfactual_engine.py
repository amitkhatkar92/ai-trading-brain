"""
oios/engine/counterfactual_engine.py

Layer 4 Sub-B: Counterfactual Engine — four standard queries.
Phase D, Shadow Mode.

CF-1: TTL Sensitivity
    "Would outcomes improve if TTL × 1.25?"
    Finds TTL_EXHAUSTED opportunities where the stock peaked AFTER the TTL expired.

CF-2: RE Threshold Sensitivity
    "What happened to PASS_RE_LOW decisions?"
    Only uses CLEAN counterfactual records (no subsequent-opp contamination).

CF-3: Theme Phase Override
    "What happened to PASS_THEME_SUPPRESSED decisions?"
    Only uses CLEAN counterfactual records.

CF-4: Hold Duration Sensitivity
    "Would 20% longer or shorter holds improve returns?"
    Compares median days_to_peak to effective_ttl_days across completed lifecycles.

Nightly retroactive job:
    populate_outcome_prices()      — fills price_5d/10d/20d_later, max_adverse/favorable
    classify_counterfactual_types() — labels each PASS record as CLEAN / SAME_OPP_RECOVERED
                                      / NEW_OPP_SUCCEEDED / NEW_OPP_FAILED / AMBIGUOUS

Shadow mode discipline:
    This module only writes to decision_log (retroactive price fields).
    It does NOT write to pending_adjustments or any Phase C table.
"""

from __future__ import annotations
import logging
import sqlite3
from typing import Optional

log = logging.getLogger(__name__)

# Counterfactual type labels
CF_CLEAN             = "CLEAN"
CF_SAME_OPP_RECOVERED = "SAME_OPP_RECOVERED"
CF_NEW_OPP_SUCCEEDED  = "NEW_OPP_SUCCEEDED"
CF_NEW_OPP_FAILED     = "NEW_OPP_FAILED"
CF_AMBIGUOUS          = "AMBIGUOUS"

# How many trading days constitute "new opportunity window" for classification
_NEW_OPP_WINDOW_DAYS = 20

# Success threshold: 5-day move > this fraction of expected_move is a "winner"
_SUCCESS_MOVE_THRESHOLD = 0.0   # any positive move counts

# TTL sensitivity: if > this fraction of TTL_EXHAUSTED opps peaked after TTL → extension warranted
_TTL_EXTENSION_TRIGGER = 0.30


# ---------------------------------------------------------------------------
# Trading-day helpers
# ---------------------------------------------------------------------------

def _nth_trading_day_after(
    conn: sqlite3.Connection,
    from_date: str,
    n: int,
) -> Optional[str]:
    """Return the date of the Nth trading day AFTER from_date (1-indexed)."""
    row = conn.execute("""
        SELECT calendar_date FROM trading_calendar
        WHERE is_trading_day = 1 AND calendar_date > ?
        ORDER BY calendar_date
        LIMIT 1 OFFSET ?
    """, (from_date, n - 1)).fetchone()
    return row[0] if row else None


def _close_price(
    conn: sqlite3.Connection,
    symbol: str,
    trade_date: str,
) -> Optional[float]:
    row = conn.execute(
        "SELECT close FROM ohlcv_daily WHERE symbol = ? AND trade_date = ?",
        (symbol, trade_date)
    ).fetchone()
    return row[0] if row else None


def _max_min_price_window(
    conn: sqlite3.Connection,
    symbol: str,
    from_date: str,
    to_date: str,
) -> tuple[Optional[float], Optional[float]]:
    """Return (max_close, min_close) over a date range."""
    row = conn.execute("""
        SELECT MAX(close), MIN(close) FROM ohlcv_daily
        WHERE symbol = ? AND trade_date > ? AND trade_date <= ?
    """, (symbol, from_date, to_date)).fetchone()
    return (row[0], row[1]) if row else (None, None)


# ---------------------------------------------------------------------------
# Nightly retroactive job
# ---------------------------------------------------------------------------

def populate_outcome_prices(
    conn: sqlite3.Connection,
    today: str,
    max_batch: int = 500,
) -> int:
    """
    Fill price_5d_later, price_10d_later, price_20d_later, max_adverse_20d,
    max_favorable_20d for decision_log records where they are NULL and
    at least 20 trading days have elapsed since the decision.

    Returns the number of records updated.
    """
    # Find the date 20 trading days before today — only records before this are eligible
    cutoff_row = conn.execute("""
        SELECT calendar_date FROM trading_calendar
        WHERE is_trading_day = 1 AND calendar_date < ?
        ORDER BY calendar_date DESC
        LIMIT 1 OFFSET 19
    """, (today,)).fetchone()
    if not cutoff_row:
        return 0
    cutoff = cutoff_row[0]

    records = conn.execute("""
        SELECT decision_id, symbol, decided_at, price_at_decision
        FROM decision_log
        WHERE price_5d_later IS NULL
          AND DATE(decided_at) <= ?
        ORDER BY decided_at
        LIMIT ?
    """, (cutoff, max_batch)).fetchall()

    updated = 0
    for rec in records:
        dec_date = rec["decided_at"][:10]  # ISO date portion
        symbol   = rec["symbol"]

        d5  = _nth_trading_day_after(conn, dec_date, 5)
        d10 = _nth_trading_day_after(conn, dec_date, 10)
        d20 = _nth_trading_day_after(conn, dec_date, 20)

        p5  = _close_price(conn, symbol, d5)  if d5  else None
        p10 = _close_price(conn, symbol, d10) if d10 else None
        p20 = _close_price(conn, symbol, d20) if d20 else None

        if d20:
            max_close, min_close = _max_min_price_window(conn, symbol, dec_date, d20)
            ref = rec["price_at_decision"]
            max_fav = (max_close - ref) / ref * 100 if max_close and ref else None
            max_adv = (min_close - ref) / ref * 100 if min_close and ref else None
        else:
            max_fav = max_adv = None

        if any(v is not None for v in (p5, p10, p20)):
            conn.execute("""
                UPDATE decision_log
                SET price_5d_later   = ?,
                    price_10d_later  = ?,
                    price_20d_later  = ?,
                    max_favorable_20d = ?,
                    max_adverse_20d  = ?,
                    outcome_populated_at = datetime('now')
                WHERE decision_id = ?
            """, (p5, p10, p20, max_fav, max_adv, rec["decision_id"]))
            updated += 1

    if updated:
        log.info("[Counterfactual] Populated outcome prices for %d decision_log records", updated)
    return updated


def classify_counterfactual_types(
    conn: sqlite3.Connection,
    today: str,
) -> int:
    """
    Classify counterfactual_type for PASS decision_log records where it is NULL
    and outcome prices are already populated.

    Classification:
        CLEAN             — no subsequent opportunity on same symbol within 20 trading days
        SAME_OPP_RECOVERED — this opportunity later transitioned to ACTIVE
        NEW_OPP_SUCCEEDED  — a new opportunity on same symbol succeeded
        NEW_OPP_FAILED     — a new opportunity on same symbol also failed
        AMBIGUOUS          — multiple subsequent opportunities

    Returns number of records classified.
    """
    pass_records = conn.execute("""
        SELECT d.decision_id, d.opportunity_id, d.symbol,
               d.decided_at, d.price_5d_later, d.price_at_decision
        FROM decision_log d
        WHERE d.action LIKE 'PASS%'
          AND d.counterfactual_type IS NULL
          AND d.price_20d_later IS NOT NULL
        ORDER BY d.decided_at
    """).fetchall()

    classified = 0
    for rec in pass_records:
        cf_type = _classify_one(conn, rec, today)
        conn.execute("""
            UPDATE decision_log
            SET counterfactual_type = ?
            WHERE decision_id = ?
        """, (cf_type, rec["decision_id"]))
        classified += 1

    if classified:
        log.info("[Counterfactual] Classified %d PASS records", classified)
    return classified


def _classify_one(
    conn: sqlite3.Connection,
    rec: sqlite3.Row,
    today: str,
) -> str:
    """Classify one PASS record into a counterfactual type."""
    dec_date = rec["decided_at"][:10]
    window_end = _nth_trading_day_after(conn, dec_date, _NEW_OPP_WINDOW_DAYS)
    if window_end is None:
        window_end = today

    # Did this same opportunity later recover to ACTIVE?
    recovered = conn.execute("""
        SELECT COUNT(*) FROM signal_state_transitions
        WHERE opportunity_id = ?
          AND from_state = 'WATCHING'
          AND to_state   = 'ACTIVE'
          AND transitioned_at > ?
          AND transitioned_at <= ?
    """, (rec["opportunity_id"], dec_date, window_end)).fetchone()[0]
    if recovered > 0:
        return CF_SAME_OPP_RECOVERED

    # New opportunities on same symbol within window
    new_opps = conn.execute("""
        SELECT opportunity_id, current_state, final_state, invalidation_reason
        FROM opportunities
        WHERE symbol = ?
          AND opportunity_id != ?
          AND created_at > ?
          AND created_at <= ?
    """, (rec["symbol"], rec["opportunity_id"], dec_date, window_end)).fetchall()

    if not new_opps:
        return CF_CLEAN

    if len(new_opps) > 1:
        return CF_AMBIGUOUS

    opp = new_opps[0]
    # "Succeeded" = reached ACTIVE or produced positive trade_pnl_pct
    if opp["current_state"] == "ACTIVE" or (
        opp["final_state"] in ("ACTIVE", "WATCHING") and
        opp["invalidation_reason"] not in ("TTL_EXHAUSTED", "NEVER_MATURED")
    ):
        return CF_NEW_OPP_SUCCEEDED

    return CF_NEW_OPP_FAILED


# ---------------------------------------------------------------------------
# CF-1: TTL Sensitivity
# ---------------------------------------------------------------------------

def run_cf1_ttl_sensitivity(conn: sqlite3.Connection) -> dict:
    """
    CF-1: TTL Sensitivity — would outcomes improve if TTL × 1.25?

    Finds completed signal_births (final_state IS NOT NULL, invalidation_reason
    = TTL_EXHAUSTED in the linked opportunity) where the stock peaked AFTER the TTL
    expired (days_to_peak > expected_ttl_days).

    Returns a diagnostic dict.
    """
    rows = conn.execute("""
        SELECT sb.signal_id, sb.archetype_id, sb.expected_ttl_days,
               sb.days_to_peak, sb.peak_move_pct, sb.expected_move_pct,
               sb.regime_at_birth
        FROM signal_births sb
        WHERE sb.final_state IS NOT NULL
          AND sb.days_to_peak IS NOT NULL
    """).fetchall()

    if not rows:
        return {
            "sample_count": 0, "continued_moving_count": 0,
            "continued_moving_pct": 0.0, "avg_peak_delay_days": 0.0,
            "ttl_extension_would_help": False, "recommended_multiplier": 1.0,
            "by_archetype": {},
        }

    ttl_expired = [r for r in rows if r["days_to_peak"] is not None
                   and r["days_to_peak"] > (r["expected_ttl_days"] or 0)]

    total = len(rows)
    continued = len(ttl_expired)
    continued_pct = continued / total if total else 0.0
    avg_delay = (
        sum(r["days_to_peak"] - (r["expected_ttl_days"] or 0) for r in ttl_expired)
        / continued if continued else 0.0
    )

    # Per-archetype breakdown
    by_arch: dict[str, dict] = {}
    for r in rows:
        aid = r["archetype_id"]
        if aid not in by_arch:
            by_arch[aid] = {"total": 0, "late_peak": 0}
        by_arch[aid]["total"] += 1
        if r["days_to_peak"] is not None and r["days_to_peak"] > (r["expected_ttl_days"] or 0):
            by_arch[aid]["late_peak"] += 1

    extension_helps = continued_pct >= _TTL_EXTENSION_TRIGGER
    # Recommend a conservative 1.15 unless very strong evidence (>50%)
    rec_mult = 1.15 if continued_pct < 0.50 else 1.25

    return {
        "sample_count":            total,
        "continued_moving_count":  continued,
        "continued_moving_pct":    round(continued_pct, 4),
        "avg_peak_delay_days":     round(avg_delay, 1),
        "ttl_extension_would_help": extension_helps,
        "recommended_multiplier":  rec_mult if extension_helps else 1.0,
        "by_archetype":            by_arch,
    }


# ---------------------------------------------------------------------------
# CF-2: RE Threshold Sensitivity
# ---------------------------------------------------------------------------

def run_cf2_re_threshold_sensitivity(conn: sqlite3.Connection) -> dict:
    """
    CF-2: RE Threshold Sensitivity — what happened to PASS_RE_LOW decisions?
    Uses only CLEAN counterfactual records.
    """
    from ..domain.state_machine import RE_THRESHOLD

    rows = conn.execute("""
        SELECT d.decision_id, d.re_score, d.price_at_decision,
               d.price_5d_later, d.price_10d_later
        FROM decision_log d
        WHERE d.action = 'PASS_RE_LOW'
          AND d.counterfactual_type = 'CLEAN'
          AND d.price_5d_later IS NOT NULL
    """).fetchall()

    if not rows:
        return {
            "sample_count": 0, "success_count": 0, "success_rate": 0.0,
            "avg_5d_move_pct": 0.0, "median_re_at_decision": None,
            "current_threshold": RE_THRESHOLD, "suggested_threshold": None,
        }

    success_count  = 0
    moves          = []
    re_scores      = []

    for r in rows:
        ref   = r["price_at_decision"]
        p5    = r["price_5d_later"]
        if ref and p5:
            move = (p5 - ref) / ref * 100
            moves.append(move)
            if move > _SUCCESS_MOVE_THRESHOLD:
                success_count += 1
        if r["re_score"] is not None:
            re_scores.append(r["re_score"])

    n = len(rows)
    avg_5d = sum(moves) / len(moves) if moves else 0.0
    success_rate = success_count / n if n else 0.0
    median_re = sorted(re_scores)[len(re_scores) // 2] if re_scores else None

    # If > 55% of PASS_RE_LOW would have succeeded, suggest lowering threshold
    suggested = None
    if success_rate > 0.55 and median_re is not None:
        suggested = round(median_re * 0.85, 2)   # 15% reduction

    return {
        "sample_count":        n,
        "success_count":       success_count,
        "success_rate":        round(success_rate, 4),
        "avg_5d_move_pct":     round(avg_5d, 4),
        "median_re_at_decision": round(median_re, 3) if median_re else None,
        "current_threshold":   RE_THRESHOLD,
        "suggested_threshold": suggested,
    }


# ---------------------------------------------------------------------------
# CF-3: Theme Phase Override
# ---------------------------------------------------------------------------

def run_cf3_theme_phase_override(conn: sqlite3.Connection) -> dict:
    """
    CF-3: Theme Phase Override — what happened to PASS_THEME_SUPPRESSED decisions?
    Uses only CLEAN counterfactual records.
    """
    rows = conn.execute("""
        SELECT d.decision_id, d.theme_phase, d.price_at_decision, d.price_5d_later
        FROM decision_log d
        WHERE d.action = 'PASS_THEME_SUPPRESSED'
          AND d.counterfactual_type = 'CLEAN'
          AND d.price_5d_later IS NOT NULL
    """).fetchall()

    if not rows:
        return {
            "sample_count": 0, "success_count": 0, "success_rate": 0.0,
            "avg_5d_move_pct": 0.0, "by_theme_phase": {},
            "suppression_appears_correct": True,
        }

    success_count = 0
    moves         = []
    by_phase: dict[str, dict] = {}

    for r in rows:
        ref = r["price_at_decision"]
        p5  = r["price_5d_later"]
        phase = r["theme_phase"] or "UNKNOWN"
        if ref and p5:
            move = (p5 - ref) / ref * 100
            moves.append(move)
            won = move > _SUCCESS_MOVE_THRESHOLD
            if won:
                success_count += 1
            if phase not in by_phase:
                by_phase[phase] = {"total": 0, "success": 0}
            by_phase[phase]["total"] += 1
            if won:
                by_phase[phase]["success"] += 1

    n = len(rows)
    avg_5d = sum(moves) / len(moves) if moves else 0.0
    success_rate = success_count / n if n else 0.0

    return {
        "sample_count":               n,
        "success_count":              success_count,
        "success_rate":               round(success_rate, 4),
        "avg_5d_move_pct":            round(avg_5d, 4),
        "by_theme_phase":             by_phase,
        "suppression_appears_correct": success_rate <= 0.45,
    }


# ---------------------------------------------------------------------------
# CF-4: Hold Duration Sensitivity
# ---------------------------------------------------------------------------

def run_cf4_hold_duration_sensitivity(conn: sqlite3.Connection) -> dict:
    """
    CF-4: Hold Duration Sensitivity — would 20% longer or shorter holds improve returns?

    Compares days_to_peak vs effective_ttl_days for completed opportunities.
    TTL utilization = days_to_peak / effective_ttl_days.

    If median utilization < 0.50 → TTL may be too long (extend holds wasted).
    If median utilization > 0.85 → TTL may be too short (peaks cut off).
    """
    rows = conn.execute("""
        SELECT sb.archetype_id, sb.expected_ttl_days, sb.days_to_peak,
               sb.peak_move_pct, sb.expected_move_pct
        FROM signal_births sb
        WHERE sb.final_state IS NOT NULL
          AND sb.days_to_peak IS NOT NULL
          AND sb.expected_ttl_days IS NOT NULL
          AND sb.expected_ttl_days > 0
    """).fetchall()

    if not rows:
        return {
            "sample_count": 0, "median_ttl_utilization": None,
            "pct_utilization_under50": 0.0, "pct_utilization_over85": 0.0,
            "recommendation": "INSUFFICIENT_DATA", "by_archetype": {},
        }

    utilizations = [
        (r["days_to_peak"] or 0) / r["expected_ttl_days"]
        for r in rows
    ]
    sorted_u = sorted(utilizations)
    n = len(sorted_u)
    median_u = sorted_u[n // 2]

    under50 = sum(1 for u in sorted_u if u < 0.50) / n
    over85  = sum(1 for u in sorted_u if u > 0.85) / n

    if median_u < 0.50:
        recommendation = "SHORTEN_TTL_20PCT"
    elif median_u > 0.85:
        recommendation = "EXTEND_TTL_20PCT"
    else:
        recommendation = "TTL_WELL_CALIBRATED"

    # Per-archetype
    by_arch: dict[str, dict] = {}
    for r, u in zip(rows, utilizations):
        aid = r["archetype_id"]
        if aid not in by_arch:
            by_arch[aid] = {"utils": [], "count": 0}
        by_arch[aid]["utils"].append(u)
        by_arch[aid]["count"] += 1
    for aid in by_arch:
        us = sorted(by_arch[aid]["utils"])
        by_arch[aid]["median_utilization"] = us[len(us) // 2]
        del by_arch[aid]["utils"]

    return {
        "sample_count":            n,
        "median_ttl_utilization":  round(median_u, 4),
        "pct_utilization_under50": round(under50, 4),
        "pct_utilization_over85":  round(over85, 4),
        "recommendation":          recommendation,
        "by_archetype":            by_arch,
    }


# ---------------------------------------------------------------------------
# Combined entry points
# ---------------------------------------------------------------------------

def run_all_counterfactuals(conn: sqlite3.Connection) -> dict:
    """Run all four CF analyses and return consolidated report."""
    return {
        "cf1_ttl_sensitivity":       run_cf1_ttl_sensitivity(conn),
        "cf2_re_threshold":          run_cf2_re_threshold_sensitivity(conn),
        "cf3_theme_phase_override":  run_cf3_theme_phase_override(conn),
        "cf4_hold_duration":         run_cf4_hold_duration_sensitivity(conn),
    }


def run_nightly_retroactive_job(conn: sqlite3.Connection, today: str) -> dict:
    """
    Full nightly retroactive pipeline:
        1. populate_outcome_prices()
        2. classify_counterfactual_types()

    Returns summary dict.
    """
    n_prices = populate_outcome_prices(conn, today)
    n_classified = classify_counterfactual_types(conn, today)
    return {
        "prices_populated":   n_prices,
        "types_classified":   n_classified,
        "date":               today,
    }
