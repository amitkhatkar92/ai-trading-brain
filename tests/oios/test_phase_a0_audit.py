"""
tests/oios/test_phase_a0_audit.py

Phase A0 Forensic Implementation Audit — tests A0-15 through A0-27.

Gate for Phase A authorization. ALL tests must pass before Phase A begins.

Audit categories:
  Cat 1 — Data Integrity         (A0-15, A0-16, A0-17)
  Cat 2 — State Machine          (A0-18, A0-19)
  Cat 3 — Event Integrity        (A0-20, A0-21)
  Cat 4 — Merge Logic            (A0-22, A0-23, A0-24)
  Cat 5 — Freeze Compliance      (A0-25)
  Cat 6 — Repository Consistency (A0-26)
  Cat 7 — Trading Calendar       (A0-27, A0-28, A0-29)
"""

import os
import sqlite3
import uuid
import pytest
from pathlib import Path

os.environ["OIOS_DB_PATH"] = ":memory:"

from oios.db.migrations import apply_phase_a0
from oios.db import repository as R
from oios.db.calendar import (
    count_trading_days,
    add_trading_days,
    is_trading_day,
    populate_trading_calendar_with_names,
)
from oios.domain.models import (
    Opportunity, SignalBirth, OpportunitySignal,
    OpportunityState, InvalidationReason, EventType,
)
from oios.domain.state_machine import (
    try_activate, try_watch, try_reactivate, try_invalidate,
    check_terminal_conditions, ACTIVE_THRESHOLD,
)
from oios.domain.opportunity_service import attach_or_create_opportunity

from .conftest import make_opportunity, make_signal


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:", detect_types=sqlite3.PARSE_DECLTYPES)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys=ON;")
    apply_phase_a0(conn=c)
    yield c
    c.close()


@pytest.fixture
def conn_with_calendar(conn):
    """
    Conn with trading_calendar seeded for June 2026.
    NSE holidays: 2026-06-01 (hypothetical) and Diwali week 2026-10-20..24
    """
    # Standard June 2026 + holiday edge cases
    with conn:
        populate_trading_calendar_with_names(
            conn,
            from_date="2026-01-01",
            to_date="2026-12-31",
            holidays={
                "2026-01-26": "REPUBLIC_DAY",
                "2026-03-25": "HOLI",
                "2026-04-10": "GOOD_FRIDAY",
                "2026-04-14": "DR_AMBEDKAR_JAYANTI",
                "2026-05-01": "MAHARASHTRA_DAY",
                "2026-08-15": "INDEPENDENCE_DAY",
                "2026-10-02": "GANDHI_JAYANTI",
                "2026-10-20": "DIWALI_EVE",
                "2026-10-21": "DIWALI",
                "2026-10-22": "DIWALI_DAY2",
                "2026-10-23": "DIWALI_DAY3",
                "2026-10-24": "DIWALI_BALIPRATIPADA",
                "2026-11-19": "GURU_NANAK_JAYANTI",
                "2026-12-25": "CHRISTMAS",
            }
        )
    yield conn


# ===========================================================================
# CAT 1 — DATA INTEGRITY
# ===========================================================================

# A0-15: Orphan signal_births row (FK must reject non-existent opportunity_id)
def test_a0_15_orphan_signal_birth_rejected(conn):
    sig = make_signal()
    sig.opportunity_id = "non-existent-opp-id"
    with pytest.raises(sqlite3.IntegrityError):
        with conn:
            R.create_signal_birth(conn, sig)


# A0-16: Orphan opportunity_signals row (FK must reject non-existent opportunity)
def test_a0_16_orphan_opportunity_signal_rejected(conn):
    # Create a valid signal first with no opportunity linkage
    opp = make_opportunity()
    sig = make_signal(opportunity_id=opp.opportunity_id)
    with conn:
        R.create_opportunity(conn, opp)
        R.create_signal_birth(conn, sig)

    # Now try linking to a non-existent opportunity
    bad_os = OpportunitySignal(
        opportunity_id="ghost-id",
        signal_id=sig.signal_id,
        signal_type="1B",
        signal_direction="CONFIRMING",
        evidence_weight=1.0,
        added_at="2026-06-01",
    )
    with pytest.raises(sqlite3.IntegrityError):
        with conn:
            R.add_opportunity_signal(conn, bad_os)


