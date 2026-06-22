"""
oios/db/repository.py
CRUD operations for Phase A0 entities.
All SQL is inline — no ORM. Phase A0 only.
"""

from __future__ import annotations
import sqlite3
import logging
from typing import Optional

from ..domain.models import (
    Opportunity,
    SignalBirth,
    OpportunitySignal,
    StateTransition,
    DecisionLogEntry,
    OIOSEvent,
    OpportunityState,
)

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _b(value: bool) -> int:
    """SQLite has no native bool — use 0/1."""
    return 1 if value else 0


def _row_to_opportunity(row: sqlite3.Row) -> Opportunity:
    d = dict(row)
    return Opportunity(
        opportunity_id       = d["opportunity_id"],
        symbol               = d["symbol"],
        direction            = d["direction"],
        sector               = d["sector"],
        created_at           = d["created_at"],
        first_signal_id      = d.get("first_signal_id"),
        regime_at_birth      = d["regime_at_birth"],
        theme_phase_at_birth = d.get("theme_phase_at_birth"),
        current_state        = d["current_state"],
        birth_ttl_days       = d["birth_ttl_days"],
        effective_ttl_days   = d["effective_ttl_days"],
        age_trading_days     = d.get("age_trading_days", 0),
        discovered_expires_at= d["discovered_expires_at"],
        conviction_score     = d.get("conviction_score", 0.0),
        confirming_count     = d.get("confirming_count", 0),
        conflicting_count    = d.get("conflicting_count", 0),
        consecutive_conflict_days = d.get("consecutive_conflict_days", 0),
        re_score             = d.get("re_score"),
        edge_consumed_pct    = d.get("edge_consumed_pct", 0.0),
        maturity_combined    = d.get("maturity_combined"),
        velocity_3d          = d.get("velocity_3d"),
        velocity_class       = d.get("velocity_class"),
        position_exists      = bool(d.get("position_exists", 0)),
        position_size_pct    = d.get("position_size_pct", 0.0),
        position_open_date   = d.get("position_open_date"),
        final_state          = d.get("final_state"),
        invalidation_reason  = d.get("invalidation_reason"),
        finalized_at         = d.get("finalized_at"),
        trade_pnl_pct        = d.get("trade_pnl_pct"),
        is_audit_trade       = bool(d.get("is_audit_trade", 0)),
        last_updated_at      = d.get("last_updated_at"),
    )


# ---------------------------------------------------------------------------
# Opportunities
# ---------------------------------------------------------------------------

def create_opportunity(conn: sqlite3.Connection, opp: Opportunity) -> None:
    conn.execute("""
        INSERT INTO opportunities (
            opportunity_id, symbol, direction, sector,
            created_at, first_signal_id, regime_at_birth, theme_phase_at_birth,
            current_state, birth_ttl_days, effective_ttl_days, age_trading_days,
            discovered_expires_at, conviction_score, confirming_count, conflicting_count,
            consecutive_conflict_days, re_score, edge_consumed_pct,
            position_exists, position_size_pct, is_audit_trade
        ) VALUES (
            ?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?
        )
    """, (
        opp.opportunity_id, opp.symbol, opp.direction, opp.sector,
        opp.created_at, opp.first_signal_id, opp.regime_at_birth, opp.theme_phase_at_birth,
        opp.current_state, opp.birth_ttl_days, opp.effective_ttl_days, opp.age_trading_days,
        opp.discovered_expires_at, opp.conviction_score, opp.confirming_count, opp.conflicting_count,
        opp.consecutive_conflict_days, opp.re_score, opp.edge_consumed_pct,
        _b(opp.position_exists), opp.position_size_pct, _b(opp.is_audit_trade),
    ))


def update_opportunity_state(conn: sqlite3.Connection, opp: Opportunity) -> None:
    """Persist all mutable fields after a state machine transition."""
    conn.execute("""
        UPDATE opportunities SET
            current_state           = ?,
            effective_ttl_days      = ?,
            age_trading_days        = ?,
            conviction_score        = ?,
            confirming_count        = ?,
            conflicting_count       = ?,
            consecutive_conflict_days = ?,
            re_score                = ?,
            edge_consumed_pct       = ?,
            maturity_combined       = ?,
            velocity_3d             = ?,
            velocity_class          = ?,
            position_exists         = ?,
            position_size_pct       = ?,
            position_open_date      = ?,
            final_state             = ?,
            invalidation_reason     = ?,
            finalized_at            = ?,
            trade_pnl_pct           = ?,
            is_audit_trade          = ?,
            last_updated_at         = ?
        WHERE opportunity_id = ?
    """, (
        opp.current_state,
        opp.effective_ttl_days,
        opp.age_trading_days,
        opp.conviction_score,
        opp.confirming_count,
        opp.conflicting_count,
        opp.consecutive_conflict_days,
        opp.re_score,
        opp.edge_consumed_pct,
        opp.maturity_combined,
        opp.velocity_3d,
        opp.velocity_class,
        _b(opp.position_exists),
        opp.position_size_pct,
        opp.position_open_date,
        opp.final_state,
        opp.invalidation_reason,
        opp.finalized_at,
        opp.trade_pnl_pct,
        _b(opp.is_audit_trade),
        opp.last_updated_at,
        opp.opportunity_id,
    ))


