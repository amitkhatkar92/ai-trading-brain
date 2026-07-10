"""iios/integration/news/core/news_metadata.py

Extensible metadata bag attached to any news object.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass
class NewsMetadata:
    """
    Carries supplementary key/value pairs for a news object.
    Allows providers to attach arbitrary fields without polluting core models.
    """

    meta_id:       str            = field(default_factory=lambda: str(uuid.uuid4()))
    parent_id:     str            = ""     # article_id / event_id / headline_id
    provider_id:   str            = ""
    schema_version: str           = "1.0"
    created_at:    float          = field(default_factory=time.time)
    data:          dict[str, Any] = field(default_factory=dict)

    def set(self, key: str, value: Any) -> None:
        self.data[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, default)

    def has(self, key: str) -> bool:
        return key in self.data

    def merge(self, other: "NewsMetadata") -> None:
        """Non-destructive merge — existing keys are not overwritten."""
        for k, v in other.data.items():
            if k not in self.data:
                self.data[k] = v

    def to_dict(self) -> dict[str, Any]:
        return {
            "meta_id":   self.meta_id,
            "parent_id": self.parent_id,
            "data":      dict(self.data),
        }
