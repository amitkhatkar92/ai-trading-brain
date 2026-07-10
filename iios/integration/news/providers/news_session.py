"""iios/integration/news/providers/news_session.py

Active provider connection session.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from iios.integration.news.news_constants import NewsProviderStatus


@dataclass
class NewsSession:
    session_id:    str                 = field(default_factory=lambda: str(uuid.uuid4()))
    provider_id:   str                 = ""
    status:        NewsProviderStatus  = NewsProviderStatus.DISCONNECTED
    started_at:    float               = field(default_factory=time.time)
    last_active:   float               = field(default_factory=time.time)
    articles_delivered: int            = 0
    error_count:   int                 = 0
    reconnects:    int                 = 0
    metadata:      dict[str, Any]      = field(default_factory=dict)

    def touch(self) -> None:
        self.last_active = time.time()
        self.articles_delivered += 1

    def record_error(self) -> None:
        self.error_count += 1

    def uptime_sec(self) -> float:
        return time.time() - self.started_at

    def is_connected(self) -> bool:
        return self.status in (
            NewsProviderStatus.CONNECTED,
            NewsProviderStatus.STREAMING,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id":         self.session_id,
            "provider_id":        self.provider_id,
            "status":             self.status.value,
            "articles_delivered": self.articles_delivered,
            "error_count":        self.error_count,
            "uptime_sec":         round(self.uptime_sec(), 1),
        }


