"""
oios/domain/state_machine.py

Opportunity state machine as specified in MAS_v1.2.md Section 3.

Rules:
- DISCOVERED → ACTIVE   when conviction crosses threshold AND position not full
- DISCOVERED → INVALID  when discovered_expires_at reached (NEVER_MATURED)
- ACTIVE     → WATCHING when RE drops below threshold
- WATCHING   → ACTIVE   when RE recovers (bidirectional — age < effective_ttl × 0.80)
- ACTIVE     → INVALID  on any terminal condition
- WATCHING   → INVALID  on any terminal condition
- INVALID    is terminal — no further transitions accepted

Phase A0: scoring inputs are not yet real. State transitions driven by
explicit caller-supplied conditions only (no RE computation here).
The state machine enforces rules; callers supply facts.
"""

from __future__ import annotations
import logging
from datetime import datetime, timezone
from typing import Optional

from .models import (
    Opportunity,
    StateTransition,
    OIOSEvent,
    OpportunityState,
    InvalidationReason,
    TriggerCause,
    EventType,
)

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants (match MAS_v1.2.md Section 5 Layer 5)
# ---------------------------------------------------------------------------

ACTIVE_THRESHOLD: float   = 6.0     # conviction_score to enter ACTIVE
RE_THRESHOLD: float       = 5.0     # RE below this → WATCHING
POSITION_FULL_PCT: float  = 0.80    # position_size_pct at or above this → suppress
TTL_WATCHABLE_FRACTION    = 0.80    # ACTIVE→WATCHING only if age < effective_ttl × this
CONFLICT_DAYS_THRESHOLD   = 3       # consecutive days conflicting > confirming → CONTRADICTED


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _transition_record(
    signal_id: str,
    from_state: str,
    to_state: str,
    trigger_cause: str,
    opportunity_id: Optional[str] = None,
    re_at_transition: Optional[float] = None,
    age_trading_days: Optional[int] = None,
    regime: Optional[str] = None,
    theme_phase: Optional[str] = None,
) -> StateTransition:
    import uuid
    return StateTransition(
        transition_id=str(uuid.uuid4()),
        signal_id=signal_id,
        opportunity_id=opportunity_id,
        from_state=from_state,
        to_state=to_state,
        transitioned_at=_now_iso(),
        trigger_cause=trigger_cause,
        re_at_transition=re_at_transition,
        age_trading_days=age_trading_days,
        regime_at_transition=regime,
        theme_phase_at_transition=theme_phase,
    )


def _event(
    event_type: str,
    opportunity: Opportunity,
    payload: Optional[str] = None,
) -> OIOSEvent:
    import uuid
    return OIOSEvent(
        event_id=str(uuid.uuid4()),
        event_type=event_type,
        opportunity_id=opportunity.opportunity_id,
        symbol=opportunity.symbol,
        emitted_at=_now_iso(),
        payload=payload,
    )


# ---------------------------------------------------------------------------
# State machine transitions
# Public API: each function receives an Opportunity and caller-supplied context.
# Returns (mutated Opportunity, list[StateTransition], list[OIOSEvent]).
# The repository layer persists all three.
# ---------------------------------------------------------------------------

TransitionResult = tuple[Opportunity, list[StateTransition], list[OIOSEvent]]


def _guard_terminal(opp: Opportunity) -> None:
    if opp.current_state == OpportunityState.INVALID:
        raise ValueError(
            f"[StateMachine] Attempt to transition INVALID opportunity "
            f"{opp.opportunity_id} ({opp.symbol}). INVALID is terminal."
        )


def try_activate(
    opp: Opportunity,
    signal_id: str = "SYSTEM",
    regime: Optional[str] = None,
    theme_phase: Optional[str] = None,
) -> TransitionResult:
    """
    DISCOVERED → ACTIVE when conviction_score >= ACTIVE_THRESHOLD and position not full.
    No-op if already ACTIVE or conditions not met.
    """
    _guard_terminal(opp)
    transitions: list[StateTransition] = []
    events: list[OIOSEvent] = []

    if opp.current_state != OpportunityState.DISCOVERED:
        return opp, transitions, events

    if opp.is_position_full():
        events.append(_event(EventType.POSITION_FULL_SUPPRESSED, opp))
        log.info("[StateMachine] %s suppressed DISCOVERED→ACTIVE: position full", opp.symbol)
        return opp, transitions, events

    if opp.conviction_score < ACTIVE_THRESHOLD:
        return opp, transitions, events

    from_state = opp.current_state
    opp.current_state = OpportunityState.ACTIVE
    opp.last_updated_at = _now_iso()

    transitions.append(_transition_record(
        signal_id=signal_id,
        from_state=from_state,
        to_state=OpportunityState.ACTIVE,
        trigger_cause=TriggerCause.CONVICTION_THRESHOLD,
        opportunity_id=opp.opportunity_id,
        age_trading_days=opp.age_trading_days,
        regime=regime,
        theme_phase=theme_phase,
    ))
    events.append(_event(EventType.OPPORTUNITY_ACTIVE, opp))
    log.info("[StateMachine] %s DISCOVERED→ACTIVE conviction=%.2f", opp.symbol, opp.conviction_score)
    return opp, transitions, events


