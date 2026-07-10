"""iios/integration/news/core/news_headline.py

Lightweight breaking-news headline — subset of NewsArticle for low-latency paths.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from iios.integration.news.news_constants import (
    NewsImportance,
    NewsUrgency,
    SentimentLabel,
)


@dataclass
class NewsHeadline:
    """
    Minimal news item — carries only the headline and key classification.

    Used when low latency matters more than completeness.
    Consumers can back-fill with the full NewsArticle later.
    """

    headline_id:    str             = field(default_factory=lambda: str(uuid.uuid4()))
    article_id:     str             = ""     # back-reference to full article
    provider_id:    str             = ""
    source_name:    str             = ""
    title:          str             = ""
    url:            str             = ""
    companies:      list[str]       = field(default_factory=list)
    topics:         list[str]       = field(default_factory=list)
    importance:     NewsImportance  = NewsImportance.MEDIUM
    urgency:        NewsUrgency     = NewsUrgency.NORMAL
    sentiment:      SentimentLabel  = SentimentLabel.UNKNOWN
    published_at:   float           = 0.0
    received_at:    float           = field(default_factory=time.time)
    metadata:       dict[str, Any]  = field(default_factory=dict)

    def age_ms(self, now: float | None = None) -> float:
        if now is None:
            now = time.time()
        return (now - self.received_at) * 1000.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "headline_id":  self.headline_id,
            "article_id":   self.article_id,
            "source_name":  self.source_name,
            "title":        self.title,
            "companies":    self.companies,
            "topics":       self.topics,
            "importance":   int(self.importance),
            "urgency":      self.urgency.value,
            "sentiment":    self.sentiment.value,
            "published_at": self.published_at,
            "received_at":  self.received_at,
        }