def get_opportunity(conn: sqlite3.Connection, opportunity_id: str) -> Optional[Opportunity]:
    row = conn.execute(
        "SELECT * FROM opportunities WHERE opportunity_id = ?", (opportunity_id,)
    ).fetchone()
    return _row_to_opportunity(row) if row else None


def find_live_opportunity(
    conn: sqlite3.Connection,
    symbol: str,
    direction: str,
) -> Optional[Opportunity]:
    """
    Return the most recent live (DISCOVERED/ACTIVE/WATCHING) opportunity for
    (symbol, direction). Used by the merge-window logic.
    """
    row = conn.execute("""
        SELECT * FROM opportunities
        WHERE symbol = ? AND direction = ?
          AND current_state IN ('DISCOVERED', 'ACTIVE', 'WATCHING')
        ORDER BY created_at DESC
        LIMIT 1
    """, (symbol, direction)).fetchone()
    return _row_to_opportunity(row) if row else None


def count_live_opportunities(
    conn: sqlite3.Connection,
    symbol: str,
    direction: str,
) -> int:
    """
    Guard: returns count of live opportunities for (symbol, direction).
    Should be 0 or 1. More than 1 indicates a merge-rule violation.
    """
    row = conn.execute("""
        SELECT COUNT(*) FROM opportunities
        WHERE symbol = ? AND direction = ?
          AND current_state IN ('DISCOVERED', 'ACTIVE', 'WATCHING')
    """, (symbol, direction)).fetchone()
    return row[0] if row else 0


# ---------------------------------------------------------------------------
# Opportunity signals (evidence junction)
# ---------------------------------------------------------------------------

def add_opportunity_signal(conn: sqlite3.Connection, os: OpportunitySignal) -> None:
    conn.execute("""
        INSERT INTO opportunity_signals
            (opportunity_id, signal_id, signal_type, signal_direction, evidence_weight, added_at)
        VALUES (?,?,?,?,?,?)
    """, (os.opportunity_id, os.signal_id, os.signal_type, os.signal_direction,
          os.evidence_weight, os.added_at))


def get_opportunity_signals(
    conn: sqlite3.Connection, opportunity_id: str
) -> list[OpportunitySignal]:
    rows = conn.execute(
        "SELECT * FROM opportunity_signals WHERE opportunity_id = ?", (opportunity_id,)
    ).fetchall()
    return [
        OpportunitySignal(
            opportunity_id=r["opportunity_id"],
            signal_id=r["signal_id"],
            signal_type=r["signal_type"],
            signal_direction=r["signal_direction"],
            evidence_weight=r["evidence_weight"],
            added_at=r["added_at"],
        )
        for r in rows
    ]


# ---------------------------------------------------------------------------
# Signal births
# ---------------------------------------------------------------------------

def create_signal_birth(conn: sqlite3.Connection, sb: SignalBirth) -> None:
    conn.execute("""
        INSERT INTO signal_births (
            signal_id, opportunity_id, symbol, archetype_id, archetype_version,
            signal_type, detected_at, birth_price, base_score, regime_at_birth,
            theme_phase_at_birth, consensus_score_at_birth,
            expected_move_pct, expected_move_pct_source,
            expected_ttl_days, expected_move_direction,
            current_state, age_trading_days, actual_move_pct, edge_consumed_pct
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        sb.signal_id, sb.opportunity_id, sb.symbol, sb.archetype_id, sb.archetype_version,
        sb.signal_type, sb.detected_at, sb.birth_price, sb.base_score, sb.regime_at_birth,
        sb.theme_phase_at_birth, sb.consensus_score_at_birth,
        sb.expected_move_pct, sb.expected_move_pct_source,
        sb.expected_ttl_days, sb.expected_move_direction,
        sb.current_state, sb.age_trading_days, sb.actual_move_pct, sb.edge_consumed_pct,
    ))


def get_signal_birth(conn: sqlite3.Connection, signal_id: str) -> Optional[SignalBirth]:
    row = conn.execute(
        "SELECT * FROM signal_births WHERE signal_id = ?", (signal_id,)
    ).fetchone()
    if not row:
        return None
    d = dict(row)
    return SignalBirth(
        signal_id               = d["signal_id"],
        opportunity_id          = d.get("opportunity_id"),
        symbol                  = d["symbol"],
        archetype_id            = d["archetype_id"],
        archetype_version       = d.get("archetype_version", 1),
        signal_type             = d["signal_type"],
        detected_at             = d["detected_at"],
        birth_price             = d["birth_price"],
        base_score              = d["base_score"],
        regime_at_birth         = d["regime_at_birth"],
        theme_phase_at_birth    = d.get("theme_phase_at_birth"),
        consensus_score_at_birth= d.get("consensus_score_at_birth"),
        expected_move_pct       = d.get("expected_move_pct", 8.0),
        expected_move_pct_source= d.get("expected_move_pct_source", "UNIVERSAL_DEFAULT_8PCT"),
        expected_ttl_days       = d["expected_ttl_days"],
        expected_move_direction = d["expected_move_direction"],
        current_state           = d.get("current_state", "ACTIVE"),
        age_trading_days        = d.get("age_trading_days", 0),
        actual_move_pct         = d.get("actual_move_pct", 0.0),
        edge_consumed_pct       = d.get("edge_consumed_pct", 0.0),
        re_score                = d.get("re_score"),
        trade_executed          = bool(d.get("trade_executed", 0)),
        invalidation_reason     = d.get("invalidation_reason"),
    )


# ---------------------------------------------------------------------------
# State transitions
# ---------------------------------------------------------------------------

def append_transition(conn: sqlite3.Connection, t: StateTransition) -> None:
    """Always INSERT — never UPDATE. Transition history is immutable."""
    conn.execute("""
        INSERT INTO signal_state_transitions (
            transition_id, signal_id, opportunity_id,
            from_state, to_state, transitioned_at, trigger_cause,
            re_at_transition, age_trading_days, regime_at_transition,
            theme_phase_at_transition, consensus_score, edge_consumed_pct
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        t.transition_id, t.signal_id, t.opportunity_id,
        t.from_state, t.to_state, t.transitioned_at, t.trigger_cause,
        t.re_at_transition, t.age_trading_days, t.regime_at_transition,
        t.theme_phase_at_transition, t.consensus_score, t.edge_consumed_pct,
    ))


