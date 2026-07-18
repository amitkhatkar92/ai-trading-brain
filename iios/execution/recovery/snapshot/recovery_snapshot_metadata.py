"""
iios/execution/recovery/snapshot/recovery_snapshot_metadata.py
==============================================================
AuditMetadata — immutable audit record embedded in every
ExecutionRecoverySnapshot.

C7 Execution Recovery & Resilience — Phase 1, Module 5
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple

from .constants import ACTOR_BUILDER, SCHEMA_VERSION, VERSION


@dataclass(frozen=True)
class AuditMetadata:
    """
    Immutable audit trail for a snapshot build event.

    Embedded in every ExecutionRecoverySnapshot to record:
    - who built the snapshot
    - when it was built
    - which framework versions contributed
    - how long the build took
    """

    audit_id:           str
    built_by:           str
    built_at:           float
    lifecycle_version:  str
    engine_version:     str
    policy_version:     str
    failover_version:   str
    framework_version:  str
    schema_version:     str
    build_time_ms:      float
    tags:               Tuple[str, ...]        = ()
    metadata:           Dict[str, Any]         = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "audit_id":          self.audit_id,
            "built_by":          self.built_by,
            "built_at":          self.built_at,
            "lifecycle_version": self.lifecycle_version,
            "engine_version":    self.engine_version,
            "policy_version":    self.policy_version,
            "failover_version":  self.failover_version,
            "framework_version": self.framework_version,
            "schema_version":    self.schema_version,
            "build_time_ms":     self.build_time_ms,
            "tags":              list(self.tags),
            "metadata":          dict(self.metadata),
        }


def make_audit_metadata(
    *,
    built_by:          str = ACTOR_BUILDER,
    lifecycle_version: str = VERSION,
    engine_version:    str = VERSION,
    policy_version:    str = VERSION,
    failover_version:  str = VERSION,
    framework_version: str = VERSION,
    schema_version:    str = SCHEMA_VERSION,
    build_time_ms:     float = 0.0,
    tags:              Optional[Tuple[str, ...]] = None,
    metadata:          Optional[Dict[str, Any]] = None,
    audit_id:          Optional[str] = None,
    built_at:          Optional[float] = None,
) -> AuditMetadata:
    return AuditMetadata(
        audit_id          = audit_id or str(uuid.uuid4()),
        built_by          = built_by,
        built_at          = built_at if built_at is not None else time.time(),
        lifecycle_version = lifecycle_version,
        engine_version    = engine_version,
        policy_version    = policy_version,
        failover_version  = failover_version,
        framework_version = framework_version,
        schema_version    = schema_version,
        build_time_ms     = build_time_ms,
        tags              = tags or (),
        metadata          = dict(metadata) if metadata else {},
    )
