"""iios/execution/positions/snapshot/position_snapshot_metadata.py
==================================================
SnapshotAuditMetadata — immutable audit record attached to every
PositionSnapshot describing how and when it was built.

C6 Execution Intelligence — Phase 3, Module 5
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, Tuple

from .constants import ACTOR_BUILDER, VERSION


@dataclass(frozen=True)
class SnapshotAuditMetadata:
    """
    Immutable audit record embedded in every ``PositionSnapshot``.

    Records provenance: who built the snapshot, how long it took,
    whether validation passed, and which source objects were consumed.
    """

    built_by:                str
    built_at:                float
    build_duration_ms:       float
    source_position_id:      str
    source_snapshot_version: int
    validation_passed:       bool
    validation_errors:       Tuple[str, ...]
    version:                 str = VERSION
    notes:                   str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "built_by":                self.built_by,
            "built_at":                self.built_at,
            "build_duration_ms":       self.build_duration_ms,
            "source_position_id":      self.source_position_id,
            "source_snapshot_version": self.source_snapshot_version,
            "validation_passed":       self.validation_passed,
            "validation_errors":       list(self.validation_errors),
            "version":                 self.version,
            "notes":                   self.notes,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SnapshotAuditMetadata":
        return cls(
            built_by=data.get("built_by", ACTOR_BUILDER),
            built_at=float(data.get("built_at", time.time())),
            build_duration_ms=float(data.get("build_duration_ms", 0.0)),
            source_position_id=data.get("source_position_id", ""),
            source_snapshot_version=int(data.get("source_snapshot_version", 1)),
            validation_passed=bool(data.get("validation_passed", False)),
            validation_errors=tuple(data.get("validation_errors", [])),
            version=data.get("version", VERSION),
            notes=data.get("notes", ""),
        )


def make_audit_metadata(
    source_position_id:      str,
    source_snapshot_version: int,
    build_duration_ms:       float,
    validation_passed:       bool,
    validation_errors:       Tuple[str, ...] = (),
    *,
    built_by: str = ACTOR_BUILDER,
    notes:    str = "",
) -> SnapshotAuditMetadata:
    """Factory for ``SnapshotAuditMetadata`` with a current timestamp."""
    return SnapshotAuditMetadata(
        built_by=built_by,
        built_at=time.time(),
        build_duration_ms=build_duration_ms,
        source_position_id=source_position_id,
        source_snapshot_version=source_snapshot_version,
        validation_passed=validation_passed,
        validation_errors=validation_errors,
        notes=notes,
    )
