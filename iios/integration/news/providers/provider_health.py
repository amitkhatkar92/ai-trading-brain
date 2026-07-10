"""iios/integration/news/providers/provider_health.py"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class NewsProviderHealth:
    provider_id:           str   = ""
    is_connected:          bool  = False
    is_streaming:          bool  = False
    latency_ms:            float = 0.0
    last_article_at:       float = 0.0
    articles_per_min:      float = 0.0
    active_subscriptions:  int   = 0
    error_count:           int   = 0
    last_error:            str   = ""
    uptime_sec:            float = 0.0
    checked_at:            float = field(default_factory=time.time)

    def is_healthy(self) -> bool:
        return self.is_connected and not self.last_error

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider_id":         self.provider_id,
            "is_connected":        self.is_connected,
            "latency_ms":          round(self.latency_ms, 2),
            "articles_per_min":    round(self.articles_per_min, 2),
            "error_count":         self.error_count,
            "last_error":          self.last_error,
            "uptime_sec":          round(self.uptime_sec, 1),
            "is_healthy":          self.is_healthy(),
        }


