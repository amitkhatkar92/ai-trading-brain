"""
market_snapshot_metadata.py — iios.market.snapshot
====================================================
Immutable snapshot metadata value object.

C12 Market Intelligence — Phase 1, Module 5
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .constants import VERSION


@dataclass(frozen=True)
class SnapshotMetadata:
    """
    Immutable metadata attached to every market snapshot.

    Fields
    ------
    metadata_id :         Unique metadata identifier.
    environment :         Deployment environment (prod / staging / dev).
    framework_version :   Framework version string.
    build_version :       Container or package build version.
    source_components :   Names of subsystems that contributed data.
    correlation_ids :     Upstream correlation identifiers.
    trace_ids :           Distributed trace identifiers.
    analytics_version :   Analytics framework version.
    model_versions :      Mapping of model name → version string.
    policy_versions :     Mapping of policy name → version string.
    created_at :          Creation timestamp.
    extra :               Supplementary key-value pairs.
    """
    metadata_id:        str
    environment:        str
    framework_version:  str
    build_version:      str
    source_components:  Tuple[str, ...]
    correlation_ids:    Tuple[str, ...]
    trace_ids:          Tuple[str, ...]
    analytics_version:  str
    model_versions:     Dict[str, str]
    policy_versions:    Dict[str, str]
    created_at:         float
    extra:              Dict[str, Any]

    @classmethod
    def create(
        cls,
        *,
        environment:       str                       = "production",
        framework_version: str                       = VERSION,
        build_version:     str                       = "1.0.0",
        source_components: Optional[List[str]]       = None,
        correlation_ids:   Optional[List[str]]       = None,
        trace_ids:         Optional[List[str]]       = None,
        analytics_version: str                       = VERSION,
        model_versions:    Optional[Dict[str, str]]  = None,
        policy_versions:   Optional[Dict[str, str]]  = None,
        extra:             Optional[Dict[str, Any]]  = None,
    ) -> "SnapshotMetadata":
        return cls(
            metadata_id        = str(uuid.uuid4()),
            environment        = environment,
            framework_version  = framework_version,
            build_version      = build_version,
            source_components  = tuple(source_components or []),
            correlation_ids    = tuple(correlation_ids or []),
            trace_ids          = tuple(trace_ids or []),
            analytics_version  = analytics_version,
            model_versions     = dict(model_versions or {}),
            policy_versions    = dict(policy_versions or {}),
            created_at         = time.time(),
            extra              = dict(extra or {}),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "metadata_id":        self.metadata_id,
            "environment":        self.environment,
            "framework_version":  self.framework_version,
            "build_version":      self.build_version,
            "source_components":  list(self.source_components),
            "correlation_ids":    list(self.correlation_ids),
            "trace_ids":          list(self.trace_ids),
            "analytics_version":  self.analytics_version,
            "model_versions":     dict(self.model_versions),
            "policy_versions":    dict(self.policy_versions),
            "created_at":         self.created_at,
            "extra":              dict(self.extra),
        }
