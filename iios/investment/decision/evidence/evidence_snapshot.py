"""iios/investment/decision/evidence/evidence_snapshot.py
EvidenceSnapshot — immutable, versioned, published evidence record.
This is the canonical output consumed by Decision Intelligence engines.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from iios.investment.decision.evidence.evidence_constants import (
    EvidenceCategory,
    EvidencePriority,
    EvidenceSourceType,
    EvidenceStatus,
    EvidenceValidationStatus,
)
from iios.investment.decision.evidence.evidence_item import EvidenceItem
from iios.investment.decision.evidence.evidence_package import EvidencePackage


@dataclass(frozen=True)
class EvidenceSnapshot:
    """
    Canonical, immutable, versioned evidence package.
    Produced after collection, validation, ranking, and quality scoring.
    Downstream engines consume ONLY this object.
    """
    snapshot_id:        str
    package_id:         str
    decision_id:        str
    subject_id:         str
    subject_type:       str
    version:            int
    items:              Tuple[EvidenceItem, ...]    # ranked, validated, immutable
    sources_included:   Tuple[str, ...]             # EvidenceSourceType.value strings
    categories_present: Tuple[str, ...]             # EvidenceCategory.value strings
    item_count:         int
    required_items_met: bool
    validation_status:  EvidenceValidationStatus
    overall_confidence: float                       # 0–100 weighted avg
    overall_freshness:  float                       # 0–1 weighted avg
    quality_score:      float                       # 0–100 overall evidence quality
    coverage_fraction:  float                       # 0–1 sources present / all sources
    status:             EvidenceStatus
    created_at:         datetime
    collection_duration_ms: float

    def item_by_key(self, key: str) -> Optional[EvidenceItem]:
        for item in self.items:
            if item.key == key:
                return item
        return None

    def items_by_source(self, source_type: EvidenceSourceType) -> List[EvidenceItem]:
        return [i for i in self.items if i.source_type == source_type]

    def items_by_category(self, category: EvidenceCategory) -> List[EvidenceItem]:
        return [i for i in self.items if i.category == category]

    def items_by_priority(self, priority: EvidencePriority) -> List[EvidenceItem]:
        return [i for i in self.items if i.priority == priority]

    @property
    def is_publishable(self) -> bool:
        return self.validation_status.allows_publishing

    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id":          self.snapshot_id,
            "package_id":           self.package_id,
            "decision_id":          self.decision_id,
            "subject_id":           self.subject_id,
            "subject_type":         self.subject_type,
            "version":              self.version,
            "item_count":           self.item_count,
            "sources_included":     list(self.sources_included),
            "categories_present":   list(self.categories_present),
            "required_items_met":   self.required_items_met,
            "validation_status":    self.validation_status.value,
            "overall_confidence":   round(self.overall_confidence, 2),
            "overall_freshness":    round(self.overall_freshness, 4),
            "quality_score":        round(self.quality_score, 2),
            "coverage_fraction":    round(self.coverage_fraction, 4),
            "status":               self.status.value,
            "is_publishable":       self.is_publishable,
            "created_at":           self.created_at.isoformat(),
            "collection_duration_ms": round(self.collection_duration_ms, 1),
        }


def build_snapshot(
    package:             EvidencePackage,
    ranked_items:        List[EvidenceItem],
    validation_status:   EvidenceValidationStatus,
    quality_score:       float,
    version:             int,
    collection_start:    datetime,
) -> EvidenceSnapshot:
    """Construct an immutable EvidenceSnapshot from a sealed package."""
    items      = tuple(ranked_items)
    sources    = tuple(sorted({i.source_type.value for i in items}))
    categories = tuple(sorted({i.category.value for i in items}))
    required   = all(True for i in items if i.is_required)

    n = len(items)
    avg_conf  = sum(i.confidence     for i in items) / n if n else 0.0
    avg_fresh = sum(i.freshness_score for i in items) / n if n else 0.0

    total_sources = len(EvidenceSourceType)
    coverage = len(sources) / total_sources if total_sources else 0.0

    duration_ms = (datetime.now(timezone.utc) - collection_start).total_seconds() * 1000.0

    if n == 0:
        status = EvidenceStatus.PARTIAL
    elif validation_status == EvidenceValidationStatus.FAILED:
        status = EvidenceStatus.PARTIAL
    else:
        status = EvidenceStatus.COMPLETE

    return EvidenceSnapshot(
        snapshot_id=str(uuid.uuid4()),
        package_id=package.package_id,
        decision_id=package.decision_id,
        subject_id=package.subject_id,
        subject_type=package.subject_type,
        version=version,
        items=items,
        sources_included=sources,
        categories_present=categories,
        item_count=n,
        required_items_met=required,
        validation_status=validation_status,
        overall_confidence=round(avg_conf, 2),
        overall_freshness=round(avg_fresh, 4),
        quality_score=round(quality_score, 2),
        coverage_fraction=round(coverage, 4),
        status=status,
        created_at=datetime.now(timezone.utc),
        collection_duration_ms=round(duration_ms, 1),
    )
