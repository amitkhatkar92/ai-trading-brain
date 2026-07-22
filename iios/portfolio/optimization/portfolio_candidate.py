"""
portfolio_candidate.py — iios.portfolio.optimization
======================================================
Portfolio candidate domain object.

A PortfolioCandidate is a policy-approved portfolio configuration
submitted to the optimization framework for evaluation and ranking.

C10 Portfolio Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

import time
import uuid
from typing import Any, Dict, Optional

from .constants import CandidateStatus, VERSION


class PortfolioCandidate:
    """
    Mutable portfolio candidate submitted for optimization.

    Parameters
    ----------
    candidate_id :   Unique identifier (auto-generated UUID if omitted/empty).
    portfolio_id :   Portfolio this candidate belongs to.
    inputs :         Input data dict (snapshots, allocation hints, etc.).
    status :         Initial status (default: APPROVED, ready for evaluation).
    metadata :       Supplementary metadata.
    """

    def __init__(
        self,
        candidate_id: str = "",
        portfolio_id: str = "",
        *,
        inputs:   Optional[Dict[str, Any]] = None,
        status:   CandidateStatus = CandidateStatus.APPROVED,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        self._candidate_id = candidate_id or str(uuid.uuid4())
        self._portfolio_id = portfolio_id
        self._inputs       = dict(inputs or {})
        self._status       = status
        self._metadata     = dict(metadata or {})
        self._score:  float = 0.0
        self._rank:   int   = 0
        self._created_at:   float = time.time()
        self._evaluated_at: Optional[float] = None

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def candidate_id(self) -> str:
        return self._candidate_id

    @property
    def portfolio_id(self) -> str:
        return self._portfolio_id

    @property
    def inputs(self) -> Dict[str, Any]:
        return dict(self._inputs)

    @property
    def status(self) -> CandidateStatus:
        return self._status

    @property
    def score(self) -> float:
        return self._score

    @property
    def rank(self) -> int:
        return self._rank

    @property
    def is_approved(self) -> bool:
        return self._status == CandidateStatus.APPROVED

    @property
    def is_selected(self) -> bool:
        return self._status == CandidateStatus.SELECTED

    @property
    def created_at(self) -> float:
        return self._created_at

    @property
    def evaluated_at(self) -> Optional[float]:
        return self._evaluated_at

    # ------------------------------------------------------------------
    # Mutators
    # ------------------------------------------------------------------

    def set_score(self, score: float) -> None:
        self._score       = max(0.0, min(1.0, score))
        self._evaluated_at = time.time()

    def set_rank(self, rank: int) -> None:
        self._rank = rank

    def select(self) -> None:
        self._status = CandidateStatus.SELECTED

    def reject(self) -> None:
        self._status = CandidateStatus.REJECTED

    def discard(self) -> None:
        self._status = CandidateStatus.DISCARDED

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        return {
            "candidate_id": self._candidate_id,
            "portfolio_id": self._portfolio_id,
            "status":       self._status.value,
            "score":        self._score,
            "rank":         self._rank,
            "input_keys":   sorted(self._inputs.keys()),
            "created_at":   self._created_at,
        }

    def __repr__(self) -> str:
        return (
            f"PortfolioCandidate(id={self._candidate_id!r}, "
            f"portfolio={self._portfolio_id!r}, score={self._score:.3f}, "
            f"status={self._status.value!r})"
        )
