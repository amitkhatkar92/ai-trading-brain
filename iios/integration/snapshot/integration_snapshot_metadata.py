"""
integration_snapshot_metadata.py — iios.integration.snapshot
--------------------------------------------------------------
SnapshotMetadata — the environment, versioning, and traceability
information attached to every IntegrationSnapshot.

Immutable. Serializable. No vendor dependencies.

C15 Enterprise Integration & Connectivity — Phase 1, Module 5
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from iios.common.logging.logging_manager import get_logger

_log = get_logger(__name__)


@dataclass(frozen=True)
class SnapshotMetadata:
    """
    Immutable metadata record attached to every IntegrationSnapshot.

    Fields
    ------
    environment          Target environment (e.g. "production", "staging")
    framework_version    IIOS framework version string
    build_version        Application build version string
    source_components    Tuple of component names that contributed data
    correlation_ids      Tuple of upstream correlation identifiers
    trace_ids            Tuple of distributed-trace identifiers
    tags                 Dict of freeform key/value annotation pairs
    generated_at         ISO-8601 UTC timestamp of metadata creation
    """
    environment:       str
    framework_version: str
    build_version:     str
    source_components: Tuple[str, ...]
    correlation_ids:   Tuple[str, ...]
    trace_ids:         Tuple[str, ...]
    tags:              Dict[str, str]
    generated_at:      str

    # ── Factory ──────────────────────────────────────────────────────────

    @classmethod
    def create(
        cls,
        *,
        environment:       str                        = "production",
        framework_version: str                        = "1.0.0",
        build_version:     str                        = "1.0.0",
        source_components: Optional[List[str]]        = None,
        correlation_ids:   Optional[List[str]]        = None,
        trace_ids:         Optional[List[str]]        = None,
        tags:              Optional[Dict[str, str]]   = None,
    ) -> "SnapshotMetadata":
        """Create metadata with sensible defaults."""
        return cls(
            environment       = environment,
            framework_version = framework_version,
            build_version     = build_version,
            source_components = tuple(source_components or []),
            correlation_ids   = tuple(correlation_ids   or []),
            trace_ids         = tuple(trace_ids         or []),
            tags              = dict(tags or {}),
            generated_at      = datetime.now(tz=timezone.utc).isoformat(),
        )

    # ── Serialization ─────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        return {
            "environment":       self.environment,
            "framework_version": self.framework_version,
            "build_version":     self.build_version,
            "source_components": list(self.source_components),
            "correlation_ids":   list(self.correlation_ids),
            "trace_ids":         list(self.trace_ids),
            "tags":              dict(self.tags),
            "generated_at":      self.generated_at,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "SnapshotMetadata":
        return cls(
            environment       = d.get("environment",       "production"),
            framework_version = d.get("framework_version", "1.0.0"),
            build_version     = d.get("build_version",     "1.0.0"),
            source_components = tuple(d.get("source_components", [])),
            correlation_ids   = tuple(d.get("correlation_ids",   [])),
            trace_ids         = tuple(d.get("trace_ids",         [])),
            tags              = dict(d.get("tags",               {})),
            generated_at      = d.get("generated_at",
                                      datetime.now(tz=timezone.utc).isoformat()),
        )
