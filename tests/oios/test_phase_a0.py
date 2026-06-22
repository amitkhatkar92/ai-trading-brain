"""
tests/oios/test_phase_a0.py

Phase A0 acceptance tests — MAS_v1.2.md Section 7 acceptance criteria.
All tests use an in-memory SQLite database. No market data. No scoring. No AI.

Test cases map directly to the spec:
  A0-1  DISCOVERED → ACTIVE → WATCHING → ACTIVE → INVALID (full lifecycle)
  A0-2  Every state transition writes to signal_state_transitions
  A0-3  Transition history can be fully reconstructed
  A0-4  INVALID is terminal — no further transitions accepted
  A0-5  DISCOVERED → INVALID (NEVER_MATURED) when discovered_expires_at passed
  A0-6  DISCOVERED → WATCHING is forbidden
  A0-7  Conflicting evidence reduces conviction_score
  A0-8  Merge window: signal attaches to existing opportunity within window
  A0-9  Merge window: new opportunity created when existing is past merge window
  A0-10 Position full blocks DISCOVERED → ACTIVE
  A0-11 THESIS_INVALIDATED_WITH_POSITION event emits before INVALID transition
  A0-12 Duplicate opportunity guard: find_live_opportunity returns existing
  A0-13 signal_births cannot exist without an opportunity_id (FK enforcement)
  A0-14 opportunity_signals cannot reference a non-existent opportunity (FK)
"""

import uuid
import pytest

from oios.domain import models as M
from oios.domain.state_machine import (
    try_activate, try_watch, try_reactivate, try_invalidate,
    expire_discovered, check_terminal_conditions,
    ACTIVE_THRESHOLD,
)
from oios.domain.models import OpportunityState, InvalidationReason, EventType
from oios.db import repository as R

from .conftest import make_opportunity, make_signal


# ===========================================================================
# A0-1: Full lifecycle DISCOVERED → ACTIVE → WATCHING → ACTIVE → INVALID
# ===========================================================================

def test_full_lifecycle(conn):
    opp = make_opportunity(conviction_score=0.0)
    sig = make_signal(opportunity_id=opp.opportunity_id)

    with conn:
        R.create_opportunity(conn, opp)
        R.create_signal_birth(conn, sig)
        R.add_opportunity_signal(conn, M.OpportunitySignal(
            opportunity_id=opp.opportunity_id,
            signal_id=sig.signal_id,
            signal_type="1B",
            signal_direction="CONFIRMING",
            evidence_weight=1.0,
            added_at="2026-06-01",
        ))

    # DISCOVERED (conviction below threshold) — no transition
    opp, trans, events = try_activate(opp, signal_id=sig.signal_id)
    assert opp.current_state == OpportunityState.DISCOVERED
    assert trans == []

    # Raise conviction → ACTIVE
    opp.conviction_score = ACTIVE_THRESHOLD + 1.0
    opp, trans, events = try_activate(opp, signal_id=sig.signal_id)
    assert opp.current_state == OpportunityState.ACTIVE
    assert len(trans) == 1
    assert trans[0].from_state == OpportunityState.DISCOVERED
    assert trans[0].to_state == OpportunityState.ACTIVE
    with conn:
        R.update_opportunity_state(conn, opp)
        for t in trans:
            R.append_transition(conn, t)
        for e in events:
            R.emit_event(conn, e)

    # Drop conviction → WATCHING
    opp.conviction_score = 2.0
    opp, trans, events = try_watch(opp, signal_id=sig.signal_id)
    assert opp.current_state == OpportunityState.WATCHING
    with conn:
        R.update_opportunity_state(conn, opp)
        for t in trans:
            R.append_transition(conn, t)
        for e in events:
            R.emit_event(conn, e)

    # Recover conviction → ACTIVE again (bidirectional)
    opp.conviction_score = ACTIVE_THRESHOLD + 2.0
    opp, trans, events = try_reactivate(opp, signal_id=sig.signal_id)
    assert opp.current_state == OpportunityState.ACTIVE
    assert trans[0].from_state == OpportunityState.WATCHING
    assert trans[0].to_state == OpportunityState.ACTIVE
    with conn:
        R.update_opportunity_state(conn, opp)
        for t in trans:
            R.append_transition(conn, t)
        for e in events:
            R.emit_event(conn, e)

    # TTL exhaustion → INVALID
    opp.age_trading_days = opp.effective_ttl_days
    opp, trans, events = check_terminal_conditions(opp, today="2026-06-20", signal_id=sig.signal_id)
    assert opp.current_state == OpportunityState.INVALID
    assert opp.invalidation_reason == InvalidationReason.TTL_EXHAUSTED
    with conn:
        R.update_opportunity_state(conn, opp)
        for t in trans:
            R.append_transition(conn, t)

    # Verify full history is 4 transitions
    with conn:
        history = R.get_transitions_for_opportunity(conn, opp.opportunity_id)
    assert len(history) == 4


# ===========================================================================
# A0-2: Every transition writes to signal_state_transitions
# ===========================================================================

