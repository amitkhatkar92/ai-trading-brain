"""iios/investment/strategy/portfolio/portfolio_lifecycle.py
PortfolioLifecycle — enforces state machine transitions and emits events.
"""
from __future__ import annotations

import threading
import uuid
from datetime import datetime, timezone
from typing import Dict, Optional

from iios.investment.strategy.portfolio.strategy_portfolio import (
    StrategyPortfolio, PortfolioState
)
from iios.investment.strategy.portfolio.portfolio_events import (
    PortfolioEvent, PortfolioEventType, PortfolioEventBus
)

_STATE_TO_EVENT: Dict[PortfolioState, PortfolioEventType] = {
    PortfolioState.CREATED:    PortfolioEventType.CREATED,
    PortfolioState.OPTIMIZED:  PortfolioEventType.OPTIMIZED,
    PortfolioState.APPROVED:   PortfolioEventType.APPROVED,
    PortfolioState.ACTIVE:     PortfolioEventType.ACTIVATED,
    PortfolioState.REBALANCED: PortfolioEventType.REBALANCED,
    PortfolioState.PAUSED:     PortfolioEventType.PAUSED,
    PortfolioState.ARCHIVED:   PortfolioEventType.ARCHIVED,
}


class PortfolioLifecycle:
    """
    Manages state transitions for StrategyPortfolio objects.
    Each portfolio gets an RLock for concurrent-safe transitions.
    Emits PortfolioEvents via the shared event bus.
    """

    def __init__(self, event_bus: Optional[PortfolioEventBus] = None) -> None:
        self._bus   = event_bus or PortfolioEventBus()
        self._locks: Dict[str, threading.RLock] = {}
        self._meta_lock = threading.Lock()

    def _lock_for(self, portfolio_id: str) -> threading.RLock:
        with self._meta_lock:
            if portfolio_id not in self._locks:
                self._locks[portfolio_id] = threading.RLock()
            return self._locks[portfolio_id]

    def transition(
        self,
        portfolio: StrategyPortfolio,
        new_state: PortfolioState,
        reason:    str = "",
        payload:   Optional[Dict] = None,
    ) -> bool:
        """
        Attempt a state transition.  Returns True on success, False if invalid.
        Thread-safe per portfolio_id.
        """
        lock = self._lock_for(portfolio.portfolio_id)
        with lock:
            if not portfolio.can_transition_to(new_state):
                return False
            portfolio.apply_transition(new_state, reason=reason)
            event_type = _STATE_TO_EVENT.get(new_state, PortfolioEventType.SCORE_CHANGED)
            self._emit(portfolio, event_type, payload or {}, reason)
            return True

    def activate(self, portfolio: StrategyPortfolio, reason: str = "") -> bool:
        return self.transition(portfolio, PortfolioState.ACTIVE, reason)

    def approve(self, portfolio: StrategyPortfolio, reason: str = "") -> bool:
        return self.transition(portfolio, PortfolioState.APPROVED, reason)

    def pause(self, portfolio: StrategyPortfolio, reason: str = "") -> bool:
        return self.transition(portfolio, PortfolioState.PAUSED, reason)

    def archive(self, portfolio: StrategyPortfolio, reason: str = "") -> bool:
        return self.transition(portfolio, PortfolioState.ARCHIVED, reason)

    def mark_rebalanced(self, portfolio: StrategyPortfolio, reason: str = "") -> bool:
        ok = self.transition(portfolio, PortfolioState.REBALANCED, reason)
        if ok:
            portfolio.last_rebalanced = datetime.now(timezone.utc)
        return ok

    def _emit(
        self,
        portfolio:  StrategyPortfolio,
        event_type: PortfolioEventType,
        payload:    Dict,
        reason:     str,
    ) -> None:
        event = PortfolioEvent(
            event_id=str(uuid.uuid4()),
            event_type=event_type,
            portfolio_id=portfolio.portfolio_id,
            payload={"reason": reason, "version": portfolio.version, **payload},
        )
        self._bus.emit(event)

    @property
    def event_bus(self) -> PortfolioEventBus:
        return self._bus
