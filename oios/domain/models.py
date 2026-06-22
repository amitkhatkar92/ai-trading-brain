"""
oios/domain/models.py
Dataclasses for every Phase A0 entity.
No market data, no scoring, no network I/O.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Value objects
# ---------------------------------------------------------------------------

class Direction:
    LONG  = "LONG"
    SHORT = "SHORT"


class OpportunityState:
    DISCOVERED = "DISCOVERED"
    ACTIVE     = "ACTIVE"
    WATCHING   = "WATCHING"
    INVALID    = "INVALID"

    _VALID = frozenset([DISCOVERED, ACTIVE, WATCHING, INVALID])

    @classmethod
    def is_valid(cls, value: str) -> bool:
        return value in cls._VALID

    @classmethod
    def is_terminal(cls, value: str) -> bool:
        return value == cls.INVALID

    @classmethod
    def is_live(cls, value: str) -> bool:
        return value in (cls.DISCOVERED, cls.ACTIVE, cls.WATCHING)


class SignalDirection:
    CONFIRMING  = "CONFIRMING"
    CONFLICTING = "CONFLICTING"
    NEUTRAL     = "NEUTRAL"


class InvalidationReason:
    NEVER_MATURED   = "NEVER_MATURED"
    TTL_EXHAUSTED   = "TTL_EXHAUSTED"
    EC_EXHAUSTED    = "EC_EXHAUSTED"
    THESIS_INVALID  = "THESIS_INVALIDATED"
    ZOMBIE_CAP      = "ZOMBIE_CAP"
    CONTRADICTED    = "CONTRADICTED"


class TriggerCause:
    TIME_DECAY           = "TIME_DECAY"
    EC_THRESHOLD         = "EC_THRESHOLD"
    REGIME_CHANGE        = "REGIME_CHANGE"
    CONSENSUS_RECOVERY   = "CONSENSUS_RECOVERY"
    VOLUME_BURST         = "VOLUME_BURST"
    CONVICTION_THRESHOLD = "CONVICTION_THRESHOLD"
    ZOMBIE_CAP           = "ZOMBIE_CAP"
    MANUAL_OVERRIDE      = "MANUAL_OVERRIDE"
    DISCOVERED_EXPIRED   = "DISCOVERED_EXPIRED"
    CONTRADICTED         = "CONTRADICTED"


class EventType:
    OPPORTUNITY_ACTIVE               = "OPPORTUNITY_ACTIVE"
    OPPORTUNITY_WATCHING             = "OPPORTUNITY_WATCHING"
    OPPORTUNITY_INVALID              = "OPPORTUNITY_INVALID"
    THESIS_INVALIDATED_WITH_POSITION = "THESIS_INVALIDATED_WITH_POSITION"
    POSITION_FULL_SUPPRESSED         = "POSITION_FULL_SUPPRESSED"
    ADD_TO_POSITION                  = "ADD_TO_POSITION"


# ---------------------------------------------------------------------------
# Domain models
# ---------------------------------------------------------------------------

@dataclass
class Opportunity:
    opportunity_id:         str
    symbol:                 str
    direction:              str
    sector:                 str

    created_at:             str             # ISO-8601 date
    regime_at_birth:        str
    birth_ttl_days:         int
    effective_ttl_days:     int
    discovered_expires_at:  str             # ISO-8601 date

    first_signal_id:        Optional[str]   = None
    theme_phase_at_birth:   Optional[str]   = None

    current_state:          str             = OpportunityState.DISCOVERED
    age_trading_days:       int             = 0

    conviction_score:       float           = 0.0
    confirming_count:       int             = 0
    conflicting_count:      int             = 0
    consecutive_conflict_days: int          = 0

    re_score:               Optional[float] = None
    edge_consumed_pct:      float           = 0.0
    maturity_combined:      Optional[str]   = None
    velocity_3d:            Optional[float] = None
    velocity_class:         Optional[str]   = None

    position_exists:        bool            = False
    position_size_pct:      float           = 0.0
    position_open_date:     Optional[str]   = None

    final_state:            Optional[str]   = None
    invalidation_reason:    Optional[str]   = None
    finalized_at:           Optional[str]   = None
    trade_pnl_pct:          Optional[float] = None
    is_audit_trade:         bool            = False

    last_updated_at:        Optional[str]   = None

    # ------------------------------------------------------------------
    # Merge window check (R3-1)
    # ------------------------------------------------------------------
    def within_merge_window(self) -> bool:
        """
        Returns True if this opportunity is young enough to accept new evidence.
        An opportunity in the final 25% of its TTL does not absorb new signals.
        """
        return self.age_trading_days < self.effective_ttl_days * 0.75

    # ------------------------------------------------------------------
    # State predicates
    # ------------------------------------------------------------------
    def is_live(self) -> bool:
        return OpportunityState.is_live(self.current_state)

    def is_invalid(self) -> bool:
        return self.current_state == OpportunityState.INVALID

    def is_position_full(self) -> bool:
        return self.position_size_pct >= 0.80


@dataclass
class SignalBirth:
    signal_id:              str
    symbol:                 str
    archetype_id:           str
    signal_type:            str
    detected_at:            str             # ISO-8601 date
    birth_price:            float
    base_score:             float
    regime_at_birth:        str
    expected_ttl_days:      int
    expected_move_direction: str

    opportunity_id:         Optional[str]   = None
    archetype_version:      int             = 1
    theme_phase_at_birth:   Optional[str]   = None
    consensus_score_at_birth: Optional[float] = None

    expected_move_pct:      float           = 8.0
    expected_move_pct_source: str           = "UNIVERSAL_DEFAULT_8PCT"

    current_state:          str             = "ACTIVE"
    current_price:          Optional[float] = None
    age_trading_days:       int             = 0
    actual_move_pct:        float           = 0.0
    edge_consumed_pct:      float           = 0.0
    re_score:               Optional[float] = None

    final_state:            Optional[str]   = None
    final_age_trading_days: Optional[int]   = None
    peak_move_pct:          Optional[float] = None
    days_to_peak:           Optional[int]   = None
    trade_executed:         bool            = False
    trade_outcome_pct:      Optional[float] = None
    invalidation_reason:    Optional[str]   = None
    last_updated_at:        Optional[str]   = None


@dataclass
class OpportunitySignal:
    opportunity_id:     str
    signal_id:          str
    signal_type:        str
    signal_direction:   str
    evidence_weight:    float
    added_at:           str             # ISO-8601 date


@dataclass
class StateTransition:
    transition_id:              str
    signal_id:                  str
    transitioned_at:            str     # ISO-8601 datetime
    from_state:                 str
    to_state:                   str
    trigger_cause:              str

    opportunity_id:             Optional[str]   = None
    re_at_transition:           Optional[float] = None
    age_trading_days:           Optional[int]   = None
    regime_at_transition:       Optional[str]   = None
    theme_phase_at_transition:  Optional[str]   = None
    consensus_score:            Optional[float] = None
    edge_consumed_pct:          Optional[float] = None


@dataclass
class DecisionLogEntry:
    decision_id:                str
    opportunity_id:             str
    symbol:                     str
    decided_at:                 str     # ISO-8601 datetime
    action:                     str
    price_at_decision:          float

    signal_id:                  Optional[str]   = None
    conviction_score:           Optional[float] = None
    re_score:                   Optional[float] = None
    re_threshold_applied:       Optional[float] = None
    suppression_reason:         Optional[str]   = None
    signal_age_trading_days:    Optional[int]   = None
    regime:                     Optional[str]   = None
    theme_phase:                Optional[str]   = None
    edge_consumed_pct:          Optional[float] = None
    maturity_combined:          Optional[str]   = None
    position_size_pct_at_decision: Optional[float] = None

    # Populated retroactively by Self-Audit
    price_5d_later:             Optional[float] = None
    price_10d_later:            Optional[float] = None
    price_20d_later:            Optional[float] = None
    max_adverse_20d:            Optional[float] = None
    max_favorable_20d:          Optional[float] = None
    outcome_populated_at:       Optional[str]   = None
    subsequent_opportunity_id:  Optional[str]   = None
    subsequent_opportunity_pnl: Optional[float] = None
    counterfactual_type:        Optional[str]   = None


@dataclass
class OIOSEvent:
    event_id:       str
    event_type:     str
    symbol:         str
    emitted_at:     str     # ISO-8601 datetime

    opportunity_id: Optional[str] = None
    payload:        Optional[str] = None    # JSON string
    consumed_at:    Optional[str] = None
    consumed_by:    Optional[str] = None
