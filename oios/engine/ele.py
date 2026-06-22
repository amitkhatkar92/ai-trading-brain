"""
oios/engine/ele.py

Sub-D: Edge Lifecycle Engine — Daily Orchestrator
Layer 5 — ELE

The ELE is the daily entry point that advances every live opportunity
through one cycle of the Phase C lifecycle:

    1. Update effective_ttl via regime-adjusted multiplier
    2. Compute actual_move_pct and edge_consumed_pct
    3. Compute crowding proxy (C_crowding)
    4. Compute RE score
    5. Compute maturity_combined
    6. Run state machine transitions (terminal → WATCHING/ACTIVE cycling)
    7. Compute conviction score from RE-weighted confirming/conflicting signals
    8. Evaluate ACTIVE / WATCHING / INVALID classification
    9. Write all updates to DB via repository

Phase C constraints:
    - NO adaptive parameter changes (Layer 6 is Phase D)
    - NO archetype_outcome_distributions writes
    - NO pending_adjustments writes
    - 5% audit paper-trade override computed (PHASE_C_ACCEPTANCE C4) but
      decision routing is via decision_log only (no actual execution in Phase C)

Shadow validation:
    All RE scores, maturity stages, and conviction scores are persisted
    daily. After 60–90 trading days, these are compared to the replay
    baseline in REPLAY_FINDINGS_v1.md before Phase D begins.

CRITICAL: This module does NOT write directly to DB tables.
All writes go through oios.db.repository. This maintains the invariant
established in Phase A: ELE → Repository → Database.
"""

from __future__ import annotations
import hashlib
import logging
import sqlite3
from dataclasses import dataclass
from typing import Optional

from ..db import repository as R
from ..domain.models import OpportunityState, InvalidationReason, TriggerCause
from ..domain.state_machine import (
    try_activate,
    try_watch,
    try_reactivate,
    try_invalidate,
    expire_discovered,
    check_terminal_conditions,
    RE_THRESHOLD,
    ACTIVE_THRESHOLD,
    TTL_WATCHABLE_FRACTION,
)
from .re_calculator import (
    compute_re,
    compute_ec_path,
    compute_actual_move_pct,
    compute_crowding,
    compute_effective_ttl,
    get_half_life,
)
from .maturity_engine import compute_maturity

# ---------------------------------------------------------------------------
# Phase D instrumentation — graceful degradation when Phase D tables absent
# ---------------------------------------------------------------------------
# The velocity engine writes to opportunity_re_snapshots and
# opportunity_daily_state_snapshot which are Phase D schema additions.
# When those tables don't exist (Phase C-only DBs), calls are silently skipped.
try:
    from .velocity_engine import (
        record_re_snapshot as _record_re_snapshot,
        update_velocity as _update_velocity,
        record_daily_state_snapshot as _record_daily_state_snapshot,
    )
    _PHASE_D_VELOCITY = True
except ImportError:
    _PHASE_D_VELOCITY = False


def _phase_d_record_snapshot(
    conn: sqlite3.Connection,
    opportunity_id: str,
    today: str,
    re_score: Optional[float],
    ec_path: float,
    c_crowding: float,
    regime: str,
    age: int,
) -> None:
    """Write daily RE snapshot — silently skipped if Phase D tables absent."""
    if not _PHASE_D_VELOCITY:
        return
    try:
        _record_re_snapshot(conn, opportunity_id, today, re_score, ec_path, c_crowding, regime, age)
    except sqlite3.OperationalError:
        pass  # Phase D tables not yet created


def _phase_d_update_velocity(
    conn: sqlite3.Connection,
    opportunity_id: str,
    today: str,
    base_score: float,
    signal_type: str,
) -> None:
    """Compute and store velocity — silently skipped if Phase D tables absent."""
    if not _PHASE_D_VELOCITY:
        return
    try:
        _update_velocity(conn, opportunity_id, today, base_score, signal_type)
    except sqlite3.OperationalError:
        pass  # Phase D tables not yet created

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Audit paper-trade override (C4)
# ---------------------------------------------------------------------------

# 5% of INVALID signals are routed to paper trading for audit purposes.
# Selection criterion: hash(signal_id) % 20 == 0
_AUDIT_MODULUS = 20


def _is_audit_trade(signal_id: str) -> bool:
    """Return True for ~5% of signal_ids selected by hash."""
    h = int(hashlib.sha256(signal_id.encode()).hexdigest(), 16)
    return (h % _AUDIT_MODULUS) == 0


# ---------------------------------------------------------------------------
# ELE cycle result (per opportunity)
# ---------------------------------------------------------------------------

