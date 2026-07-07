"""
iios/knowledge/governance/models/quality_violation.py
======================================================
QualityViolation — a single quality rule violation detected on a
knowledge record during validation or monitoring.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

from ..quality_constants import (
    QualityDimension,
    ViolationSeverity,
    ViolationType,
)

__all__ = ["QualityViolation"]


@dataclass
class QualityViolation:
    """Describes one quality rule violation on a knowledge record."""

    violation_id:  str                = field(default_factory=lambda: str(uuid.uuid4()))
    knowledge_id:  str                = ""
    violation_type:ViolationType      = ViolationType.MISSING_FIELD
    severity:      ViolationSeverity  = ViolationSeverity.MEDIUM
    dimension:     QualityDimension   = QualityDimension.COMPLETENESS
    field_name:    str                = ""   # affected field, empty if record-level
    message:       str                = ""
    suggestion:    str                = ""   # remediation hint
    details:       dict[str, Any]     = field(default_factory=dict)
    detected_at:   float              = field(default_factory=time.time)
    resolved:      bool               = False
    resolved_at:   Optional[float]    = None

    # ── Convenience properties ────────────────────────────────────────────────

    @property
    def is_critical(self) -> bool:
        return self.severity == ViolationSeverity.CRITICAL

    @property
    def blocks_approval(self) -> bool:
        return self.severity in (ViolationSeverity.CRITICAL,)

    def resolve(self) -> None:
        self.resolved    = True
        self.resolved_at = time.time()

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        return {
            "violation_id":   self.violation_id,
            "knowledge_id":   self.knowledge_id,
            "violation_type": self.violation_type.value,
            "severity":       self.severity.value,
            "dimension":      self.dimension.value,
            "field_name":     self.field_name,
            "message":        self.message,
            "suggestion":     self.suggestion,
            "details":        dict(self.details),
            "detected_at":    self.detected_at,
            "resolved":       self.resolved,
            "resolved_at":    self.resolved_at,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "QualityViolation":
        return cls(
            violation_id   = d.get("violation_id",   str(uuid.uuid4())),
            knowledge_id   = d.get("knowledge_id",   ""),
            violation_type = ViolationType(d.get("violation_type",
                                                  ViolationType.MISSING_FIELD.value)),
            severity       = ViolationSeverity(d.get("severity",
                                                      ViolationSeverity.MEDIUM.value)),
            dimension      = QualityDimension(d.get("dimension",
                                                     QualityDimension.COMPLETENESS.value)),
            field_name     = d.get("field_name",  ""),
            message        = d.get("message",     ""),
            suggestion     = d.get("suggestion",  ""),
            details        = dict(d.get("details", {})),
            detected_at    = d.get("detected_at", time.time()),
            resolved       = d.get("resolved",    False),
            resolved_at    = d.get("resolved_at"),
        )
