"""iios/execution/monitoring/lifecycle/monitoring_metadata.py
==================================================
MonitoringMetadata — immutable metadata attached to a monitoring session.

C6 Execution Intelligence — Phase 6, Module 1
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple

from .constants import SCHEMA_VERSION, VERSION


@dataclass(frozen=True)
class MonitoringMetadata:
    """Immutable metadata record for a monitoring session."""

    session_id:     str
    source_system:  str
    created_by:     str
    environment:    str
    schema_version: str = SCHEMA_VERSION
    tags:           Tuple[str, ...] = ()
    notes:          str = ""
    custom:         Dict[str, Any] = field(default_factory=dict, compare=False)
    created_at:     float = field(default_factory=time.time, compare=False)

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
            "session_id":     self.session_id,
            "source_system":  self.source_system,
            "created_by":     self.created_by,
            "environment":    self.environment,
            "schema_version": self.schema_version,
            "tags":           list(self.tags),
            "notes":          self.notes,
            "created_at":     self.created_at,
        }


def make_monitoring_metadata(
    session_id:    str,
    *,
    source_system: str = "iios:execution:monitoring",
    created_by:    str = "iios:system",
    environment:   str = "PROD",
    tags:          Optional[Tuple[str, ...]] = None,
    notes:         str = "",
    custom:        Optional[Dict[str, Any]] = None,
) -> MonitoringMetadata:
    return MonitoringMetadata(
        session_id=session_id,
        source_system=source_system,
        created_by=created_by,
        environment=environment,
        tags=tags or (),
        notes=notes,
        custom=custom or {},
    )