@dataclass
class ELECycleResult:
    opportunity_id: str
    symbol:         str
    re_score:       Optional[float]
    ec_path:        float
    maturity:       str
    conviction:     float
    new_state:      str
    state_changed:  bool
    audit_trade:    bool     = False


# ---------------------------------------------------------------------------
# Conviction score (RE-weighted)
# ---------------------------------------------------------------------------

def _compute_conviction_re_weighted(
    conn: sqlite3.Connection,
    opportunity_id: str,
    as_of_date: str,
    regime: str,
) -> float:
    """
    Compute conviction as weighted sum of confirming RE minus conflicting RE.

    MAS v1.2 Section 5:
        conviction = Σ(w_i × RE_i for confirming) − Σ(w_j × RE_j for conflicting)

    For Phase C, each signal's RE is computed individually and weighted by
    its evidence_weight from opportunity_signals.

    Falls back to the Phase B proxy (confirming_count × 2.5) when no OHLCV
    data is available to compute RE per signal.
    """
    signals = conn.execute("""
        SELECT os.signal_id, os.signal_direction, os.evidence_weight,
               sb.base_score, sb.signal_type, sb.birth_price,
               sb.expected_move_pct, sb.expected_move_direction,
               sb.detected_at
        FROM opportunity_signals os
        JOIN signal_births sb ON sb.signal_id = os.signal_id
        WHERE os.opportunity_id = ?
    """, (opportunity_id,)).fetchall()

    if not signals:
        return 0.0

    symbol_row = conn.execute(
        "SELECT symbol, age_trading_days FROM opportunities WHERE opportunity_id = ?",
        (opportunity_id,)
    ).fetchone()
    if not symbol_row:
        return 0.0

    symbol        = symbol_row["symbol"]
    direction_row = conn.execute(
        "SELECT direction FROM opportunities WHERE opportunity_id = ?",
        (opportunity_id,)
    ).fetchone()
    direction = direction_row["direction"] if direction_row else "LONG"

    confirming_re  = 0.0
    conflicting_re = 0.0

    for sig in signals:
        # Age of this specific signal (not opportunity age)
        sig_detected = sig["detected_at"]
        sig_age = conn.execute("""
            SELECT COUNT(*) FROM trading_calendar
            WHERE is_trading_day = 1
              AND calendar_date > ?
              AND calendar_date <= ?
        """, (sig_detected, as_of_date)).fetchone()
        signal_age_days = sig_age[0] if sig_age else 0

        actual_move = compute_actual_move_pct(
            conn, symbol, sig["expected_move_direction"], sig["birth_price"], as_of_date
        )
        c_crowd = compute_crowding(conn, symbol, as_of_date)

        re_i = compute_re(
            base_score        = sig["base_score"],
            age_trading_days  = signal_age_days,
            signal_type       = sig["signal_type"],
            regime            = regime,
            actual_move_pct   = actual_move,
            expected_move_pct = sig["expected_move_pct"] or 8.0,
            c_crowding        = c_crowd,
        )
        weight = sig["evidence_weight"] or 1.0

        if sig["signal_direction"] == "CONFIRMING":
            confirming_re += weight * re_i
        else:
            conflicting_re += weight * re_i

    conviction = confirming_re - conflicting_re
    return max(0.0, min(10.0, conviction))


# ---------------------------------------------------------------------------
# Single-opportunity ELE cycle
# ---------------------------------------------------------------------------

