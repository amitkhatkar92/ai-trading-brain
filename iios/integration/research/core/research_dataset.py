"""iios/integration/research/core/research_dataset.py"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from iios.integration.research.research_constants import (
    DatasetSourceType,
    ResearchDatasetStatus,
)
from iios.integration.research.core.research_metadata import ResearchMetadata


@dataclass
class DatasetSnapshot:
    """Point-in-time snapshot reference for a research dataset."""
    snapshot_id:  str   = field(default_factory=lambda: str(uuid.uuid4()))
    dataset_id:   str   = ""
    version:      str   = ""
    record_count: int   = 0
    size_bytes:   int   = 0
    description:  str   = ""
    created_at:   float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "snapshot_id":  self.snapshot_id,
            "dataset_id":   self.dataset_id,
            "version":      self.version,
            "record_count": self.record_count,
            "created_at":   self.created_at,
        }


@dataclass
class ResearchDataset:
    """
    Dataset registered with the research framework.

    Supports versioning (via ``version``), lineage tracking
    (``parent_ids`` chain), and snapshots.
    """
    dataset_id:   str                  = field(default_factory=lambda: str(uuid.uuid4()))
    name:         str                  = ""
    description:  str                  = ""
    source_type:  DatasetSourceType    = DatasetSourceType.CUSTOM
    status:       ResearchDatasetStatus = ResearchDatasetStatus.PENDING
    version:      str                  = "1.0.0"
    schema:       dict[str, Any]       = field(default_factory=dict)
    record_count: int                  = 0
    size_bytes:   int                  = 0
    parent_ids:   list[str]            = field(default_factory=list)   # lineage
    snapshots:    list[DatasetSnapshot] = field(default_factory=list)
    tags:         list[str]            = field(default_factory=list)
    source_ref:   str                  = ""   # path / dataset_id in history layer
    created_at:   float                = field(default_factory=time.time)
    updated_at:   float                = field(default_factory=time.time)
    metadata:     ResearchMetadata     = field(default_factory=ResearchMetadata)

    def touch(self) -> None:
        self.updated_at = time.time()

    def create_snapshot(self, description: str = "") -> DatasetSnapshot:
        snap = DatasetSnapshot(
            dataset_id   = self.dataset_id,
            version      = self.version,
            record_count = self.record_count,
            size_bytes   = self.size_bytes,
            description  = description,
        )
        self.snapshots.append(snap)
        return snap

    def bump_version(self) -> str:
        """Increment patch version and return new version string."""
        parts = self.version.split(".")
        parts[-1] = str(int(parts[-1]) + 1)
        self.version = ".".join(parts)
        self.touch()
        return self.version

    def lineage_depth(self) -> int:
        return len(self.parent_ids)

    def to_dict(self) -> dict[str, Any]:
        return {
            "dataset_id":   self.dataset_id,
            "name":         self.name,
            "source_type":  self.source_type.value,
            "status":       self.status.value,
            "version":      self.version,
            "record_count": self.record_count,
            "size_bytes":   self.size_bytes,
            "parent_ids":   list(self.parent_ids),
            "tags":         list(self.tags),
            "created_at":   self.created_at,
        }
