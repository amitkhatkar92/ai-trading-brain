"""
iios/knowledge/models/knowledge_metadata.py
============================================
Rich metadata attached to every knowledge item.
Immutable once stamped; mutable copy returned via ``evolve()``.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field, replace
from typing import Any, Optional

from ..knowledge_constants import (
    KnowledgeDomain,
    KnowledgePriority,
    KnowledgeSource,
    MAX_TAGS,
    SYSTEM_OWNER,
    DEFAULT_CONFIDENCE,
    MIN_CONFIDENCE,
    MAX_CONFIDENCE,
    DEFAULT_TTL_SECONDS,
    SCHEMA_VERSION,
)

__all__ = ["KnowledgeMetadata"]


@dataclass
class KnowledgeMetadata:
    """Metadata envelope attached to every knowledge item."""

    # Ownership & authorship
    owner_id: str              = SYSTEM_OWNER
    created_by: str            = SYSTEM_OWNER
    updated_by: str            = SYSTEM_OWNER

    # Timestamps (Unix epoch floats)
    created_at: float          = field(default_factory=time.time)
    updated_at: float          = field(default_factory=time.time)
    expires_at: Optional[float] = None   # None = never

    # Domain context
    domain: KnowledgeDomain    = KnowledgeDomain.GENERAL
    source: KnowledgeSource    = KnowledgeSource.SYSTEM
    priority: KnowledgePriority = KnowledgePriority.MEDIUM

    # Descriptors
    description: str           = ""
    tags: list[str]            = field(default_factory=list)
    labels: dict[str, str]     = field(default_factory=dict)
    attributes: dict[str, Any] = field(default_factory=dict)

    # Confidence (0.0 – 1.0)
    confidence: float          = DEFAULT_CONFIDENCE

    # Schema
    schema_version: str        = SCHEMA_VERSION

    # Provenance
    source_uri: str            = ""
    checksum: str              = ""

    # Free-form notes
    notes: str                 = ""

    # TTL in seconds (0 = never expires)
    ttl_seconds: int           = DEFAULT_TTL_SECONDS

    def __post_init__(self) -> None:
        # Clamp confidence
        self.confidence = max(MIN_CONFIDENCE, min(MAX_CONFIDENCE, self.confidence))
        # Truncate tags
        if len(self.tags) > MAX_TAGS:
            self.tags = self.tags[:MAX_TAGS]

    @property
    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return time.time() > self.expires_at

    @property
    def age_seconds(self) -> float:
        return time.time() - self.created_at

    def add_tag(self, tag: str) -> None:
        if tag not in self.tags and len(self.tags) < MAX_TAGS:
            self.tags.append(tag)

    def remove_tag(self, tag: str) -> bool:
        if tag in self.tags:
            self.tags.remove(tag)
            return True
        return False

    def has_tag(self, tag: str) -> bool:
        return tag in self.tags

    def touch(self, updated_by: str = SYSTEM_OWNER) -> None:
        """Update the ``updated_at`` timestamp."""
        self.updated_at = time.time()
        self.updated_by = updated_by

    def evolve(self, **changes: Any) -> "KnowledgeMetadata":
        """Return a copy of this metadata with *changes* applied."""
        return replace(self, **changes)

    def to_dict(self) -> dict[str, Any]:
        return {
            "owner_id":       self.owner_id,
            "created_by":     self.created_by,
            "updated_by":     self.updated_by,
            "created_at":     self.created_at,
            "updated_at":     self.updated_at,
            "expires_at":     self.expires_at,
            "domain":         self.domain.value,
            "source":         self.source.value,
            "priority":       self.priority.value,
            "description":    self.description,
            "tags":           list(self.tags),
            "labels":         dict(self.labels),
            "attributes":     dict(self.attributes),
            "confidence":     self.confidence,
            "schema_version": self.schema_version,
            "source_uri":     self.source_uri,
            "checksum":       self.checksum,
            "notes":          self.notes,
            "ttl_seconds":    self.ttl_seconds,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "KnowledgeMetadata":
        return cls(
            owner_id       = d.get("owner_id", SYSTEM_OWNER),
            created_by     = d.get("created_by", SYSTEM_OWNER),
            updated_by     = d.get("updated_by", SYSTEM_OWNER),
            created_at     = d.get("created_at", time.time()),
            updated_at     = d.get("updated_at", time.time()),
            expires_at     = d.get("expires_at"),
            domain         = KnowledgeDomain(d.get("domain", KnowledgeDomain.GENERAL)),
            source         = KnowledgeSource(d.get("source", KnowledgeSource.SYSTEM)),
            priority       = KnowledgePriority(d.get("priority", KnowledgePriority.MEDIUM)),
            description    = d.get("description", ""),
            tags           = list(d.get("tags", [])),
            labels         = dict(d.get("labels", {})),
            attributes     = dict(d.get("attributes", {})),
            confidence     = d.get("confidence", DEFAULT_CONFIDENCE),
            schema_version = d.get("schema_version", SCHEMA_VERSION),
            source_uri     = d.get("source_uri", ""),
            checksum       = d.get("checksum", ""),
            notes          = d.get("notes", ""),
            ttl_seconds    = d.get("ttl_seconds", DEFAULT_TTL_SECONDS),
        )
