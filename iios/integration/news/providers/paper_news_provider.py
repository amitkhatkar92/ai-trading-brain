"""iios/integration/news/providers/paper_news_provider.py

Synthetic news provider for testing and paper trading.
Generates deterministic random news articles — no external calls.
"""
from __future__ import annotations

import asyncio
import random
import time
import uuid
from typing import Any, AsyncGenerator

from iios.integration.news.core.news_article  import NewsArticle
from iios.integration.news.core.news_event    import NewsEvent
from iios.integration.news.core.news_headline import NewsHeadline
from iios.integration.news.news_constants     import (
    EventImpact,
    NewsCategory,
    NewsEventType,
    NewsImportance,
    NewsLanguage,
    NewsProviderStatus,
    NewsRegion,
    NewsUrgency,
    SentimentLabel,
)
from iios.integration.news.providers.base_news_provider    import BaseNewsProvider
from iios.integration.news.providers.news_session          import NewsSession
from iios.integration.news.providers.provider_capabilities import NewsProviderCapabilities
from iios.integration.news.providers.provider_health       import NewsProviderHealth
from iios.integration.news.providers.provider_metadata     import NewsProviderMetadata

_SAMPLE_COMPANIES = ["AAPL", "MSFT", "GOOG", "AMZN", "RELIANCE", "TCS", "NIFTY"]
_SAMPLE_TOPICS = ["earnings", "merger", "rates", "technology", "markets"]
_CATEGORIES = [NewsCategory.EARNINGS, NewsCategory.MARKETS, NewsCategory.TECHNOLOGY,
               NewsCategory.MACRO_ECONOMIC, NewsCategory.CORPORATE]
_SENTIMENTS = [SentimentLabel.BULLISH, SentimentLabel.NEUTRAL, SentimentLabel.BEARISH]


class PaperNewsProvider(BaseNewsProvider):
    """
    Synthetic news provider — generates deterministic random articles for testing.
    """

    _PROVIDER_ID = "paper_news"

    def __init__(self, seed: int = 42, stream_interval_sec: float = 0.05) -> None:
        super().__init__()
        self._rng             = random.Random(seed)
        self._interval        = stream_interval_sec
        self._article_counter = 0
        self._capabilities    = NewsProviderCapabilities(
            categories           = list(NewsCategory),
            languages            = [NewsLanguage.EN],
            regions              = [NewsRegion.GLOBAL],
            supports_articles    = True,
            supports_events      = True,
            supports_streaming   = True,
            supports_alerts      = True,
            supports_search      = True,
            supports_historical  = True,
            historical_depth_days = 9999,
            max_articles_per_fetch = 1000,
        )
        self._meta = NewsProviderMetadata(
            provider_id  = self._PROVIDER_ID,
            display_name = "Paper News",
            description  = "Synthetic news provider for testing.",
            vendor       = "IIOS",
            is_free      = True,
            is_demo      = True,
            tags         = ["paper", "simulation", "testing"],
        )

    @property
    def provider_id(self) -> str:
        return self._PROVIDER_ID

    @property
    def capabilities(self) -> NewsProviderCapabilities:
        return self._capabilities

    @property
    def metadata(self) -> NewsProviderMetadata:
        return self._meta

    async def connect(self) -> None:
        self._connected_at = time.time()
        self._session = NewsSession(
            provider_id=self._PROVIDER_ID,
            status=NewsProviderStatus.CONNECTED,
        )

    async def disconnect(self) -> None:
        if self._session:
            self._session.status = NewsProviderStatus.DISCONNECTED
            self._session = None

    async def fetch_articles(
        self, query: str = "", limit: int = 10, from_ts: float = 0.0, to_ts: float = 0.0
    ) -> list[NewsArticle]:
        self._assert_connected()
        arts = [self._make_article() for _ in range(min(limit, 50))]
        self._stats["articles_fetched"] = int(self._stats.get("articles_fetched", 0)) + len(arts)
        return arts

    async def fetch_events(self, from_ts: float = 0.0, to_ts: float = 0.0) -> list[NewsEvent]:
        self._assert_connected()
        events = [self._make_event() for _ in range(5)]
        self._stats["events_fetched"] = int(self._stats.get("events_fetched", 0)) + len(events)
        return events

    async def search_news(self, query: str, limit: int = 10) -> list[NewsArticle]:
        self._assert_connected()
        arts = [self._make_article(title_prefix=query) for _ in range(min(limit, 10))]
        return arts

    async def stream_news(self) -> AsyncGenerator[NewsArticle, None]:
        self._assert_connected()
        if self._session:
            self._session.status = NewsProviderStatus.STREAMING
        while self.is_connected():
            yield self._make_article()
            await asyncio.sleep(self._interval)

    async def stream_alerts(self) -> AsyncGenerator[NewsHeadline, None]:
        self._assert_connected()
        while self.is_connected():
            yield self._make_headline()
            await asyncio.sleep(self._interval)

    async def health_check(self) -> NewsProviderHealth:
        h = self._base_health()
        h.latency_ms = self._rng.uniform(0.5, 3.0)
        return h

    # ── Helpers ────────────────────────────────────────────────────────────────

    def _make_article(self, title_prefix: str = "") -> NewsArticle:
        self._article_counter += 1
        company = self._rng.choice(_SAMPLE_COMPANIES)
        cat     = self._rng.choice(_CATEGORIES)
        sent    = self._rng.choice(_SENTIMENTS)
        title   = f"{title_prefix + ' — ' if title_prefix else ''}Synthetic news #{self._article_counter}: {company}"
        return NewsArticle(
            provider_id   = self._PROVIDER_ID,
            source_name   = "PaperFeed",
            title         = title,
            body          = f"This is synthetic body content for article {self._article_counter}.",
            summary       = f"Summary for {company}.",
            companies     = [company],
            categories    = [cat],
            topics        = [self._rng.choice(_SAMPLE_TOPICS)],
            tags          = [company.lower(), cat.value],
            language      = NewsLanguage.EN,
            region        = NewsRegion.GLOBAL,
            importance    = NewsImportance.MEDIUM,
            urgency       = NewsUrgency.NORMAL,
            sentiment     = sent,
            sentiment_score = self._rng.uniform(-1.0, 1.0),
            published_at  = time.time(),
        )

    def _make_headline(self) -> NewsHeadline:
        company = self._rng.choice(_SAMPLE_COMPANIES)
        return NewsHeadline(
            provider_id  = self._PROVIDER_ID,
            source_name  = "PaperFeed",
            title        = f"BREAKING: {company} news",
            companies    = [company],
            urgency      = NewsUrgency.BREAKING,
            importance   = NewsImportance.HIGH,
            published_at = time.time(),
        )

    def _make_event(self) -> NewsEvent:
        company = self._rng.choice(_SAMPLE_COMPANIES)
        return NewsEvent(
            provider_id     = self._PROVIDER_ID,
            event_type      = self._rng.choice(list(NewsEventType)),
            title           = f"Event for {company}",
            companies       = [company],
            impact          = EventImpact.MEDIUM,
            is_confirmed    = True,
            event_timestamp = time.time(),
            published_at    = time.time(),
        )
