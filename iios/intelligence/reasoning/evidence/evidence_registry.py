"""
iios/intelligence/reasoning/evidence/evidence_registry.py
=========================================================
Evidence dataclass + thread-safe registry.
The Evidence model lives here so all other evidence modules can import it
without introducing circular dependencies.
"""
from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from ..reasoning_constants import (
    EvidenceStatus,
    EvidenceStrength,
    EvidenceType,
)
from ..reasoning_exceptions import EvidenceNotFoundError


# ── Evidence model ─────────────────────────────────────────────────────────────

@dataclass
class Evidence:
    """
    A single piece of evidence used during reasoning.

    Attributes
    ----------
    evidence_id    : Unique identifier.
    evidence_type  : Qualitative category (quantitative, expert, …).
    strength       : Ordinal strength rating.
    source         : Free-form source label (tool name, agent id, URL, …).
    claim          : Human-readable statement of what this evidence asserts.
    value          : Raw evidence data (any serialisable type).
    confidence     : How confident the source is in this evidence [0, 1].
    status         : Validation status.
    session_id     : Owning reasoning session (if any).
    tags           : Free-form searchable tags.
    metadata       : Caller-supplied extra fields.
    created_at     : Unix timestamp.
    validated_at   : Timestamp of last validation (or None).
    """

    evidence_id:  str                    = field(
        default_factory=lambda: str(uuid.uuid4())
    )
    evidence_type: EvidenceType          = EvidenceType.GENERIC
    strength:      EvidenceStrength      = EvidenceStrength.MODERATE
    source:        str                   = ""
    claim:         str                   = ""
    value:         Any                   = None
    confidence:    float                 = 1.0
    status:        EvidenceStatus        = EvidenceStatus.UNVALIDATED
    session_id:    str | None            = None
    tags:          list[str]             = field(default_factory=list)
    metadata:      dict[str, Any]        = field(default_factory=dict)
    created_at:    float                 = field(default_factory=time.time)
    validated_at:  float | None          = None

    # -- Properties ────────────────────────────────────────────────────────────

    @property
    def is_valid(self) -> bool:
        return self.status == EvidenceStatus.VALID

    @property
    def numeric_strength(self) -> int:
        return int(self.strength)

    @property
    def composite_score(self) -> float:
        """Combined quality score: strength × confidence (both normalised to [0,1])."""
        return (self.numeric_strength / 5.0) * max(0.0, min(1.0, self.confidence))

    # -- Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        return {
            "evidence_id":   self.evidence_id,
            "evidence_type": self.evidence_type.value,
            "strength":      self.strength.name,
            "source":        self.source,
            "claim":         self.claim,
            "value":         self.value,
            "confidence":    round(self.confidence, 4),
            "status":        self.status.value,
            "session_id":    self.session_id,
            "tags":          self.tags,
            "metadata":      self.metadata,
            "created_at":    self.created_at,
            "validated_at":  self.validated_at,
        }


# ── Registry ───────────────────────────────────────────────────────────────────

class EvidenceRegistry:
    """Thread-safe, in-memory store for Evidence items."""

    def __init__(self) -> None:
        self._store:    dict[str, Evidence]           = {}
        self._by_session: dict[str, list[str]]        = {}
        self._lock:     threading.RLock               = threading.RLock()

    # -- Write operations ──────────────────────────────────────────────────────

    def add(self, evidence: Evidence) -> None:
        with self._lock:
            self._store[evidence.evidence_id] = evidence
            if evidence.session_id:
                bucket = self._by_session.setdefault(evidence.session_id, [])
                if evidence.evidence_id not in bucket:
                    bucket.append(evidence.evidence_id)

    def remove(self, evidence_id: str) -> None:
        with self._lock:
            ev = self._store.pop(evidence_id, None)
            if ev and ev.session_id and ev.session_id in self._by_session:
                ids = self._by_session[ev.session_id]
                if evidence_id in ids:
                    ids.remove(evidence_id)

    # -- Read operations ───────────────────────────────────────────────────────

    def get(self, evidence_id: str) -> Evidence:
        with self._lock:
            ev = self._store.get(evidence_id)
        if ev is None:
            raise EvidenceNotFoundError(evidence_id)
        return ev

    def has(self, evidence_id: str) -> bool:
        with self._lock:
            return evidence_id in self._store

    def get_by_session(self, session_id: str) -> list[Evidence]:
        with self._lock:
            ids = list(self._by_session.get(session_id, []))
            return [self._store[i] for i in ids if i in self._store]

    def get_by_type(self, evidence_type: EvidenceType) -> list[Evidence]:
        with self._lock:
            return [
                e for e in self._store.values()
                if e.evidence_type == evidence_type
            ]

    def get_valid(self, session_id: str | None = None) -> list[Evidence]:
        items = (
            self.get_by_session(session_id)
            if session_id
            else list(self._store.values())
        )
        return [e for e in items if e.is_valid]

    def all(self) -> list[Evidence]:
        with self._lock:
            return list(self._store.values())

    # -- Stats ─────────────────────────────────────────────────────────────────

    def stats(self) -> dict[str, Any]:
        with self._lock:
            total   = len(self._store)
            by_type: dict[str, int] = {}
            by_status: dict[str, int] = {}
            for e in self._store.values():
                by_type[e.evidence_type.value]   = by_type.get(e.evidence_type.value, 0)   + 1
                by_status[e.status.value]         = by_status.get(e.status.value, 0)         + 1
            return {
                "total":    total,
                "by_type":  by_type,
                "by_status": by_status,
                "sessions": len(self._by_session),
            }


# ── Singleton ──────────────────────────────────────────────────────────────────

_LOCK      = threading.Lock()
_REGISTRY: EvidenceRegistry | None = None


def get_evidence_registry() -> EvidenceRegistry:
    global _REGISTRY
    if _REGISTRY is None:
        with _LOCK:
            if _REGISTRY is None:
                _REGISTRY = EvidenceRegistry()
    return _REGISTRY


def reset_evidence_registry() -> None:
    global _REGISTRY
    with _LOCK:
        _REGISTRY = None
