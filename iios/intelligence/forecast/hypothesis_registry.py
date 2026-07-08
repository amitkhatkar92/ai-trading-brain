"""
iios/intelligence/forecast/hypothesis_registry.py
=================================================
Hypothesis dataclass + thread-safe registry.
The Hypothesis model lives here so subpackages can import it
without circular dependencies.
"""
from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from .hypothesis_constants import (
    HypothesisStatus,
    HypothesisType,
    DEFAULT_HYPOTHESIS_TTL_S,
    DEFAULT_PRIOR_PROBABILITY,
    MAX_HYPOTHESES,
)
from .hypothesis_exceptions import (
    HypothesisNotFoundError,
    HypothesisAlreadyExistsError,
    HypothesisExpiredError,
)


@dataclass
class Hypothesis:
    """
    A testable proposition with associated evidence and lifecycle state.

    Attributes
    ----------
    hypothesis_id   : Unique identifier.
    statement       : Human-readable proposition (the hypothesis text).
    hypothesis_type : Semantic category.
    status          : Current lifecycle status.
    probability     : Current probability estimate [0, 1] (Bayesian posterior).
    confidence      : Confidence in the probability estimate [0, 1].
    evidence_ids    : Supporting/opposing evidence item IDs.
    forecast_ids    : Forecasts generated under this hypothesis.
    parent_id       : Parent hypothesis (for derived hypotheses).
    tags            : Searchable tags.
    ttl_s           : Time-to-live in seconds (0 = never expires).
    metadata        : Caller-supplied extras.
    created_at      : Unix timestamp.
    updated_at      : Last mutation timestamp.
    """

    hypothesis_id:   str                 = field(default_factory=lambda: str(uuid.uuid4()))
    statement:       str                 = ""
    hypothesis_type: HypothesisType      = HypothesisType.GENERIC
    status:          HypothesisStatus    = HypothesisStatus.DRAFT
    probability:     float               = DEFAULT_PRIOR_PROBABILITY
    confidence:      float               = 0.0
    evidence_ids:    list[str]           = field(default_factory=list)
    forecast_ids:    list[str]           = field(default_factory=list)
    parent_id:       str | None          = None
    tags:            list[str]           = field(default_factory=list)
    ttl_s:           float               = DEFAULT_HYPOTHESIS_TTL_S
    metadata:        dict[str, Any]      = field(default_factory=dict)
    created_at:      float               = field(default_factory=time.time)
    updated_at:      float               = field(default_factory=time.time)

    # -- Properties ────────────────────────────────────────────────────────────

    @property
    def is_active(self) -> bool:
        return self.status in (
            HypothesisStatus.ACTIVE,
            HypothesisStatus.TESTING,
        )

    @property
    def is_terminal(self) -> bool:
        return self.status in (
            HypothesisStatus.CONFIRMED,
            HypothesisStatus.REJECTED,
            HypothesisStatus.RETIRED,
            HypothesisStatus.ARCHIVED,
        )

    @property
    def is_expired(self) -> bool:
        if self.ttl_s <= 0:
            return False
        return time.time() - self.created_at > self.ttl_s

    def touch(self) -> None:
        self.updated_at = time.time()

    def add_evidence(self, evidence_id: str) -> None:
        if evidence_id not in self.evidence_ids:
            self.evidence_ids.append(evidence_id)
            self.touch()

    def add_forecast(self, forecast_id: str) -> None:
        if forecast_id not in self.forecast_ids:
            self.forecast_ids.append(forecast_id)
            self.touch()

    # -- Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        return {
            "hypothesis_id":   self.hypothesis_id,
            "statement":       self.statement,
            "hypothesis_type": self.hypothesis_type.value,
            "status":          self.status.value,
            "probability":     round(self.probability, 4),
            "confidence":      round(self.confidence, 4),
            "evidence_count":  len(self.evidence_ids),
            "forecast_count":  len(self.forecast_ids),
            "parent_id":       self.parent_id,
            "tags":            self.tags,
            "ttl_s":           self.ttl_s,
            "is_expired":      self.is_expired,
            "metadata":        self.metadata,
            "created_at":      self.created_at,
            "updated_at":      self.updated_at,
        }


