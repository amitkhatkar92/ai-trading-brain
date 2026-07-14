"""iios/investment/strategy/debate/evidence_registry.py
Thread-safe registry and query store for all collected evidence.
"""
from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from iios.investment.strategy.debate.debate_constants import (
    EvidenceReliability,
    EvidenceSource,
    EvidenceWeight,
)
from iios.investment.strategy.debate.evidence_score import EvidenceScore, compute_evidence_score


@dataclass
class Evidence:
    """A single piece of evidence collected for a debate session."""
    evidence_id:   str
    session_id:    str
    source:        EvidenceSource
    category:      str                    # e.g. "technical", "risk", "macro"
    title:         str
    description:   str
    raw_score:     float                  # 0–100 (directional: >50 bullish, <50 bearish)
    reliability:   EvidenceReliability
    weight:        EvidenceWeight
    relevance:     float                  # 0–1
    evidence_ts:   Optional[datetime]
    collected_at:  datetime
    score:         Optional[EvidenceScore] = None
    tags:          List[str]              = field(default_factory=list)
    metadata:      Dict[str, Any]         = field(default_factory=dict)

    def compute_score(self, decay_hours: float = 24.0) -> EvidenceScore:
        self.score = compute_evidence_score(
            self.evidence_id,
            self.raw_score,
            self.reliability,
            self.weight,
            self.evidence_ts,
            self.relevance,
            decay_hours,
        )
        return self.score

    def to_dict(self) -> Dict[str, Any]:
        return {
            "evidence_id":  self.evidence_id,
            "session_id":   self.session_id,
            "source":       self.source.value,
            "category":     self.category,
            "title":        self.title,
            "description":  self.description,
            "raw_score":    round(self.raw_score, 2),
            "reliability":  self.reliability.value,
            "weight":       self.weight.value,
            "relevance":    round(self.relevance, 3),
            "evidence_ts":  self.evidence_ts.isoformat() if self.evidence_ts else None,
            "collected_at": self.collected_at.isoformat(),
            "score":        self.score.to_dict() if self.score else None,
            "tags":         self.tags,
        }


def make_evidence(
    session_id:  str,
    source:      EvidenceSource,
    category:    str,
    title:       str,
    description: str,
    raw_score:   float,
    reliability: EvidenceReliability = EvidenceReliability.MEDIUM,
    weight:      EvidenceWeight = EvidenceWeight.MEDIUM,
    relevance:   float = 0.7,
    evidence_ts: Optional[datetime] = None,
    tags:        Optional[List[str]] = None,
    metadata:    Optional[Dict[str, Any]] = None,
) -> Evidence:
    ev = Evidence(
        evidence_id=str(uuid.uuid4()),
        session_id=session_id,
        source=source,
        category=category,
        title=title,
        description=description,
        raw_score=min(max(raw_score, 0.0), 100.0),
        reliability=reliability,
        weight=weight,
        relevance=min(max(relevance, 0.0), 1.0),
        evidence_ts=evidence_ts,
        collected_at=datetime.now(timezone.utc),
        tags=tags or [],
        metadata=metadata or {},
    )
    ev.compute_score()
    return ev


class EvidenceRegistry:
    """Thread-safe store and query interface for all debate evidence."""

    def __init__(self, session_id: str) -> None:
        self._session_id = session_id
        self._lock       = threading.RLock()
        self._store:     Dict[str, Evidence] = {}

    def add(self, evidence: Evidence) -> None:
        with self._lock:
            self._store[evidence.evidence_id] = evidence

    def add_all(self, items: List[Evidence]) -> None:
        with self._lock:
            for ev in items:
                self._store[ev.evidence_id] = ev

    def get(self, evidence_id: str) -> Optional[Evidence]:
        with self._lock:
            return self._store.get(evidence_id)

    def all(self) -> List[Evidence]:
        with self._lock:
            return list(self._store.values())

    def by_source(self, source: EvidenceSource) -> List[Evidence]:
        with self._lock:
            return [e for e in self._store.values() if e.source == source]

    def by_category(self, category: str) -> List[Evidence]:
        with self._lock:
            return [e for e in self._store.values() if e.category == category]

    def bullish(self) -> List[Evidence]:
        """Evidence with raw_score > 55 (directionally positive)."""
        with self._lock:
            return [e for e in self._store.values() if e.raw_score > 55]

    def bearish(self) -> List[Evidence]:
        """Evidence with raw_score < 45."""
        with self._lock:
            return [e for e in self._store.values() if e.raw_score < 45]

    def high_weight(self) -> List[Evidence]:
        with self._lock:
            return [
                e for e in self._store.values()
                if e.weight in (EvidenceWeight.HIGH, EvidenceWeight.CRITICAL)
            ]

    def average_weighted_score(self) -> float:
        with self._lock:
            scored = [e for e in self._store.values() if e.score is not None]
            if not scored:
                return 50.0
            return sum(e.score.weighted_score for e in scored) / len(scored)

    def count(self) -> int:
        with self._lock:
            return len(self._store)

    def ids(self) -> List[str]:
        with self._lock:
            return list(self._store.keys())