def run_ele_cycle_for_opportunity(
    conn: sqlite3.Connection,
    opportunity_id: str,
    today: str,
    regime: str,
) -> Optional[ELECycleResult]:
    """
    Run one full ELE cycle for a single opportunity.

    Returns an ELECycleResult (even if no state change occurred) or None
    if the opportunity cannot be found.

    All DB writes go through repository calls.
    """
    opp = R.get_opportunity(conn, opportunity_id)
    if opp is None:
        return None

    # Already terminal — no work to do
    if opp.current_state == OpportunityState.INVALID:
        return ELECycleResult(
            opportunity_id = opportunity_id,
            symbol         = opp.symbol,
            re_score       = None,
            ec_path        = opp.edge_consumed_pct or 0.0,
            maturity       = opp.maturity_combined or "SEED",
            conviction     = opp.conviction_score or 0.0,
            new_state      = OpportunityState.INVALID,
            state_changed  = False,
        )

    # ── Step 1: Update effective_ttl ──────────────────────────────────────
    new_effective_ttl = compute_effective_ttl(opp.birth_ttl_days, opp.signal_type if hasattr(opp, 'signal_type') else "1A", regime)
    if opp.first_signal_id:
        sb = conn.execute(
            "SELECT signal_type FROM signal_births WHERE signal_id = ?",
            (opp.first_signal_id,)
        ).fetchone()
        if sb:
            new_effective_ttl = compute_effective_ttl(opp.birth_ttl_days, sb["signal_type"], regime)
    opp.effective_ttl_days = new_effective_ttl

    # ── Step 2: Actual move and EC_path ────────────────────────────────────
    sb_row = conn.execute("""
        SELECT base_score, signal_type, birth_price,
               expected_move_pct, expected_move_direction
        FROM signal_births WHERE signal_id = ?
    """, (opp.first_signal_id,)).fetchone() if opp.first_signal_id else None

    birth_price        = sb_row["birth_price"]        if sb_row else 0.0
    expected_move_pct  = (sb_row["expected_move_pct"] or 8.0) if sb_row else 8.0
    signal_type        = sb_row["signal_type"]        if sb_row else "1A"
    base_score         = sb_row["base_score"]         if sb_row else 4.0
    birth_direction    = sb_row["expected_move_direction"] if sb_row else opp.direction

    actual_move = compute_actual_move_pct(conn, opp.symbol, birth_direction, birth_price, today)
    ec_path     = compute_ec_path(actual_move, expected_move_pct)
    opp.edge_consumed_pct = ec_path

    # ── Step 3: Crowding ───────────────────────────────────────────────────
    c_crowding = compute_crowding(conn, opp.symbol, today)

    # ── Step 4: RE score ──────────────────────────────────────────────────
    re_score = compute_re(
        base_score        = base_score,
        age_trading_days  = opp.age_trading_days,
        signal_type       = signal_type,
        regime            = regime,
        actual_move_pct   = actual_move,
        expected_move_pct = expected_move_pct,
        c_crowding        = c_crowding,
    )
    opp.re_score = re_score

    # ── Phase D: daily RE snapshot + velocity (graceful if tables absent) ─
    _phase_d_record_snapshot(
        conn, opportunity_id, today, re_score, ec_path, c_crowding,
        regime, opp.age_trading_days
    )
    _phase_d_update_velocity(conn, opportunity_id, today, base_score, signal_type)

    # ── Step 5: Maturity ──────────────────────────────────────────────────
    maturity = compute_maturity(
        age_trading_days  = opp.age_trading_days,
        effective_ttl_days = opp.effective_ttl_days,
        ec_path           = ec_path,
        confirming_count  = opp.confirming_count,
    )
    opp.maturity_combined = maturity

    # ── Step 6: Conviction (RE-weighted) ──────────────────────────────────
    conviction = _compute_conviction_re_weighted(conn, opportunity_id, today, regime)
    opp.conviction_score = conviction

    # Persist updated fields before state transitions
    R.update_opportunity_state(conn, opp)

    original_state = opp.current_state
    # Use the founding signal as the attributed signal_id for ELE-driven transitions.
    # This satisfies the signal_births FK on signal_state_transitions because
    # ELE transitions are attributed to the founding signal of the opportunity.
    sig_id = opp.first_signal_id or "SYSTEM"

    # ── Step 7: State machine transitions ─────────────────────────────────

    # DISCOVERED: expiry check then activation attempt
    if opp.current_state == OpportunityState.DISCOVERED:
        opp, transitions, _ = expire_discovered(opp, today, signal_id=sig_id)
        for t in transitions:
            R.append_transition(conn, t)
        if opp.current_state == OpportunityState.INVALID:
            R.update_opportunity_state(conn, opp)
            _maybe_log_audit_trade(conn, opp, today)
            return ELECycleResult(
                opportunity_id = opportunity_id,
                symbol         = opp.symbol,
                re_score       = re_score,
                ec_path        = ec_path,
                maturity       = maturity,
                conviction     = conviction,
                new_state      = OpportunityState.INVALID,
                state_changed  = True,
            )

        opp, transitions, _ = try_activate(opp, signal_id=sig_id, regime=regime)
        for t in transitions:
            R.append_transition(conn, t)
        R.update_opportunity_state(conn, opp)

    # ACTIVE / WATCHING: terminal conditions first
    elif opp.current_state in (OpportunityState.ACTIVE, OpportunityState.WATCHING):
        opp, transitions, _ = check_terminal_conditions(opp, today, signal_id=sig_id, regime=regime)
        for t in transitions:
            R.append_transition(conn, t)
        if opp.current_state == OpportunityState.INVALID:
            R.update_opportunity_state(conn, opp)
            _maybe_log_audit_trade(conn, opp, today)
            return ELECycleResult(
                opportunity_id = opportunity_id,
                symbol         = opp.symbol,
                re_score       = re_score,
                ec_path        = ec_path,
                maturity       = maturity,
                conviction     = conviction,
                new_state      = OpportunityState.INVALID,
                state_changed  = True,
            )

        # RE-based ACTIVE → WATCHING when RE drops below threshold
        if opp.current_state == OpportunityState.ACTIVE and re_score < RE_THRESHOLD:
            opp, transitions, _ = try_watch(
                opp,
                signal_id     = sig_id,
                re_score      = re_score,
                trigger_cause = TriggerCause.TIME_DECAY,
                regime        = regime,
            )
            for t in transitions:
                R.append_transition(conn, t)

        # RE-based WATCHING → ACTIVE when RE recovers
        elif opp.current_state == OpportunityState.WATCHING and re_score >= RE_THRESHOLD:
            opp, transitions, _ = try_reactivate(opp, signal_id=sig_id, regime=regime)
            for t in transitions:
                R.append_transition(conn, t)

        R.update_opportunity_state(conn, opp)

    state_changed = opp.current_state != original_state

    # ── Step 8: Audit paper-trade override (5% of INVALID) ────────────────
    audit_trade = False
    if opp.current_state == OpportunityState.INVALID and opp.first_signal_id:
        audit_trade = _is_audit_trade(opp.first_signal_id)
        if audit_trade:
            conn.execute(
                "UPDATE opportunities SET is_audit_trade = 1 WHERE opportunity_id = ?",
                (opportunity_id,)
            )
            log.info("[ELE] Audit trade flagged: %s (%s) reason=%s",
                     opp.symbol, opportunity_id, opp.invalidation_reason)

    return ELECycleResult(
        opportunity_id = opportunity_id,
        symbol         = opp.symbol,
        re_score       = re_score,
        ec_path        = ec_path,
        maturity       = maturity,
        conviction     = conviction,
        new_state      = opp.current_state,
        state_changed  = state_changed,
        audit_trade    = audit_trade,
    )


