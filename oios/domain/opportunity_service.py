"""
oios/domain/opportunity_service.py

Business logic layer for opportunity creation and evidence attachment.
This is the merge-window decision layer the Discovery Engine will call.

Phase A0: pure domain logic — no market data, no scoring.
Callers supply all facts; this module enforces the rules.
"""

from __future__ import annotations
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional
import sqlite3

from .models import (
    Opportunity,
    SignalBirth,
    OpportunitySignal,
    OpportunityState,
    SignalDirection,
)
from ..db import repository as R
from ..db.calendar import add_trading_days

log = logging.getLogger(__name__)

# Default evidence weights by signal type (MAS_v1.2 Section 4, Table 4)
DEFAULT_EVIDENCE_WEIGHTS: dict[str, float] = {
    "1B": 1.00,
    "3":  0.70,
    "1A": 0.80,
    "1.5": 0.60,
    "2":  0.50,
}


def _now_date() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


# ---------------------------------------------------------------------------
# Core merge-or-create logic (MAS_v1.2 Section 4, Table 3, Opportunity Creation Rule)
# ---------------------------------------------------------------------------

def attach_or_create_opportunity(
    conn: sqlite3.Connection,
    signal: SignalBirth,
    birth_ttl_days: int,
    regime: str,
    theme_phase: Optional[str] = None,
    today: Optional[str] = None,
) -> tuple[Opportunity, bool]:
    """
    Implements the MAS_v1.2 opportunity creation rule.

    Returns (opportunity, is_new) where is_new=True means a new opportunity was created.

    Rules (in priority order):
    1. Existing ACTIVE/WATCHING/DISCOVERED opportunity for same (symbol, direction)
       AND within merge window → attach signal as CONFIRMING evidence.
    2. Same (symbol, direction) but PAST merge window → create new opportunity.
    3. No live opportunity → create new opportunity.
    4. Existing ACTIVE/WATCHING in OPPOSITE direction AND within merge window
       → attach as CONFLICTING evidence to the opposite-direction opportunity.
    5. All matches INVALID → create new opportunity.
    """
    today = today or _now_date()

    move_direction = signal.expected_move_direction

    # Check same direction
    same_dir_opp = R.find_live_opportunity(conn, signal.symbol, move_direction)

    if same_dir_opp is not None:
        if same_dir_opp.within_merge_window():
            # Attach confirming evidence
            _attach_signal(conn, same_dir_opp, signal, SignalDirection.CONFIRMING)
            log.info(
                "[OpportunityService] Attached CONFIRMING signal %s to existing opp %s (%s %s)",
                signal.signal_id, same_dir_opp.opportunity_id, signal.symbol, move_direction,
            )
            return same_dir_opp, False
        else:
            # Past merge window — create fresh opportunity
            log.info(
                "[OpportunityService] %s %s past merge window (age=%d, ttl×0.75=%.1f) — creating new",
                signal.symbol, move_direction,
                same_dir_opp.age_trading_days,
                same_dir_opp.effective_ttl_days * 0.75,
            )
            return _create_new(conn, signal, birth_ttl_days, regime, theme_phase, today), True

    # Check opposite direction — attach conflicting evidence if applicable
    opposite_dir = "SHORT" if move_direction == "LONG" else "LONG"
    opposite_opp = R.find_live_opportunity(conn, signal.symbol, opposite_dir)

    if opposite_opp is not None and opposite_opp.within_merge_window():
        _attach_signal(conn, opposite_opp, signal, SignalDirection.CONFLICTING,
                       update_signal_birth_link=False)
        log.info(
            "[OpportunityService] Attached CONFLICTING signal %s to opp %s (%s %s)",
            signal.signal_id, opposite_opp.opportunity_id, signal.symbol, opposite_dir,
        )
        # Still create a new opportunity for the new direction
        return _create_new(conn, signal, birth_ttl_days, regime, theme_phase, today), True

    # No live opportunity — create new
    return _create_new(conn, signal, birth_ttl_days, regime, theme_phase, today), True


def _attach_signal(
    conn: sqlite3.Connection,
    opp: Opportunity,
    signal: SignalBirth,
    direction: str,
    update_signal_birth_link: bool = True,
) -> None:
    """Attach a signal as evidence to an existing opportunity and persist."""
    weight = DEFAULT_EVIDENCE_WEIGHTS.get(signal.signal_type, 0.5)
    os_record = OpportunitySignal(
        opportunity_id=opp.opportunity_id,
        signal_id=signal.signal_id,
        signal_type=signal.signal_type,
        signal_direction=direction,
        evidence_weight=weight,
        added_at=signal.detected_at,
    )
    R.add_opportunity_signal(conn, os_record)

    # Update signal_births with the opportunity linkage only for primary attachment.
    # CONFLICTING signals are cross-attached and must NOT overwrite the link
    # that _create_new will set for the new direction opportunity.
    if update_signal_birth_link:
        conn.execute(
            "UPDATE signal_births SET opportunity_id = ? WHERE signal_id = ?",
            (opp.opportunity_id, signal.signal_id),
        )

    if direction == SignalDirection.CONFIRMING:
        opp.confirming_count += 1
    elif direction == SignalDirection.CONFLICTING:
        opp.conflicting_count += 1
        opp.consecutive_conflict_days += 1

    R.update_opportunity_state(conn, opp)


def _create_new(
    conn: sqlite3.Connection,
    signal: SignalBirth,
    birth_ttl_days: int,
    regime: str,
    theme_phase: Optional[str],
    today: str,
) -> Opportunity:
    """Create a new opportunity from a founding signal."""
    opp_id = str(uuid.uuid4())
    weight = DEFAULT_EVIDENCE_WEIGHTS.get(signal.signal_type, 0.5)

    # discovered_expires_at = created_at + floor(birth_ttl × 0.5) trading days
    # Use calendar if available; fall back to a simple date arithmetic sentinel.
    try:
        expires_at = add_trading_days(conn, today, int(birth_ttl_days * 0.5))
    except ValueError:
        # Calendar not populated — use 999 sentinel for tests that don't need it
        from datetime import date, timedelta
        expires_at = (date.fromisoformat(today) + timedelta(days=999)).isoformat()

    opp = Opportunity(
        opportunity_id       = opp_id,
        symbol               = signal.symbol,
        direction            = signal.expected_move_direction,
        sector               = getattr(signal, "sector", "UNKNOWN"),
        created_at           = today,
        first_signal_id      = signal.signal_id,
        regime_at_birth      = regime,
        theme_phase_at_birth = theme_phase,
        birth_ttl_days       = birth_ttl_days,
        effective_ttl_days   = birth_ttl_days,
        discovered_expires_at= expires_at,
        conviction_score     = 0.0,
        confirming_count     = 1,
        conflicting_count    = 0,
    )

    R.create_opportunity(conn, opp)

    # Link signal to opportunity
    conn.execute(
        "UPDATE signal_births SET opportunity_id = ? WHERE signal_id = ?",
        (opp_id, signal.signal_id),
    )

    os_record = OpportunitySignal(
        opportunity_id  = opp_id,
        signal_id       = signal.signal_id,
        signal_type     = signal.signal_type,
        signal_direction= SignalDirection.CONFIRMING,
        evidence_weight = weight,
        added_at        = signal.detected_at,
    )
    R.add_opportunity_signal(conn, os_record)

    log.info(
        "[OpportunityService] Created new opportunity %s for %s %s",
        opp_id, signal.symbol, signal.expected_move_direction,
    )
    return opp
