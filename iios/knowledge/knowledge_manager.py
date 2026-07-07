"""
iios/knowledge/knowledge_manager.py
=====================================
High-level service façade over the knowledge subsystem.
External callers use this as the primary entry-point.
"""

from __future__ import annotations

import logging
import threading
from typing import Any, Optional

from .knowledge_constants import (
    KnowledgeDomain,
    KnowledgePriority,
    KnowledgeSource,
    KnowledgeStatus,
    KnowledgeType,
    RelationshipType,
    RelationshipStrength,
    VersionBump,
    SYSTEM_OWNER,
)
from .knowledge_exceptions import KnowledgeNotFoundError
from .models.knowledge_record import KnowledgeRecord
from .models.knowledge_reference import KnowledgeReference
from .models.knowledge_query import KnowledgeQuery, SearchQuery, PageResult
from .models.knowledge_identifier import generate_id, KnowledgeId
from .models.knowledge_metadata import KnowledgeMetadata
from .repositories.knowledge_repository import KnowledgeRepository, get_knowledge_repository
from .search.knowledge_search import KnowledgeSearchEngine, get_search_engine, SearchResult
from .graph.knowledge_graph import KnowledgeGraph, get_knowledge_graph
from .versioning.knowledge_versioning import KnowledgeVersioningEngine, get_versioning_engine
from .validators.knowledge_validator import KnowledgeValidator, get_knowledge_validator
from .knowledge_factory import KnowledgeFactory, get_knowledge_factory

__all__ = [
    "KnowledgeManager",
    "get_knowledge_manager",
    "reset_knowledge_manager",
]

_LOG = logging.getLogger("iios.knowledge.manager")
_lock = threading.Lock()
_manager: Optional["KnowledgeManager"] = None


