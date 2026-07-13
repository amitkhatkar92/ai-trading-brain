"""iios/investment/company/opportunity/lifecycle_tracker.py
Stateful lifecycle tracker — maintains current lifecycle state per ticker.
"""
from __future__ import annotations

import threading
from collections import deque
from datetime import datetime, timezone
from typing import Dict, List, Optional

from iios.investment.company.opportunity.opportunity_lifecycle import (
    LifecycleChange, determine_lifecycle, is_valid_transition,
)
from iios.investment.company.opportunity.opportunity_profile import OpportunityLifecycle


_MAX_HISTORY = 30


class LifecycleTracker:
    """
    Thread-safe state machine for per-ticker lifecycle management.
    Enforces valid transition rules from opportunity_lifecycle.py.
    """

    def __init__(self) -> None:
        self._lock  = threading.RLock()
        self._state:  Dict[str, OpportunityLifecycle] = {}
        self._eval_count: Dict[str, int] = {}
        self._history: Dict[str, deque] = {}          # ticker → deque[LifecycleChange]
        self._first_seen: Dict[str, datetime] = {}

    # ── Public API ────────────────────────────────────────────────────────────

    def update(
        self,
        ticker:     str,
        score:      float,
        confidence: float,
        score_trend: float = 0.0,
    ) -> OpportunityLifecycle:
        """
        Evaluate and possibly transition the lifecycle state for *ticker*.
        Returns the new (or unchanged) state.
        """
        with self._lock:
            if ticker not in self._state:
                self._state[ticker]     = OpportunityLifecycle.DISCOVERED
                self._eval_count[ticker] = 0
                self._history[ticker]   = deque(maxlen=_MAX_HISTORY)
                self._first_seen[ticker] = datetime.now(timezone.utc)

            self._eval_count[ticker] += 1
            current = self._state[ticker]
            proposed = determine_lifecycle(
                score=score,
                confidence=confidence,
                current=current,
                evaluation_count=self._eval_count[ticker],
                score_trend=score_trend,
            )
            if proposed != current and is_valid_transition(current, proposed):
                change = LifecycleChange(
                    from_state=current,
                    to_state=proposed,
                    score_at_change=score,
                    changed_at=datetime.now(timezone.utc),
                    reason=f"score={score:.1f}, confidence={confidence:.2f}, trend={score_trend:.1f}",
                )
                self._history[ticker].append(change)
                self._state[ticker] = proposed

            return self._state[ticker]

    def force_archive(self, ticker: str) -> None:
        """Manually archive a ticker (terminal transition)."""
        with self._lock:
            if ticker in self._state:
                current = self._state[ticker]
                if current != OpportunityLifecycle.ARCHIVED:
                    change = LifecycleChange(
                        from_state=current,
                        to_state=OpportunityLifecycle.ARCHIVED,
                        score_at_change=0.0,
                        changed_at=datetime.now(timezone.utc),
                        reason="manually archived",
                    )
                    if ticker not in self._history:
                        self._history[ticker] = deque(maxlen=_MAX_HISTORY)
                    self._history[ticker].append(change)
                    self._state[ticker] = OpportunityLifecycle.ARCHIVED

    def get_state(self, ticker: str) -> Optional[OpportunityLifecycle]:
        with self._lock:
            return self._state.get(ticker)

    def get_history(self, ticker: str) -> List[LifecycleChange]:
        with self._lock:
            buf = self._history.get(ticker, deque())
            return list(buf)[::-1]   # most-recent first

    def get_evaluation_count(self, ticker: str) -> int:
        with self._lock:
            return self._eval_count.get(ticker, 0)

    def first_seen(self, ticker: str) -> Optional[datetime]:
        with self._lock:
            return self._first_seen.get(ticker)

    def known_tickers(self) -> List[str]:
        with self._lock:
            return list(self._state.keys())
