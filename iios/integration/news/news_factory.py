"""iios/integration/news/news_factory.py

Factory that constructs all major news framework components.

Separates construction from wiring so that NewsEngine and tests
can both create consistent component graphs.
"""
from __future__ import annotations

from typing import Any

from iios.integration.news.alternative.alternative_data_engine  import AlternativeDataEngine
from iios.integration.news.cache                                import NewsDataCache
from iios.integration.news.classification.classification_engine import ClassificationEngine
from iios.integration.news.classification.entity_extractor      import EntityExtractor
from iios.integration.news.classification.sentiment_router      import SentimentRouter
from iios.integration.news.classification.tag_generator         import TagGenerator
from iios.integration.news.classification.topic_classifier      import TopicClassifier
from iios.integration.news.distribution.news_event_publisher    import NewsEventPublisher
from iios.integration.news.monitoring.news_monitor              import NewsMonitor
from iios.integration.news.normalization.news_normalizer        import NewsNormalizer
from iios.integration.news.news_constants                       import (
    DEFAULT_MAX_PROVIDERS,
    DEFAULT_STALE_ARTICLE_SEC,
    DEFAULT_MAX_ARTICLE_BODY_CHARS,
    DEFAULT_MAX_TAGS,
    NewsImportance,
)
from iios.integration.news.news_registry   import NewsRegistry
from iios.integration.news.sentiment.sentiment_engine   import SentimentEngine
from iios.integration.news.sentiment.sentiment_registry import SentimentRegistry


class NewsFactory:
    """
    Centralised factory for all news framework objects.

    All ``create_*`` methods return a new instance each time — there is no
    singleton state inside the factory itself.
    """

    # ── Component factories ───────────────────────────────────────────────────

    @staticmethod
    def create_registry(max_providers: int = DEFAULT_MAX_PROVIDERS) -> NewsRegistry:
        return NewsRegistry(max_providers=max_providers)

    @staticmethod
    def create_cache(
        max_size: int = 10_000,
        ttl_sec:  int = DEFAULT_STALE_ARTICLE_SEC,
    ) -> NewsDataCache:
        return NewsDataCache(max_size=max_size, ttl_sec=ttl_sec)

    @staticmethod
    def create_normalizer(
        max_title_len: int = 500,
        max_body_len:  int = DEFAULT_MAX_ARTICLE_BODY_CHARS,
    ) -> NewsNormalizer:
        return NewsNormalizer(max_title_len=max_title_len, max_body_len=max_body_len)

    @staticmethod
    def create_topic_classifier(max_topics: int = 5) -> TopicClassifier:
        return TopicClassifier(max_topics=max_topics)

    @staticmethod
    def create_entity_extractor() -> EntityExtractor:
        return EntityExtractor()

    @staticmethod
    def create_tag_generator(max_tags: int = DEFAULT_MAX_TAGS) -> TagGenerator:
        return TagGenerator(max_tags=max_tags)

    @staticmethod
    def create_sentiment_router() -> SentimentRouter:
        return SentimentRouter()

    @staticmethod
    def create_classification_engine(
        topic_classifier: TopicClassifier | None = None,
        entity_extractor: EntityExtractor | None = None,
        tag_generator:    TagGenerator | None = None,
        sentiment_router: SentimentRouter | None = None,
    ) -> ClassificationEngine:
        return ClassificationEngine(
            topic_classifier=topic_classifier,
            entity_extractor=entity_extractor,
            tag_generator=tag_generator,
            sentiment_router=sentiment_router,
        )

    @staticmethod
    def create_sentiment_registry() -> SentimentRegistry:
        return SentimentRegistry()

    @staticmethod
    def create_sentiment_engine(
        registry: SentimentRegistry | None = None,
    ) -> SentimentEngine:
        return SentimentEngine(registry=registry)

    @staticmethod
    def create_publisher(
        breaking_threshold: NewsImportance = NewsImportance.HIGH,
    ) -> NewsEventPublisher:
        return NewsEventPublisher(breaking_threshold=breaking_threshold)

    @staticmethod
    def create_alternative_engine() -> AlternativeDataEngine:
        return AlternativeDataEngine()

    @staticmethod
    def create_monitor(
        poll_interval_sec: int = 60,
        max_latency_ms:    float = 5_000.0,
    ) -> NewsMonitor:
        return NewsMonitor(
            poll_interval_sec=poll_interval_sec,
            max_latency_ms=max_latency_ms,
        )