def _maybe_log_audit_trade(
    conn: sqlite3.Connection,
    opp,
    today: str,
) -> None:
    """Flag the opportunity as an audit trade if selected (5% override)."""
    if opp.first_signal_id and _is_audit_trade(opp.first_signal_id):
        conn.execute(
            "UPDATE opportunities SET is_audit_trade = 1 WHERE opportunity_id = ?",
            (opp.opportunity_id,)
        )


# ---------------------------------------------------------------------------
# Full daily ELE run (all live opportunities)
# ---------------------------------------------------------------------------

@dataclass
class ELEDailyResult:
    date:             str
    regime:           str
    opps_processed:   int      = 0
    opps_activated:   int      = 0
    opps_watching:    int      = 0
    opps_recovered:   int      = 0
    opps_invalidated: int      = 0
    opps_audit:       int      = 0


def run_ele_daily(
    conn: sqlite3.Connection,
    today: str,
    regime: str,
) -> ELEDailyResult:
    """
    Run the full ELE cycle for every live opportunity.

    Called once per trading day, after scanners and sector conviction have run.

    Does NOT advance age_trading_days — that is the caller's responsibility
    (or the history loader's). The ELE reads the current age from the DB.

    Returns an ELEDailyResult summary for logging and diagnostics.
    """
    live_ids = [
        r[0] for r in conn.execute("""
            SELECT opportunity_id FROM opportunities
            WHERE current_state IN ('DISCOVERED', 'ACTIVE', 'WATCHING')
        """).fetchall()
    ]

    result = ELEDailyResult(date=today, regime=regime)

    for opp_id in live_ids:
        try:
            with conn:
                cycle = run_ele_cycle_for_opportunity(conn, opp_id, today, regime)
        except Exception as exc:
            log.warning("[ELE] Cycle failed for %s: %s", opp_id, exc)
            continue

        if cycle is None:
            continue

        result.opps_processed += 1

        if cycle.state_changed:
            if cycle.new_state == OpportunityState.ACTIVE:
                # Could be DISCOVERED→ACTIVE or WATCHING→ACTIVE
                result.opps_activated += 1
            elif cycle.new_state == OpportunityState.WATCHING:
                result.opps_watching += 1
            elif cycle.new_state == OpportunityState.INVALID:
                result.opps_invalidated += 1

        if cycle.audit_trade:
            result.opps_audit += 1

    # ── Phase D: daily state distribution snapshot ─────────────────────────
    if _PHASE_D_VELOCITY:
        try:
            _record_daily_state_snapshot(conn, today)
        except sqlite3.OperationalError:
            pass  # Phase D tables not yet created

    log.info(
        "[ELE] %s regime=%-12s  processed=%d  activated=%d  watching=%d  "
        "invalidated=%d  audit=%d",
        today, regime,
        result.opps_processed,
        result.opps_activated,
        result.opps_watching,
        result.opps_invalidated,
        result.opps_audit,
    )
    return result
