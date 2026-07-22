"""
portfolio_snapshot_metadata.py — iios.portfolio.snapshot
=========================================================
Immutable metadata value objects attached to every PortfolioSnapshot.

C10 Portfolio Intelligence — Phase 1, Module 5
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from .constants import SNAPSHOT_SYSTEM_ID, VERSION


@dataclass(frozen=True)
class SnapshotAuditMetadata:
    """
    Immutable audit record describing how this snapshot was built,
    validated, and published.

    Fields
    ------
    built_by :              Actor that triggered the build.
    validated_by :          Actor that validated the snapshot.
    published_by :          Actor that published the snapshot.
    build_duration_ms :     Wall-clock ms consumed by the builder.
    validation_duration_ms: Wall-clock ms consumed by validation.
    framework_version :     Framework version at build time.
    built_at :              Wall-clock build timestamp.
    validated_at :          Wall-clock validation timestamp (0 = not yet validated).
    published_at :          Wall-clock publication timestamp (0 = not yet published).
    build_context :         Supplementary build context dict.
    """
    built_by:              str
    validated_by:          str
    published_by:          str
    build_duration_ms:     float
    validation_duration_ms: float
    framework_version:     str
    built_at:              float
    validated_at:          float
    published_at:          float
    build_context:         Dict[str, Any]

    @classmethod
    def create(
        cls,
        *,
        built_by:           str = SNAPSHOT_SYSTEM_ID,
        build_duration_ms:  float = 0.0,
        framework_version:  str   = VERSION,
        build_context:      Optional[Dict[str, Any]] = None,
    ) -> "SnapshotAuditMetadata":
        return cls(
            built_by               = built_by,
            validated_by           = "",
            published_by           = "",
            build_duration_ms      = build_duration_ms,
            validation_duration_ms = 0.0,
            framework_version      = framework_version,
            built_at               = time.time(),
            validated_at           = 0.0,
            published_at           = 0.0,
            build_context          = dict(build_context or {}),
        )

    def with_validation(
        self,
        validated_by:          str   = SNAPSHOT_SYSTEM_ID,
        validation_duration_ms: float = 0.0,
    ) -> "SnapshotAuditMetadata":
        """Return a new record with validation fields populated."""
        import dataclasses
        return dataclasses.replace(
            self,
            validated_by           = validated_by,
            validation_duration_ms = validation_duration_ms,
            validated_at           = time.time(),
        )

    def with_publication(self, published_by: str = SNAPSHOT_SYSTEM_ID) -> "SnapshotAuditMetadata":
        """Return a new record with publication fields populated."""
        import dataclasses
        return dataclasses.replace(
            self, published_by=published_by, published_at=time.time()
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "built_by":              self.built_by,
            "validated_by":          self.validated_by,
            "published_by":          self.published_by,
            "build_duration_ms":     self.build_duration_ms,
            "validation_duration_ms": self.validation_duration_ms,
            "framework_version":     self.framework_version,
            "built_at":              self.built_at,
            "validated_at":          self.validated_at,
            "published_at":          self.published_at,
            "build_context":         dict(self.build_context),
        }


@dataclass(frozen=True)
class PortfolioSnapshotMetadata:
    """
    Immutable descriptive metadata for a PortfolioSnapshot.

    Fields
    ------
    snapshot_id :      The snapshot this metadata belongs to.
    portfolio_id :     Portfolio identifier.
    created_at :       Wall-clock creation timestamp.
    tags :             Tuple of string tags.
    labels :           Key-value label dict.
    build_source :     Identifier of the build source system.
    description :      Optional human-readable description.
    framework_version: Framework version string.
    """
    snapshot_id:       str
    portfolio_id:      str
    created_at:        float
    tags:              tuple        # Tuple[str, ...]
    labels:            Dict[str, str]
    build_source:      str
    description:       str
    framework_version: str

    @classmethod
    def create(
        cls,
        snapshot_id:  str,
        portfolio_id: str,
        *,
        tags:         Optional[list] = None,
        labels:       Optional[Dict[str, str]] = None,
        build_source: str = SNAPSHOT_SYSTEM_ID,
        description:  str = "",
    ) -> "PortfolioSnapshotMetadata":
        return cls(
            snapshot_id       = snapshot_id,
            portfolio_id      = portfolio_id,
            created_at        = time.time(),
            tags              = tuple(tags or []),
            labels            = dict(labels or {}),
            build_source      = build_source,
            description       = description,
            framework_version = VERSION,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id":      self.snapshot_id,
            "portfolio_id":     self.portfolio_id,
            "created_at":       self.created_at,
            "tags":             list(self.tags),
            "labels":           dict(self.labels),
            "build_source":     self.build_source,
            "description":      self.description,
            "framework_version": self.framework_version,
        }