# ── Registry ───────────────────────────────────────────────────────────────────

class HypothesisRegistry:
    """Thread-safe in-memory store for Hypothesis objects."""

    def __init__(self) -> None:
        self._store:    dict[str, Hypothesis]      = {}
        self._by_type:  dict[str, list[str]]       = {}
        self._by_status: dict[str, list[str]]      = {}
        self._lock:     threading.RLock             = threading.RLock()

    # -- Write ─────────────────────────────────────────────────────────────────

    def add(
        self,
        hypothesis: Hypothesis,
        overwrite:  bool = False,
    ) -> None:
        with self._lock:
            if not overwrite and hypothesis.hypothesis_id in self._store:
                raise HypothesisAlreadyExistsError(hypothesis.hypothesis_id)
            if len(self._store) >= MAX_HYPOTHESES and hypothesis.hypothesis_id not in self._store:
                raise OverflowError(
                    f"HypothesisRegistry is full (max {MAX_HYPOTHESES})"
                )
            self._store[hypothesis.hypothesis_id] = hypothesis
            # index by type
            t = hypothesis.hypothesis_type.value
            if hypothesis.hypothesis_id not in self._by_type.setdefault(t, []):
                self._by_type[t].append(hypothesis.hypothesis_id)

    def remove(self, hypothesis_id: str) -> None:
        with self._lock:
            h = self._store.pop(hypothesis_id, None)
            if h:
                t = h.hypothesis_type.value
                if t in self._by_type and hypothesis_id in self._by_type[t]:
                    self._by_type[t].remove(hypothesis_id)

    # -- Read ──────────────────────────────────────────────────────────────────

    def get(self, hypothesis_id: str) -> Hypothesis:
        with self._lock:
            h = self._store.get(hypothesis_id)
        if h is None:
            raise HypothesisNotFoundError(hypothesis_id)
        return h

    def has(self, hypothesis_id: str) -> bool:
        with self._lock:
            return hypothesis_id in self._store

    def get_by_type(self, hypothesis_type: HypothesisType) -> list[Hypothesis]:
        with self._lock:
            ids = list(self._by_type.get(hypothesis_type.value, []))
            return [self._store[i] for i in ids if i in self._store]

    def get_by_status(self, status: HypothesisStatus) -> list[Hypothesis]:
        with self._lock:
            return [
                h for h in self._store.values() if h.status == status
            ]

    def get_active(self) -> list[Hypothesis]:
        with self._lock:
            return [h for h in self._store.values() if h.is_active]

    def all(self) -> list[Hypothesis]:
        with self._lock:
            return list(self._store.values())

    # -- Stats ─────────────────────────────────────────────────────────────────

    def stats(self) -> dict[str, Any]:
        with self._lock:
            by_status: dict[str, int] = {}
            for h in self._store.values():
                by_status[h.status.value] = by_status.get(h.status.value, 0) + 1
            return {
                "total":     len(self._store),
                "active":    sum(1 for h in self._store.values() if h.is_active),
                "by_status": by_status,
            }


# ── Singleton ──────────────────────────────────────────────────────────────────

_LOCK:     threading.Lock             = threading.Lock()
_REGISTRY: HypothesisRegistry | None = None


def get_hypothesis_registry() -> HypothesisRegistry:
    global _REGISTRY
    if _REGISTRY is None:
        with _LOCK:
            if _REGISTRY is None:
                _REGISTRY = HypothesisRegistry()
    return _REGISTRY


def reset_hypothesis_registry() -> None:
    global _REGISTRY
    with _LOCK:
        _REGISTRY = None
