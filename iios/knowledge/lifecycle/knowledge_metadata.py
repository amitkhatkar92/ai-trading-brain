"""
knowledge_metadata.py — iios.knowledge.lifecycle
--------------------------------------------------
Immutable metadata block attached to a knowledge session.

C14 Enterprise Knowledge Intelligence — Phase 1, Module 1
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, FrozenSet, List, Optional

from .constants import (
    KnowledgeScope,
    KnowledgeSource,
    KnowledgeType,
    VERSION,
)


@dataclass(frozen=True)
class KnowledgeMetadata:
    """
    Immutable metadata attached to a :class:`~knowledge_session.KnowledgeSession`.

    Fields
    ------
    knowledge_type :    Classification of the knowledge artifact.
    knowledge_scope :   Institutional scope.
    knowledge_source :  Provenance / origin.
    knowledge_version : Semantic version string of the artifact.
    author :            Identity that authored or submitted the artifact.
    tags :              Immutable set of classification tags.
    description :       Human-readable description.
    custom :            Supplementary key-value metadata.
    schema_version :    Version of this metadata schema.
    """
    knowledge_type:    KnowledgeType
    knowledge_scope:   KnowledgeScope  = KnowledgeScope.DOMAIN
    knowledge_source:  KnowledgeSource = KnowledgeSource.INTERNAL
    knowledge_version: str             = "1.0.0"
    author:            str             = ""
    tags:              FrozenSet[str]  = field(default_factory=frozenset)
    description:       str             = ""
    custom:            Dict[str, Any]  = field(default_factory=dict)
    schema_version:    str             = VERSION

    @classmethod
    def create(
        cls,
        knowledge_type:    KnowledgeType,
        *,
        knowledge_scope:   KnowledgeScope  = KnowledgeScope.DOMAIN,
        knowledge_source:  KnowledgeSource = KnowledgeSource.INTERNAL,
        knowledge_version: str             = "1.0.0",
        author:            str             = "",
        tags:              Optional[List[str]] = None,
        description:       str             = "",
        custom:            Optional[Dict[str, Any]] = None,
    ) -> "KnowledgeMetadata":
        return cls(
            knowledge_type    = knowledge_type,
            knowledge_scope   = knowledge_scope,
            knowledge_source  = knowledge_source,
            knowledge_version = knowledge_version,
            author            = author,
            tags              = frozenset(tags or []),
            description       = description,
            custom            = custom or {},
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "knowledge_type":    self.knowledge_type.value,
            "knowledge_scope":   self.knowledge_scope.value,
            "knowledge_source":  self.knowledge_source.value,
            "knowledge_version": self.knowledge_version,
            "author":            self.author,
            "tags":              sorted(self.tags),
            "description":       self.description,
            "schema_version":    self.schema_version,
        }
