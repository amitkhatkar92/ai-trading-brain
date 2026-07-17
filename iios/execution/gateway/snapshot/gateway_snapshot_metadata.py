"""iios/execution/gateway/snapshot/gateway_snapshot_metadata.py
==================================================
GatewaySnapshotMetadata — typed, immutable metadata container
attached to an ExecutionGatewaySnapshot.

C6 Execution Intelligence — Phase 5, Module 5
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple

from .constants import ACTOR_SNAPSHOT_SYSTEM, SCHEMA_VERSION, VERSION


@dataclass(frozen=True)
class GatewaySnapshotMetadata:
    """
    Typed, immutable metadata for a gateway snapshot.

    Carries provenance, tagging, and environment information.
    The snapshot builder accepts a GatewaySnapshotMetadata to
    populate the snapshot's ``audit_metadata`` field.
    """

    snapshot_id:    str
    source_system:  str          # which system produced this snapshot
    created_by:     str          # actor / service / process
    environment:    str          # PROD / UAT / DEV / TEST
    schema_version: str          = SCHEMA_VERSION
    tags:           Tuple[str, ...] = field(default_factory=tuple)
    notes:          str          = ""
    custom:         Dict[str, Any] = field(default_factory=dict, compare=False)
    created_at:     float        = field(default_factory=time.time)

    # ── Derived ───────────────────────────────────────────────────────────────

    @property
    def is_production(self) -> bool:
        return self.environment.upper() == "PROD"

    @property
    def has_tags(self) -> bool:
        return len(self.tags) > 0

    @property
    def has_notes(self) -> bool:
        return bool(self.notes)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id":    self.snapshot_id,
            "source_system":  self.source_system,
            "created_by":     self.created_by,
            "environment":    self.environment,
            "schema_version": self.schema_version,
            "tags":           list(self.tags),
            "notes":          self.notes,
            "custom":         dict(self.custom),
            "created_at":     self.created_at,
        }


# ── Factory function ──────────────────────────────────────────────────────────

def make_audit_metadata(
    snapshot_id:   str,
    *,
    source_system: str = ACTOR_SNAPSHOT_SYSTEM,
    created_by:    str = ACTOR_SNAPSHOT_SYSTEM,
    environment:   str = "PROD",
    tags:          Optional[Tuple[str, ...]] = None,
    notes:         str = "",
    custom:        Optional[Dict[str, Any]] = None,
) -> GatewaySnapshotMetadata:
    """Create standard audit metadata for a snapshot."""
    return GatewaySnapshotMetadata(
        snapshot_id=snapshot_id,
        source_system=source_system,
        created_by=created_by,
        environment=environment,
        tags=tags or (),
        notes=notes,
        custom=dict(custom or {}),
    )