# A0-17: Delete cascade safety — deleting an opportunity with children must fail
# (FK prevents orphaning child records)
def test_a0_17_delete_opportunity_with_children_fails(conn):
    opp = make_opportunity()
    sig = make_signal(opportunity_id=opp.opportunity_id)
    with conn:
        R.create_opportunity(conn, opp)
        R.create_signal_birth(conn, sig)
        R.add_opportunity_signal(conn, OpportunitySignal(
            opportunity_id=opp.opportunity_id,
            signal_id=sig.signal_id,
            signal_type="1B",
            signal_direction="CONFIRMING",
            evidence_weight=1.0,
            added_at="2026-06-01",
        ))

    with pytest.raises(sqlite3.IntegrityError):
        with conn:
            conn.execute("DELETE FROM opportunities WHERE opportunity_id = ?",
                         (opp.opportunity_id,))


# ===========================================================================
# CAT 2 — STATE MACHINE INTEGRITY
# ===========================================================================

# A0-18: Activation/watch/reactivate raise on INVALID; check_terminal_conditions is a no-op
def test_a0_18_all_transitions_raise_on_invalid(conn):
    opp = make_opportunity(state=OpportunityState.INVALID)
    opp.final_state = "ACTIVE"

    # Modifier functions must raise
    with pytest.raises(ValueError):
        try_activate(opp)
    with pytest.raises(ValueError):
        try_watch(opp)
    with pytest.raises(ValueError):
        try_reactivate(opp)

    # check_terminal_conditions is an observation function — must silently no-op for INVALID
    # (it would cause infinite recursion if it tried to invalidate an already-INVALID opp)
    result, trans, events = check_terminal_conditions(opp, today="2026-06-20")
    assert trans == [], "check_terminal_conditions must return [] transitions for INVALID"
    assert result.current_state == OpportunityState.INVALID


# A0-19: Idempotent no-ops — ACTIVE→ACTIVE and WATCHING→WATCHING produce no transitions
def test_a0_19_idempotent_no_ops(conn):
    # try_activate on ACTIVE: no-op (already in ACTIVE, not DISCOVERED)
    opp_active = make_opportunity(
        state=OpportunityState.ACTIVE,
        conviction_score=ACTIVE_THRESHOLD + 1.0,
    )
    result, trans, events = try_activate(opp_active)
    assert result.current_state == OpportunityState.ACTIVE
    assert trans == []

    # try_reactivate on ACTIVE: no-op (already ACTIVE)
    result, trans, events = try_reactivate(opp_active)
    assert result.current_state == OpportunityState.ACTIVE
    assert trans == []

    # try_watch on WATCHING: no-op (not ACTIVE)
    opp_watching = make_opportunity(state=OpportunityState.WATCHING)
    result, trans, events = try_watch(opp_watching)
    assert result.current_state == OpportunityState.WATCHING
    assert trans == []


# ===========================================================================
# CAT 3 — EVENT INTEGRITY
# ===========================================================================

# A0-20: INVALID with position → exactly one THESIS_INVALIDATED_WITH_POSITION event
def test_a0_20_thesis_invalidated_event_exactly_once(conn):
    opp = make_opportunity(
        state=OpportunityState.ACTIVE,
        position_exists=True,
        position_size_pct=0.60,
    )
    sig = make_signal(opportunity_id=opp.opportunity_id)
    with conn:
        R.create_opportunity(conn, opp)
        R.create_signal_birth(conn, sig)

    opp, trans, events = try_invalidate(
        opp, InvalidationReason.CONTRADICTED, signal_id=sig.signal_id
    )

    thesis_events = [e for e in events if e.event_type == EventType.THESIS_INVALIDATED_WITH_POSITION]
    assert len(thesis_events) == 1, (
        f"Expected exactly 1 THESIS_INVALIDATED_WITH_POSITION, got {len(thesis_events)}"
    )


