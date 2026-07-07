"""
iios/knowledge/versioning/version_factory.py
=============================================
VersionFactory — convenience factory for creating pre-configured
KnowledgeVersion, VersionBranch, ProvenanceRecord, and LineageEdge
objects without direct dataclass construction.

Usage::

    from iios.knowledge.versioning.version_factory import get_version_factory

    factory = get_version_factory()
    branch  = factory.create_branch(knowledge_id="iios.knowledge/uuid", name="experimental")
    pr      = factory.create_provenance_creation(knowledge_id, author="user:alice")
"""

from __future__ import annotations

import threading
from typing import Any, Optional

from ..knowledge_constants import VersionBump
from .version_constants import (
    DEFAULT_BRANCH,
    LineageRelationType,
    ProvenanceType,
    SYSTEM_VERSIONING_ACTOR,
    BranchStatus,
)
from .models.knowledge_version import KnowledgeVersion, VersionStatus
from .models.version_branch import VersionBranch
from .models.version_diff import FieldChange, RecordDiff
from .models.provenance_record import ProvenanceRecord
from .models.lineage_graph import LineageEdge

__all__ = ["VersionFactory", "get_version_factory", "reset_version_factory"]

_lock = threading.Lock()
_factory: Optional["VersionFactory"] = None


class VersionFactory:
    """Thin factory that produces versioning domain objects."""

    # ── KnowledgeVersion ──────────────────────────────────────────────────────

    def create_version(
        self,
        knowledge_id:      str,
        version_string:    str,
        version_seq:       int,
        bump_type:         VersionBump         = VersionBump.MINOR,
        status:            VersionStatus        = VersionStatus.CURRENT,
        branch:            str                 = DEFAULT_BRANCH,
        author:            str                 = SYSTEM_VERSIONING_ACTOR,
        change_summary:    str                 = "",
        change_reason:     str                 = "",
        payload:           Optional[dict[str, Any]] = None,
        parent_version_id: Optional[str]        = None,
        is_draft:          bool                = False,
    ) -> KnowledgeVersion:
        actual_status = VersionStatus.DRAFT if is_draft else status
        return KnowledgeVersion(
            knowledge_id      = knowledge_id,
            version_string    = version_string,
            version_seq       = version_seq,
            bump_type         = bump_type,
            status            = actual_status,
            branch_name       = branch,
            author            = author,
            change_summary    = change_summary,
            change_reason     = change_reason,
            payload           = dict(payload or {}),
            parent_version_id = parent_version_id,
        )

    def create_draft(
        self,
        knowledge_id: str,
        version_string: str,
        version_seq: int,
        payload: Optional[dict[str, Any]] = None,
        author: str = SYSTEM_VERSIONING_ACTOR,
    ) -> KnowledgeVersion:
        return self.create_version(
            knowledge_id   = knowledge_id,
            version_string = version_string,
            version_seq    = version_seq,
            status         = VersionStatus.DRAFT,
            payload        = payload,
            author         = author,
            is_draft       = True,
        )

    # ── VersionBranch ─────────────────────────────────────────────────────────

    def create_branch(
        self,
        knowledge_id:      str,
        name:              str,
        source_branch:     str            = DEFAULT_BRANCH,
        source_version_id: Optional[str]  = None,
        created_by:        str            = SYSTEM_VERSIONING_ACTOR,
        description:       str            = "",
    ) -> VersionBranch:
        return VersionBranch(
            knowledge_id      = knowledge_id,
            name              = name,
            source_branch     = source_branch,
            source_version_id = source_version_id,
            created_by        = created_by,
            description       = description,
        )

    def create_experimental_branch(
        self,
        knowledge_id:      str,
        name:              str,
        source_version_id: Optional[str] = None,
        created_by:        str = SYSTEM_VERSIONING_ACTOR,
    ) -> VersionBranch:
        return self.create_branch(
            knowledge_id      = knowledge_id,
            name              = f"experimental/{name}",
            source_branch     = DEFAULT_BRANCH,
            source_version_id = source_version_id,
            created_by        = created_by,
            description       = "Experimental branch — not for production.",
        )

    def create_working_branch(
        self,
        knowledge_id:      str,
        name:              str,
        source_version_id: Optional[str] = None,
        created_by:        str = SYSTEM_VERSIONING_ACTOR,
    ) -> VersionBranch:
        return self.create_branch(
            knowledge_id      = knowledge_id,
            name              = f"work/{name}",
            source_branch     = DEFAULT_BRANCH,
            source_version_id = source_version_id,
            created_by        = created_by,
            description       = "Working branch for in-progress changes.",
        )

    # ── ProvenanceRecord ─────────────────────────────────────────────────────

    def create_provenance_creation(
        self,
        knowledge_id: str,
        actor:        str = SYSTEM_VERSIONING_ACTOR,
        description:  str = "",
    ) -> ProvenanceRecord:
        return ProvenanceRecord(
            knowledge_id    = knowledge_id,
            provenance_type = ProvenanceType.CREATED,
            actor           = actor,
            description     = description or f"Created by {actor}",
        )

    def create_provenance_derivation(
        self,
        knowledge_id:      str,
        source_id:         str,
        transformation:    str,
        actor:             str = SYSTEM_VERSIONING_ACTOR,
        source_version_id: Optional[str] = None,
    ) -> ProvenanceRecord:
        return ProvenanceRecord(
            knowledge_id      = knowledge_id,
            provenance_type   = ProvenanceType.DERIVED_FROM,
            source_id         = source_id,
            source_version_id = source_version_id,
            actor             = actor,
            transformation    = transformation,
            description       = f"Derived from {source_id} via {transformation}",
        )

    # ── LineageEdge ───────────────────────────────────────────────────────────

    def create_lineage_edge(
        self,
        source_id: str,
        target_id: str,
        relation:  LineageRelationType = LineageRelationType.DERIVED_FROM,
        weight:    float = 1.0,
    ) -> LineageEdge:
        return LineageEdge(
            source_id = source_id,
            target_id = target_id,
            relation  = relation,
            weight    = weight,
        )


# ── Singleton helpers ─────────────────────────────────────────────────────────

def get_version_factory() -> VersionFactory:
    global _factory
    if _factory is None:
        with _lock:
            if _factory is None:
                _factory = VersionFactory()
    return _factory


def reset_version_factory() -> None:
    global _factory
    with _lock:
        _factory = None
