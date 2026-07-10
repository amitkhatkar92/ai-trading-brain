"""iios/integration/news/core/news_category_model.py

Hierarchical category taxonomy node.
Separate from the NewsCategory enum — provides tree structure.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

from iios.integration.news.news_constants import NewsCategory


@dataclass
class NewsCategoryNode:
    """
    One node in the news category taxonomy tree.

    A taxonomy allows multi-level classification:
    e.g. FINANCIAL → EARNINGS → EARNINGS_MISS
    """

    node_id:     str          = field(default_factory=lambda: str(uuid.uuid4()))
    category:    NewsCategory = NewsCategory.UNKNOWN
    label:       str          = ""           # human-readable name
    parent_id:   str          = ""           # empty = root node
    keywords:    list[str]    = field(default_factory=list)   # trigger words
    weight:      float        = 1.0          # routing priority
    is_active:   bool         = True
    metadata:    dict[str, Any] = field(default_factory=dict)

    def matches(self, text: str) -> bool:
        """Check if any keyword appears in the given text (case-insensitive)."""
        lowered = text.lower()
        return any(kw.lower() in lowered for kw in self.keywords)

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id":   self.node_id,
            "category":  self.category.value,
            "label":     self.label,
            "parent_id": self.parent_id,
            "keywords":  self.keywords,
            "weight":    self.weight,
        }
