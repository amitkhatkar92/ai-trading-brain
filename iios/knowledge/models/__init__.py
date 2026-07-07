"""
iios/knowledge/models/__init__.py
===================================
Public API of the knowledge models subpackage.
"""

from __future__ import annotations

from .knowledge_identifier import KnowledgeId, generate_id, parse_id
from .knowledge_metadata import KnowledgeMetadata
from .knowledge_reference import KnowledgeReference
from .knowledge_record import KnowledgeRecord
from .knowledge_snapshot import KnowledgeSnapshot, VersionDiff
from .knowledge_statistics import KnowledgeItemStats, KnowledgeRepositoryStats
from .knowledge_query import (
    FilterCondition,
    KnowledgeFilter,
    KnowledgeQuery,
    SearchQuery,
    PageRequest,
    PageResult,
)

__all__ = [
    "KnowledgeId", "generate_id", "parse_id",
    "KnowledgeMetadata",
    "KnowledgeReference",
    "KnowledgeRecord",
    "KnowledgeSnapshot", "VersionDiff",
    "KnowledgeItemStats", "KnowledgeRepositoryStats",
    "FilterCondition", "KnowledgeFilter", "KnowledgeQuery",
    "SearchQuery", "PageRequest", "PageResult",
]