def try_watch(
    opp: Opportunity,
    signal_id: str = "SYSTEM",
    trigger_cause: str = TriggerCause.TIME_DECAY,
    re_score: Optional[float] = None,
    regime: Optional[str] = None,
    theme_phase: Optional[str] = None,
) -> TransitionResult:
    """
    ACTIVE → WATCHING when RE drops below threshold AND age < effective_ttl × 0.80.
    """
    _guard_terminal(opp)
    transitions: list[StateTransition] = []
    events: list[OIOSEvent] = []

    if opp.current_state != OpportunityState.ACTIVE:
        return opp, transitions, events

    age_fraction = (
        opp.age_trading_days / opp.effective_ttl_days
        if opp.effective_ttl_days > 0 else 1.0
    )
    if age_fraction >= TTL_WATCHABLE_FRACTION:
        # Too old to watch — must go to INVALID directly via try_invalidate
        return opp, transitions, events

    from_state = opp.current_state
    opp.current_state = OpportunityState.WATCHING
    opp.last_updated_at = _now_iso()

    transitions.append(_transition_record(
        signal_id=signal_id,
        from_state=from_state,
        to_state=OpportunityState.WATCHING,
        trigger_cause=trigger_cause,
        opportunity_id=opp.opportunity_id,
        re_at_transition=re_score,
        age_trading_days=opp.age_trading_days,
        regime=regime,
        theme_phase=theme_phase,
    ))
    events.append(_event(EventType.OPPORTUNITY_WATCHING, opp))
    log.info("[StateMachine] %s ACTIVE→WATCHING age=%d ttl=%d",
             opp.symbol, opp.age_trading_days, opp.effective_ttl_days)
    return opp, transitions, events


def try_reactivate(
    opp: Opportunity,
    signal_id: str = "SYSTEM",
    regime: Optional[str] = None,
    theme_phase: Optional[str] = None,
) -> TransitionResult:
    """
    WATCHING → ACTIVE when RE recovers above threshold AND age < effective_ttl × 0.80.
    This is the bidirectional ACTIVE↔WATCHING transition.
    """
    _guard_terminal(opp)
    transitions: list[StateTransition] = []
    events: list[OIOSEvent] = []

    if opp.current_state != OpportunityState.WATCHING:
        return opp, transitions, events

    age_fraction = (
        opp.age_trading_days / opp.effective_ttl_days
        if opp.effective_ttl_days > 0 else 1.0
    )
    if age_fraction >= TTL_WATCHABLE_FRACTION:
        return opp, transitions, events

    if opp.conviction_score < ACTIVE_THRESHOLD:
        return opp, transitions, events

    if opp.is_position_full():
        events.append(_event(EventType.POSITION_FULL_SUPPRESSED, opp))
        return opp, transitions, events

    from_state = opp.current_state
    opp.current_state = OpportunityState.ACTIVE
    opp.last_updated_at = _now_iso()

    transitions.append(_transition_record(
        signal_id=signal_id,
        from_state=from_state,
        to_state=OpportunityState.ACTIVE,
        trigger_cause=TriggerCause.CONSENSUS_RECOVERY,
        opportunity_id=opp.opportunity_id,
        age_trading_days=opp.age_trading_days,
        regime=regime,
        theme_phase=theme_phase,
    ))
    events.append(_event(EventType.OPPORTUNITY_ACTIVE, opp))
    log.info("[StateMachine] %s WATCHING→ACTIVE (recovered)", opp.symbol)
    return opp, transitions, events


