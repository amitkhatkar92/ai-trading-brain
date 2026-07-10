"""iios/integration/news/core/news_statistics.py

Aggregated statistics for news volume and sentiment over a period.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from iios.integration.news.news_constants import NewsCategory, SentimentLabel


@dataclass
class NewsStatistics:
    """
    Rolled-up news statistics for a symbol, sector, or market-wide period.
    """

    stat_id:         str          = field(default_factory=lambda: str(uuid.uuid4()))
    provider_id:     str          = ""
    subject:         str          = ""    # ticker, sector, "MARKET", etc.
    period_start:    float        = 0.0
    period_end:      float        = 0.0

    # Volume
    total_articles:  int          = 0
    articles_per_hr: float        = 0.0
    breaking_count:  int          = 0
    unique_sources:  int          = 0

    # Category breakdown: category_value → count
    category_counts: dict[str, int]   = field(default_factory=dict)

    # Sentiment
    avg_sentiment:   float        = 0.0    # [-1, +1]
    bullish_count:   int          = 0
    bearish_count:   int          = 0
    neutral_count:   int          = 0

    # Top keywords
    top_keywords:    list[str]    = field(default_factory=list)
    top_companies:   list[str]    = field(default_factory=list)

    computed_at:     float        = field(default_factory=time.time)
    metadata:        dict[str, Any] = field(default_factory=dict)

    def sentiment_ratio(self) -> float:
        """Bullish/bearish ratio. +1 = all bullish, −1 = all bearish."""
        total = self.bullish_count + self.bearish_count
        if total == 0:
            return 0.0
        return (self.bullish_count - self.bearish_count) / total

    def to_dict(self) -> dict[str, Any]:
        return {
            "stat_id":        self.stat_id,
            "subject":        self.subject,
            "period_start":   self.period_start,
            "period_end":     self.period_end,
            "total_articles": self.total_articles,
            "breaking_count": self.breaking_count,
            "avg_sentiment":  round(self.avg_sentiment, 4),
            "bullish_count":  self.bullish_count,
            "bearish_count":  self.bearish_count,
            "neutral_count":  self.neutral_count,
            "top_keywords":   self.top_keywords,
            "computed_at":    self.computed_at,
        }
