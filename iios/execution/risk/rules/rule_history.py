"""iios/execution/risk/rules/rule_history.py
==================================================
RuleHistory — thread-safe, bounded record of rule execution results.

C6 Execution Intelligence — Phase 4, Module 3
"""
from __future__ import annotations

import threading
from typing import List

from .constants import DEFAULT_MAX_HISTORY, RuleOutcome
from .rule_result import RuleResult


class RuleHistory:
    """
    Thread-safe, bounded, append-only history of ``RuleResult`` records.

    When capacity is reached, the oldest entry is evicted.
    """

    def __init__(self, max_size: int = DEFAULT_MAX_HISTORY) -> None:
        self._max      = max(1, max_size)
        self._results: List[RuleResult] = []
        self._evicted  = 0
        self._lock     = threading.Lock()

    # ── Write ─────────────────────────────────────────────────────────────────

    def append(self, result: RuleResult) -> None:
        with self._lock:
            if len(self._results) >= self._max:
                self._results.pop(0)
                self._evicted += 1
            self._results.append(result)

    # ── Read ──────────────────────────────────────────────────────────────────

    def all(self) -> List[RuleResult]:
        with self._lock:
            return list(self._results)

    def latest(self, n: int = 10) -> List[RuleResult]:
        """Most recent *n* results, newest first."""
        with self._lock:
            return list(reversed(self._results[-n:]))

    def by_rule(self, rule_id: str) -> List[RuleResult]:
        with self._lock:
            return [r for r in self._results if r.rule_id == rule_id]

    def by_outcome(self, outcome: RuleOutcome) -> List[RuleResult]:
        with self._lock:
            return [r for r in self._results if r.outcome == outcome]

    def failed(self) -> List[RuleResult]:
        with self._lock:
            return [r for r in self._results if r.failed]

    def blocked(self) -> List[RuleResult]:
        with self._lock:
            return [r for r in self._results if r.blocked]

    def warned(self) -> List[RuleResult]:
        with self._lock:
            return [r for r in self._results if r.warned]

    # ── Counts ────────────────────────────────────────────────────────────────

    @property
    def total(self) -> int:
        """Total appended (including evicted)."""
        with self._lock:
            return len(self._results) + self._evicted

    @property
    def evicted(self) -> int:
        with self._lock:
            return self._evicted

    def __len__(self) -> int:
        with self._lock:
            return len(self._results)

    def is_empty(self) -> bool:
        with self._lock:
            return len(self._results) == 0
