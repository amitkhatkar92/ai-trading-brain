"""iios/investment/strategy/opportunity/strategy_opportunity.py
StrategyOpportunity — the core output type with lifecycle state machine.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, FrozenSet, List, Optional


class OpportunityState(str, Enum):
    DISCOVERED  = "discovered"
    CANDIDATE   = "candidate"
    RECOMMENDED = "recommended"
    APPROVED    = "approved"
    MONITORING  = "monitoring"
    EXPIRED     = "expired"
    ARCHIVED    = "archived"


# Valid state transitions (from → {allowed targets})
_TRANSITIONS: Dict[OpportunityState, FrozenSet[OpportunityState]] = {
    OpportunityState.DISCOVERED:  frozenset({OpportunityState.CANDIDATE,   OpportunityState.EXPIRED}),
    OpportunityState.CANDIDATE:   frozenset({OpportunityState.RECOMMENDED, OpportunityState.EXPIRED,  OpportunityState.ARCHIVED}),
    OpportunityState.RECOMMENDED: frozenset({OpportunityState.APPROVED,    OpportunityState.EXPIRED,  OpportunityState.ARCHIVED}),
    OpportunityState.APPROVED:    frozenset({OpportunityState.MONITORING,   OpportunityState.EXPIRED,  OpportunityState.ARCHIVED}),
    OpportunityState.MONITORING:  frozenset({OpportunityState.EXPIRED,      OpportunityState.ARCHIVED}),
    OpportunityState.EXPIRED:     frozenset({OpportunityState.ARCHIVED}),
    OpportunityState.ARCHIVED:    frozenset(),
}


@dataclass
class StateTransitionRecord:
    from_state:       OpportunityState
    to_state:         OpportunityState
    transitioned_at:  datetime
    reason:           str
    triggered_by:     str = "system"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "from_state":      self.from_state.value,
            "to_state":        self.to_state.value,
            "transitioned_at": self.transitioned_at.isoformat(),
            "reason":          self.reason,
            "triggered_by":    self.triggered_by,
        }


@dataclass
class StrategyOpportunity:
    """
    Matched strategy-opportunity pair.  Lifecycle managed by LifecycleEngine.
    All score fields are in [0, 100].
    """
    opportunity_id:         str
    strategy_id:            str
    strategy_name:          str
    market_opportunity_id:  Optional[str]
    company_opportunity_id: Optional[str]

    state:             OpportunityState = OpportunityState.DISCOVERED
    matching_score:    float = 0.0   # from MatchingEngine
    suitability_score: float = 0.0   # from SuitabilityEngine
    ranking_score:     float = 0.0   # from RankingEngine

    recommendation_id: Optional[str] = None

    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = None

    state_history: List[StateTransitionRecord] = field(default_factory=list)
    metadata:      Dict[str, Any] = field(default_factory=dict)

    # ── state machine ────────────────────────────────────────────────────────

    def can_transition_to(self, new_state: OpportunityState) -> bool:
        return new_state in _TRANSITIONS.get(self.state, frozenset())

    def _apply_transition(
        self, new_state: OpportunityState, reason: str, triggered_by: str = "system"
    ) -> None:
        if not self.can_transition_to(new_state):
            raise ValueError(
                f"Invalid transition: {self.state.value} → {new_state.value}"
            )
        self.state_history.append(
            StateTransitionRecord(
                from_state=self.state,
                to_state=new_state,
                transitioned_at=datetime.now(timezone.utc),
                reason=reason,
                triggered_by=triggered_by,
            )
        )
        self.state = new_state
        self.updated_at = datetime.now(timezone.utc)

    # ── convenience queries ───────────────────────────────────────────────────

    def is_active(self) -> bool:
        return self.state not in (OpportunityState.EXPIRED, OpportunityState.ARCHIVED)

    def is_terminal(self) -> bool:
        return self.state in (OpportunityState.EXPIRED, OpportunityState.ARCHIVED)

    def is_expired(self) -> bool:
        if self.expires_at is not None and datetime.now(timezone.utc) >= self.expires_at:
            return True
        return self.state == OpportunityState.EXPIRED

    def composite_score(self) -> float:
        return (
            0.35 * self.matching_score
            + 0.35 * self.suitability_score
            + 0.30 * self.ranking_score
        )

    # ── serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        return {
            "opportunity_id":         self.opportunity_id,
            "strategy_id":            self.strategy_id,
            "strategy_name":          self.strategy_name,
            "market_opportunity_id":  self.market_opportunity_id,
            "company_opportunity_id": self.company_opportunity_id,
            "state":                  self.state.value,
            "matching_score":         self.matching_score,
            "suitability_score":      self.suitability_score,
            "ranking_score":          self.ranking_score,
            "composite_score":        self.composite_score(),
            "recommendation_id":      self.recommendation_id,
            "created_at":             self.created_at.isoformat(),
            "updated_at":             self.updated_at.isoformat(),
            "expires_at":             self.expires_at.isoformat() if self.expires_at else None,
            "state_history":          [r.to_dict() for r in self.state_history],
        }
