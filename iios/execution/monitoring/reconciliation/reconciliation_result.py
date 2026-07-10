"""iios/execution/monitoring/reconciliation/reconciliation_result.py"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from iios.execution.monitoring.monitoring_constants import (
    AlertSeverity,
    DiscrepancyType,
    EntityType,
    ReconciliationStatus,
)


@dataclass
class Discrepancy:
    """One field-level discrepancy found during reconciliation."""

    discrepancy_type:  DiscrepancyType
    field_name:        str          = ""
    internal_value:    Any          = None
    external_value:    Any          = None
    severity:          AlertSeverity = AlertSeverity.HIGH
    description:       str          = ""
    discrepancy_id:    str          = field(default_factory=lambda: str(uuid.uuid4()))

    def to_dict(self) -> dict[str, Any]:
        return {
            "discrepancy_id":   self.discrepancy_id,
            "discrepancy_type": self.discrepancy_type.value,
            "field_name":       self.field_name,
            "internal_value":   self.internal_value,
            "external_value":   self.external_value,
            "severity":         self.severity.value,
            "description":      self.description,
        }


@dataclass
class ReconciliationResult:
    """
    Comparison outcome for a single entity (order / trade / position).
    One result per entity pair.
    """

    entity_type:       EntityType          = EntityType.ORDER
    internal_id:       str                 = ""
    external_id:       str                 = ""
    status:            ReconciliationStatus = ReconciliationStatus.MATCHED
    discrepancies:     list[Discrepancy]   = field(default_factory=list)
    internal_record:   dict[str, Any]      = field(default_factory=dict)
    external_record:   dict[str, Any]      = field(default_factory=dict)
    result_id:         str                 = field(default_factory=lambda: str(uuid.uuid4()))
    reconciled_at:     float               = field(default_factory=time.time)
    metadata:          dict[str, Any]      = field(default_factory=dict)

    def has_discrepancies(self) -> bool:
        return len(self.discrepancies) > 0

    def critical_discrepancies(self) -> list[Discrepancy]:
        return [d for d in self.discrepancies if d.severity == AlertSeverity.CRITICAL]

    def to_dict(self) -> dict[str, Any]:
        return {
            "result_id":       self.result_id,
            "entity_type":     self.entity_type.value,
            "internal_id":     self.internal_id,
            "external_id":     self.external_id,
            "status":          self.status.value,
            "discrepancies":   [d.to_dict() for d in self.discrepancies],
            "discrepancy_count": len(self.discrepancies),
            "reconciled_at":   self.reconciled_at,
            "metadata":        self.metadata,
        }
