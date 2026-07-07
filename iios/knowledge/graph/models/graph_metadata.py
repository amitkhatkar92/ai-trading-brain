"""
iios/knowledge/graph/models/graph_metadata.py
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from ..graph_constants import GRAPH_SCHEMA_VERSION, SYSTEM_GRAPH_ACTOR

__all__ = ["GraphMetadata"]


@dataclass
class GraphMetadata:
    owner_id:       str              = SYSTEM_GRAPH_ACTOR
    created_by:     str              = SYSTEM_GRAPH_ACTOR
    updated_by:     str              = SYSTEM_GRAPH_ACTOR
    created_at:     float            = field(default_factory=time.time)
    updated_at:     float            = field(default_factory=time.time)
    description:    str              = ""
    tags:           list[str]        = field(default_factory=list)
    labels:         dict[str, str]   = field(default_factory=dict)
    attributes:     dict[str, Any]   = field(default_factory=dict)
    schema_version: str              = GRAPH_SCHEMA_VERSION
    source:         str              = ""
    notes:          str              = ""

    def touch(self, actor: str = SYSTEM_GRAPH_ACTOR) -> None:
        self.updated_at = time.time()
        self.updated_by = actor

    def add_tag(self, tag: str) -> None:
        if tag and tag not in self.tags:
            self.tags.append(tag)

    def has_tag(self, tag: str) -> bool:
        return tag in self.tags

    def to_dict(self) -> dict[str, Any]:
        return {
            "owner_id":       self.owner_id,
            "created_by":     self.created_by,
            "updated_by":     self.updated_by,
            "created_at":     self.created_at,
            "updated_at":     self.updated_at,
            "description":    self.description,
            "tags":           list(self.tags),
            "labels":         dict(self.labels),
            "attributes":     dict(self.attributes),
            "schema_version": self.schema_version,
            "source":         self.source,
            "notes":          self.notes,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> GraphMetadata:
        return cls(
            owner_id       = d.get("owner_id",       SYSTEM_GRAPH_ACTOR),
            created_by     = d.get("created_by",     SYSTEM_GRAPH_ACTOR),
            updated_by     = d.get("updated_by",     SYSTEM_GRAPH_ACTOR),
            created_at     = d.get("created_at",     time.time()),
            updated_at     = d.get("updated_at",     time.time()),
            description    = d.get("description",    ""),
            tags           = list(d.get("tags",      [])),
            labels         = dict(d.get("labels",    {})),
            attributes     = dict(d.get("attributes", {})),
            schema_version = d.get("schema_version", GRAPH_SCHEMA_VERSION),
            source         = d.get("source",         ""),
            notes          = d.get("notes",          ""),
        )
