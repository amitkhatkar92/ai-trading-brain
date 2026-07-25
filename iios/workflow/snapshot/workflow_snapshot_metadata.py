"""
workflow_snapshot_metadata.py — iios.workflow.snapshot
-------------------------------------------------------
WorkflowSnapshotMetadata — immutable metadata attached to every snapshot.

C16 Enterprise Workflow & Process Orchestration — Phase 1, Module 5
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .constants import BUILD_VERSION, FRAMEWORK_VERSION, PREFIX_META, SNAPSHOT_VERSION


@dataclass(frozen=True)
class WorkflowSnapshotMetadata:
    """
    Immutable metadata for a WorkflowSnapshot.

    Captures provenance, version, environment, and correlation identifiers.
    """
    metadata_id:      str
    snapshot_version: str
    framework_version: str
    build_version:    str
    environment:      str
    correlation_id:   str
    trace_id:         str
    source_components: tuple          # Tuple[str, ...]
    tags:             Dict[str, str]
    extra:            Dict[str, Any]
    created_at:       str

    @classmethod
    def create(
        cls,
        *,
        environment:       str                     = "production",
        correlation_id:    str                     = "",
        trace_id:          str                     = "",
        source_components: Optional[List[str]]     = None,
        tags:              Optional[Dict[str, str]] = None,
        extra:             Optional[Dict[str, Any]] = None,
        snapshot_version:  str                     = SNAPSHOT_VERSION,
        framework_version: str                     = FRAMEWORK_VERSION,
        build_version:     str                     = BUILD_VERSION,
    ) -> "WorkflowSnapshotMetadata":
        return cls(
            metadata_id       = f"{PREFIX_META}{uuid.uuid4().hex[:10]}",
            snapshot_version  = snapshot_version,
            framework_version = framework_version,
            build_version     = build_version,
            environment       = environment,
            correlation_id    = correlation_id or uuid.uuid4().hex,
            trace_id          = trace_id       or uuid.uuid4().hex[:16],
            source_components = tuple(source_components or []),
            tags              = dict(tags or {}),
            extra             = dict(extra or {}),
            created_at        = datetime.now(tz=timezone.utc).isoformat(),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "metadata_id":       self.metadata_id,
            "snapshot_version":  self.snapshot_version,
            "framework_version": self.framework_version,
            "build_version":     self.build_version,
            "environment":       self.environment,
            "correlation_id":    self.correlation_id,
            "trace_id":          self.trace_id,
            "source_components": list(self.source_components),
            "tags":              dict(self.tags),
            "created_at":        self.created_at,
        }
