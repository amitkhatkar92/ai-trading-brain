"""
iios/knowledge/validators/knowledge_consistency.py
===================================================
Cross-item consistency checks — detects conflicts and duplicates across
the repository.
"""

from __future__ import annotations

import logging
import threading
from typing import TYPE_CHECKING, Optional

from ..knowledge_constants import RelationshipType
from ..knowledge_exceptions import KnowledgeConsistencyError
from ..models.knowledge_record import KnowledgeRecord

if TYPE_CHECKING:
    from ..repositories.knowledge_repository import KnowledgeRepository

__all__ = [
    "KnowledgeConsistencyChecker",
    "get_consistency_checker",
    "reset_consistency_checker",
]

_LOG = logging.getLogger("iios.knowledge.consistency")
_lock = threading.Lock()
_checker: Optional["KnowledgeConsistencyChecker"] = None


class KnowledgeConsistencyChecker:
    """Checks a record for consistency against the wider knowledge base.

    This is a light-weight checker that operates without the full validator
    pipeline.  For integration with the full validation pipeline, wire this
    into KnowledgeValidator as a custom rule.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._repository: Optional["KnowledgeRepository"] = None

    def set_repository(self, repo: "KnowledgeRepository") -> None:
        self._repository = repo

    def check_duplicate_title(self, record: KnowledgeRecord, limit: int = 5) -> list[str]:
        """Return IDs of existing records with the same title (different ID)."""
        if not self._repository or not record.title:
            return []
        from ..models.knowledge_query import KnowledgeFilter, KnowledgeQuery
        from ..knowledge_constants import QueryOperator
        q = KnowledgeQuery()
        q.filter.add_condition("title", QueryOperator.EQ, record.title)
        results = self._repository.query(q)
        return [r.id for r in results.items if r.id != record.id][:limit]

    def check_dangling_references(self, record: KnowledgeRecord) -> list[str]:
        """Return target IDs in record.references that do not exist."""
        if not self._repository:
            return []
        dangling = []
        for ref in record.references:
            if not ref.is_active:
                continue
            if not self._repository.exists(ref.target_id):
                dangling.append(ref.target_id)
        return dangling

    def check_superseded_circular(self, record: KnowledgeRecord) -> bool:
        """Return True if SUPERSEDES references would create a cycle."""
        if not self._repository:
            return False
        seen: set[str] = {record.id}
        to_visit = [
            ref.target_id for ref in record.references
            if ref.relationship_type == RelationshipType.SUPERSEDES and ref.is_active
        ]
        while to_visit:
            tid = to_visit.pop()
            if tid in seen:
                return True
            seen.add(tid)
            try:
                target = self._repository.get(tid)
                for ref in target.references:
                    if ref.relationship_type == RelationshipType.SUPERSEDES and ref.is_active:
                        to_visit.append(ref.target_id)
            except Exception:
                pass
        return False

    def assert_consistent(self, record: KnowledgeRecord) -> None:
        """Raise KnowledgeConsistencyError on any consistency violation."""
        dangling = self.check_dangling_references(record)
        if dangling:
            raise KnowledgeConsistencyError(
                f"Record '{record.id}' has dangling references: {dangling}",
                code="KCS-001",
                context={"dangling": dangling},
            )
        if self.check_superseded_circular(record):
            raise KnowledgeConsistencyError(
                f"Record '{record.id}' SUPERSEDES chain contains a cycle",
                code="KCS-002",
            )


def get_consistency_checker() -> KnowledgeConsistencyChecker:
    global _checker
    with _lock:
        if _checker is None:
            _checker = KnowledgeConsistencyChecker()
        return _checker


def reset_consistency_checker() -> None:
    global _checker
    with _lock:
        _checker = None