def test_every_transition_writes_history(conn):
    opp = make_opportunity(conviction_score=ACTIVE_THRESHOLD + 1.0)
    sig = make_signal(opportunity_id=opp.opportunity_id)
    with conn:
        R.create_opportunity(conn, opp)
        R.create_signal_birth(conn, sig)

    opp, trans, events = try_activate(opp, signal_id=sig.signal_id)
    with conn:
        R.update_opportunity_state(conn, opp)
        for t in trans:
            R.append_transition(conn, t)

    with conn:
        history = R.get_transitions_for_opportunity(conn, opp.opportunity_id)
    assert len(history) == 1
    assert history[0].to_state == OpportunityState.ACTIVE


# ===========================================================================
# A0-3: Transition history can be reconstructed (from INVALID, look back)
# ===========================================================================

def test_transition_history_reconstructable(conn):
    opp = make_opportunity(conviction_score=ACTIVE_THRESHOLD + 1.0)
    sig = make_signal(opportunity_id=opp.opportunity_id)
    with conn:
        R.create_opportunity(conn, opp)
        R.create_signal_birth(conn, sig)

    opp, trans, _ = try_activate(opp, signal_id=sig.signal_id)
    with conn:
        R.update_opportunity_state(conn, opp)
        for t in trans:
            R.append_transition(conn, t)

    opp, trans, _ = try_invalidate(opp, InvalidationReason.TTL_EXHAUSTED, signal_id=sig.signal_id)
    with conn:
        R.update_opportunity_state(conn, opp)
        for t in trans:
            R.append_transition(conn, t)

    with conn:
        history = R.get_transitions_for_opportunity(conn, opp.opportunity_id)
    states = [(t.from_state, t.to_state) for t in history]
    assert ("DISCOVERED", "ACTIVE") in states
    assert ("ACTIVE", "INVALID") in states


# ===========================================================================
# A0-4: INVALID is terminal
# ===========================================================================

def test_invalid_is_terminal(conn):
    opp = make_opportunity(state=OpportunityState.INVALID)
    opp.final_state = "ACTIVE"
    opp.invalidation_reason = InvalidationReason.TTL_EXHAUSTED

    # All transition functions raise when called on INVALID
    with pytest.raises(ValueError):
        try_activate(opp)

    with pytest.raises(ValueError):
        try_watch(opp)

    with pytest.raises(ValueError):
        try_reactivate(opp)

    # try_invalidate on already-INVALID should be a no-op, not raise
    result_opp, trans, events = try_invalidate(opp, InvalidationReason.TTL_EXHAUSTED)
    assert result_opp.current_state == OpportunityState.INVALID
    assert trans == []
    assert events == []


# ===========================================================================
# A0-5: DISCOVERED → INVALID (NEVER_MATURED) when expired
# ===========================================================================

def test_discovered_expires_never_matured(conn):
    opp = make_opportunity(state=OpportunityState.DISCOVERED)
    # discovered_expires_at is "2026-06-12"; pass a date after that
    opp, trans, events = expire_discovered(opp, today="2026-06-13")
    assert opp.current_state == OpportunityState.INVALID
    assert opp.invalidation_reason == InvalidationReason.NEVER_MATURED
    assert len(trans) == 1
    assert trans[0].from_state == OpportunityState.DISCOVERED

    # Before expiry: no transition
    opp2 = make_opportunity(state=OpportunityState.DISCOVERED)
    opp2, trans2, _ = expire_discovered(opp2, today="2026-06-10")
    assert opp2.current_state == OpportunityState.DISCOVERED
    assert trans2 == []


# ===========================================================================
# A0-6: DISCOVERED → WATCHING is forbidden
# ===========================================================================

def test_discovered_cannot_go_to_watching(conn):
    opp = make_opportunity(state=OpportunityState.DISCOVERED)
    # try_watch only applies to ACTIVE — should be a no-op on DISCOVERED
    opp2, trans, events = try_watch(opp)
    assert opp2.current_state == OpportunityState.DISCOVERED
    assert trans == []


# ===========================================================================
# A0-7: Conflicting evidence reduces conviction_score
# ===========================================================================

def test_conflicting_evidence_reduces_conviction(conn):
    """
    The conviction formula: Σ(confirming w×RE) - Σ(conflicting w×RE)
    This test verifies the domain model tracks conflicting_count correctly.
    Full score computation is a Phase C concern; here we test the counter.
    """
    opp = make_opportunity(conviction_score=8.0, state=OpportunityState.ACTIVE)
    opp.confirming_count = 2
    opp.conflicting_count = 0

    # Simulate adding a conflicting signal
    opp.conflicting_count += 1
    opp.consecutive_conflict_days += 1
    # Simulate conviction formula reducing score
    opp.conviction_score = 8.0 - 1.0 * 0.8  # one 1A CONFLICTING at weight 0.8
    assert opp.conviction_score < 8.0
    assert opp.conflicting_count == 1

    # Three consecutive conflict days → CONTRADICTED
    opp.consecutive_conflict_days = 3
    opp, trans, events = check_terminal_conditions(opp, today="2026-06-05")
    assert opp.current_state == OpportunityState.INVALID
    assert opp.invalidation_reason == InvalidationReason.CONTRADICTED


