"""iios/integration/news/__init__.py

News & Alternative Data Framework for IIOS.

Public surface:
    NewsEngine              — top-level facade
    get_news_engine()       — module-level singleton accessor
    reset_news_engine()     — destroy the singleton
"""
from iios.integration.news.news_engine import NewsEngine, get_news_engine, reset_news_engine
from iios.integration.news.news_manager import NewsManager
from iios.integration.news.news_registry import NewsRegistry
from iios.integration.news.news_factory import NewsFactory
from iios.integration.news.news_context import NewsContext, NewsContextState
from iios.integration.news.news_constants import (
    NewsCategory, NewsImportance, NewsUrgency, NewsLanguage, NewsRegion,
    SentimentLabel, NewsEventType, EventImpact, AlternativeDataType,
    NewsProviderStatus, NewsEngineStatus, SentimentScope,
    NEWS_ENGINE_VERSION, NEWS_ENGINE_SYSTEM_ID,
)
from iios.integration.news.news_exceptions import (
    NewsDataError, NewsEngineNotRunningError, NewsEngineAlreadyRunningError,
    NewsProviderNotFoundError, NoNewsProviderAvailableError,
)
from iios.integration.news.core import (
    NewsArticle, NewsEvent, NewsHeadline, NewsSource,
    NewsMetadata, NewsStatistics, NewsCategoryNode,
)
from iios.integration.news.providers import (
    BaseNewsProvider, NewsProviderCapabilities, NewsProviderMetadata,
    NewsProviderHealth, NewsSession, PaperNewsProvider,
)

__all__ = [
    # Engine
    "NewsEngine", "get_news_engine", "reset_news_engine",
    "NewsManager", "NewsRegistry", "NewsFactory",
    "NewsContext", "NewsContextState",
    # Constants
    "NewsCategory", "NewsImportance", "NewsUrgency", "NewsLanguage", "NewsRegion",
    "SentimentLabel", "NewsEventType", "EventImpact", "AlternativeDataType",
    "NewsProviderStatus", "NewsEngineStatus", "SentimentScope",
    "NEWS_ENGINE_VERSION", "NEWS_ENGINE_SYSTEM_ID",
    # Exceptions
    "NewsDataError", "NewsEngineNotRunningError", "NewsEngineAlreadyRunningError",
    "NewsProviderNotFoundError", "NoNewsProviderAvailableError",
    # Core models
    "NewsArticle", "NewsEvent", "NewsHeadline", "NewsSource",
    "NewsMetadata", "NewsStatistics", "NewsCategoryNode",
    # Provider base types
    "BaseNewsProvider", "NewsProviderCapabilities", "NewsProviderMetadata",
    "NewsProviderHealth", "NewsSession", "PaperNewsProvider",
]
