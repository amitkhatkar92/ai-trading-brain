"""iios/integration/news/core/news_event.py

Structured financial / corporate event (earnings, merger, rate decision, etc.)
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from iios.integration.news.news_constants import (
    EventImpact,
    NewsEventType,
    NewsLanguage,
    NewsRegion,
    SentimentLabel,
)


@dataclass
class NewsEvent:
    """
    A structured event extracted from news.

    Unlike NewsArticle which carries raw text, a NewsEvent represents
    a parsed, machine-actionable event (earnings release, rate decision, …).
    """

    event_id:       str            = field(default_factory=lambda: str(uuid.uuid4()))
    event_type:     NewsEventType  = NewsEventType.UNKNOWN
    provider_id:    str            = ""
    source_article: str            = ""    # article_id that originated this event

    # ── Content ───────────────────────────────────────────────────────────────
    title:          str            = ""
    description:    str            = ""

    # ── Entities ──────────────────────────────────────────────────────────────
    companies:      list[str]      = field(default_factory=list)   # tickers
    sectors:        list[str]      = field(default_factory=list)
    countries:      list[str]      = field(default_factory=list)
    region:         NewsRegion     = NewsRegion.UNKNOWN
    language:       NewsLanguage   = NewsLanguage.EN

    # ── Impact ────────────────────────────────────────────────────────────────
    impact:         EventImpact    = EventImpact.MEDIUM
    sentiment:      SentimentLabel = SentimentLabel.UNKNOWN
    is_scheduled:   bool           = False   # True = future-dated event
    is_confirmed:   bool           = False   # False = rumour / unconfirmed

    # ── Timing ────────────────────────────────────────────────────────────────
    event_timestamp: float         = 0.0    # when the event occurs / occurred
    published_at:   float          = 0.0
    received_at:    float          = field(default_factory=time.time)

    # ── Quantitative data ─────────────────────────────────────────────────────
    numeric_data:   dict[str, float] = field(default_factory=dict)  # EPS, revenue, etc.

    metadata:       dict[str, Any]   = field(default_factory=dict)

    def is_future(self, now: float | None = None) -> bool:
        if now is None:
            now = time.time()
        return self.event_timestamp > now

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id":       self.event_id,
            "event_type":     self.event_type.value,
            "provider_id":    self.provider_id,
            "title":          self.title,
            "companies":      self.companies,
            "sectors":        self.sectors,
            "countries":      self.countries,
            "impact":         self.impact.value,
            "sentiment":      self.sentiment.value,
            "is_scheduled":   self.is_scheduled,
            "is_confirmed":   self.is_confirmed,
            "event_timestamp": self.event_timestamp,
            "published_at":   self.published_at,
            "received_at":    self.received_at,
        }
