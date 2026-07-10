"""provenance/provenance_engine.py — Provenance orchestrator."""
from __future__ import annotations

from typing import Any, Optional

from iios.integration.research.governance.governance_constants import ProvenanceType, ReproducibilityStatus
from iios.integration.research.governance.provenance.provenance_record   import ProvenanceRecord
from iios.integration.research.governance.provenance.provenance_registry import ProvenanceRegistry
from iios.integration.research.governance.provenance.provenance_report   import ProvenanceReport


class ProvenanceEngine:
    """Facade for all provenance operations."""

    def __init__(self) -> None:
        self._registry = ProvenanceRegistry()

    def record(
        self,
        entity_id:   str,
        entity_type: ProvenanceType,
        author:      str,
        **kwargs: Any,
    ) -> ProvenanceRecord:
        rec = ProvenanceRecord.create(entity_id, entity_type, author, **kwargs)
        self._registry.register(rec)
        return rec

    def get(self, record_id: str) -> ProvenanceRecord:
        return self._registry.get(record_id)

    def get_for_entity(self, entity_id: str) -> list[ProvenanceRecord]:
        return self._registry.get_for_entity(entity_id)

    def latest_for_entity(self, entity_id: str) -> Optional[ProvenanceRecord]:
        return self._registry.latest_for_entity(entity_id)

    def generate_report(
        self,
        entity_id:    str,
        generated_by: Optional[str] = None,
    ) -> ProvenanceReport:
        records = self._registry.get_for_entity(entity_id)
        return ProvenanceReport.build(entity_id, records, generated_by=generated_by)

    def set_reproducibility(
        self,
        record_id: str,
        status:    ReproducibilityStatus,
    ) -> None:
        rec = self._registry.get(record_id)
        rec.reproducibility_status = status

    def stats(self) -> dict[str, Any]:
        return self._registry.stats()
