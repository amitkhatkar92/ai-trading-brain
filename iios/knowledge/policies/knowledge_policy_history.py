"""
knowledge_policy_history.py — iios.knowledge.policies
-------------------------------------------------------
KnowledgeGovernanceHistory — thread-safe bounded history of evaluation results.

C14 Enterprise Knowledge Intelligence — Phase 1, Module 3
"""
from __future__ import annotations

import threading
from typing import List

from .constants import DEFAULT_MAX_HISTORY
from .knowledge_policy_result import PolicyEvaluationResult


class KnowledgeGovernanceHistory:
    """
    Thread-safe, bounded log of PolicyEvaluationResults.

    Oldest entries are evicted when capacity is reached (FIFO eviction).
    """

    def __init__(self, max_entries: int = DEFAULT_MAX_HISTORY) -> None:
        self._max_entries = max_entries
        self._entries:    List[PolicyEvaluationResult] = []
        self._lock        = threading.Lock()

    # ------------------------------------------------------------------
    # Recording
    # ------------------------------------------------------------------

    def record(self, result: PolicyEvaluationResult) -> None:
        with self._lock:
            if len(self._entries) >= self._max_entries:
                self._entries.pop(0)
            self._entries.append(result)

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------

    def all(self) -> List[PolicyEvaluationResult]:
        with self._lock:
            return list(self._entries)

    def recent(self, n: int = 50) -> List[PolicyEvaluationResult]:
        with self._lock:
            return list(self._entries[-n:])

    def for_policy_id(self, policy_id: str) -> List[PolicyEvaluationResult]:
        with self._lock:
            return [e for e in self._entries if e.policy_id == policy_id]

    def count(self) -> int:
        with self._lock:
            return len(self._entries)

    # ------------------------------------------------------------------
    # Maintenance
    # ------------------------------------------------------------------

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()
