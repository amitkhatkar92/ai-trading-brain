"""
iios/knowledge/models/knowledge_reference.py
=============================================
Lightweight cross-reference between knowledge items.
Used in the knowledge graph and for provenance tracking.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

from ..knowledge_constants import (
    RelationshipType,
    RelationshipStrength,
    SYSTEM_OWNER,
)

__all__ = ["KnowledgeReference"]


def _new_id() -> str:
    return str(uuid.uuid4())


@dataclass
class KnowledgeReference:
    """A directed relationship from one knowledge item to another.

    ``source_id`` → ``target_id`` via ``relationship_type``.
    """

    source_id:         str
    target_id:         str
    relationship_type: RelationshipType   = RelationshipType.RELATED_TO
    strength:          float              = RelationshipStrength.MODERATE.value

    # Metadata
    ref_id:      str            = field(default_factory=_new_id)
    created_by:  str            = SYSTEM_OWNER
    created_at:  float          = field(default_factory=time.time)
    description: str            = ""
    attributes:  dict[str, Any] = field(default_factory=dict)
    is_active:   bool           = True

    def __post_init__(self) -> None:
        # Clamp strength to [0, 1]
        self.strength = max(0.0, min(1.0, self.strength))

    def deactivate(self) -> None:
        self.is_active = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "ref_id":            self.ref_id,
            "source_id":         self.source_id,
            "target_id":         self.target_id,
            "relationship_type": self.relationship_type.value,
            "strength":          self.strength,
            "created_by":        self.created_by,
            "created_at":        self.created_at,
            "description":       self.description,
            "attributes":        dict(self.attributes),
            "is_active":         self.is_active,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "KnowledgeReference":
        return cls(
            source_id         = d["source_id"],
            target_id         = d["target_id"],
            relationship_type = RelationshipType(d.get("relationship_type", RelationshipType.RELATED_TO)),
            strength          = d.get("strength", RelationshipStrength.MODERATE.value),
            ref_id            = d.get("ref_id", _new_id()),
            created_by        = d.get("created_by", SYSTEM_OWNER),
            created_at        = d.get("created_at", time.time()),
            description       = d.get("description", ""),
            attributes        = dict(d.get("attributes", {})),
            is_active         = d.get("is_active", True),
        )
