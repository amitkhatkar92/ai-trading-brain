"""
decision_candidate_registry.py — iios.decision.optimization
============================================================
Thread-safe registry for DecisionCandidate objects.

C9 Decision Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

import threading
from typing import Dict, List, Optional

from .constants import DEFAULT_MAX_CANDIDATES
from .decision_candidate import DecisionCandidate
from .exceptions import CandidateRegistryError


class DecisionCandidateRegistry:
    """
    Thread-safe runtime store for :class:`DecisionCandidate` objects.

    Candidates are typically transient — they are loaded for a specific
    optimization run and cleared afterwards.

    Parameters
    ----------
    max_candidates : Maximum candidates the registry accepts.
    """

    def __init__(self, max_candidates: int = DEFAULT_MAX_CANDIDATES) -> None:
        self._lock        = threading.RLock()
        self._candidates: Dict[str, DecisionCandidate] = {}
        self._max         = max_candidates

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def register(self, candidate: DecisionCandidate) -> None:
        with self._lock:
            if len(self._candidates) >= self._max:
                raise CandidateRegistryError(
                    f"Registry is full (max {self._max} candidates)"
                )
            self._candidates[candidate.candidate_id] = candidate

    def register_all(self, candidates: List[DecisionCandidate]) -> None:
        for c in candidates:
            self.register(c)

    def deregister(self, candidate_id: str) -> Optional[DecisionCandidate]:
        with self._lock:
            return self._candidates.pop(candidate_id, None)

    def clear(self) -> None:
        with self._lock:
            self._candidates.clear()

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def get(self, candidate_id: str) -> Optional[DecisionCandidate]:
        with self._lock:
            return self._candidates.get(candidate_id)

    def all_candidates(self) -> List[DecisionCandidate]:
        with self._lock:
            return list(self._candidates.values())

    def count(self) -> int:
        with self._lock:
            return len(self._candidates)
