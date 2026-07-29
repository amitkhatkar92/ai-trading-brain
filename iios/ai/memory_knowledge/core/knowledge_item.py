"""
knowledge_item.py -- iios.ai.memory_knowledge.core
===================================================
:class:`KnowledgeItem` — the fundamental unit of stored knowledge.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, FrozenSet, Optional

from .knowledge_category import KnowledgeCategory
from .knowledge_metadata import KnowledgeMetadata


@dataclass(frozen=True)
class KnowledgeItem:
    """Immutable unit of stored knowledge."""
    metadata: KnowledgeMetadata
    content:  Any            # Arbitrary payload: str, dict, list, etc.

    # ── Convenience aliases ───────────────────────────────────────────────────

    @property
    def item_id(self) -> str:
        return self.metadata.item_id

    @property
    def title(self) -> str:
        return self.metadata.title

    @property
    def category(self) -> KnowledgeCategory:
        return self.metadata.category

    @property
    def tags(self) -> FrozenSet[str]:
        return self.metadata.tags

    @property
    def collection_id(self) -> Optional[str]:
        return self.metadata.collection_id

    # ── Factory ───────────────────────────────────────────────────────────────

    @classmethod
    def create(
        cls,
        title:         str,
        content:       Any,
        category:      KnowledgeCategory   = KnowledgeCategory.DOCUMENT,
        tags:          FrozenSet[str]       = frozenset(),
        author:        str                  = "system",
        source:        str                  = "",
        language:      str                  = "en",
        collection_id: Optional[str]        = None,
        *,
        item_id:       Optional[str]        = None,
    ) -> "KnowledgeItem":
        meta = KnowledgeMetadata.create(
            title         = title,
            category      = category,
            tags          = tags,
            author        = author,
            source        = source,
            language      = language,
            collection_id = collection_id,
            item_id       = item_id,
        )
        return cls(metadata=meta, content=content)

    def with_content(self, new_content: Any) -> "KnowledgeItem":
        """Return a new item with updated content and incremented version."""
        return KnowledgeItem(
            metadata = self.metadata.with_update(),
            content  = new_content,
        )
