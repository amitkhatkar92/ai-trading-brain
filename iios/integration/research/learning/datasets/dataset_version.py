"""datasets/dataset_version.py — Dataset versioning model."""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class DatasetVersion:
    """
    Records a specific version of a dataset.

    Enables lineage tracking: a dataset can derive from a parent via
    transformations such as feature engineering, filtering, or augmentation.
    """
    version_id:     str
    dataset_id:     str
    version:        str
    parent_version: Optional[str]
    record_count:   int
    change_summary: str
    created_by:     Optional[str]
    created_at:     float
    metadata:       dict[str, Any]

    @classmethod
    def create(
        cls,
        dataset_id:     str,
        version:        str,
        record_count:   int,
        change_summary: str,
        *,
        version_id:     Optional[str] = None,
        parent_version: Optional[str] = None,
        created_by:     Optional[str] = None,
        metadata:       Optional[dict] = None,
    ) -> "DatasetVersion":
        return cls(
            version_id     = version_id or f"dsv_{uuid.uuid4().hex[:10]}",
            dataset_id     = dataset_id,
            version        = version,
            parent_version = parent_version,
            record_count   = record_count,
            change_summary = change_summary,
            created_by     = created_by,
            created_at     = time.time(),
            metadata       = metadata or {},
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "version_id":     self.version_id,
            "dataset_id":     self.dataset_id,
            "version":        self.version,
            "parent_version": self.parent_version,
            "record_count":   self.record_count,
            "change_summary": self.change_summary,
            "created_by":     self.created_by,
            "created_at":     self.created_at,
        }
