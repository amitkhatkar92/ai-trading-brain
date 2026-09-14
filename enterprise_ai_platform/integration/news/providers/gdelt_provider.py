from enterprise_ai_platform.integration.news.providers.base_news_provider import BaseNewsProvider
from enterprise_ai_platform.integration.news.providers.news_session import NewsSession
from enterprise_ai_platform.integration.news.providers.provider_capabilities import NewsProviderCapabilities
from enterprise_ai_platform.integration.news.providers.provider_health import NewsProviderHealth
from enterprise_ai_platform.integration.news.providers.provider_metadata import NewsProviderMetadata
from enterprise_ai_platform.integration.news.news_constants import (
    NewsProviderStatus, NewsLanguage, NewsRegion, NewsCategory, AlternativeDataType,
)
from enterprise_ai_platform.integration.news.core.news_article import NewsArticle
from enterprise_ai_platform.integration.news.core.news_event import NewsEvent
from enterprise_ai_platform.integration.news.core.news_headline import NewsHeadline
from typing import AsyncGenerator
import time


class GDELTProvider(BaseNewsProvider):
    """GDELT Project provider — scaffold only. All data methods raise NotImplementedError."""

    def __init__(self) -> None:
        super().__init__()
        self._capabilities = NewsProviderCapabilities(
            supports_articles=True,
            supports_events=True,
            supports_search=True,
            is_free=True,
            languages=list(NewsLanguage),
            historical_depth_days=9999,
        )
        self._metadata = NewsProviderMetadata(
            provider_id="gdelt",
            display_name="GDELT Project",
        )

    @property
    def provider_id(self) -> str:
        return "gdelt"

    @property
    def capabilities(self) -> NewsProviderCapabilities:
        return self._capabilities

    @property
    def metadata(self) -> NewsProviderMetadata:
        return self._metadata

    async def connect(self) -> None:
        self._session = NewsSession(
            provider_id="gdelt",
            status=NewsProviderStatus.CONNECTED,
        )
        self._connected_at = time.time()

    async def disconnect(self) -> None:
        if self._session:
            self._session.status = NewsProviderStatus.DISCONNECTED
            self._session = None

    async def fetch_articles(self, **kwargs):
        raise NotImplementedError("GDELTProvider.fetch_articles not yet wired.")

    async def fetch_events(self, **kwargs):
        raise NotImplementedError("GDELTProvider.fetch_events not yet wired.")

    async def search_news(self, **kwargs):
        raise NotImplementedError("GDELTProvider.search_news not yet wired.")

    async def stream_news(self) -> AsyncGenerator[NewsArticle, None]:
        raise NotImplementedError("GDELTProvider.stream_news not yet wired.")
        if False:
            yield NewsArticle()

    async def stream_alerts(self) -> AsyncGenerator[NewsHeadline, None]:
        raise NotImplementedError("GDELTProvider.stream_alerts not yet wired.")
        if False:
            yield NewsHeadline()

    async def health_check(self) -> NewsProviderHealth:
        return self._base_health()


