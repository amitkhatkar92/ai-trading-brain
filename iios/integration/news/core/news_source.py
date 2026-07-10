"""iios/integration/news/core/news_source.py

Metadata for a news source (wire, publication, feed).
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from iios.integration.news.news_constants import NewsLanguage, NewsRegion


@dataclass
class NewsSource:
    """Describes a named source within a provider (e.g. 'Reuters Business')."""

    source_id:    str            = field(default_factory=lambda: str(uuid.uuid4()))
    provider_id:  str            = ""
    name:         str            = ""
    description:  str            = ""
    url:          str            = ""
    language:     NewsLanguage   = NewsLanguage.EN
    region:       NewsRegion     = NewsRegion.GLOBAL
    country:      str            = ""
    categories:   list[str]      = field(default_factory=list)
    is_premium:   bool           = False
    is_realtime:  bool           = False
    reliability:  float          = 1.0    # [0.0 – 1.0]
    registered_at: float         = field(default_factory=time.time)
    metadata:     dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_id":    self.source_id,
            "provider_id":  self.provider_id,
            "name":         self.name,
            "url":          self.url,
            "language":     self.language.value,
            "region":       self.region.value,
            "is_realtime":  self.is_realtime,
            "reliability":  self.reliability,
        }
