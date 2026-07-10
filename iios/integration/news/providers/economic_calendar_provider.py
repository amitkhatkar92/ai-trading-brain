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


class EconomicCalendarProvider(BaseNewsProvider):
    """Economic Calendar provider — scaffold only. All data methods raise NotImplementedError."""

    def __init__(self) -> None:
        super().__init__()
        self._capabilities = NewsProviderCapabilities(
            supports_events=True,
            supports_historical=True,
            is_free=True,
            categories=[
                NewsCategory.MACRO_ECONOMIC,
                NewsCategory.CENTRAL_BANK,
                NewsCategory.INTEREST_RATES,
                NewsCategory.EMPLOYMENT,
                NewsCategory.GDP,
                NewsCategory.INFLATION,
            ],
            alt_data_types=[AlternativeDataType.ECONOMIC_CALENDAR],
        )
        self._metadata = NewsProviderMetadata(
            provider_id="economic_calendar",
            display_name="Economic Calendar",
        )

    @property
    def provider_id(self) -> str:
        return "economic_calendar"

    @property
    def capabilities(self) -> NewsProviderCapabilities:
        return self._capabilities

    @property
    def metadata(self) -> NewsProviderMetadata:
        return self._metadata

    async def connect(self) -> None:
        self._session = NewsSession(
            provider_id="economic_calendar",
            status=NewsProviderStatus.CONNECTED,
        )
        self._connected_at = time.time()

    async def disconnect(self) -> None:
        if self._session:
            self._session.status = NewsProviderStatus.DISCONNECTED
            self._session = None

    async def fetch_articles(self, **kwargs):
        raise NotImplementedError("EconomicCalendarProvider.fetch_articles not yet wired.")

    async def fetch_events(self, **kwargs):
        raise NotImplementedError("EconomicCalendarProvider.fetch_events not yet wired.")

    async def search_news(self, **kwargs):
        raise NotImplementedError("EconomicCalendarProvider.search_news not yet wired.")

    async def stream_news(self) -> AsyncGenerator[NewsArticle, None]:
        raise NotImplementedError("EconomicCalendarProvider.stream_news not yet wired.")
        if False:
            yield NewsArticle()

    async def stream_alerts(self) -> AsyncGenerator[NewsHeadline, None]:
        raise NotImplementedError("EconomicCalendarProvider.stream_alerts not yet wired.")
        if False:
            yield NewsHeadline()

    async def health_check(self) -> NewsProviderHealth:
        return self._base_health()


