from iios.integration.news.providers.base_news_provider import BaseNewsProvider
from iios.integration.news.providers.news_session import NewsSession
from iios.integration.news.providers.provider_capabilities import NewsProviderCapabilities
from iios.integration.news.providers.provider_health import NewsProviderHealth
from iios.integration.news.providers.provider_metadata import NewsProviderMetadata
from iios.integration.news.news_constants import (
    NewsProviderStatus, NewsLanguage, NewsRegion, NewsCategory, AlternativeDataType,
)
from iios.integration.news.core.news_article import NewsArticle
from iios.integration.news.core.news_event import NewsEvent
from iios.integration.news.core.news_headline import NewsHeadline
from typing import AsyncGenerator
import time


class TwitterProvider(BaseNewsProvider):
    """X (Twitter) provider — scaffold only. All data methods raise NotImplementedError."""

    def __init__(self) -> None:
        super().__init__()
        self._capabilities = NewsProviderCapabilities(
            supports_streaming=True,
            supports_alerts=True,
            supports_search=True,
            requires_authentication=True,
            alt_data_types=[AlternativeDataType.SOCIAL_MEDIA],
        )
        self._metadata = NewsProviderMetadata(
            provider_id="twitter_x",
            display_name="X (Twitter)",
        )

    @property
    def provider_id(self) -> str:
        return "twitter_x"

    @property
    def capabilities(self) -> NewsProviderCapabilities:
        return self._capabilities

    @property
    def metadata(self) -> NewsProviderMetadata:
        return self._metadata

    async def connect(self) -> None:
        self._session = NewsSession(
            provider_id="twitter_x",
            status=NewsProviderStatus.CONNECTED,
        )
        self._connected_at = time.time()

    async def disconnect(self) -> None:
        if self._session:
            self._session.status = NewsProviderStatus.DISCONNECTED
            self._session = None

    async def fetch_articles(self, **kwargs):
        raise NotImplementedError("TwitterProvider.fetch_articles not yet wired.")

    async def fetch_events(self, **kwargs):
        raise NotImplementedError("TwitterProvider.fetch_events not yet wired.")

    async def search_news(self, **kwargs):
        raise NotImplementedError("TwitterProvider.search_news not yet wired.")

    async def stream_news(self) -> AsyncGenerator[NewsArticle, None]:
        raise NotImplementedError("TwitterProvider.stream_news not yet wired.")
        if False:
            yield NewsArticle()

    async def stream_alerts(self) -> AsyncGenerator[NewsHeadline, None]:
        raise NotImplementedError("TwitterProvider.stream_alerts not yet wired.")
        if False:
            yield NewsHeadline()

    async def health_check(self) -> NewsProviderHealth:
        return self._base_health()


