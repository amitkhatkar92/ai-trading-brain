"""iios/integration/news/sentiment/sentiment_engine.py

Facade: coordinates all registered sentiment providers and builds
aggregated results for articles, tickers and sectors.

No ML / NLP libraries are imported here — everything is delegated
to plugged-in BaseSentimentProvider implementations.
"""
from __future__ import annotations

import logging
import threading
from typing import Any

from iios.integration.news.core.news_article import NewsArticle
from iios.integration.news.news_constants    import SentimentScope
from iios.integration.news.sentiment.sentiment_registry   import BaseSentimentProvider, SentimentRegistry
from iios.integration.news.sentiment.sentiment_result     import SentimentResult
from iios.integration.news.sentiment.sentiment_statistics import SentimentStatistics

logger = logging.getLogger(__name__)


class SentimentEngine:
    """
    Top-level sentiment analysis facade.

    Usage:
        engine = SentimentEngine()
        engine.register_provider(MyLexiconProvider())
        result = engine.analyze(article)
    """

    def __init__(self, registry: SentimentRegistry | None = None) -> None:
        self._registry = registry or SentimentRegistry()
        self._lock     = threading.RLock()
        self._stats:    dict[str, int] = {"analyzed": 0, "errors": 0}
        # Per-subject running stats
        self._subject_stats: dict[str, SentimentStatistics] = {}

    # ── Provider management ───────────────────────────────────────────────────

    def register_provider(self, provider: BaseSentimentProvider) -> None:
        self._registry.register(provider)

    def unregister_provider(self, analyzer_id: str) -> None:
        self._registry.unregister(analyzer_id)

    def provider_count(self) -> int:
        return self._registry.count()

    # ── Analysis ──────────────────────────────────────────────────────────────

    def analyze(self, article: NewsArticle) -> SentimentResult | None:
        """
        Analyze article with all providers supporting NEWS scope.

        Returns a SentimentResult that is the average of all providers,
        or None if no providers are registered.
        """
        providers = self._registry.find_for_scope(SentimentScope.NEWS)
        if not providers:
            return None

        scores:      list[float] = []
        last_result: SentimentResult | None = None

        for prov in providers:
            try:
                res = prov.analyze_article(article)
                scores.append(res.score)
                last_result = res
            except Exception as exc:
                self._stats["errors"] += 1
                logger.warning("[SentimentEngine] Provider '%s' failed: %s", prov.analyzer_id, exc)

        if not scores or last_result is None:
            return None

        avg = sum(scores) / len(scores)
        last_result.score = avg
        last_result.label = SentimentResult._score_to_label(avg)

        # Update running stats for subject
        with self._lock:
            subj = article.article_id
            if subj not in self._subject_stats:
                self._subject_stats[subj] = SentimentStatistics(subject_id=subj)
            self._subject_stats[subj].add_score(avg, last_result.label)
            self._stats["analyzed"] += 1

        return last_result

    def get_stats_for(self, subject_id: str) -> SentimentStatistics | None:
        with self._lock:
            return self._subject_stats.get(subject_id)

    def stats(self) -> dict[str, Any]:
        return dict(self._stats)
