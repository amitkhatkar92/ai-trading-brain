"""iios/investment/decision/evidence/evidence_item.py
EvidenceItem — the atomic, immutable unit of evidence.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from iios.investment.decision.evidence.evidence_constants import (
    EvidenceCategory,
    EvidencePriority,
    EvidenceSourceType,
)


@dataclass(frozen=True)
class EvidenceItem:
    """
    One atomic piece of evidence from one source.

    Immutable by design — evidence is never mutated after creation.
    The engine may derive NEW items (e.g. normalized copies) but always
    traces them back to the original via trace_id.
    """
    evidence_id:     str
    decision_id:     str
    source_type:     EvidenceSourceType
    source_provider: str                # provider name (e.g. "MarketEvidenceProvider")
    subject_id:      str                # subject of the decision (e.g. ticker, portfolio_id)
    subject_type:    str                # "equity" | "portfolio" | "strategy" | ...
    category:        EvidenceCategory
    key:             str                # e.g. "pe_ratio" | "rsi_14" | "news_sentiment_score"
    value:           Any                # raw value — never modified, preserved for auditability
    unit:            str                # "%" | "x" | "points" | "" etc.
    timestamp:       datetime           # when source generated this data
    collected_at:    datetime           # when this engine collected it
    confidence:      float              # 0–100 from source
    freshness_score: float              # 0–1 (1 = fresh, 0 = very stale)
    priority:        EvidencePriority
    is_required:     bool               # must be present for decision to proceed
    version:         str                # evidence schema version
    trace_id:        str                # traceability to originating intelligence record
    tags:            tuple              # optional free-form tags
    metadata:        Dict[str, Any]     # source-specific extra data

    @property
    def age_seconds(self) -> float:
        now = datetime.now(timezone.utc)
        return max(0.0, (now - self.timestamp).total_seconds())

    @property
    def is_fresh(self) -> bool:
        from iios.investment.decision.evidence.evidence_constants import EVIDENCE_FRESHNESS_WARN_SECONDS
        return self.age_seconds <= EVIDENCE_FRESHNESS_WARN_SECONDS

    @property
    def is_stale(self) -> bool:
        from iios.investment.decision.evidence.evidence_constants import EVIDENCE_FRESHNESS_STALE_SECONDS
        return self.age_seconds > EVIDENCE_FRESHNESS_STALE_SECONDS

    def to_dict(self) -> Dict[str, Any]:
        return {
            "evidence_id":     self.evidence_id,
            "decision_id":     self.decision_id,
            "source_type":     self.source_type.value,
            "source_provider": self.source_provider,
            "subject_id":      self.subject_id,
            "subject_type":    self.subject_type,
            "category":        self.category.value,
            "key":             self.key,
            "value":           self.value,
            "unit":            self.unit,
            "timestamp":       self.timestamp.isoformat(),
            "collected_at":    self.collected_at.isoformat(),
            "confidence":      round(self.confidence, 2),
            "freshness_score": round(self.freshness_score, 4),
            "priority":        self.priority.value,
            "is_required":     self.is_required,
            "version":         self.version,
            "trace_id":        self.trace_id,
            "tags":            list(self.tags),
            "metadata":        self.metadata,
        }


def make_evidence_item(
    decision_id:     str,
    source_type:     EvidenceSourceType,
    source_provider: str,
    subject_id:      str,
    subject_type:    str,
    category:        EvidenceCategory,
    key:             str,
    value:           Any,
    unit:            str                = "",
    confidence:      float              = 70.0,
    freshness_score: float              = 1.0,
    priority:        EvidencePriority   = EvidencePriority.MEDIUM,
    is_required:     bool               = False,
    version:         str                = "1.0",
    trace_id:        Optional[str]      = None,
    timestamp:       Optional[datetime] = None,
    tags:            tuple              = (),
    metadata:        Optional[Dict[str, Any]] = None,
) -> EvidenceItem:
    now = datetime.now(timezone.utc)
    return EvidenceItem(
        evidence_id=str(uuid.uuid4()),
        decision_id=decision_id,
        source_type=source_type,
        source_provider=source_provider,
        subject_id=subject_id,
        subject_type=subject_type,
        category=category,
        key=key,
        value=value,
        unit=unit,
        timestamp=timestamp or now,
        collected_at=now,
        confidence=max(0.0, min(100.0, confidence)),
        freshness_score=max(0.0, min(1.0, freshness_score)),
        priority=priority,
        is_required=is_required,
        version=version,
        trace_id=trace_id or str(uuid.uuid4()),
        tags=tags,
        metadata=metadata or {},
    )