# A0-21: INVALID without position → THESIS_INVALIDATED_WITH_POSITION must NOT emit
def test_a0_21_no_thesis_event_without_position(conn):
    opp = make_opportunity(
        state=OpportunityState.ACTIVE,
        position_exists=False,
        position_size_pct=0.0,
    )
    sig = make_signal(opportunity_id=opp.opportunity_id)
    with conn:
        R.create_opportunity(conn, opp)
        R.create_signal_birth(conn, sig)

    opp, trans, events = try_invalidate(
        opp, InvalidationReason.TTL_EXHAUSTED, signal_id=sig.signal_id
    )

    thesis_events = [e for e in events if e.event_type == EventType.THESIS_INVALIDATED_WITH_POSITION]
    assert len(thesis_events) == 0, (
        "THESIS_INVALIDATED_WITH_POSITION must not emit when no position exists"
    )

    # OPPORTUNITY_INVALID must still emit
    invalid_events = [e for e in events if e.event_type == EventType.OPPORTUNITY_INVALID]
    assert len(invalid_events) == 1


# ===========================================================================
# CAT 4 — MERGE LOGIC
# ===========================================================================

# A0-22: Same symbol + direction within merge window → 1 opp, 2 evidence signals
def test_a0_22_merge_within_window_attaches(conn_with_calendar):
    conn = conn_with_calendar

    sig1 = make_signal(symbol="BEL.NS", signal_type="1B")
    with conn:
        R.create_signal_birth(conn, sig1)

    with conn:
        opp1, is_new1 = attach_or_create_opportunity(
            conn, sig1, birth_ttl_days=18, regime="BULL", today="2026-06-02"
        )
    assert is_new1 is True

    # Advance 5 days (within merge window of 18 × 0.75 = 13.5)
    opp1.age_trading_days = 5
    with conn:
        R.update_opportunity_state(conn, opp1)

    sig2 = make_signal(symbol="BEL.NS", signal_type="1A")
    with conn:
        R.create_signal_birth(conn, sig2)

    with conn:
        opp2, is_new2 = attach_or_create_opportunity(
            conn, sig2, birth_ttl_days=10, regime="BULL", today="2026-06-09"
        )

    assert is_new2 is False
    assert opp2.opportunity_id == opp1.opportunity_id

    signals = R.get_opportunity_signals(conn, opp1.opportunity_id)
    assert len(signals) == 2

    count = R.count_live_opportunities(conn, "BEL.NS", "LONG")
    assert count == 1


# A0-23: Same symbol + direction past merge window → 2 separate opportunities
def test_a0_23_merge_past_window_creates_new(conn_with_calendar):
    conn = conn_with_calendar

    sig1 = make_signal(symbol="HAL.NS", signal_type="1B")
    with conn:
        R.create_signal_birth(conn, sig1)

    with conn:
        opp1, _ = attach_or_create_opportunity(
            conn, sig1, birth_ttl_days=18, regime="BULL", today="2026-06-02"
        )

    # Age the opportunity past the merge window (18 × 0.75 = 13.5 → use 14)
    opp1.age_trading_days = 14
    with conn:
        R.update_opportunity_state(conn, opp1)

    sig2 = make_signal(symbol="HAL.NS", signal_type="1A")
    with conn:
        R.create_signal_birth(conn, sig2)

    with conn:
        opp2, is_new2 = attach_or_create_opportunity(
            conn, sig2, birth_ttl_days=10, regime="BULL", today="2026-06-24"
        )

    assert is_new2 is True
    assert opp2.opportunity_id != opp1.opportunity_id

    # Two separate live opportunities for the same symbol/direction
    count = R.count_live_opportunities(conn, "HAL.NS", "LONG")
    assert count == 2


