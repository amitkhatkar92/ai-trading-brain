"""
supervisor_snapshot_metadata.py — iios.supervisor.snapshot
-----------------------------------------------------------
Supervisor Snapshot Metadata.

Captures environment, versioning, and traceability context for a
SupervisorSnapshot.

C13 AI Supervisor & Autonomous Governance — Phase 1, Module 5
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple

from .constants import PLATFORM_VERSION, SCHEMA_VERSION, VERSION


@dataclass(frozen=True)
class SupervisorSnapshotMetadata:
    """
    Immutable metadata for a SupervisorSnapshot.

    Captures:
    - environment (prod, staging, paper, test, dev)
    - versioning (framework, build, schema)
    - traceability (source components, correlation IDs, trace IDs)
    """

    metadata_id:       str
    environment:       str
    framework_version: str
    build_version:     str
    schema_version:    str
    source_components: Tuple[str, ...]
    correlation_ids:   Tuple[str, ...]
    trace_ids:         Tuple[str, ...]
    generated_at:      float
    extra:             Dict[str, Any]

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def create(
        cls,
        *,
        environment:       str                          = "production",
        build_version:     str                          = VERSION,
        source_components: Optional[Tuple[str, ...]]   = None,
        correlation_ids:   Optional[Tuple[str, ...]]   = None,
        trace_ids:         Optional[Tuple[str, ...]]   = None,
        metadata_id:       Optional[str]                = None,
        extra:             Optional[Dict[str, Any]]     = None,
    ) -> "SupervisorSnapshotMetadata":
        return cls(
            metadata_id       = metadata_id or str(uuid.uuid4()),
            environment       = environment,
            framework_version = VERSION,
            build_version     = build_version,
            schema_version    = SCHEMA_VERSION,
            source_components = source_components or (
                "iios:supervisor:lifecycle",
                "iios:supervisor:engine",
                "iios:supervisor:policies",
                "iios:supervisor:governance",
            ),
            correlation_ids   = correlation_ids or (),
            trace_ids         = trace_ids or (),
            generated_at      = time.time(),
            extra             = extra or {},
        )

    # ------------------------------------------------------------------
    # Derivative constructors
    # ------------------------------------------------------------------

    def with_correlation_id(self, correlation_id: str) -> "SupervisorSnapshotMetadata":
        """Return a new metadata with an additional correlation ID."""
        return SupervisorSnapshotMetadata(
            metadata_id       = self.metadata_id,
            environment       = self.environment,
            framework_version = self.framework_version,
            build_version     = self.build_version,
            schema_version    = self.schema_version,
            source_components = self.source_components,
            correlation_ids   = self.correlation_ids + (correlation_id,),
            trace_ids         = self.trace_ids,
            generated_at      = self.generated_at,
            extra             = self.extra,
        )

    def with_trace_id(self, trace_id: str) -> "SupervisorSnapshotMetadata":
        """Return a new metadata with an additional trace ID."""
        return SupervisorSnapshotMetadata(
            metadata_id       = self.metadata_id,
            environment       = self.environment,
            framework_version = self.framework_version,
            build_version     = self.build_version,
            schema_version    = self.schema_version,
            source_components = self.source_components,
            correlation_ids   = self.correlation_ids,
            trace_ids         = self.trace_ids + (trace_id,),
            generated_at      = self.generated_at,
            extra             = self.extra,
        )

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        return {
            "metadata_id":       self.metadata_id,
            "environment":       self.environment,
            "framework_version": self.framework_version,
            "build_version":     self.build_version,
            "schema_version":    self.schema_version,
            "source_components": list(self.source_components),
            "correlation_ids":   list(self.correlation_ids),
            "trace_ids":         list(self.trace_ids),
            "generated_at":      self.generated_at,
            "extra":             self.extra,
        }
