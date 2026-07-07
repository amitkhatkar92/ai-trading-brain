"""
iios/knowledge/versioning/models/provenance_record.py
======================================================
ProvenanceRecord — captures how a knowledge item came into existence
(created, derived, imported, merged, transformed, validated, etc.) and
links it to its source(s).

A single knowledge item may accumulate multiple provenance records over
its lifetime as it is derived from other items, validated, or transformed.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

from ..version_constants import (
    ProvenanceType,
    SYSTEM_VERSIONING_ACTOR,
    VERSIONING_SCHEMA_VERSION,
)

__all__ = ["ProvenanceRecord"]


def _new_id() -> str:
    return str(uuid.uuid4())


@dataclass
class ProvenanceRecord:
    """Tracks the origin and transformation history of a knowledge item."""

    provenance_id:      str            = field(default_factory=_new_id)
    knowledge_id:       str            = ""   # the item whose provenance this is

    provenance_type:    ProvenanceType = ProvenanceType.CREATED

    # Optional link to a source knowledge item
    source_id:          Optional[str]  = None
    source_version_id:  Optional[str]  = None

    # Who performed the operation
    actor:              str            = SYSTEM_VERSIONING_ACTOR
    description:        str            = ""

    # How the item was derived / transformed (e.g. "enriched", "filtered")
    transformation:     str            = ""

    # Free-form attributes
    attributes:         dict[str, Any] = field(default_factory=dict)

    created_at:         float          = field(default_factory=time.time)
    schema_version:     str            = VERSIONING_SCHEMA_VERSION

    # ── Helpers ───────────────────────────────────────────────────────────────

    @property
    def has_source(self) -> bool:
        return self.source_id is not None

    @property
    def is_creation(self) -> bool:
        return self.provenance_type == ProvenanceType.CREATED

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        return {
            "provenance_id":     self.provenance_id,
            "knowledge_id":      self.knowledge_id,
            "provenance_type":   self.provenance_type.value,
            "source_id":         self.source_id,
            "source_version_id": self.source_version_id,
            "actor":             self.actor,
            "description":       self.description,
            "transformation":    self.transformation,
            "attributes":        dict(self.attributes),
            "created_at":        self.created_at,
            "schema_version":    self.schema_version,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "ProvenanceRecord":
        return cls(
            provenance_id     = d.get("provenance_id",     _new_id()),
            knowledge_id      = d.get("knowledge_id",      ""),
            provenance_type   = ProvenanceType(d.get("provenance_type",
                                                      ProvenanceType.CREATED.value)),
            source_id         = d.get("source_id"),
            source_version_id = d.get("source_version_id"),
            actor             = d.get("actor",             SYSTEM_VERSIONING_ACTOR),
            description       = d.get("description",       ""),
            transformation    = d.get("transformation",    ""),
            attributes        = dict(d.get("attributes",   {})),
            created_at        = d.get("created_at",        time.time()),
            schema_version    = d.get("schema_version",    VERSIONING_SCHEMA_VERSION),
        )
