"""
iios/intelligence/reasoning/evidence/evidence_manager.py
========================================================
High-level façade that unifies all evidence operations for a session.
"""
from __future__ import annotations

import threading
import uuid
from typing import Any

from ..reasoning_constants import EvidenceStrength, EvidenceType
from ..reasoning_exceptions import InsufficientEvidenceError
from .evidence_chain import EvidenceChain
from .evidence_graph import EvidenceGraph, EvidenceEdge
from .evidence_ranker import EvidenceRanker, RankedEvidence
from .evidence_registry import Evidence, EvidenceRegistry, get_evidence_registry
from .evidence_validator import EvidenceValidator, ValidationResult
from ..reasoning_constants import EvidenceRelation


class EvidenceManager:
    """
    One-stop shop for evidence lifecycle management.

    Injects:
    --------
    registry  : EvidenceRegistry  – storage
    validator : EvidenceValidator  – validation
    ranker    : EvidenceRanker     – ranking
    """

    def __init__(
        self,
        registry:  EvidenceRegistry  | None = None,
        validator: EvidenceValidator  | None = None,
        ranker:    EvidenceRanker     | None = None,
    ) -> None:
        self._registry  = registry  or get_evidence_registry()
        self._validator = validator or EvidenceValidator()
        self._ranker    = ranker    or EvidenceRanker()
        self._graphs:   dict[str, EvidenceGraph]  = {}   # keyed by session_id
        self._chains:   dict[str, EvidenceChain]  = {}   # keyed by chain_id
        self._lock:     threading.RLock            = threading.RLock()

    # ── Add / remove ───────────────────────────────────────────────────────────

    def add(
        self,
        *,
        evidence_type: EvidenceType    = EvidenceType.GENERIC,
        strength:      EvidenceStrength = EvidenceStrength.MODERATE,
        source:        str              = "",
        claim:         str              = "",
        value:         Any              = None,
        confidence:    float            = 1.0,
        session_id:    str | None       = None,
        tags:          list[str]        = (),  # type: ignore[assignment]
        metadata:      dict[str, Any]   = (),  # type: ignore[assignment]
        evidence_id:   str | None       = None,
    ) -> Evidence:
        ev = Evidence(
            evidence_id   = evidence_id or str(uuid.uuid4()),
            evidence_type = evidence_type,
            strength      = strength,
            source        = source,
            claim         = claim,
            value         = value,
            confidence    = confidence,
            session_id    = session_id,
            tags          = list(tags),
            metadata      = dict(metadata),
        )
        self._registry.add(ev)
        # Auto-wire into the session graph
        if session_id:
            with self._lock:
                g = self._graphs.setdefault(session_id, EvidenceGraph())
            g.add_node(ev.evidence_id)
        return ev

    def remove(self, evidence_id: str) -> None:
        self._registry.remove(evidence_id)

    # ── Retrieval ─────────────────────────────────────────────────────────────

    def get(self, evidence_id: str) -> Evidence:
        return self._registry.get(evidence_id)

    def get_by_session(self, session_id: str) -> list[Evidence]:
        return self._registry.get_by_session(session_id)

    def get_valid(self, session_id: str | None = None) -> list[Evidence]:
        return self._registry.get_valid(session_id)

    # ── Validation ────────────────────────────────────────────────────────────

    def validate(
        self, evidence_id: str, *, raise_on_failure: bool = False
    ) -> ValidationResult:
        ev = self._registry.get(evidence_id)
        return self._validator.validate(ev, raise_on_failure=raise_on_failure)

    def validate_session(
        self, session_id: str, *, raise_on_failure: bool = False
    ) -> list[ValidationResult]:
        items = self._registry.get_by_session(session_id)
        return self._validator.validate_many(items, raise_on_failure=raise_on_failure)

    def detect_conflicts(
        self, session_id: str, *, mark_conflicting: bool = True
    ) -> list[tuple[str, str]]:
        items = self._registry.get_by_session(session_id)
        return self._validator.detect_conflicts(
            items, mark_conflicting=mark_conflicting
        )

    # ── Ranking ────────────────────────────────────────────────────────────────

    def rank(
        self,
        session_id: str,
        *,
        valid_only: bool       = False,
        top_n:      int | None = None,
    ) -> list[RankedEvidence]:
        items = self._registry.get_by_session(session_id)
        return self._ranker.rank(items, valid_only=valid_only, top_n=top_n)

    # ── Graph ─────────────────────────────────────────────────────────────────

    def add_graph_edge(
        self,
        session_id: str,
        from_id:    str,
        to_id:      str,
        relation:   EvidenceRelation = EvidenceRelation.SUPPORTS,
        weight:     float            = 1.0,
    ) -> EvidenceEdge:
        with self._lock:
            g = self._graphs.setdefault(session_id, EvidenceGraph())
        return g.add_edge(from_id, to_id, relation, weight)

    def get_graph(self, session_id: str) -> EvidenceGraph | None:
        with self._lock:
            return self._graphs.get(session_id)

    # ── Chain ─────────────────────────────────────────────────────────────────

    def create_chain(
        self, session_id: str, initial_claim: str = ""
    ) -> EvidenceChain:
        chain = EvidenceChain(session_id=session_id, initial_claim=initial_claim)
        with self._lock:
            self._chains[chain.chain_id] = chain
        return chain

    def get_chain(self, chain_id: str) -> EvidenceChain | None:
        with self._lock:
            return self._chains.get(chain_id)

    # ── Aggregate helpers ─────────────────────────────────────────────────────

    def mean_confidence(self, session_id: str) -> float:
        """Average confidence across all evidence in the session."""
        items = self._registry.get_by_session(session_id)
        if not items:
            return 0.0
        return sum(e.confidence for e in items) / len(items)

    def require_evidence(
        self, session_id: str, minimum: int = 1
    ) -> None:
        """Raise InsufficientEvidenceError if session has fewer than *minimum* items."""
        n = len(self._registry.get_by_session(session_id))
        if n < minimum:
            raise InsufficientEvidenceError(minimum, n)

    # ── Stats ─────────────────────────────────────────────────────────────────

    def stats(self) -> dict[str, Any]:
        reg_stats = self._registry.stats()
        with self._lock:
            reg_stats["graphs"] = len(self._graphs)
            reg_stats["chains"] = len(self._chains)
        return reg_stats


# ── Singleton ──────────────────────────────────────────────────────────────────

_LOCK    = threading.Lock()
_MANAGER: EvidenceManager | None = None


def get_evidence_manager() -> EvidenceManager:
    global _MANAGER
    if _MANAGER is None:
        with _LOCK:
            if _MANAGER is None:
                _MANAGER = EvidenceManager()
    return _MANAGER


def reset_evidence_manager() -> None:
    global _MANAGER
    with _LOCK:
        _MANAGER = None
