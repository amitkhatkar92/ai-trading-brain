"""
portfolio_candidate_registry.py — iios.portfolio.optimization
=============================================================
Thread-safe, bounded registry for portfolio optimization candidates.

C10 Portfolio Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

import threading
from typing import Dict, List, Optional

from .constants import CandidateStatus, DEFAULT_MAX_CANDIDATES
from .exceptions import (
    PortfolioOptimizationCapacityError,
    PortfolioOptimizationNotFoundError,
)
from .portfolio_candidate import PortfolioCandidate


class PortfolioCandidateRegistry:
    """
    Thread-safe, bounded store for portfolio candidates.

    Parameters
    ----------
    max_candidates : Hard upper bound on stored candidates.
    """

    def __init__(self, max_candidates: int = DEFAULT_MAX_CANDIDATES) -> None:
        self._max = max_candidates
        self._store: Dict[str, PortfolioCandidate] = {}
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Mutation
    # ------------------------------------------------------------------

    def register(self, candidate: PortfolioCandidate) -> None:
        """Register a candidate.  Raises PortfolioOptimizationCapacityError if full."""
        with self._lock:
            if (
                len(self._store) >= self._max
                and candidate.candidate_id not in self._store
            ):
                raise PortfolioOptimizationCapacityError(
                    self._max, resource="candidate registry"
                )
            self._store[candidate.candidate_id] = candidate

    def remove(self, candidate_id: str) -> None:
        """Remove a candidate.  Raises PortfolioOptimizationNotFoundError if missing."""
        with self._lock:
            if candidate_id not in self._store:
                raise PortfolioOptimizationNotFoundError(
                    candidate_id, item_type="candidate"
                )
            del self._store[candidate_id]

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get(self, candidate_id: str) -> Optional[PortfolioCandidate]:
        with self._lock:
            return self._store.get(candidate_id)

    def get_or_raise(self, candidate_id: str) -> PortfolioCandidate:
        cand = self.get(candidate_id)
        if cand is None:
            raise PortfolioOptimizationNotFoundError(
                candidate_id, item_type="candidate"
            )
        return cand

    def all(self) -> List[PortfolioCandidate]:
        with self._lock:
            return list(self._store.values())

    def approved(self) -> List[PortfolioCandidate]:
        with self._lock:
            return [
                c for c in self._store.values()
                if c.status == CandidateStatus.APPROVED
            ]

    def for_portfolio(self, portfolio_id: str) -> List[PortfolioCandidate]:
        with self._lock:
            return [
                c for c in self._store.values()
                if c.portfolio_id == portfolio_id
            ]

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def count(self) -> int:
        with self._lock:
            return len(self._store)

    @property
    def is_empty(self) -> bool:
        return self.count == 0

    def __contains__(self, candidate_id: str) -> bool:
        with self._lock:
            return candidate_id in self._store
