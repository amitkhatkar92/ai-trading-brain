"""iios/execution/risk/controls/risk_control_history.py
==================================================
ControlHistory — bounded, thread-safe decision history store.

C6 Execution Intelligence — Phase 4, Module 4
"""
from __future__ import annotations

import threading
from collections import deque
from typing import List, Optional

from .constants import ControlAction, DEFAULT_MAX_HISTORY
from .risk_control_decision import RiskControlDecision


class ControlHistory:
    """
    Thread-safe, bounded store for RiskControlDecision objects.

    When capacity is reached the oldest entry is evicted (FIFO).
    """

    def __init__(self, max_size: int = DEFAULT_MAX_HISTORY) -> None:
        self._max_size = max_size
        self._store:   deque = deque()
        self._evicted: int   = 0
        self._lock            = threading.Lock()

    # ── Mutation ──────────────────────────────────────────────────────────────

    def append(self, decision: RiskControlDecision) -> None:
        with self._lock:
            if len(self._store) >= self._max_size:
                self._store.popleft()
                self._evicted += 1
            self._store.append(decision)

    # ── Reads ─────────────────────────────────────────────────────────────────

    def all(self) -> List[RiskControlDecision]:
        with self._lock:
            return list(self._store)

    def latest(self, n: int) -> List[RiskControlDecision]:
        with self._lock:
            items = list(self._store)
        return items[-n:] if n < len(items) else items

    def by_action(self, action: ControlAction) -> List[RiskControlDecision]:
        with self._lock:
            return [d for d in self._store if d.action == action]

    def blocked(self) -> List[RiskControlDecision]:
        with self._lock:
            return [d for d in self._store if d.blocked]

    def allowed(self) -> List[RiskControlDecision]:
        with self._lock:
            return [d for d in self._store if d.allowed]

    def emergencies(self) -> List[RiskControlDecision]:
        with self._lock:
            return [d for d in self._store if d.is_emergency]

    def overridden(self) -> List[RiskControlDecision]:
        with self._lock:
            return [d for d in self._store if d.was_overridden]

    def by_evaluation(self, evaluation_id: str) -> List[RiskControlDecision]:
        with self._lock:
            return [d for d in self._store if d.evaluation_id == evaluation_id]

    def by_execution(self, execution_id: str) -> List[RiskControlDecision]:
        with self._lock:
            return [d for d in self._store if d.execution_id == execution_id]

    def get(self, decision_id: str) -> Optional[RiskControlDecision]:
        with self._lock:
            for d in self._store:
                if d.decision_id == decision_id:
                    return d
        return None

    # ── Properties ───────────────────────────────────────────────────────────

    @property
    def total(self) -> int:
        with self._lock:
            return len(self._store)

    @property
    def evicted(self) -> int:
        with self._lock:
            return self._evicted

    def is_empty(self) -> bool:
        with self._lock:
            return len(self._store) == 0

    def __len__(self) -> int:
        return self.total
