"""iios/investment/portfolio/recommendation/recommendation_lifecycle.py

Lifecycle state machine for portfolio recommendations.
"""
from __future__ import annotations

from typing import Set

from iios.investment.portfolio.recommendation.recommendation_types import (
    LifecycleState, RecommendationStatus, now_utc,
)

# Valid state transitions
_ALLOWED_TRANSITIONS = {
    LifecycleState.CREATED:    {LifecycleState.PUBLISHED, LifecycleState.WITHDRAWN},
    LifecycleState.PUBLISHED:  {LifecycleState.ACTIVE, LifecycleState.WITHDRAWN},
    LifecycleState.ACTIVE:     {LifecycleState.MONITORING, LifecycleState.UPDATED,
                                LifecycleState.EXPIRED, LifecycleState.WITHDRAWN},
    LifecycleState.MONITORING: {LifecycleState.ACTIVE, LifecycleState.UPDATED,
                                LifecycleState.EXPIRED, LifecycleState.WITHDRAWN},
    LifecycleState.UPDATED:    {LifecycleState.ACTIVE, LifecycleState.EXPIRED,
                                LifecycleState.WITHDRAWN},
    LifecycleState.EXPIRED:    {LifecycleState.ARCHIVED},
    LifecycleState.WITHDRAWN:  {LifecycleState.ARCHIVED},
    LifecycleState.ARCHIVED:   set(),
}

# LifecycleState → RecommendationStatus mapping
_STATE_TO_STATUS = {
    LifecycleState.CREATED:    RecommendationStatus.DRAFT,
    LifecycleState.PUBLISHED:  RecommendationStatus.PUBLISHED,
    LifecycleState.ACTIVE:     RecommendationStatus.ACTIVE,
    LifecycleState.MONITORING: RecommendationStatus.MONITORING,
    LifecycleState.UPDATED:    RecommendationStatus.UPDATED,
    LifecycleState.EXPIRED:    RecommendationStatus.EXPIRED,
    LifecycleState.WITHDRAWN:  RecommendationStatus.WITHDRAWN,
    LifecycleState.ARCHIVED:   RecommendationStatus.ARCHIVED,
}


def get_allowed_transitions(state: LifecycleState) -> Set[LifecycleState]:
    """Return the set of valid next states from the current state."""
    return set(_ALLOWED_TRANSITIONS.get(state, set()))


def is_valid_transition(
    current: LifecycleState,
    target:  LifecycleState,
) -> bool:
    """Return True if the transition is allowed."""
    return target in _ALLOWED_TRANSITIONS.get(current, set())


def state_to_status(state: LifecycleState) -> RecommendationStatus:
    """Map a lifecycle state to the corresponding operational status."""
    return _STATE_TO_STATUS.get(state, RecommendationStatus.DRAFT)


def is_terminal(state: LifecycleState) -> bool:
    """Return True if no further transitions are possible."""
    return len(_ALLOWED_TRANSITIONS.get(state, set())) == 0


def is_active(state: LifecycleState) -> bool:
    """Return True if the recommendation is in an active/observable state."""
    return state in {
        LifecycleState.PUBLISHED,
        LifecycleState.ACTIVE,
        LifecycleState.MONITORING,
        LifecycleState.UPDATED,
    }


class LifecycleManager:
    """
    Applies lifecycle transitions to PortfolioRecommendation objects.
    Since recommendations are frozen, each transition returns a NEW instance.
    """

    def transition(self, rec: "PortfolioRecommendation", new_state: LifecycleState) -> "PortfolioRecommendation":
        """
        Transition a recommendation to a new lifecycle state.
        Returns a new frozen instance with updated state fields.
        Raises ValueError if the transition is invalid.
        """
        if not is_valid_transition(rec.lifecycle_state, new_state):
            raise ValueError(
                f"Invalid lifecycle transition: {rec.lifecycle_state.value} → {new_state.value}"
            )
        new_status = state_to_status(new_state)
        # Replace state fields using dataclasses.replace-equivalent (re-create)
        from iios.investment.portfolio.recommendation.portfolio_recommendation import PortfolioRecommendation
        import dataclasses
        return dataclasses.replace(
            rec,
            lifecycle_state = new_state,
            status          = new_status,
            updated_at      = now_utc(),
        )

    def publish(self, rec: "PortfolioRecommendation") -> "PortfolioRecommendation":
        return self.transition(rec, LifecycleState.PUBLISHED)

    def activate(self, rec: "PortfolioRecommendation") -> "PortfolioRecommendation":
        return self.transition(rec, LifecycleState.ACTIVE)

    def monitor(self, rec: "PortfolioRecommendation") -> "PortfolioRecommendation":
        return self.transition(rec, LifecycleState.MONITORING)

    def expire(self, rec: "PortfolioRecommendation") -> "PortfolioRecommendation":
        return self.transition(rec, LifecycleState.EXPIRED)

    def withdraw(self, rec: "PortfolioRecommendation") -> "PortfolioRecommendation":
        return self.transition(rec, LifecycleState.WITHDRAWN)

    def archive(self, rec: "PortfolioRecommendation") -> "PortfolioRecommendation":
        return self.transition(rec, LifecycleState.ARCHIVED)
