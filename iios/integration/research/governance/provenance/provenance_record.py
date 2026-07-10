"""provenance/provenance_record.py — Provenance data for a research entity."""
from __future__ import annotations

import platform
import socket
import sys
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

from iios.integration.research.governance.governance_constants import (
    ProvenanceType,
    ReproducibilityStatus,
)


@dataclass
class ProvenanceRecord:
    """
    Full provenance snapshot for a research entity.

    Captures everything needed to understand where results came from:
    environment, software, configuration, datasets, random seed, and timing.
    """
    record_id:              str
    entity_id:              str
    entity_type:            ProvenanceType
    author:                 str
    execution_env:          dict[str, str]    # python version, OS, hostname
    software_versions:      dict[str, str]    # key packages and their versions
    config_version:         str
    dataset_versions:       dict[str, str]
    feature_versions:       dict[str, str]
    model_versions:         dict[str, str]
    timestamps:             dict[str, float]  # "created", "started", "completed"
    reproducibility_status: ReproducibilityStatus
    seed:                   Optional[int]
    notes:                  str
    created_at:             float
    metadata:               dict[str, Any]

    @classmethod
    def create(
        cls,
        entity_id:    str,
        entity_type:  ProvenanceType,
        author:       str,
        *,
        record_id:       Optional[str]         = None,
        config_version:  str                   = "unknown",
        dataset_versions: Optional[dict]       = None,
        feature_versions: Optional[dict]       = None,
        model_versions:   Optional[dict]       = None,
        seed:             Optional[int]        = None,
        notes:            str                  = "",
        metadata:         Optional[dict]       = None,
    ) -> "ProvenanceRecord":
        now = time.time()
        execution_env = {
            "python_version": sys.version.split()[0],
            "platform":       platform.platform(),
            "hostname":       socket.gethostname(),
        }
        return cls(
            record_id              = record_id or f"prov_{uuid.uuid4().hex[:10]}",
            entity_id              = entity_id,
            entity_type            = entity_type,
            author                 = author,
            execution_env          = execution_env,
            software_versions      = {},
            config_version         = config_version,
            dataset_versions       = dataset_versions or {},
            feature_versions       = feature_versions or {},
            model_versions         = model_versions or {},
            timestamps             = {"created": now},
            reproducibility_status = ReproducibilityStatus.UNKNOWN,
            seed                   = seed,
            notes                  = notes,
            created_at             = now,
            metadata               = metadata or {},
        )

    def mark_started(self) -> None:
        self.timestamps["started"] = time.time()

    def mark_completed(self) -> None:
        self.timestamps["completed"] = time.time()

    def to_dict(self) -> dict[str, Any]:
        return {
            "record_id":              self.record_id,
            "entity_id":              self.entity_id,
            "entity_type":            self.entity_type.value,
            "author":                 self.author,
            "execution_env":          self.execution_env,
            "software_versions":      self.software_versions,
            "config_version":         self.config_version,
            "dataset_versions":       self.dataset_versions,
            "feature_versions":       self.feature_versions,
            "model_versions":         self.model_versions,
            "timestamps":             self.timestamps,
            "reproducibility_status": self.reproducibility_status.value,
            "seed":                   self.seed,
            "notes":                  self.notes,
            "created_at":             self.created_at,
        }