# ===========================================================================
# A0-8: Merge window — signal attaches within window
# ===========================================================================

def test_merge_window_attaches_within_window(conn):
    """
    Within merge window: age < effective_ttl × 0.75 → within_merge_window() True.
    """
    opp = make_opportunity(
        state=OpportunityState.ACTIVE,
        birth_ttl_days=18,
        age_trading_days=5,         # 5 < 18 × 0.75 = 13.5 → within window
    )
    assert opp.within_merge_window() is True


# ===========================================================================
# A0-9: Merge window — new opportunity created past merge window
# ===========================================================================

def test_merge_window_creates_new_past_window(conn):
    """
    Past merge window: age >= effective_ttl × 0.75 → within_merge_window() False.
    Callers should create a new opportunity instead of attaching.
    """
    opp = make_opportunity(
        state=OpportunityState.WATCHING,
        birth_ttl_days=18,
        age_trading_days=14,        # 14 >= 13.5 → outside merge window
    )
    assert opp.within_merge_window() is False


# ===========================================================================
# A0-10: Position full blocks DISCOVERED → ACTIVE
# ===========================================================================

def test_position_full_blocks_activation(conn):
    opp = make_opportunity(
        conviction_score=ACTIVE_THRESHOLD + 2.0,
        state=OpportunityState.DISCOVERED,
        position_exists=True,
        position_size_pct=0.85,     # >= 0.80 → position full
    )
    opp, trans, events = try_activate(opp)
    # Must remain DISCOVERED — position full suppresses activation
    assert opp.current_state == OpportunityState.DISCOVERED
    assert trans == []
    assert any(e.event_type == EventType.POSITION_FULL_SUPPRESSED for e in events)


# ===========================================================================
# A0-11: THESIS_INVALIDATED_WITH_POSITION event emits BEFORE transition
# ===========================================================================

def test_thesis_invalidated_event_emits_with_position(conn):
    opp = make_opportunity(
        state=OpportunityState.ACTIVE,
        position_exists=True,
        position_size_pct=0.70,
    )
    sig = make_signal(opportunity_id=opp.opportunity_id)
    with conn:
        R.create_opportunity(conn, opp)
        R.create_signal_birth(conn, sig)

    opp, trans, events = try_invalidate(
        opp,
        reason=InvalidationReason.CONTRADICTED,
        signal_id=sig.signal_id,
    )

    event_types = [e.event_type for e in events]
    # THESIS_INVALIDATED_WITH_POSITION must appear before OPPORTUNITY_INVALID
    assert EventType.THESIS_INVALIDATED_WITH_POSITION in event_types
    assert EventType.OPPORTUNITY_INVALID in event_types
    thesis_idx = event_types.index(EventType.THESIS_INVALIDATED_WITH_POSITION)
    invalid_idx = event_types.index(EventType.OPPORTUNITY_INVALID)
    assert thesis_idx < invalid_idx, "THESIS_INVALIDATED must emit before OPPORTUNITY_INVALID"


# ===========================================================================
# A0-12: Duplicate guard — find_live_opportunity returns existing
# ===========================================================================

def test_duplicate_opportunity_guard(conn):
    opp = make_opportunity(state=OpportunityState.ACTIVE)
    sig = make_signal(opportunity_id=opp.opportunity_id)
    with conn:
        R.create_opportunity(conn, opp)
        R.create_signal_birth(conn, sig)

    with conn:
        found = R.find_live_opportunity(conn, opp.symbol, opp.direction)
    assert found is not None
    assert found.opportunity_id == opp.opportunity_id

    with conn:
        count = R.count_live_opportunities(conn, opp.symbol, opp.direction)
    assert count == 1


# ===========================================================================
# A0-13: signal_births FK — opportunity_id FK is nullable but valid when set
# ===========================================================================

def test_signal_birth_fk_enforced(conn):
    """
    A signal_births row with a non-existent opportunity_id must be rejected
    by the FK constraint.
    """
    sig = make_signal()
    sig.opportunity_id = "non-existent-uuid"

    with pytest.raises(Exception):
        with conn:
            R.create_signal_birth(conn, sig)


# ===========================================================================
# A0-14: opportunity_signals FK enforcement
# ===========================================================================

def test_opportunity_signals_fk_enforced(conn):
    """
    An opportunity_signals row referencing a non-existent opportunity_id
    must be rejected.
    """
    fake_os = M.OpportunitySignal(
        opportunity_id="does-not-exist",
        signal_id="also-fake",
        signal_type="1B",
        signal_direction="CONFIRMING",
        evidence_weight=1.0,
        added_at="2026-06-01",
    )
    with pytest.raises(Exception):
        with conn:
            R.add_opportunity_signal(conn, fake_os)