# A0-24: Conflicting direction → CONFLICTING evidence on existing LONG + new SHORT created
def test_a0_24_conflicting_direction_attaches_as_conflicting(conn_with_calendar):
    conn = conn_with_calendar

    # Step 1: Create a LONG opportunity for BEML.NS
    sig_long = make_signal(symbol="BEML.NS", signal_type="1B")
    with conn:
        R.create_signal_birth(conn, sig_long)
    with conn:
        opp_long, _ = attach_or_create_opportunity(
            conn, sig_long, birth_ttl_days=18, regime="BULL", today="2026-06-02"
        )
    long_opp_id = opp_long.opportunity_id

    # Step 2: Create a SHORT signal for the same symbol (directly, not via factory)
    from oios.domain.models import SignalBirth
    import uuid
    sig_short = SignalBirth(
        signal_id               = str(uuid.uuid4()),
        symbol                  = "BEML.NS",
        archetype_id            = "DNA_1B_QUIET_ACC",
        signal_type             = "1A",
        detected_at             = "2026-06-03",
        birth_price             = 1320.0,
        base_score              = 6.2,
        regime_at_birth         = "BULL",
        expected_ttl_days       = 10,
        expected_move_direction = "SHORT",   # opposite direction
    )
    with conn:
        R.create_signal_birth(conn, sig_short)

    # Step 3: Call the service with the SHORT signal
    # Service should: attach CONFLICTING to the LONG opp, then create a new SHORT opp
    with conn:
        opp_short, is_new = attach_or_create_opportunity(
            conn, sig_short, birth_ttl_days=10, regime="BEAR", today="2026-06-03"
        )

    assert is_new is True, "A SHORT signal must create a new opportunity"
    assert opp_short.opportunity_id != long_opp_id, "SHORT opp must be distinct from LONG opp"
    assert opp_short.direction == "SHORT"

    # Step 4: Verify the LONG opp now has conflicting_count=1
    updated_long = R.get_opportunity(conn, long_opp_id)
    assert updated_long.conflicting_count == 1, (
        f"LONG opp must have conflicting_count=1, got {updated_long.conflicting_count}"
    )

    # Step 5: Verify CONFLICTING signal is in opportunity_signals for the LONG opp
    long_signals = R.get_opportunity_signals(conn, long_opp_id)
    directions = [s.signal_direction for s in long_signals]
    assert "CONFLICTING" in directions, (
        f"LONG opp must have a CONFLICTING signal; found: {directions}"
    )

    # Step 6: Verify the SHORT opp has 1 CONFIRMING signal
    short_signals = R.get_opportunity_signals(conn, opp_short.opportunity_id)
    short_directions = [s.signal_direction for s in short_signals]
    assert "CONFIRMING" in short_directions


# ===========================================================================
# CAT 5 — FREEZE COMPLIANCE
# ===========================================================================

# A0-25: No TODO/redesign/experimental comments in oios/ code
def test_a0_25_freeze_compliance_no_architectural_drift():
    oios_root = Path(__file__).resolve().parents[2] / "oios"
    forbidden = ["TODO redesign", "future layer", "experimental", "HACK:", "XXX:"]
    violations = []

    for py_file in oios_root.rglob("*.py"):
        text = py_file.read_text(encoding="utf-8")
        for phrase in forbidden:
            if phrase.lower() in text.lower():
                violations.append(f"{py_file.name}: contains '{phrase}'")

    assert violations == [], (
        "Architecture freeze violation — forbidden phrases found:\n" +
        "\n".join(violations)
    )


# ===========================================================================
# CAT 6 — REPOSITORY CONSISTENCY
# ===========================================================================