class KnowledgeManager:
    """
    Unified façade for all knowledge operations.

    Wires together:
    - KnowledgeRepository  (CRUD + pagination)
    - KnowledgeSearchEngine (full-text / tag / type search)
    - KnowledgeGraph        (relationship traversal)
    - KnowledgeVersioningEngine (snapshot + rollback)
    - KnowledgeValidator    (pre-save validation)
    - KnowledgeFactory      (typed record construction)

    Usage::

        km = get_knowledge_manager()
        rec = km.create_fact("NIFTY close", {"close": 24350}, domain=KnowledgeDomain.MARKET)
        km.link(rec.id, other.id, RelationshipType.RELATED_TO)
        results = km.search("NIFTY trend")
    """

    def __init__(
        self,
        repository:  Optional[KnowledgeRepository]     = None,
        search:      Optional[KnowledgeSearchEngine]    = None,
        graph:       Optional[KnowledgeGraph]           = None,
        versioning:  Optional[KnowledgeVersioningEngine] = None,
        validator:   Optional[KnowledgeValidator]       = None,
        factory:     Optional[KnowledgeFactory]         = None,
    ) -> None:
        self._lock      = threading.RLock()
        self._repo      = repository or get_knowledge_repository()
        self._search    = search     or get_search_engine()
        self._graph     = graph      or get_knowledge_graph()
        self._versioning = versioning or get_versioning_engine()
        self._validator  = validator  or get_knowledge_validator()
        self._factory    = factory    or get_knowledge_factory()

    # ── Create ────────────────────────────────────────────────────────────────

    def save(self, record: KnowledgeRecord, validate: bool = True) -> KnowledgeRecord:
        """Store a new KnowledgeRecord. Optionally validates before saving."""
        if validate:
            self._validator.validate_or_raise(record)
        saved = self._repo.add(record)
        self._graph.sync_from_record(saved)
        self._versioning.snapshot(saved, change_summary="Initial creation")
        return saved

    def create_fact(self, title: str, content: Any = None, **kwargs: Any) -> KnowledgeRecord:
        rec = self._factory.create_fact(title, content, **kwargs)
        return self.save(rec)

    def create_rule(self, title: str, content: Any = None, **kwargs: Any) -> KnowledgeRecord:
        rec = self._factory.create_rule(title, content, **kwargs)
        return self.save(rec)

    def create_concept(self, title: str, content: Any = None, **kwargs: Any) -> KnowledgeRecord:
        rec = self._factory.create_concept(title, content, **kwargs)
        return self.save(rec)

    def create_strategy(self, title: str, content: Any = None, **kwargs: Any) -> KnowledgeRecord:
        rec = self._factory.create_strategy(title, content, **kwargs)
        return self.save(rec)

    def create_signal(self, title: str, content: Any = None, **kwargs: Any) -> KnowledgeRecord:
        rec = self._factory.create_signal(title, content, **kwargs)
        return self.save(rec)

    def create_observation(self, title: str, content: Any = None, **kwargs: Any) -> KnowledgeRecord:
        rec = self._factory.create_observation(title, content, **kwargs)
        return self.save(rec)

    def create_inference(self, title: str, content: Any = None, **kwargs: Any) -> KnowledgeRecord:
        rec = self._factory.create_inference(title, content, **kwargs)
        return self.save(rec)

    # ── Read ──────────────────────────────────────────────────────────────────

    def get(self, knowledge_id: str) -> KnowledgeRecord:
        return self._repo.get(knowledge_id)

    def get_optional(self, knowledge_id: str) -> Optional[KnowledgeRecord]:
        return self._repo.get_optional(knowledge_id)

    def exists(self, knowledge_id: str) -> bool:
        return self._repo.exists(knowledge_id)

    # ── Update ────────────────────────────────────────────────────────────────

    def update(
        self,
        record: KnowledgeRecord,
        bump: VersionBump = VersionBump.PATCH,
        change_summary: str = "",
        validate: bool = True,
    ) -> KnowledgeRecord:
        if validate:
            self._validator.validate_or_raise(record)
        self._versioning.bump_version(record, bump, change_summary)
        updated = self._repo.update(record)
        self._graph.sync_from_record(updated)
        return updated

    # ── Delete ────────────────────────────────────────────────────────────────

    def delete(self, knowledge_id: str, hard: bool = False) -> bool:
        deleted = self._repo.delete(knowledge_id, hard=hard)
        if deleted and hard:
            self._graph.remove_node(knowledge_id)
        return deleted

    def restore(self, knowledge_id: str) -> bool:
        ok = self._repo.restore(knowledge_id)
        if ok:
            rec = self._repo.get(knowledge_id)
            self._graph.sync_from_record(rec)
        return ok

    # ── Query & Search ────────────────────────────────────────────────────────

    def query(self, query: Optional[KnowledgeQuery] = None) -> PageResult:
        return self._repo.query(query)

    def search(self, text: str, **kwargs: Any) -> list[SearchResult]:
        sq = SearchQuery(text=text, **kwargs)
        return self._search.search(sq)

    def search_paged(self, sq: SearchQuery) -> PageResult:
        return self._search.search_paged(sq)

    def find_by_tags(self, tags: list[str], match_all: bool = False) -> list[KnowledgeRecord]:
        return self._search.find_by_tags(tags, match_all=match_all)

    def find_by_type(self, kt: KnowledgeType) -> list[KnowledgeRecord]:
        return self._search.find_by_type(kt)

    # ── Relationships ─────────────────────────────────────────────────────────

    def link(
        self,
        source_id: str,
        target_id: str,
        relationship_type: RelationshipType = RelationshipType.RELATED_TO,
        strength: RelationshipStrength = RelationshipStrength.WEAK,
        description: str = "",
        actor_id: str = SYSTEM_OWNER,
    ) -> KnowledgeReference:
        # Ensure both records exist
        self._repo.get(source_id)
        self._repo.get(target_id)

        ref = KnowledgeReference(
            source_id         = source_id,
            target_id         = target_id,
            relationship_type = relationship_type,
            strength          = strength,
            created_by        = actor_id,
            description       = description,
        )
        # Attach ref to source record
        source = self._repo.get(source_id)
        source.add_reference(ref)
        self._repo.update(source)
        self._graph.add_edge(ref)
        return ref

    def unlink(self, source_id: str, target_id: str, ref_id: Optional[str] = None) -> bool:
        source = self._repo.get_optional(source_id)
        if source is None:
            return False
        if ref_id:
            source.remove_reference(ref_id)
        else:
            source.references = [r for r in source.references if r.target_id != target_id]
        self._repo.update(source)
        return self._graph.remove_edge(source_id, target_id, ref_id)

    def related(self, knowledge_id: str, rel_type: Optional[RelationshipType] = None) -> list[str]:
        if rel_type:
            return self._graph.related_by_type(knowledge_id, rel_type)
        return list(self._graph.successors(knowledge_id))

    # ── History ───────────────────────────────────────────────────────────────

    def history(self, knowledge_id: str) -> list[Any]:
        return self._versioning.history(knowledge_id)

    def rollback(self, knowledge_id: str, snapshot_id: str) -> KnowledgeRecord:
        record = self._repo.get(knowledge_id)
        rolled = self._versioning.rollback(record, snapshot_id)
        return self._repo.update(rolled)

    # ── Misc ──────────────────────────────────────────────────────────────────

    def count(self) -> int:
        return self._repo.count()


# ── Singleton ─────────────────────────────────────────────────────────────────

def get_knowledge_manager() -> KnowledgeManager:
    global _manager
    with _lock:
        if _manager is None:
            _manager = KnowledgeManager()
        return _manager


def reset_knowledge_manager() -> None:
    global _manager
    with _lock:
        if _manager is not None:
            _manager._repo.reset()
        _manager = None
