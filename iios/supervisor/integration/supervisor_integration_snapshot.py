"""
supervisor_integration_snapshot.py — iios.supervisor.integration
-----------------------------------------------------------------
Wrapper that pairs a published M5 SupervisorSnapshot with the
integration metadata that generated it.

C13 AI Supervisor & Autonomous Governance — Phase 1, Module 6
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from .constants import VERSION


@dataclass(frozen=True)
class SupervisorIntegrationSnapshot:
    """
    Immutable wrapper around a published M5 supervisor snapshot.

    Carries the M5 snapshot (typed as ``Any`` to avoid circular imports)
    together with integration-layer metadata: which integration run produced
    it, which request triggered it, and when it was published.

    Fields
    ------
    integration_snapshot_id : Unique wrapper identifier.
    integration_id :          Integration run that produced this snapshot.
    request_id :              Originating integration request.
    session_id :              Owning lifecycle session.
    supervisor_snapshot :     The raw M5 SupervisorSnapshot object.
    snapshot_id :             M5 snapshot identifier (copied for quick access).
    published_at :            Wall-clock publication time.
    integration_version :     Framework version string.
    metadata :                Supplementary metadata.
    """
    integration_snapshot_id: str
    integration_id:          str
    request_id:              str
    session_id:              str
    supervisor_snapshot:     Any            # iios.supervisor.snapshot.SupervisorSnapshot
    snapshot_id:             str
    published_at:            float = field(default_factory=time.time)
    integration_version:     str   = VERSION
    metadata:                Dict[str, Any] = field(default_factory=dict)

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def create(
        cls,
        integration_id:      str,
        request_id:          str,
        supervisor_snapshot: Any,
        *,
        session_id:               str                      = "",
        integration_snapshot_id:  Optional[str]            = None,
        metadata:                 Optional[Dict[str, Any]] = None,
    ) -> "SupervisorIntegrationSnapshot":
        snap_id = (
            getattr(supervisor_snapshot, "snapshot_id", None) or str(uuid.uuid4())
        )
        return cls(
            integration_snapshot_id = integration_snapshot_id or str(uuid.uuid4()),
            integration_id          = integration_id,
            request_id              = request_id,
            session_id              = session_id,
            supervisor_snapshot     = supervisor_snapshot,
            snapshot_id             = snap_id,
            metadata                = metadata or {},
        )

    # ------------------------------------------------------------------
    # Derived properties
    # ------------------------------------------------------------------

    @property
    def is_valid(self) -> bool:
        """True when the inner snapshot reports itself valid."""
        snap = self.supervisor_snapshot
        if snap is None:
            return False
        return bool(getattr(snap, "is_valid", True))

    @property
    def is_published(self) -> bool:
        """True when the inner snapshot is marked published."""
        snap = self.supervisor_snapshot
        if snap is None:
            return False
        return bool(getattr(snap, "is_published", False))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "integration_snapshot_id": self.integration_snapshot_id,
            "integration_id":          self.integration_id,
            "request_id":              self.request_id,
            "session_id":              self.session_id,
            "snapshot_id":             self.snapshot_id,
            "is_valid":                self.is_valid,
            "is_published":            self.is_published,
            "published_at":            self.published_at,
            "integration_version":     self.integration_version,
        }
