"""
knowledge_factory.py — iios.knowledge.lifecycle
-------------------------------------------------
Factory responsible for constructing :class:`KnowledgeSession` instances.

C14 Enterprise Knowledge Intelligence — Phase 1, Module 1
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from .constants import (
    ACTOR_LIFECYCLE,
    KnowledgeScope,
    KnowledgeSource,
    KnowledgeType,
)
from .knowledge_metadata import KnowledgeMetadata
from .knowledge_session import KnowledgeSession


class KnowledgeFactory:
    """
    Factory for :class:`KnowledgeSession`.

    All session construction MUST pass through this factory so that
    metadata defaults and initial state recording are applied consistently.
    """

    def create(
        self,
        artifact_id:       str,
        knowledge_type:    KnowledgeType,
        *,
        session_id:        Optional[str]            = None,
        knowledge_scope:   KnowledgeScope           = KnowledgeScope.DOMAIN,
        knowledge_source:  KnowledgeSource          = KnowledgeSource.INTERNAL,
        knowledge_version: str                      = "1.0.0",
        author:            str                      = "",
        tags:              Optional[List[str]]       = None,
        description:       str                      = "",
        custom:            Optional[Dict[str, Any]] = None,
        actor:             str                      = ACTOR_LIFECYCLE,
    ) -> KnowledgeSession:
        """
        Create and return a new :class:`KnowledgeSession` in CREATED state.

        The initial CREATED state is recorded in the session's state history.
        """
        metadata = KnowledgeMetadata.create(
            knowledge_type    = knowledge_type,
            knowledge_scope   = knowledge_scope,
            knowledge_source  = knowledge_source,
            knowledge_version = knowledge_version,
            author            = author,
            tags              = tags,
            description       = description,
            custom            = custom,
        )

        session = KnowledgeSession(
            session_id  = session_id,
            artifact_id = artifact_id,
            metadata    = metadata,
        )
        session.record_initial_state(actor)
        return session
