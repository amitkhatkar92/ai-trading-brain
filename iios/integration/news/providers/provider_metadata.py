"""iios/integration/news/providers/provider_metadata.py"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from iios.integration.news.news_constants import NewsProviderStatus


@dataclass
class NewsProviderMetadata:
    provider_id:    str                  = ""
    display_name:   str                  = ""
    description:    str                  = ""
    version:        str                  = "1.0.0"
    vendor:         str                  = ""
    vendor_url:     str                  = ""
    is_free:        bool                 = False
    is_demo:        bool                 = False
    status:         NewsProviderStatus   = NewsProviderStatus.DISCONNECTED
    tags:           list[str]            = field(default_factory=list)
    extra:          dict[str, Any]       = field(default_factory=dict)
    connect_count:  int                  = 0
    total_articles_delivered: int        = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider_id":  self.provider_id,
            "display_name": self.display_name,
            "vendor":       self.vendor,
            "is_free":      self.is_free,
            "is_demo":      self.is_demo,
            "status":       self.status.value,
        }


