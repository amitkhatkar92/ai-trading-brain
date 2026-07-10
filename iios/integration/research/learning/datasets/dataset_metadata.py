"""datasets/dataset_metadata.py — Dataset metadata model."""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

from iios.integration.research.learning.learning_constants import DataSplitStrategy


@dataclass
class DatasetMetadata:
    """Lightweight descriptor for a registered dataset."""
    dataset_id:     str
    name:           str
    version:        str
    description:    Optional[str]
    split_strategy: DataSplitStrategy
    record_count:   int
    feature_names:  list[str]
    label_name:     Optional[str]
    has_timestamps: bool
    created_at:     float
    updated_at:     float
    lineage:        list[str]         # parent dataset_ids
    tags:           list[str]
    extra:          dict[str, Any]

    @classmethod
    def create(
        cls,
        name:           str,
        version:        str           = "1.0.0",
        *,
        dataset_id:     Optional[str] = None,
        description:    Optional[str] = None,
        split_strategy: DataSplitStrategy = DataSplitStrategy.RANDOM,
        record_count:   int           = 0,
        feature_names:  Optional[list] = None,
        label_name:     Optional[str] = None,
        has_timestamps: bool          = False,
        lineage:        Optional[list] = None,
        tags:           Optional[list] = None,
    ) -> "DatasetMetadata":
        now = time.time()
        return cls(
            dataset_id     = dataset_id or f"ds_{uuid.uuid4().hex[:12]}",
            name           = name,
            version        = version,
            description    = description,
            split_strategy = split_strategy,
            record_count   = record_count,
            feature_names  = feature_names or [],
            label_name     = label_name,
            has_timestamps = has_timestamps,
            created_at     = now,
            updated_at     = now,
            lineage        = lineage or [],
            tags           = tags or [],
            extra          = {},
        )

    def touch(self) -> None:
        self.updated_at = time.time()

    def to_dict(self) -> dict[str, Any]:
        return {
            "dataset_id":     self.dataset_id,
            "name":           self.name,
            "version":        self.version,
            "description":    self.description,
            "split_strategy": self.split_strategy.value,
            "record_count":   self.record_count,
            "feature_count":  len(self.feature_names),
            "feature_names":  self.feature_names,
            "label_name":     self.label_name,
            "has_timestamps": self.has_timestamps,
            "created_at":     self.created_at,
            "updated_at":     self.updated_at,
            "lineage":        self.lineage,
            "tags":           self.tags,
        }
