"""iios/investment/decision/evidence/evidence_package.py
EvidencePackage — mutable collection of EvidenceItems during the collection phase.
Seals into an EvidenceSnapshot when collection is complete.
"""
from __future__ import annotations

import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from iios.investment.decision.evidence.evidence_constants import (
    EvidenceCategory,
    EvidencePriority,
    EvidenceSourceType,
    EvidenceStatus,
)
from iios.investment.decision.evidence.evidence_item import EvidenceItem


class EvidencePackage:
    """
    Mutable, thread-safe accumulator for evidence collected for one decision.
    Once sealed, no further items may be added.
    """

    def __init__(
        self,
        package_id:   str,
        decision_id:  str,
        subject_id:   str,
        subject_type: str,
    ) -> None:
        self._lock       = threading.RLock()
        self.package_id  = package_id
        self.decision_id = decision_id
        self.subject_id  = subject_id
        self.subject_type = subject_type
        self.created_at  = datetime.now(timezone.utc)
        self.sealed_at:  Optional[datetime]  = None
        self._items:     List[EvidenceItem]  = []
        self._status     = EvidenceStatus.COLLECTING

    # ----------------------------------------------------------------- mutation

    def add_item(self, item: EvidenceItem) -> None:
        with self._lock:
            if self.sealed_at is not None:
                raise RuntimeError(f"EvidencePackage {self.package_id!r} is already sealed.")
            self._items.append(item)

    def add_items(self, items: List[EvidenceItem]) -> None:
        for item in items:
            self.add_item(item)

    def seal(self) -> None:
        with self._lock:
            if self.sealed_at is not None:
                return
            self.sealed_at = datetime.now(timezone.utc)
            self._status   = EvidenceStatus.COMPLETE if self._items else EvidenceStatus.PARTIAL

    # ----------------------------------------------------------------- accessors

    @property
    def is_sealed(self) -> bool:
        return self.sealed_at is not None

    @property
    def status(self) -> EvidenceStatus:
        return self._status

    @property
    def item_count(self) -> int:
        with self._lock:
            return len(self._items)

    @property
    def items(self) -> List[EvidenceItem]:
        with self._lock:
            return list(self._items)

    def by_source(self, source_type: EvidenceSourceType) -> List[EvidenceItem]:
        with self._lock:
            return [i for i in self._items if i.source_type == source_type]

    def by_category(self, category: EvidenceCategory) -> List[EvidenceItem]:
        with self._lock:
            return [i for i in self._items if i.category == category]

    def by_priority(self, priority: EvidencePriority) -> List[EvidenceItem]:
        with self._lock:
            return [i for i in self._items if i.priority == priority]

    def required_items(self) -> List[EvidenceItem]:
        with self._lock:
            return [i for i in self._items if i.is_required]

    def sources_present(self) -> List[EvidenceSourceType]:
        with self._lock:
            return list({i.source_type for i in self._items})

    def avg_confidence(self) -> float:
        with self._lock:
            if not self._items:
                return 0.0
            return sum(i.confidence for i in self._items) / len(self._items)

    def avg_freshness(self) -> float:
        with self._lock:
            if not self._items:
                return 0.0
            return sum(i.freshness_score for i in self._items) / len(self._items)

    def to_dict(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "package_id":   self.package_id,
                "decision_id":  self.decision_id,
                "subject_id":   self.subject_id,
                "subject_type": self.subject_type,
                "item_count":   len(self._items),
                "status":       self._status.value,
                "is_sealed":    self.is_sealed,
                "created_at":   self.created_at.isoformat(),
                "sealed_at":    self.sealed_at.isoformat() if self.sealed_at else None,
                "avg_confidence": round(self.avg_confidence(), 2),
                "avg_freshness":  round(self.avg_freshness(), 4),
                "sources_present": [s.value for s in self.sources_present()],
            }
