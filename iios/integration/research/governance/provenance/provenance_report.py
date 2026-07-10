"""provenance/provenance_report.py — Provenance audit report for an entity."""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

from iios.integration.research.governance.provenance.provenance_record import ProvenanceRecord


@dataclass
class ProvenanceReport:
    """
    Human-readable provenance summary generated on demand.
    """
    report_id:      str
    entity_id:      str
    records:        list[ProvenanceRecord]
    gaps:           list[str]   # descriptions of missing / incomplete provenance
    generated_at:   float
    generated_by:   Optional[str]

    @classmethod
    def build(
        cls,
        entity_id:    str,
        records:      list[ProvenanceRecord],
        *,
        generated_by: Optional[str] = None,
    ) -> "ProvenanceReport":
        gaps: list[str] = []
        for rec in records:
            if rec.reproducibility_status.value == "unknown":
                gaps.append(f"Record {rec.record_id}: reproducibility status not evaluated")
            if not rec.timestamps.get("completed"):
                gaps.append(f"Record {rec.record_id}: completion timestamp missing")
            if not rec.software_versions:
                gaps.append(f"Record {rec.record_id}: software versions not captured")
        return cls(
            report_id    = f"prr_{uuid.uuid4().hex[:10]}",
            entity_id    = entity_id,
            records      = records,
            gaps         = gaps,
            generated_at = time.time(),
            generated_by = generated_by,
        )

    def is_complete(self) -> bool:
        return len(self.gaps) == 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_id":    self.report_id,
            "entity_id":    self.entity_id,
            "record_count": len(self.records),
            "gaps":         self.gaps,
            "is_complete":  self.is_complete(),
            "generated_at": self.generated_at,
            "generated_by": self.generated_by,
        }