# A0-26: last_updated_at is set after every state transition (not NULL after update)
def test_a0_26_last_updated_at_set_after_transition(conn):
    opp = make_opportunity(conviction_score=ACTIVE_THRESHOLD + 1.0)
    sig = make_signal(opportunity_id=opp.opportunity_id)
    with conn:
        R.create_opportunity(conn, opp)
        R.create_signal_birth(conn, sig)

    # At creation last_updated_at is NULL — this is expected
    with conn:
        created = R.get_opportunity(conn, opp.opportunity_id)
    assert created.last_updated_at is None, "last_updated_at should be NULL at creation"

    # After a state transition it must be populated
    opp, trans, events = try_activate(opp, signal_id=sig.signal_id)
    with conn:
        R.update_opportunity_state(conn, opp)
        for t in trans:
            R.append_transition(conn, t)

    with conn:
        after_transition = R.get_opportunity(conn, opp.opportunity_id)
    assert after_transition.last_updated_at is not None, (
        "last_updated_at must be set after state transition"
    )
    assert after_transition.current_state == OpportunityState.ACTIVE


# ===========================================================================
# CAT 7 — TRADING CALENDAR
# ===========================================================================

# A0-27: Basic trading day counting (Mon-Fri, no holidays)
def test_a0_27_basic_trading_day_count(conn_with_calendar):
    conn = conn_with_calendar
    # 2026-06-01 is a Monday. Count Mon–Fri = 5 trading days in the week.
    count = count_trading_days(conn, from_date="2026-06-01", to_date="2026-06-05")
    assert count == 4, f"Expected 4 trading days Mon(excl)–Fri, got {count}"

    # Weekends must not count
    # Sat 2026-06-06 and Sun 2026-06-07 → add to range
    count_with_weekend = count_trading_days(conn, from_date="2026-06-01", to_date="2026-06-07")
    assert count_with_weekend == 4, "Weekend days must not count"


# A0-28: Friday → Monday holiday → Tuesday = 1 trading day
def test_a0_28_friday_to_tuesday_across_holiday(conn_with_calendar):
    """
    Scenario: Friday 2026-06-05 → next trading days are Mon 2026-06-08, Tue 2026-06-09.
    No holiday on Monday → from_date=Fri, to_date=Mon should be 1 trading day.
    Test the Friday → Monday-holiday → Tuesday scenario using Diwali week.
    2026-10-16 (Fri) → 2026-10-20 (Tue, post Diwali holidays Mon 10-19 is Sun actually)

    Use a simpler explicit test: from_date = 2026-10-19 (Mon), to_date = 2026-10-26 (Mon)
    Diwali holidays: 10-20, 10-21, 10-22, 10-23, 10-24 (Tue-Sat)
    So 10-19 (Mon) is a trading day. 10-25 (Sun) is weekend. 10-26 (Mon) is trading.
    from 10-19 (exclusive) to 10-26 = only 10-26 = 1 trading day.
    """
    conn = conn_with_calendar
    # From Mon 10-19 (exclusive) to Mon 10-26 → only Mon 10-26 is trading
    count = count_trading_days(conn, from_date="2026-10-19", to_date="2026-10-26")
    assert count == 1, f"Expected 1 trading day across Diwali week, got {count}"


# A0-29: add_trading_days correctly skips weekends and NSE holidays
def test_a0_29_add_trading_days_skips_holidays(conn_with_calendar):
    conn = conn_with_calendar

    # From 2026-10-16 (Fri), add 1 trading day = 2026-10-19 (Mon, next trading day)
    result = add_trading_days(conn, from_date="2026-10-16", n_days=1)
    assert result == "2026-10-19", f"Expected 2026-10-19, got {result}"

    # From 2026-10-19 (Mon), add 1 trading day = 2026-10-26 (Mon, after Diwali)
    result = add_trading_days(conn, from_date="2026-10-19", n_days=1)
    assert result == "2026-10-26", f"Expected 2026-10-26 (skip Diwali), got {result}"

    # From 2026-10-19 (Mon), add 3 trading days = 2026-10-26, 10-27, 10-28 → 2026-10-28
    result = add_trading_days(conn, from_date="2026-10-19", n_days=3)
    assert result == "2026-10-28", f"Expected 2026-10-28, got {result}"

    # is_trading_day on a Diwali holiday must return False
    assert is_trading_day(conn, "2026-10-21") is False
    # is_trading_day on a regular Monday must return True
    assert is_trading_day(conn, "2026-10-26") is True
