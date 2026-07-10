"""iios/integration/news/classification/classification_engine.py

Orchestrates topic classification, entity extraction, tag generation
and sentiment routing for incoming news articles.
"""
from __future__ import annotations

import logging
from typing import Any

from iios.integration.news.classification.entity_extractor  import EntityExtractor
from iios.integration.news.classification.sentiment_router  import SentimentRouter
from iios.integration.news.classification.tag_generator     import TagGenerator
from iios.integration.news.classification.topic_classifier  import TopicClassifier
from iios.integration.news.core.news_article import NewsArticle
from iios.integration.news.news_constants    import NewsCategory

logger = logging.getLogger(__name__)


class ClassificationEngine:
    """
    Full classification pipeline for NewsArticle objects.

    Pipeline order:
    1. TopicClassifier  → sets article.categories + article.topics
    2. EntityExtractor  → sets article.companies, article.countries, article.sectors
    3. TagGenerator     → sets article.tags
    4. SentimentRouter  → updates article.sentiment_score
    """

    def __init__(
        self,
        topic_classifier: TopicClassifier | None = None,
        entity_extractor: EntityExtractor | None = None,
        tag_generator:    TagGenerator    | None = None,
        sentiment_router: SentimentRouter | None = None,
    ) -> None:
        self._topic     = topic_classifier or TopicClassifier()
        self._entity    = entity_extractor or EntityExtractor()
        self._tags      = tag_generator    or TagGenerator()
        self._sentiment = sentiment_router or SentimentRouter()
        self._stats: dict[str, int] = {"classified": 0, "errors": 0}

    def classify(self, article: NewsArticle) -> NewsArticle:
        """
        Run the full classification pipeline on one article.
        Modifies the article in-place and returns it.
        """
        try:
            text = article.full_text()

            # 1. Topics / categories
            categories = self._topic.classify(text)
            article.categories = list(dict.fromkeys(article.categories + categories))
            article.topics     = [c.value for c in categories]

            # 2. Entities
            entities = self._entity.extract(text)
            # Merge without duplicates
            seen_co = set(article.companies)
            for c in entities.companies:
                if c not in seen_co:
                    article.companies.append(c)
                    seen_co.add(c)
            seen_ct = set(article.countries)
            for c in entities.countries:
                if c not in seen_ct:
                    article.countries.append(c)
                    seen_ct.add(c)
            seen_se = set(article.sectors)
            for s in entities.sectors:
                if s not in seen_se:
                    article.sectors.append(s)
                    seen_se.add(s)

            # 3. Tags
            self._tags.generate(article)

            # 4. Sentiment routing
            self._sentiment.route(article)

            self._stats["classified"] += 1

        except Exception as exc:
            self._stats["errors"] += 1
            logger.warning("[ClassificationEngine] Error classifying '%s': %s", article.article_id, exc)

        return article

    def classify_batch(self, articles: list[NewsArticle]) -> list[NewsArticle]:
        return [self.classify(a) for a in articles]

    # ── Access to sub-components ──────────────────────────────────────────────

    def topic_classifier(self)  -> TopicClassifier:  return self._topic
    def entity_extractor(self)  -> EntityExtractor:  return self._entity
    def tag_generator(self)     -> TagGenerator:     return self._tags
    def sentiment_router(self)  -> SentimentRouter:  return self._sentiment

    def stats(self) -> dict[str, Any]:
        return {
            **self._stats,
            "topic":     self._topic.stats(),
            "entity":    self._entity.stats(),
            "tags":      self._tags.stats(),
            "sentiment": self._sentiment.stats(),
        }
