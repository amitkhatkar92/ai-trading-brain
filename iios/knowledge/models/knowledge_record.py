"""
iios/knowledge/models/knowledge_record.py
==========================================
The core knowledge record dataclass.  This is the primary data
structure stored, retrieved, and versioned by the Knowledge Engine.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

from ..knowledge_constants import (
    KnowledgeType,
    KnowledgeStatus,
    KnowledgeDomain,
    KnowledgeSource,
    KnowledgePriority,
    DEFAULT_CONFIDENCE,
    SYSTEM_OWNER,
    KNOWLEDGE_NAMESPACE,
)
from .knowledge_identifier import KnowledgeId, generate_id
from .knowledge_metadata import KnowledgeMetadata
from .knowledge_reference import KnowledgeReference

__all__ = ["KnowledgeRecord"]


def _new_id() -> str:
    return str(uuid.uuid4())


@dataclass
class KnowledgeRecord:
    """Primary knowledge unit stored in the Knowledge Engine.

    Every piece of domain knowledge is represented as a ``KnowledgeRecord``.
    The ``content`` field holds the actual knowledge payload — it can be a
    string, number, dict, list, or any JSON-serializable object.

    Usage::

        rec = KnowledgeRecord(
            knowledge_id=generate_id(),
            knowledge_type=KnowledgeType.FACT,
            title="NIFTY 50 daily close",
            content={"symbol": "^NSEI", "close": 24350.0, "date": "2026-07-07"},
        )
    """

    # ── Identity ──────────────────────────────────────────────────────────────
    knowledge_id: KnowledgeId           = field(default_factory=generate_id)

    # ── Type & status ─────────────────────────────────────────────────────────
    knowledge_type: KnowledgeType       = KnowledgeType.FACT
    status: KnowledgeStatus             = KnowledgeStatus.DRAFT

    # ── Core content ──────────────────────────────────────────────────────────
    title: str                          = ""
    content: Any                        = None         # JSON-serializable payload

    # ── Metadata ──────────────────────────────────────────────────────────────
    metadata: KnowledgeMetadata         = field(default_factory=KnowledgeMetadata)

    # ── Versioning ────────────────────────────────────────────────────────────
    version: str                        = "1.0.0"     # semver
    version_sequence: int               = 1           # monotonic counter
    previous_version_id: Optional[str]  = None

    # ── Relationships ─────────────────────────────────────────────────────────
    references: list[KnowledgeReference] = field(default_factory=list)

    # ── Internal timestamps (redundant shortcut, sync with metadata) ──────────
    created_at: float                   = field(default_factory=time.time)
    updated_at: float                   = field(default_factory=time.time)

    # ── Extra ─────────────────────────────────────────────────────────────────
    checksum: str                       = ""   # content integrity hash
    is_deleted: bool                    = False

    @property
    def id(self) -> str:
        """Return the string form of the knowledge ID."""
        return self.knowledge_id.full

    @property
    def uid(self) -> str:
        return self.knowledge_id.uid

    @property
    def is_active(self) -> bool:
        return self.status == KnowledgeStatus.ACTIVE and not self.is_deleted

    @property
    def is_expired(self) -> bool:
        return self.metadata.is_expired

    def activate(self) -> None:
        self.status = KnowledgeStatus.ACTIVE
        self.touch()

    def archive(self) -> None:
        from ..knowledge_exceptions import KnowledgeArchivedError
        if self.status == KnowledgeStatus.ARCHIVED:
            raise KnowledgeArchivedError(f"'{self.id}' is already archived", code="KR-001")
        self.status = KnowledgeStatus.ARCHIVED
        self.touch()

    def deprecate(self) -> None:
        self.status = KnowledgeStatus.DEPRECATED
        self.touch()

    def touch(self) -> None:
        """Update timestamps."""
        self.updated_at = time.time()
        self.metadata.touch()

    def add_reference(self, ref: KnowledgeReference) -> None:
        self.references.append(ref)

    def remove_reference(self, ref_id: str) -> bool:
        for ref in self.references:
            if ref.ref_id == ref_id:
                ref.deactivate()
                return True
        return False

    def to_dict(self) -> dict[str, Any]:
        return {
            "knowledge_id":        self.knowledge_id.full,
            "knowledge_type":      self.knowledge_type.value,
            "status":              self.status.value,
            "title":               self.title,
            "content":             self.content,
            "metadata":            self.metadata.to_dict(),
            "version":             self.version,
            "version_sequence":    self.version_sequence,
            "previous_version_id": self.previous_version_id,
            "references":          [r.to_dict() for r in self.references],
            "created_at":          self.created_at,
            "updated_at":          self.updated_at,
            "checksum":            self.checksum,
            "is_deleted":          self.is_deleted,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "KnowledgeRecord":
        from .knowledge_identifier import KnowledgeId
        return cls(
            knowledge_id       = KnowledgeId.parse(d["knowledge_id"]),
            knowledge_type     = KnowledgeType(d.get("knowledge_type", KnowledgeType.FACT)),
            status             = KnowledgeStatus(d.get("status", KnowledgeStatus.DRAFT)),
            title              = d.get("title", ""),
            content            = d.get("content"),
            metadata           = KnowledgeMetadata.from_dict(d.get("metadata", {})),
            version            = d.get("version", "1.0.0"),
            version_sequence   = d.get("version_sequence", 1),
            previous_version_id = d.get("previous_version_id"),
            references         = [KnowledgeReference.from_dict(r) for r in d.get("references", [])],
            created_at         = d.get("created_at", time.time()),
            updated_at         = d.get("updated_at", time.time()),
            checksum           = d.get("checksum", ""),
            is_deleted         = d.get("is_deleted", False),
        )