def try_invalidate(
    opp: Opportunity,
    reason: str,
    signal_id: str = "SYSTEM",
    trigger_cause: Optional[str] = None,
    re_score: Optional[float] = None,
    regime: Optional[str] = None,
    theme_phase: Optional[str] = None,
) -> TransitionResult:
    """
    Terminal transition to INVALID from ACTIVE or WATCHING.
    Emits THESIS_INVALIDATED_WITH_POSITION if a live position exists.
    INVALID → INVALID is a no-op (idempotent).
    """
    if opp.current_state == OpportunityState.INVALID:
        return opp, [], []

    _guard_terminal(opp)  # raises if somehow already terminal and not INVALID (shouldn't happen)

    if opp.current_state == OpportunityState.DISCOVERED:
        # DISCOVERED → INVALID only via NEVER_MATURED
        if reason != InvalidationReason.NEVER_MATURED:
            raise ValueError(
                f"DISCOVERED opportunities may only be invalidated with NEVER_MATURED, "
                f"got '{reason}' for {opp.opportunity_id}"
            )

    transitions: list[StateTransition] = []
    events: list[OIOSEvent] = []

    import json

    # Critical: emit THESIS_INVALIDATED_WITH_POSITION BEFORE recording the transition
    if opp.position_exists and opp.current_state != OpportunityState.DISCOVERED:
        events.append(_event(
            EventType.THESIS_INVALIDATED_WITH_POSITION,
            opp,
            payload=json.dumps({
                "invalidation_reason": reason,
                "position_size_pct": opp.position_size_pct,
                "conviction_score": opp.conviction_score,
            }),
        ))
        log.warning(
            "[StateMachine] %s THESIS_INVALIDATED_WITH_POSITION reason=%s position_pct=%.2f",
            opp.symbol, reason, opp.position_size_pct,
        )

    from_state = opp.current_state
    now = _now_iso()

    opp.current_state       = OpportunityState.INVALID
    opp.final_state         = from_state
    opp.invalidation_reason = reason
    opp.finalized_at        = now[:10]      # date only
    opp.last_updated_at     = now

    transitions.append(_transition_record(
        signal_id=signal_id,
        from_state=from_state,
        to_state=OpportunityState.INVALID,
        trigger_cause=trigger_cause or reason,
        opportunity_id=opp.opportunity_id,
        re_at_transition=re_score,
        age_trading_days=opp.age_trading_days,
        regime=regime,
        theme_phase=theme_phase,
    ))
    events.append(_event(EventType.OPPORTUNITY_INVALID, opp,
                         payload=json.dumps({"reason": reason})))
    log.info("[StateMachine] %s →INVALID from=%s reason=%s", opp.symbol, from_state, reason)
    return opp, transitions, events


def expire_discovered(
    opp: Opportunity,
    today: str,
    signal_id: str = "SYSTEM",
) -> TransitionResult:
    """
    Check whether a DISCOVERED opportunity has exceeded its discovered_expires_at date.
    If so, invalidate with NEVER_MATURED.
    today: ISO-8601 date string.
    """
    if opp.current_state != OpportunityState.DISCOVERED:
        return opp, [], []
    if today > opp.discovered_expires_at:
        return try_invalidate(
            opp,
            reason=InvalidationReason.NEVER_MATURED,
            signal_id=signal_id,
            trigger_cause=TriggerCause.DISCOVERED_EXPIRED,
        )
    return opp, [], []


def check_terminal_conditions(
    opp: Opportunity,
    today: str,
    signal_id: str = "SYSTEM",
    volume_burst: bool = False,
    regime: Optional[str] = None,
) -> TransitionResult:
    """
    Evaluate all terminal conditions defined in MAS_v1.2.md Section 3.
    Returns transitions and events if any terminal condition is triggered.
    Checks are applied in priority order.
    """
    if opp.current_state in (OpportunityState.DISCOVERED, OpportunityState.INVALID):
        return opp, [], []

    # 1. Volume burst — highest priority (thesis fundamentally invalidated)
    if volume_burst:
        return try_invalidate(
            opp, InvalidationReason.THESIS_INVALID, signal_id,
            trigger_cause=TriggerCause.VOLUME_BURST, regime=regime,
        )

    # 2. Sustained contradiction
    if opp.consecutive_conflict_days >= CONFLICT_DAYS_THRESHOLD:
        return try_invalidate(
            opp, InvalidationReason.CONTRADICTED, signal_id,
            trigger_cause=TriggerCause.CONTRADICTED, regime=regime,
        )

    # 3. Edge consumed
    if opp.edge_consumed_pct >= 1.0:
        return try_invalidate(
            opp, InvalidationReason.EC_EXHAUSTED, signal_id,
            trigger_cause=TriggerCause.EC_THRESHOLD, regime=regime,
        )

    # 4. Zombie cap — hard age ceiling
    if opp.age_trading_days > opp.effective_ttl_days * 1.2:
        return try_invalidate(
            opp, InvalidationReason.ZOMBIE_CAP, signal_id,
            trigger_cause=TriggerCause.ZOMBIE_CAP, regime=regime,
        )

    # 5. TTL exhaustion
    if opp.age_trading_days >= opp.effective_ttl_days:
        return try_invalidate(
            opp, InvalidationReason.TTL_EXHAUSTED, signal_id,
            trigger_cause=TriggerCause.TIME_DECAY, regime=regime,
        )

    return opp, [], []
