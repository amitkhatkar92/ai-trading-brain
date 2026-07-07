"""
iios/knowledge/search/models/unified_result.py
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional, TYPE_CHECKING

from ..search_constants import ItemType, SearchIndexType

if TYPE_CHECKING:
    pass

__all__ = ["UnifiedSearchResult"]


def _content_to_str(content: Any) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, (int, float, bool)):
        return str(content)
    try:
        import json
        return json.dumps(content, default=str)[:2000]
    except Exception:
        return str(content)[:2000]


@dataclass
class UnifiedSearchResult:
    """A single ranked item returned by the search engine.

    Covers both KnowledgeRecord items (item_type='knowledge') and
    GraphNode items (item_type='graph_node').
    """

    result_id:    str
    item_id:      str
    item_type:    str           # ItemType.value
    title:        str
    content:      str           = ""
    score:        float         = 0.0
    confidence:   float         = 1.0
    tags:         list[str]     = field(default_factory=list)
    metadata:     dict[str, Any] = field(default_factory=dict)
    snippet:      str           = ""
    source_index: str           = SearchIndexType.PRIMARY.value
    rank:         int           = 0
    highlights:   list[str]     = field(default_factory=list)
    created_at:   float         = field(default_factory=time.time)
    updated_at:   float         = field(default_factory=time.time)

    def __lt__(self, other: "UnifiedSearchResult") -> bool:
        return self.score < other.score

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, UnifiedSearchResult):
            return False
        return self.item_id == other.item_id

    def __hash__(self) -> int:
        return hash(self.item_id)

    def to_dict(self) -> dict[str, Any]:
        return {
            "result_id":    self.result_id,
            "item_id":      self.item_id,
            "item_type":    self.item_type,
            "title":        self.title,
            "content":      self.content,
            "score":        round(self.score, 6),
            "confidence":   self.confidence,
            "tags":         self.tags,
            "metadata":     self.metadata,
            "snippet":      self.snippet,
            "source_index": self.source_index,
            "rank":         self.rank,
            "highlights":   self.highlights,
            "created_at":   self.created_at,
            "updated_at":   self.updated_at,
        }

    # ── Constructors from domain objects ──────────────────────────────────────

    @classmethod
    def from_knowledge_record(
        cls,
        record:     Any,
        score:      float      = 0.0,
        highlights: list[str]  | None = None,
    ) -> "UnifiedSearchResult":
        """Build from a KnowledgeRecord."""
        meta = record.metadata
        content_str = _content_to_str(record.content)
        snippet     = (meta.description or content_str)[:300]
        return cls(
            result_id    = f"sr:{record.id}",
            item_id      = record.id,
            item_type    = ItemType.KNOWLEDGE.value,
            title        = record.title or record.id,
            content      = content_str,
            score        = score,
            confidence   = meta.confidence,
            tags         = list(meta.tags),
            metadata     = {
                "knowledge_type": str(record.knowledge_type.value),
                "domain":         str(meta.domain.value),
                "source":         str(meta.source.value),
                "priority":       str(meta.priority.value),
                "status":         str(record.status.value),
                "description":    meta.description,
                "version":        record.version,
            },
            snippet      = snippet,
            source_index = SearchIndexType.PRIMARY.value,
            highlights   = highlights or [],
            created_at   = record.created_at,
            updated_at   = record.updated_at,
        )

    @classmethod
    def from_graph_node(
        cls,
        node:   Any,
        score:  float = 0.0,
    ) -> "UnifiedSearchResult":
        """Build from a GraphNode."""
        description = node.metadata.description if node.metadata else ""
        snippet     = (description or node.label)[:300]
        return cls(
            result_id    = f"sr:{node.node_id}",
            item_id      = node.node_id,
            item_type    = ItemType.GRAPH_NODE.value,
            title        = node.label,
            content      = description,
            score        = score,
            confidence   = node.confidence,
            tags         = list(node.metadata.tags) if node.metadata else [],
            metadata     = {
                "node_type":    str(node.node_type.value),
                "weight":       node.weight,
                "knowledge_id": node.knowledge_id or "",
                "status":       str(node.status.value),
            },
            snippet      = snippet,
            source_index = SearchIndexType.GRAPH.value,
            created_at   = node.metadata.created_at if node.metadata else time.time(),
            updated_at   = node.metadata.updated_at if node.metadata else time.time(),
        )
