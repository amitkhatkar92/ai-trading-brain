"""
knowledge_metadata.py -- iios.ai.memory_knowledge.core
=======================================================
:class:`KnowledgeMetadata` — immutable metadata for a knowledge item.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from typing import FrozenSet, Optional

from .knowledge_category import KnowledgeCategory


@dataclass(frozen=True)
class KnowledgeMetadata:
    """Immutable metadata for a knowledge item."""
    item_id:     str
    title:       str
    category:    KnowledgeCategory
    tags:        FrozenSet[str]
    author:      str
    source:      str                  # provenance / URL / citation
    created_at:  float
    updated_at:  float
    version:     int
    language:    str                  # ISO 639-1 (e.g. "en")
    collection_id: Optional[str]      # parent collection, if any

    @classmethod
    def create(
        cls,
        title:         str,
        category:      KnowledgeCategory,
        tags:          FrozenSet[str]       = frozenset(),
        author:        str                  = "system",
        source:        str                  = "",
        language:      str                  = "en",
        collection_id: Optional[str]        = None,
        *,
        item_id:       Optional[str]        = None,
    ) -> "KnowledgeMetadata":
        now = time.time()
        return cls(
            item_id       = item_id or str(uuid.uuid4()),
            title         = title,
            category      = category,
            tags          = tags,
            author        = author,
            source        = source,
            created_at    = now,
            updated_at    = now,
            version       = 1,
            language      = language,
            collection_id = collection_id,
        )

    def with_update(self) -> "KnowledgeMetadata":
        return KnowledgeMetadata(
            item_id       = self.item_id,
            title         = self.title,
            category      = self.category,
            tags          = self.tags,
            author        = self.author,
            source        = self.source,
            created_at    = self.created_at,
            updated_at    = time.time(),
            version       = self.version + 1,
            language      = self.language,
            collection_id = self.collection_id,
        )