def get_transitions_for_opportunity(
    conn: sqlite3.Connection, opportunity_id: str
) -> list[StateTransition]:
    rows = conn.execute("""
        SELECT * FROM signal_state_transitions
        WHERE opportunity_id = ?
        ORDER BY transitioned_at ASC
    """, (opportunity_id,)).fetchall()
    return [
        StateTransition(
            transition_id       = r["transition_id"],
            signal_id           = r["signal_id"],
            opportunity_id      = dict(r).get("opportunity_id"),
            from_state          = r["from_state"],
            to_state            = r["to_state"],
            transitioned_at     = r["transitioned_at"],
            trigger_cause       = r["trigger_cause"],
            re_at_transition    = dict(r).get("re_at_transition"),
            age_trading_days    = dict(r).get("age_trading_days"),
            regime_at_transition= dict(r).get("regime_at_transition"),
            edge_consumed_pct   = dict(r).get("edge_consumed_pct"),
        )
        for r in rows
    ]


# ---------------------------------------------------------------------------
# Decision log
# ---------------------------------------------------------------------------

def log_decision(conn: sqlite3.Connection, entry: DecisionLogEntry) -> None:
    conn.execute("""
        INSERT INTO decision_log (
            decision_id, opportunity_id, signal_id, symbol, decided_at, action,
            conviction_score, re_score, re_threshold_applied, suppression_reason,
            signal_age_trading_days, regime, theme_phase, edge_consumed_pct,
            maturity_combined, position_size_pct_at_decision, price_at_decision
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        entry.decision_id, entry.opportunity_id, entry.signal_id,
        entry.symbol, entry.decided_at, entry.action,
        entry.conviction_score, entry.re_score, entry.re_threshold_applied,
        entry.suppression_reason, entry.signal_age_trading_days,
        entry.regime, entry.theme_phase, entry.edge_consumed_pct,
        entry.maturity_combined, entry.position_size_pct_at_decision,
        entry.price_at_decision,
    ))


# ---------------------------------------------------------------------------
# OIOS events
# ---------------------------------------------------------------------------

def emit_event(conn: sqlite3.Connection, event: OIOSEvent) -> None:
    conn.execute("""
        INSERT INTO oios_events
            (event_id, event_type, opportunity_id, symbol, emitted_at, payload)
        VALUES (?,?,?,?,?,?)
    """, (event.event_id, event.event_type, event.opportunity_id,
          event.symbol, event.emitted_at, event.payload))


def get_unconsumed_events(
    conn: sqlite3.Connection, event_type: Optional[str] = None
) -> list[OIOSEvent]:
    if event_type:
        rows = conn.execute("""
            SELECT * FROM oios_events
            WHERE consumed_at IS NULL AND event_type = ?
            ORDER BY emitted_at ASC
        """, (event_type,)).fetchall()
    else:
        rows = conn.execute("""
            SELECT * FROM oios_events
            WHERE consumed_at IS NULL
            ORDER BY emitted_at ASC
        """).fetchall()
    return [
        OIOSEvent(
            event_id=r["event_id"], event_type=r["event_type"],
            opportunity_id=r.get("opportunity_id"), symbol=r["symbol"],
            emitted_at=r["emitted_at"], payload=r.get("payload"),
        )
        for r in rows
    ]
