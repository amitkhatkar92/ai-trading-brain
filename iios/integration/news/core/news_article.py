"""iios/integration/news/core/news_article.py

Full news article — the primary carrier of news content.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from iios.integration.news.news_constants import (
    NewsCategory,
    NewsImportance,
    NewsLanguage,
    NewsRegion,
    NewsUrgency,
    SentimentLabel,
    MIN_ARTICLE_TITLE_LEN,
    MIN_ARTICLE_BODY_LEN,
)


@dataclass
class NewsArticle:
    """
    A single normalized news article.

    Fields are intentionally kept flat for fast dict serialization and
    datastore writes.  Rich typed sub-objects are avoided.
    """

    # ── Identity ──────────────────────────────────────────────────────────────
    article_id:   str               = field(default_factory=lambda: str(uuid.uuid4()))
    provider_id:  str               = ""
    source_id:    str               = ""       # upstream source identifier
    source_name:  str               = ""       # human-readable source name
    external_id:  str               = ""       # provider's own ID

    # ── Content ───────────────────────────────────────────────────────────────
    title:        str               = ""
    body:         str               = ""
    summary:      str               = ""
    author:       str               = ""
    url:          str               = ""
    image_url:    str               = ""

    # ── Taxonomy ──────────────────────────────────────────────────────────────
    language:     NewsLanguage      = NewsLanguage.UNKNOWN
    region:       NewsRegion        = NewsRegion.UNKNOWN
    countries:    list[str]         = field(default_factory=list)
    companies:    list[str]         = field(default_factory=list)   # tickers
    sectors:      list[str]         = field(default_factory=list)
    asset_class:  str               = ""
    categories:   list[NewsCategory] = field(default_factory=list)
    topics:       list[str]         = field(default_factory=list)
    tags:         list[str]         = field(default_factory=list)
    keywords:     list[str]         = field(default_factory=list)

    # ── Importance ────────────────────────────────────────────────────────────
    importance:   NewsImportance    = NewsImportance.MEDIUM
    urgency:      NewsUrgency       = NewsUrgency.NORMAL
    is_breaking:  bool              = False
    is_exclusive: bool              = False

    # ── Sentiment ─────────────────────────────────────────────────────────────
    sentiment:         SentimentLabel = SentimentLabel.UNKNOWN
    sentiment_score:   float          = 0.0    # [-1.0, +1.0]
    sentiment_confidence: float       = 0.0    # [0.0, 1.0]

    # ── Timing ────────────────────────────────────────────────────────────────
    published_at:  float            = 0.0      # UTC epoch (from source)
    received_at:   float            = field(default_factory=time.time)
    updated_at:    float            = 0.0      # last edit timestamp

    # ── Extra ─────────────────────────────────────────────────────────────────
    metadata:      dict[str, Any]   = field(default_factory=dict)

    # ── Derived helpers ───────────────────────────────────────────────────────

    def age_sec(self, now: float | None = None) -> float:
        if now is None:
            now = time.time()
        return now - self.received_at

    def is_valid(self) -> bool:
        return (
            len(self.title) >= MIN_ARTICLE_TITLE_LEN
            and (len(self.body) >= MIN_ARTICLE_BODY_LEN or len(self.summary) >= MIN_ARTICLE_BODY_LEN)
        )

    def full_text(self) -> str:
        """Return title + body for text processing."""
        return f"{self.title}\n{self.body}" if self.body else self.title

    def to_dict(self) -> dict[str, Any]:
        return {
            "article_id":     self.article_id,
            "provider_id":    self.provider_id,
            "source_name":    self.source_name,
            "title":          self.title,
            "summary":        self.summary,
            "url":            self.url,
            "language":       self.language.value,
            "region":         self.region.value,
            "countries":      self.countries,
            "companies":      self.companies,
            "sectors":        self.sectors,
            "categories":     [c.value for c in self.categories],
            "topics":         self.topics,
            "tags":           self.tags,
            "importance":     int(self.importance),
            "urgency":        self.urgency.value,
            "is_breaking":    self.is_breaking,
            "sentiment":      self.sentiment.value,
            "sentiment_score": self.sentiment_score,
            "published_at":   self.published_at,
            "received_at":    self.received_at,
        }
