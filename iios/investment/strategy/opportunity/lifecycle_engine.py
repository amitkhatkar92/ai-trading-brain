"""iios/investment/strategy/opportunity/lifecycle_engine.py
LifecycleEngine — drives StrategyOpportunity through its state machine.

Valid transitions are defined in strategy_opportunity.py.
All transitions are logged with timestamp, reason, and triggering actor.
"""
from __future__ import annotations

import logging
import threading
from datetime import datetime, timezone
from typing import Optional

from iios.investment.strategy.opportunity.strategy_opportunity import (
    StrategyOpportunity, OpportunityState
)

logger = logging.getLogger(__name__)


class LifecycleEngine:
    """
    Manages state transitions for StrategyOpportunity objects.
    Thread-safe via a per-opportunity lock held during transitions.
    """

    def __init__(self) -> None:
        self._locks: dict[str, threading.Lock] = {}
        self._meta_lock = threading.Lock()

    # ── public transition API ─────────────────────────────────────────────────

    def advance_to_candidate(
        self, opp: StrategyOpportunity, reason: str = "matched", triggered_by: str = "matching_engine"
    ) -> bool:
        return self._transition(opp, OpportunityState.CANDIDATE, reason, triggered_by)

    def advance_to_recommended(
        self, opp: StrategyOpportunity, reason: str = "top_ranked", triggered_by: str = "ranking_engine"
    ) -> bool:
        return self._transition(opp, OpportunityState.RECOMMENDED, reason, triggered_by)

    def advance_to_approved(
        self, opp: StrategyOpportunity, reason: str = "approved_by_decision_layer", triggered_by: str = "decision_layer"
    ) -> bool:
        return self._transition(opp, OpportunityState.APPROVED, reason, triggered_by)

    def advance_to_monitoring(
        self, opp: StrategyOpportunity, reason: str = "position_opened", triggered_by: str = "execution_engine"
    ) -> bool:
        return self._transition(opp, OpportunityState.MONITORING, reason, triggered_by)

    def expire(
        self, opp: StrategyOpportunity, reason: str = "ttl_expired", triggered_by: str = "lifecycle_engine"
    ) -> bool:
        return self._transition(opp, OpportunityState.EXPIRED, reason, triggered_by)

    def archive(
        self, opp: StrategyOpportunity, reason: str = "archived", triggered_by: str = "lifecycle_engine"
    ) -> bool:
        return self._transition(opp, OpportunityState.ARCHIVED, reason, triggered_by)

    def check_and_expire(self, opp: StrategyOpportunity) -> bool:
        """Automatically expire if TTL has passed. Returns True if expired."""
        if opp.is_active() and opp.expires_at is not None:
            if datetime.now(timezone.utc) >= opp.expires_at:
                return self.expire(opp, reason="ttl_expired")
        return False

    # ── internal ─────────────────────────────────────────────────────────────

    def _transition(
        self,
        opp: StrategyOpportunity,
        new_state: OpportunityState,
        reason: str,
        triggered_by: str,
    ) -> bool:
        lock = self._get_lock(opp.opportunity_id)
        with lock:
            if not opp.can_transition_to(new_state):
                logger.warning(
                    "Refused transition %s → %s for %s: %s",
                    opp.state.value, new_state.value, opp.opportunity_id, reason,
                )
                return False
            opp._apply_transition(new_state, reason, triggered_by)
            logger.debug(
                "Transitioned %s → %s (%s)",
                opp.opportunity_id, new_state.value, reason,
            )
            return True

    def _get_lock(self, opp_id: str) -> threading.Lock:
        with self._meta_lock:
            if opp_id not in self._locks:
                self._locks[opp_id] = threading.Lock()
            return self._locks[opp_id]
