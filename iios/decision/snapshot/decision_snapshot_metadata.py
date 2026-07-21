"""
decision_snapshot_metadata.py — iios.decision.snapshot
========================================================
Metadata and audit metadata value objects for DecisionSnapshot.

C9 Decision Intelligence — Phase 1, Module 5
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

from .constants import SCHEMA_VERSION, VERSION


@dataclass(frozen=True)
class DecisionSnapshotMetadata:
    """
    Supplementary classification data attached to a :class:`DecisionSnapshot`.

    Parameters
    ----------
    metadata_id :       Unique identifier.
    snapshot_id :       Parent snapshot identifier.
    session_id :        Decision lifecycle session identifier.
    decision_id :       Decision identifier.
    tags :              Immutable tuple of classification tags.
    labels :            Key-value label map (string → string).
    annotations :       Free-form annotation dict.
    schema_version :    Schema version for forward compatibility.
    created_at :        Creation timestamp.
    framework_version : Framework version.
    """

    metadata_id:       str
    snapshot_id:       str
    session_id:        str
    decision_id:       str
    tags:              Tuple[str, ...]   = field(default_factory=tuple)
    labels:            Dict[str, str]    = field(default_factory=dict)
    annotations:       Dict[str, Any]    = field(default_factory=dict)
    schema_version:    str               = SCHEMA_VERSION
    created_at:        datetime          = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    framework_version: str               = VERSION

    def to_dict(self) -> dict:
        return {
            "metadata_id":      self.metadata_id,
            "snapshot_id":      self.snapshot_id,
            "session_id":       self.session_id,
            "decision_id":      self.decision_id,
            "tags":             list(self.tags),
            "labels":           dict(self.labels),
            "annotations":      dict(self.annotations),
            "schema_version":   self.schema_version,
            "created_at":       self.created_at.isoformat(),
            "framework_version": self.framework_version,
        }

    @classmethod
    def create(
        cls,
        *,
        snapshot_id:  str,
        session_id:   str,
        decision_id:  str,
        tags:         Tuple[str, ...]              = (),
        labels:       Optional[Dict[str, str]]     = None,
        annotations:  Optional[Dict[str, Any]]     = None,
        metadata_id:  Optional[str]                = None,
    ) -> "DecisionSnapshotMetadata":
        return cls(
            metadata_id  = metadata_id or str(uuid.uuid4()),
            snapshot_id  = snapshot_id,
            session_id   = session_id,
            decision_id  = decision_id,
            tags         = tags,
            labels       = labels or {},
            annotations  = annotations or {},
        )


@dataclass(frozen=True)
class SnapshotAuditMetadata:
    """
    Audit trail for how and when a :class:`DecisionSnapshot` was constructed.

    Parameters
    ----------
    audit_id :          Unique audit record identifier.
    snapshot_id :       Parent snapshot identifier.
    builder_id :        Identifier of the builder that created the snapshot.
    build_time_s :      Wall-clock time to build the snapshot.
    source_modules :    Tuple of source module labels (e.g. M1, M2, M3, M4).
    snapshot_size :     Approximate serialized size (bytes).
    validated :         Whether the snapshot passed validation.
    validated_at :      Timestamp of validation (None if not yet validated).
    published_at :      Timestamp of publication (None if not yet published).
    archived_at :       Timestamp of archival (None if not yet archived).
    created_at :        Creation timestamp.
    framework_version : Framework version.
    """

    audit_id:          str
    snapshot_id:       str
    builder_id:        str
    build_time_s:      float
    source_modules:    Tuple[str, ...]
    snapshot_size:     int              = 0
    validated:         bool             = False
    validated_at:      Optional[datetime] = None
    published_at:      Optional[datetime] = None
    archived_at:       Optional[datetime] = None
    created_at:        datetime          = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    framework_version: str               = VERSION

    def to_dict(self) -> dict:
        return {
            "audit_id":         self.audit_id,
            "snapshot_id":      self.snapshot_id,
            "builder_id":       self.builder_id,
            "build_time_s":     self.build_time_s,
            "source_modules":   list(self.source_modules),
            "snapshot_size":    self.snapshot_size,
            "validated":        self.validated,
            "validated_at":     self.validated_at.isoformat() if self.validated_at else None,
            "published_at":     self.published_at.isoformat() if self.published_at else None,
            "archived_at":      self.archived_at.isoformat() if self.archived_at else None,
            "created_at":       self.created_at.isoformat(),
            "framework_version": self.framework_version,
        }

    @classmethod
    def create(
        cls,
        *,
        snapshot_id:    str,
        builder_id:     str,
        build_time_s:   float                = 0.0,
        source_modules: Tuple[str, ...]      = (),
        snapshot_size:  int                  = 0,
        audit_id:       Optional[str]        = None,
    ) -> "SnapshotAuditMetadata":
        return cls(
            audit_id       = audit_id or str(uuid.uuid4()),
            snapshot_id    = snapshot_id,
            builder_id     = builder_id,
            build_time_s   = build_time_s,
            source_modules = source_modules,
            snapshot_size  = snapshot_size,
        )
