"""
iios/intelligence/governance/explainability/evidence_trace.py
=============================================================
EvidenceTraceRecord — tracks what evidence contributed to a quality decision.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass
class EvidenceItem:
    """One piece of evidence referenced in a governance evaluation."""

    evidence_id:  str
    evidence_type: str              = "generic"
    source:       str               = ""
    strength:     float             = 0.5    # [0, 1]
    direction:    str               = "supporting"  # supporting | opposing | neutral
    description:  str               = ""
    metadata:     dict[str, Any]    = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "evidence_id":   self.evidence_id,
            "evidence_type": self.evidence_type,
            "source":        self.source,
            "strength":      round(self.strength, 4),
            "direction":     self.direction,
            "description":   self.description,
        }


@dataclass
class EvidenceTraceRecord:
    """
    Aggregated evidence trace for one governance evaluation.
    """

    trace_id:         str                   = field(default_factory=lambda: str(uuid.uuid4()))
    record_id:        str                   = ""
    product_id:       str                   = ""
    items:            list[EvidenceItem]    = field(default_factory=list)
    supporting_count: int                   = 0
    opposing_count:   int                   = 0
    net_strength:     float                 = 0.0
    summary:          str                   = ""
    created_at:       float                 = field(default_factory=time.time)

    def add_item(self, item: EvidenceItem) -> None:
        self.items.append(item)
        self.supporting_count = sum(
            1 for e in self.items if e.direction == "supporting"
        )
        self.opposing_count = sum(
            1 for e in self.items if e.direction == "opposing"
        )
        self.net_strength = (
            sum(e.strength for e in self.items if e.direction == "supporting")
            - sum(e.strength for e in self.items if e.direction == "opposing")
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "trace_id":         self.trace_id,
            "record_id":        self.record_id,
            "product_id":       self.product_id,
            "items":            [i.to_dict() for i in self.items],
            "supporting_count": self.supporting_count,
            "opposing_count":   self.opposing_count,
            "net_strength":     round(self.net_strength, 4),
            "summary":          self.summary,
            "created_at":       self.created_at,
        }
