"""tests/unit/integration/news/test_news_engine.py

Comprehensive tests for the News & Alternative Data Framework.
155 tests covering all layers of the news stack.

Pattern:
  - No pytest-asyncio — all coroutines run via _run(coro)
  - Each TestX class is independent
  - setUp/tearDown resets singletons when needed
"""
from __future__ import annotations

import asyncio
import time
import unittest
from unittest.mock import MagicMock

# ── asyncio helper ────────────────────────────────────────────────────────────

def _run(coro):
    return asyncio.run(coro)


# ── Imports under test ────────────────────────────────────────────────────────

from iios.integration.news.news_constants import (
    NewsCategory, NewsImportance, NewsUrgency, NewsLanguage, NewsRegion,
    SentimentLabel, NewsEventType, EventImpact, AlternativeDataType,
    NewsProviderStatus, NewsEngineStatus, SentimentScope,
    NEWS_ENGINE_VERSION, NEWS_ERROR_PREFIX,
    MIN_ARTICLE_TITLE_LEN, MIN_ARTICLE_BODY_LEN,
    DEFAULT_MAX_PROVIDERS, DEFAULT_STREAM_BUFFER_SIZE, DEFAULT_STALE_ARTICLE_SEC,
)
from iios.integration.news.news_exceptions import (
    NewsDataError, NewsProviderConnectionError, NewsProviderAuthenticationError,
    NewsProviderNotConnectedError, NewsProviderNotFoundError,
    NewsProviderAlreadyRegisteredError, NoNewsProviderAvailableError,
    NewsFetchError, NewsFetchTimeoutError, NewsArticleNotFoundError,
    NewsStreamError, NewsStreamBufferOverflowError,
    NewsValidationError, NewsDuplicateArticleError,
    ClassificationError, AlternativeDataError, AlternativeDatasetNotFoundError,
    NewsEngineNotRunningError, NewsEngineAlreadyRunningError, NewsRegistryError,
)
from iios.integration.news.core.news_article       import NewsArticle
from iios.integration.news.core.news_event         import NewsEvent
from iios.integration.news.core.news_headline      import NewsHeadline
from iios.integration.news.core.news_source        import NewsSource
from iios.integration.news.core.news_metadata      import NewsMetadata
from iios.integration.news.core.news_statistics    import NewsStatistics
from iios.integration.news.core.news_category_model import NewsCategoryNode
from iios.integration.news.providers.provider_capabilities import NewsProviderCapabilities
from iios.integration.news.providers.provider_health       import NewsProviderHealth
from iios.integration.news.providers.news_session          import NewsSession
from iios.integration.news.providers.paper_news_provider   import PaperNewsProvider
from iios.integration.news.providers.reuters_provider      import ReutersProvider
from iios.integration.news.providers.bloomberg_provider    import BloombergProvider
from iios.integration.news.classification.topic_classifier import TopicClassifier
from iios.integration.news.classification.entity_extractor import EntityExtractor
from iios.integration.news.classification.tag_generator    import TagGenerator
from iios.integration.news.classification.sentiment_router import SentimentRouter
from iios.integration.news.classification.classification_engine import ClassificationEngine
from iios.integration.news.sentiment.sentiment_result     import SentimentResult
from iios.integration.news.sentiment.sentiment_registry   import BaseSentimentProvider, SentimentRegistry
from iios.integration.news.sentiment.sentiment_statistics import SentimentStatistics
from iios.integration.news.sentiment.sentiment_engine     import SentimentEngine
from iios.integration.news.alternative.alternative_dataset import AlternativeDataset, AlternativeEvent
from iios.integration.news.alternative.alternative_source  import AlternativeSource
from iios.integration.news.alternative.alternative_data_engine import AlternativeDataEngine
from iios.integration.news.normalization.news_normalizer   import NewsNormalizer
from iios.integration.news.news_registry   import NewsRegistry
from iios.integration.news.news_context    import NewsContext
from iios.integration.news.news_factory    import NewsFactory
from iios.integration.news.news_engine     import NewsEngine, get_news_engine, reset_news_engine
from iios.integration.news.monitoring.news_monitor import NewsMonitor
from iios.integration.news.distribution.news_event_publisher import NewsEventPublisher
from iios.integration.news.cache import NewsDataCache


# ═══════════════════════════════════════════════════════════════════════════════
# 1. Constants
# ═══════════════════════════════════════════════════════════════════════════════

class TestConstants(unittest.TestCase):

    def test_version_string(self):
        self.assertEqual(NEWS_ENGINE_VERSION, "1.0.0")

    def test_error_prefix(self):
        self.assertEqual(NEWS_ERROR_PREFIX, "ND")

    def test_news_category_count(self):
        self.assertGreaterEqual(len(NewsCategory), 20)

    def test_news_importance_ordering(self):
        self.assertLess(NewsImportance.LOW, NewsImportance.HIGH)
        self.assertLess(NewsImportance.HIGH, NewsImportance.CRITICAL)

    def test_news_language_unknown(self):
        self.assertEqual(NewsLanguage.UNKNOWN.value, "unknown")

    def test_news_region_global(self):
        self.assertEqual(NewsRegion.GLOBAL.value, "global")

    def test_sentiment_label_values(self):
        self.assertIn(SentimentLabel.VERY_BULLISH, list(SentimentLabel))
        self.assertIn(SentimentLabel.VERY_BEARISH, list(SentimentLabel))

    def test_alt_data_type_satellite(self):
        self.assertIn(AlternativeDataType.SATELLITE_DATA, list(AlternativeDataType))

    def test_engine_status_values(self):
        self.assertIn(NewsEngineStatus.STOPPED,  list(NewsEngineStatus))
        self.assertIn(NewsEngineStatus.RUNNING,  list(NewsEngineStatus))

    def test_defaults(self):
        self.assertGreater(DEFAULT_MAX_PROVIDERS, 0)
        self.assertGreater(DEFAULT_STREAM_BUFFER_SIZE, 0)
        self.assertGreater(DEFAULT_STALE_ARTICLE_SEC, 0)

    def test_min_lengths(self):
        self.assertEqual(MIN_ARTICLE_TITLE_LEN, 5)
        self.assertGreaterEqual(MIN_ARTICLE_BODY_LEN, 5)

    def test_sentiment_scope_values(self):
        values = {s.value for s in SentimentScope}
        self.assertIn("news", values)
        self.assertIn("company", values)


# ═══════════════════════════════════════════════════════════════════════════════
# 2. Exceptions
# ═══════════════════════════════════════════════════════════════════════════════

class TestExceptions(unittest.TestCase):

    def _check(self, exc_class, expected_code: str):
        ex = exc_class("test")
        self.assertIn(expected_code, repr(ex))
        self.assertIsInstance(ex, NewsDataError)

    def test_root_exception(self):
        ex = NewsDataError("root", code="ND-000")
        self.assertEqual(ex.code, "ND-000")

    def test_connection_error(self):        self._check(NewsProviderConnectionError,      "ND-011")
    def test_auth_error(self):              self._check(NewsProviderAuthenticationError,  "ND-012")
    def test_not_connected_error(self):     self._check(NewsProviderNotConnectedError,    "ND-013")
    def test_not_found_error(self):         self._check(NewsProviderNotFoundError,        "ND-014")
    def test_already_registered_error(self):self._check(NewsProviderAlreadyRegisteredError,"ND-015")
    def test_no_provider_error(self):       self._check(NoNewsProviderAvailableError,     "ND-016")
    def test_fetch_error(self):             self._check(NewsFetchError,                   "ND-020")
    def test_stream_error(self):            self._check(NewsStreamError,                  "ND-030")
    def test_validation_error(self):        self._check(NewsValidationError,              "ND-040")
    def test_alt_data_error(self):          self._check(AlternativeDataError,             "ND-060")
    def test_engine_not_running_error(self):self._check(NewsEngineNotRunningError,        "ND-070")
    def test_registry_error(self):          self._check(NewsRegistryError,               "ND-072")


# ═══════════════════════════════════════════════════════════════════════════════
# 3. NewsArticle
# ═══════════════════════════════════════════════════════════════════════════════

class TestNewsArticle(unittest.TestCase):

    def _article(self, **kw) -> NewsArticle:
        defaults = dict(title="Market rally today", body="Stocks rose sharply.", source_name="Reuters")
        defaults.update(kw)
        return NewsArticle(**defaults)

    def test_defaults(self):
        a = NewsArticle()
        self.assertIsNotNone(a.article_id)
        self.assertEqual(a.sentiment, SentimentLabel.UNKNOWN)

    def test_is_valid_true(self):
        a = self._article()
        self.assertTrue(a.is_valid())

    def test_is_valid_short_title(self):
        a = self._article(title="Hi")
        self.assertFalse(a.is_valid())

    def test_is_valid_no_body_no_summary(self):
        a = NewsArticle(title="Some news title", body="", summary="")
        self.assertFalse(a.is_valid())

    def test_full_text_includes_title_and_body(self):
        a = self._article()
        ft = a.full_text()
        self.assertIn("Market rally today", ft)
        self.assertIn("Stocks rose sharply.", ft)

    def test_age_sec_non_negative(self):
        a = self._article()
        self.assertGreaterEqual(a.age_sec(), 0)

    def test_to_dict_keys(self):
        a = self._article()
        d = a.to_dict()
        self.assertIn("article_id", d)
        self.assertIn("title", d)

    def test_unique_ids(self):
        a1 = NewsArticle()
        a2 = NewsArticle()
        self.assertNotEqual(a1.article_id, a2.article_id)


# ═══════════════════════════════════════════════════════════════════════════════
# 4. NewsEvent
# ═══════════════════════════════════════════════════════════════════════════════

class TestNewsEvent(unittest.TestCase):

    def test_is_future_true(self):
        ev = NewsEvent(event_timestamp=time.time() + 3600, title="Future event")
        self.assertTrue(ev.is_future())

    def test_is_future_false(self):
        ev = NewsEvent(event_timestamp=time.time() - 3600, title="Past event")
        self.assertFalse(ev.is_future())

    def test_to_dict_keys(self):
        ev = NewsEvent(title="CPI Release", event_type=NewsEventType.ECONOMIC_RELEASE)
        d = ev.to_dict()
        self.assertIn("event_id", d)
        self.assertIn("event_type", d)

    def test_unique_ids(self):
        e1 = NewsEvent()
        e2 = NewsEvent()
        self.assertNotEqual(e1.event_id, e2.event_id)

    def test_default_impact(self):
        ev = NewsEvent()
        self.assertIsInstance(ev.impact, EventImpact)


# ═══════════════════════════════════════════════════════════════════════════════
# 5. NewsHeadline
# ═══════════════════════════════════════════════════════════════════════════════

class TestNewsHeadline(unittest.TestCase):

    def test_age_ms_non_negative(self):
        h = NewsHeadline(title="Breaking!")
        self.assertGreaterEqual(h.age_ms(), 0)

    def test_to_dict(self):
        h = NewsHeadline(title="FED raises rates")
        d = h.to_dict()
        self.assertIn("headline_id", d)
        self.assertIn("title", d)

    def test_unique_ids(self):
        h1 = NewsHeadline()
        h2 = NewsHeadline()
        self.assertNotEqual(h1.headline_id, h2.headline_id)

    def test_defaults(self):
        h = NewsHeadline()
        self.assertEqual(h.importance, NewsImportance.MEDIUM)


# ═══════════════════════════════════════════════════════════════════════════════
# 6. NewsSource
# ═══════════════════════════════════════════════════════════════════════════════

class TestNewsSource(unittest.TestCase):

    def test_to_dict(self):
        s = NewsSource(name="Reuters", url="https://reuters.com")
        d = s.to_dict()
        self.assertIn("source_id", d)

    def test_reliability_default(self):
        s = NewsSource()
        self.assertGreaterEqual(s.reliability, 0.0)
        self.assertLessEqual(s.reliability, 1.0)

    def test_unique_ids(self):
        s1 = NewsSource()
        s2 = NewsSource()
        self.assertNotEqual(s1.source_id, s2.source_id)


# ═══════════════════════════════════════════════════════════════════════════════
# 7. NewsMetadata
# ═══════════════════════════════════════════════════════════════════════════════

class TestNewsMetadata(unittest.TestCase):

    def test_set_and_get(self):
        m = NewsMetadata()
        m.set("foo", 42)
        self.assertEqual(m.get("foo"), 42)

    def test_has_true(self):
        m = NewsMetadata()
        m.set("bar", "baz")
        self.assertTrue(m.has("bar"))

    def test_has_false(self):
        m = NewsMetadata()
        self.assertFalse(m.has("nonexistent"))

    def test_merge(self):
        m  = NewsMetadata()
        m2 = NewsMetadata()
        m2.set("x", 1)
        m2.set("y", 2)
        m.merge(m2)
        self.assertEqual(m.get("x"), 1)

    def test_get_default(self):
        m = NewsMetadata()
        self.assertIsNone(m.get("missing"))
        self.assertEqual(m.get("missing", "default"), "default")

    def test_to_dict(self):
        m = NewsMetadata()
        m.set("k", "v")
        d = m.to_dict()
        self.assertIn("meta_id", d)
        self.assertEqual(d["data"]["k"], "v")


# ═══════════════════════════════════════════════════════════════════════════════
# 8. NewsStatistics
# ═══════════════════════════════════════════════════════════════════════════════

class TestNewsStatistics(unittest.TestCase):

    def test_sentiment_ratio_half(self):
        # Equal bullish/bearish → (5-5)/(5+5) = 0.0
        s = NewsStatistics(bullish_count=5, bearish_count=5)
        self.assertAlmostEqual(s.sentiment_ratio(), 0.0, places=3)

    def test_sentiment_ratio_all_bullish(self):
        s = NewsStatistics(bullish_count=10, bearish_count=0)
        self.assertAlmostEqual(s.sentiment_ratio(), 1.0, places=3)

    def test_to_dict(self):
        s = NewsStatistics(total_articles=100)
        d = s.to_dict()
        self.assertIn("total_articles", d)

    def test_unique_ids(self):
        s1 = NewsStatistics()
        s2 = NewsStatistics()
        self.assertNotEqual(s1.stat_id, s2.stat_id)


# ═══════════════════════════════════════════════════════════════════════════════
# 9. NewsCategoryModel
# ═══════════════════════════════════════════════════════════════════════════════

class TestNewsCategoryNode(unittest.TestCase):

    def test_matches_keyword(self):
        node = NewsCategoryNode(
            category=NewsCategory.EARNINGS,
            keywords=["earnings", "revenue"],
        )
        self.assertTrue(node.matches("The earnings were strong this quarter"))

    def test_no_match(self):
        node = NewsCategoryNode(category=NewsCategory.CRYPTO, keywords=["bitcoin"])
        self.assertFalse(node.matches("NIFTY rose by 1.5%"))

    def test_case_insensitive(self):
        node = NewsCategoryNode(category=NewsCategory.IPO, keywords=["ipo"])
        self.assertTrue(node.matches("Big IPO listed today"))


# ═══════════════════════════════════════════════════════════════════════════════
# 10. NewsProviderCapabilities
# ═══════════════════════════════════════════════════════════════════════════════

class TestNewsProviderCapabilities(unittest.TestCase):

    def _caps(self, **kw) -> NewsProviderCapabilities:
        return NewsProviderCapabilities(**kw)

    def test_supports_category_true(self):
        c = self._caps(categories=[NewsCategory.EARNINGS])
        self.assertTrue(c.supports_category(NewsCategory.EARNINGS))

    def test_supports_category_false(self):
        c = self._caps(categories=[NewsCategory.EARNINGS])
        self.assertFalse(c.supports_category(NewsCategory.CRYPTO))

    def test_supports_language(self):
        c = self._caps(languages=[NewsLanguage.EN])
        self.assertTrue(c.supports_language(NewsLanguage.EN))
        self.assertFalse(c.supports_language(NewsLanguage.ZH))

    def test_supports_region_global(self):
        c = self._caps(regions=[NewsRegion.GLOBAL])
        # GLOBAL matches any region
        self.assertTrue(c.supports_region(NewsRegion.ASIA_PACIFIC))
        self.assertTrue(c.supports_region(NewsRegion.EUROPE))


# ═══════════════════════════════════════════════════════════════════════════════
# 11. NewsProviderHealth
# ═══════════════════════════════════════════════════════════════════════════════

class TestNewsProviderHealth(unittest.TestCase):

    def test_is_healthy_connected_no_error(self):
        h = NewsProviderHealth(provider_id="p1", is_connected=True)
        self.assertTrue(h.is_healthy())

    def test_is_healthy_false_when_disconnected(self):
        h = NewsProviderHealth(provider_id="p1", is_connected=False)
        self.assertFalse(h.is_healthy())

    def test_is_healthy_false_with_error(self):
        h = NewsProviderHealth(provider_id="p1", is_connected=True, last_error="timeout")
        self.assertFalse(h.is_healthy())


# ═══════════════════════════════════════════════════════════════════════════════
# 12. NewsSession
# ═══════════════════════════════════════════════════════════════════════════════

class TestNewsSession(unittest.TestCase):

    def test_touch_updates_last_active(self):
        s = NewsSession(provider_id="p1", status=NewsProviderStatus.CONNECTED)
        before = s.last_active
        time.sleep(0.01)
        s.touch()
        self.assertGreater(s.last_active, before)

    def test_record_error_increments_count(self):
        s = NewsSession(provider_id="p1", status=NewsProviderStatus.CONNECTED)
        s.record_error()
        self.assertEqual(s.error_count, 1)

    def test_is_connected_true_when_connected(self):
        s = NewsSession(provider_id="p1", status=NewsProviderStatus.CONNECTED)
        self.assertTrue(s.is_connected())

    def test_is_connected_true_when_streaming(self):
        s = NewsSession(provider_id="p1", status=NewsProviderStatus.STREAMING)
        self.assertTrue(s.is_connected())

    def test_is_connected_false_when_disconnected(self):
        s = NewsSession(provider_id="p1", status=NewsProviderStatus.DISCONNECTED)
        self.assertFalse(s.is_connected())


# ═══════════════════════════════════════════════════════════════════════════════
# 13. PaperNewsProvider
# ═══════════════════════════════════════════════════════════════════════════════

class TestPaperNewsProvider(unittest.TestCase):

    def setUp(self):
        self.p = PaperNewsProvider()

    def test_provider_id(self):
        self.assertEqual(self.p.provider_id, "paper_news")

    def test_not_connected_before_connect(self):
        self.assertFalse(self.p.is_connected())

    def test_connect_sets_connected(self):
        _run(self.p.connect())
        self.assertTrue(self.p.is_connected())

    def test_disconnect_sets_disconnected(self):
        _run(self.p.connect())
        _run(self.p.disconnect())
        self.assertFalse(self.p.is_connected())

    def test_fetch_articles_returns_articles(self):
        _run(self.p.connect())
        articles = _run(self.p.fetch_articles(limit=3))
        self.assertEqual(len(articles), 3)
        self.assertIsInstance(articles[0], NewsArticle)

    def test_fetch_events_returns_events(self):
        _run(self.p.connect())
        events = _run(self.p.fetch_events())
        self.assertIsInstance(events, list)
        self.assertGreater(len(events), 0)

    def test_search_news_returns_articles(self):
        _run(self.p.connect())
        results = _run(self.p.search_news(query="NIFTY", limit=2))
        self.assertIsInstance(results, list)

    def test_stream_news_yields_articles(self):
        _run(self.p.connect())
        async def _collect():
            items = []
            async for art in self.p.stream_news():
                items.append(art)
                if len(items) >= 3:
                    break
            return items
        items = _run(_collect())
        self.assertGreaterEqual(len(items), 1)

    def test_stream_alerts_yields_headlines(self):
        _run(self.p.connect())
        async def _collect():
            items = []
            async for h in self.p.stream_alerts():
                items.append(h)
                if len(items) >= 2:
                    break
            return items
        items = _run(_collect())
        self.assertGreaterEqual(len(items), 1)

    def test_health_check(self):
        _run(self.p.connect())
        h = _run(self.p.health_check())
        self.assertIsInstance(h, NewsProviderHealth)
        self.assertTrue(h.is_connected)

    def test_get_stats(self):
        _run(self.p.connect())
        s = self.p.get_stats()
        self.assertIn("articles_fetched", s)

    def test_capabilities(self):
        caps = self.p.capabilities
        self.assertIsInstance(caps, NewsProviderCapabilities)

    def test_metadata(self):
        from iios.integration.news.providers.provider_metadata import NewsProviderMetadata
        self.assertIsInstance(self.p.metadata, NewsProviderMetadata)


# ═══════════════════════════════════════════════════════════════════════════════
# 14. Skeleton providers
# ═══════════════════════════════════════════════════════════════════════════════

class TestSkeletonProviders(unittest.TestCase):

    def _test_skeleton(self, provider):
        # connect / disconnect
        _run(provider.connect())
        self.assertTrue(provider.is_connected())
        _run(provider.disconnect())
        self.assertFalse(provider.is_connected())

    def test_reuters(self):
        self._test_skeleton(ReutersProvider())

    def test_bloomberg(self):
        self._test_skeleton(BloombergProvider())

    def test_reuters_fetch_raises(self):
        p = ReutersProvider()
        _run(p.connect())
        with self.assertRaises(NotImplementedError):
            _run(p.fetch_articles())

    def test_bloomberg_fetch_raises(self):
        p = BloombergProvider()
        _run(p.connect())
        with self.assertRaises(NotImplementedError):
            _run(p.fetch_articles())

    def test_reuters_capabilities(self):
        caps = ReutersProvider().capabilities
        self.assertTrue(caps.supports_streaming)

    def test_bloomberg_capabilities(self):
        caps = BloombergProvider().capabilities
        self.assertTrue(caps.supports_alerts)

    def test_reuters_health(self):
        p = ReutersProvider()
        _run(p.connect())
        h = _run(p.health_check())
        self.assertTrue(h.is_connected)

    def test_bloomberg_health_not_connected(self):
        p = BloombergProvider()
        _run(p.connect())  # connect first so _connected_at is set
        _run(p.disconnect())
        h = _run(p.health_check())
        self.assertFalse(h.is_connected)

    def test_reuters_region_global(self):
        caps = ReutersProvider().capabilities
        self.assertTrue(caps.supports_region(NewsRegion.ASIA_PACIFIC))

    def test_bloomberg_provider_id(self):
        self.assertEqual(BloombergProvider().provider_id, "bloomberg")


# ═══════════════════════════════════════════════════════════════════════════════
# 15. TopicClassifier
# ═══════════════════════════════════════════════════════════════════════════════

class TestTopicClassifier(unittest.TestCase):

    def setUp(self):
        self.tc = TopicClassifier()

    def test_classify_earnings(self):
        cats = self.tc.classify("Q3 earnings beat expectations, revenue up 20%")
        self.assertIn(NewsCategory.EARNINGS, cats)

    def test_classify_crypto(self):
        cats = self.tc.classify("Bitcoin surged past $70,000 on Monday")
        self.assertIn(NewsCategory.CRYPTO, cats)

    def test_unknown_returns_general(self):
        # Text with no matching finance keywords at all
        cats = self.tc.classify("aaabbbccc zzzyyyxxx nnnooo")
        self.assertEqual(cats, [NewsCategory.GENERAL])

    def test_multiple_topics(self):
        cats = self.tc.classify("Fed rate hike causes stock market correction")
        self.assertGreater(len(cats), 1)

    def test_case_insensitive(self):
        cats = self.tc.classify("EARNINGS BEAT THIS QUARTER")
        self.assertIn(NewsCategory.EARNINGS, cats)

    def test_add_keywords(self):
        self.tc.add_keywords(NewsCategory.CRYPTO, ["altcoin"])
        cats = self.tc.classify("New altcoin launched yesterday")
        self.assertIn(NewsCategory.CRYPTO, cats)

    def test_stats(self):
        self.tc.classify("earnings report")
        s = self.tc.stats()
        self.assertGreater(s["classified"], 0)

    def test_max_topics_respected(self):
        tc = TopicClassifier(max_topics=2)
        cats = tc.classify("earnings revenue bitcoin crypto merger acquisition ipo")
        self.assertLessEqual(len(cats), 2)


# ═══════════════════════════════════════════════════════════════════════════════
# 16. EntityExtractor
# ═══════════════════════════════════════════════════════════════════════════════

class TestEntityExtractor(unittest.TestCase):

    def setUp(self):
        self.ee = EntityExtractor()

    def test_extract_ticker(self):
        e = self.ee.extract("AAPL stock rose 3% today")
        self.assertIn("AAPL", e.companies)

    def test_extract_company_name(self):
        e = self.ee.extract("Apple reported strong iPhone sales")
        self.assertIn("AAPL", e.companies)

    def test_extract_country(self):
        e = self.ee.extract("India's GDP growth surprised")
        self.assertIn("India", e.countries)

    def test_no_match_returns_empty(self):
        e = self.ee.extract("xyzzy placeholder text")
        self.assertEqual(e.companies, [])

    def test_extract_sector(self):
        e = self.ee.extract("Technology sector leads market rally")
        self.assertIn("Technology", e.sectors)

    def test_register_ticker(self):
        self.ee.register_ticker("ZOMATO", "Zomato Ltd")
        e = self.ee.extract("Zomato Ltd reported loss")
        self.assertIn("ZOMATO", e.companies)


# ═══════════════════════════════════════════════════════════════════════════════
# 17. TagGenerator
# ═══════════════════════════════════════════════════════════════════════════════

class TestTagGenerator(unittest.TestCase):

    def setUp(self):
        self.tg = TagGenerator(max_tags=20)

    def _article(self) -> NewsArticle:
        a = NewsArticle(
            title="Apple earnings beat expectations",
            body="Apple Inc reported strong quarterly results.",
        )
        a.companies  = ["AAPL"]
        a.categories = [NewsCategory.EARNINGS]
        return a

    def test_generates_tags(self):
        a = self._article()
        tags = self.tg.generate(a)
        self.assertGreater(len(tags), 0)

    def test_tags_are_lowercase(self):
        a = self._article()
        tags = self.tg.generate(a)
        for t in tags:
            self.assertEqual(t, t.lower())

    def test_no_duplicate_tags(self):
        a = self._article()
        tags = self.tg.generate(a)
        self.assertEqual(len(tags), len(set(tags)))

    def test_max_tags_respected(self):
        tg = TagGenerator(max_tags=3)
        a = self._article()
        tags = tg.generate(a)
        self.assertLessEqual(len(tags), 3)

    def test_article_tags_updated(self):
        a = self._article()
        self.tg.generate(a)
        self.assertIsNotNone(a.tags)


# ═══════════════════════════════════════════════════════════════════════════════
# 18. SentimentResult
# ═══════════════════════════════════════════════════════════════════════════════

class TestSentimentResult(unittest.TestCase):

    def test_defaults(self):
        sr = SentimentResult()
        self.assertEqual(sr.label, SentimentLabel.UNKNOWN)
        self.assertEqual(sr.score, 0.0)

    def test_positive_score_sets_bullish(self):
        sr = SentimentResult(score=0.7)
        self.assertEqual(sr.label, SentimentLabel.VERY_BULLISH)

    def test_negative_score_sets_bearish(self):
        sr = SentimentResult(score=-0.7)
        self.assertEqual(sr.label, SentimentLabel.VERY_BEARISH)

    def test_to_dict(self):
        sr = SentimentResult(score=0.3)
        d = sr.to_dict()
        self.assertIn("result_id", d)
        self.assertIn("score", d)


# ═══════════════════════════════════════════════════════════════════════════════
# 19. SentimentRegistry
# ═══════════════════════════════════════════════════════════════════════════════

class _DummySentimentProvider(BaseSentimentProvider):
    @property
    def analyzer_id(self) -> str: return "dummy"
    @property
    def supported_scopes(self): return [SentimentScope.NEWS]
    def analyze_article(self, article): return SentimentResult(score=0.5, analyzer_id="dummy")


class TestSentimentRegistry(unittest.TestCase):

    def test_register_and_get(self):
        r = SentimentRegistry()
        r.register(_DummySentimentProvider())
        self.assertIsNotNone(r.get("dummy"))

    def test_count(self):
        r = SentimentRegistry()
        r.register(_DummySentimentProvider())
        self.assertEqual(r.count(), 1)

    def test_unregister(self):
        r = SentimentRegistry()
        r.register(_DummySentimentProvider())
        r.unregister("dummy")
        self.assertEqual(r.count(), 0)

    def test_find_for_scope(self):
        r = SentimentRegistry()
        r.register(_DummySentimentProvider())
        found = r.find_for_scope(SentimentScope.NEWS)
        self.assertEqual(len(found), 1)

    def test_all_ids(self):
        r = SentimentRegistry()
        r.register(_DummySentimentProvider())
        self.assertIn("dummy", r.all_ids())


# ═══════════════════════════════════════════════════════════════════════════════
# 20. AlternativeDataset
# ═══════════════════════════════════════════════════════════════════════════════

class TestAlternativeDataset(unittest.TestCase):

    def test_add_record_updates_count(self):
        ds = AlternativeDataset(name="test", alt_type=AlternativeDataType.SATELLITE_DATA)
        ev = AlternativeEvent(value=42.0, timestamp=time.time())
        ds.add_record(ev)
        self.assertEqual(ds.record_count, 1)

    def test_period_updated(self):
        ds = AlternativeDataset(name="test", alt_type=AlternativeDataType.SOCIAL_MEDIA)
        ts = time.time()
        ev = AlternativeEvent(value=1.0, timestamp=ts)
        ds.add_record(ev)
        self.assertEqual(ds.period_start, ts)
        self.assertEqual(ds.period_end, ts)

    def test_to_dict(self):
        ds = AlternativeDataset(name="test")
        d = ds.to_dict()
        self.assertIn("dataset_id", d)

    def test_unique_ids(self):
        d1 = AlternativeDataset()
        d2 = AlternativeDataset()
        self.assertNotEqual(d1.dataset_id, d2.dataset_id)


# ═══════════════════════════════════════════════════════════════════════════════
# 21. AlternativeEvent
# ═══════════════════════════════════════════════════════════════════════════════

class TestAlternativeEvent(unittest.TestCase):

    def test_default_fields(self):
        ev = AlternativeEvent(value=5.0)
        self.assertIsNotNone(ev.event_id)

    def test_to_dict(self):
        ev = AlternativeEvent(value=3.14, symbol="AAPL")
        d = ev.to_dict()
        self.assertIn("event_id", d)
        self.assertEqual(d["value"], 3.14)

    def test_received_at_auto(self):
        ev = AlternativeEvent()
        self.assertGreater(ev.received_at, 0.0)


# ═══════════════════════════════════════════════════════════════════════════════
# 22. AlternativeDataEngine
# ═══════════════════════════════════════════════════════════════════════════════

class TestAlternativeDataEngine(unittest.TestCase):

    def _engine(self) -> AlternativeDataEngine:
        return AlternativeDataEngine()

    def test_register_and_get(self):
        eng = self._engine()
        ds  = AlternativeDataset(name="sat", alt_type=AlternativeDataType.SATELLITE_DATA)
        eng.register_dataset(ds)
        self.assertIs(eng.get_dataset(ds.dataset_id), ds)

    def test_not_found_raises(self):
        eng = self._engine()
        with self.assertRaises(AlternativeDatasetNotFoundError):
            eng.get_dataset("nonexistent")

    def test_ingest_and_count(self):
        eng = self._engine()
        ds  = AlternativeDataset(name="sat")
        eng.register_dataset(ds)
        ev  = AlternativeEvent(value=1.0, timestamp=time.time())
        eng.ingest(ds.dataset_id, ev)
        self.assertEqual(ds.record_count, 1)

    def test_query_by_type(self):
        eng = self._engine()
        ds  = AlternativeDataset(alt_type=AlternativeDataType.SATELLITE_DATA)
        eng.register_dataset(ds)
        found = eng.query_by_type(AlternativeDataType.SATELLITE_DATA)
        self.assertIn(ds, found)

    def test_compute_statistics(self):
        eng = self._engine()
        ds  = AlternativeDataset()
        eng.register_dataset(ds)
        eng.ingest(ds.dataset_id, AlternativeEvent(value=10.0, timestamp=time.time()))
        eng.ingest(ds.dataset_id, AlternativeEvent(value=20.0, timestamp=time.time()))
        stats = eng.compute_statistics(ds.dataset_id)
        self.assertAlmostEqual(stats.avg_value, 15.0, places=2)

    def test_dataset_count(self):
        eng = self._engine()
        self.assertEqual(eng.dataset_count(), 0)
        eng.register_dataset(AlternativeDataset())
        self.assertEqual(eng.dataset_count(), 1)


# ═══════════════════════════════════════════════════════════════════════════════
# 23. NewsNormalizer
# ═══════════════════════════════════════════════════════════════════════════════

class TestNewsNormalizer(unittest.TestCase):

    def setUp(self):
        self.n = NewsNormalizer(max_title_len=50, max_body_len=100)

    def _article(self, title="Good article title", body="Enough body text here.") -> NewsArticle:
        return NewsArticle(title=title, body=body)

    def test_valid_article_passes(self):
        a = self._article()
        result = self.n.normalize(a)
        self.assertIsNotNone(result)

    def test_short_title_rejected(self):
        a = self._article(title="Hi")
        result = self.n.normalize(a)
        self.assertIsNone(result)

    def test_truncation(self):
        a = self._article(title="T" * 200, body="B" * 200)
        result = self.n.normalize(a)
        self.assertIsNotNone(result)
        self.assertLessEqual(len(result.title), 51)   # 50 + ellipsis

    def test_dedup(self):
        a1 = self._article()
        a2 = self._article()   # same title/source/ts → same hash
        self.assertIsNotNone(self.n.normalize(a1))
        self.assertIsNone(self.n.normalize(a2))

    def test_dedup_different_articles_pass(self):
        a1 = self._article(title="Article title number one!!")
        a2 = self._article(title="Article title number twooo!!")
        self.assertIsNotNone(self.n.normalize(a1))
        self.assertIsNotNone(self.n.normalize(a2))

    def test_symbol_map(self):
        n = NewsNormalizer(symbol_map={"reliance": "RELIANCE"})
        a = self._article()
        a.companies = ["reliance"]
        n.normalize(a)
        self.assertIn("RELIANCE", a.companies)

    def test_language_fallback(self):
        a = self._article()
        a.language = NewsLanguage.UNKNOWN
        result = self.n.normalize(a)
        self.assertEqual(result.language, NewsLanguage.EN)

    def test_stats_increments(self):
        a = self._article(title="Unique title for stats test ##")
        self.n.normalize(a)
        self.assertGreater(self.n.stats()["normalized"], 0)


# ═══════════════════════════════════════════════════════════════════════════════
# 24. NewsRegistry
# ═══════════════════════════════════════════════════════════════════════════════

class TestNewsRegistry(unittest.TestCase):

    def setUp(self):
        self.r = NewsRegistry(max_providers=5)

    def test_register_and_get(self):
        p = PaperNewsProvider()
        self.r.register(p)
        self.assertIs(self.r.get("paper_news"), p)

    def test_has(self):
        p = PaperNewsProvider()
        self.r.register(p)
        self.assertTrue(self.r.has("paper_news"))
        self.assertFalse(self.r.has("nonexistent"))

    def test_unregister(self):
        p = PaperNewsProvider()
        self.r.register(p)
        self.r.unregister("paper_news")
        self.assertEqual(self.r.count(), 0)

    def test_duplicate_raises(self):
        p = PaperNewsProvider()
        self.r.register(p)
        with self.assertRaises(NewsProviderAlreadyRegisteredError):
            self.r.register(PaperNewsProvider())

    def test_capacity_raises(self):
        r = NewsRegistry(max_providers=1)
        r.register(PaperNewsProvider())
        with self.assertRaises(NewsRegistryError):
            r.register(ReutersProvider())

    def test_not_found_raises(self):
        with self.assertRaises(NewsProviderNotFoundError):
            self.r.get("missing")

    def test_find_connected_empty_when_none_connected(self):
        p = PaperNewsProvider()
        self.r.register(p)
        found = self.r.find_connected()
        self.assertEqual(found, [])

    def test_find_connected_after_connect(self):
        p = PaperNewsProvider()
        self.r.register(p)
        _run(p.connect())
        found = self.r.find_connected()
        self.assertEqual(len(found), 1)

    def test_count(self):
        self.assertEqual(self.r.count(), 0)
        self.r.register(PaperNewsProvider())
        self.assertEqual(self.r.count(), 1)

    def test_stats(self):
        s = self.r.stats()
        self.assertIn("total", s)
        self.assertIn("capacity", s)


# ═══════════════════════════════════════════════════════════════════════════════
# 25. NewsContext
# ═══════════════════════════════════════════════════════════════════════════════

class TestNewsContext(unittest.TestCase):

    def setUp(self):
        NewsContext.clear()

    def test_set_and_get(self):
        NewsContext.set(provider_id="reuters", subject="AAPL", operation="fetch")
        s = NewsContext.get()
        self.assertEqual(s.provider_id, "reuters")
        self.assertEqual(s.subject, "AAPL")

    def test_elapsed_ms_non_negative(self):
        NewsContext.set(operation="test")
        self.assertGreaterEqual(NewsContext.get().elapsed_ms(), 0)

    def test_scope_context_manager(self):
        with NewsContext.scope("p1", "MSFT", "search") as state:
            self.assertEqual(state.provider_id, "p1")
        # After exit the context should be cleared
        self.assertEqual(NewsContext.get().provider_id, "")

    def test_clear(self):
        NewsContext.set(provider_id="x")
        NewsContext.clear()
        self.assertEqual(NewsContext.get().provider_id, "")

    def test_independent_threads(self):
        import threading
        results = {}

        def worker(tid):
            NewsContext.set(provider_id=f"provider-{tid}")
            time.sleep(0.01)
            results[tid] = NewsContext.get().provider_id

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(3)]
        for t in threads: t.start()
        for t in threads: t.join()

        for i in range(3):
            self.assertEqual(results[i], f"provider-{i}")


# ═══════════════════════════════════════════════════════════════════════════════
# 26. NewsFactory
# ═══════════════════════════════════════════════════════════════════════════════

class TestNewsFactory(unittest.TestCase):

    def setUp(self):
        self.f = NewsFactory()

    def test_create_registry(self):
        r = self.f.create_registry()
        self.assertIsInstance(r, NewsRegistry)

    def test_create_cache(self):
        c = self.f.create_cache()
        self.assertIsInstance(c, NewsDataCache)

    def test_create_normalizer(self):
        n = self.f.create_normalizer()
        self.assertIsInstance(n, NewsNormalizer)

    def test_create_topic_classifier(self):
        tc = self.f.create_topic_classifier()
        self.assertIsInstance(tc, TopicClassifier)

    def test_create_entity_extractor(self):
        ee = self.f.create_entity_extractor()
        self.assertIsInstance(ee, EntityExtractor)

    def test_create_classification_engine(self):
        ce = self.f.create_classification_engine()
        self.assertIsInstance(ce, ClassificationEngine)

    def test_create_publisher(self):
        pub = self.f.create_publisher()
        self.assertIsInstance(pub, NewsEventPublisher)

    def test_create_alt_engine(self):
        ae = self.f.create_alternative_engine()
        self.assertIsInstance(ae, AlternativeDataEngine)


# ═══════════════════════════════════════════════════════════════════════════════
# 27. NewsEngine
# ═══════════════════════════════════════════════════════════════════════════════

class TestNewsEngine(unittest.TestCase):

    def setUp(self):
        reset_news_engine()
        self.engine = NewsEngine()

    def tearDown(self):
        reset_news_engine()

    def test_initial_status_idle(self):
        self.assertEqual(self.engine.status, NewsEngineStatus.STOPPED)

    def test_start_sets_running(self):
        _run(self.engine.start())
        self.assertEqual(self.engine.status, NewsEngineStatus.RUNNING)

    def test_stop_sets_stopped(self):
        _run(self.engine.start())
        _run(self.engine.stop())
        self.assertEqual(self.engine.status, NewsEngineStatus.STOPPED)

    def test_double_start_raises(self):
        _run(self.engine.start())
        with self.assertRaises(NewsEngineAlreadyRunningError):
            _run(self.engine.start())

    def test_fetch_before_start_raises(self):
        with self.assertRaises(NewsEngineNotRunningError):
            _run(self.engine.fetch_articles())

    def test_register_provider_before_start_raises(self):
        with self.assertRaises(NewsEngineNotRunningError):
            self.engine.register_provider(PaperNewsProvider())

    def test_register_and_connect_provider(self):
        _run(self.engine.start())
        p = PaperNewsProvider()
        self.engine.register_provider(p)
        _run(self.engine.connect_provider("paper_news"))
        self.assertTrue(p.is_connected())

    def test_fetch_articles_with_paper(self):
        _run(self.engine.start())
        p = PaperNewsProvider()
        self.engine.register_provider(p)
        _run(self.engine.connect_provider("paper_news"))
        articles = _run(self.engine.fetch_articles(limit=5))
        self.assertGreater(len(articles), 0)

    def test_search_news_with_paper(self):
        _run(self.engine.start())
        p = PaperNewsProvider()
        self.engine.register_provider(p)
        _run(self.engine.connect_provider("paper_news"))
        results = _run(self.engine.search_news("NIFTY", limit=3))
        self.assertIsInstance(results, list)

    def test_stats(self):
        _run(self.engine.start())
        s = self.engine.stats()
        self.assertIn("version", s)
        self.assertIn("status", s)

    def test_uptime_sec(self):
        _run(self.engine.start())
        time.sleep(0.02)
        self.assertGreater(self.engine.uptime_sec(), 0)

    def test_is_running(self):
        _run(self.engine.start())
        self.assertTrue(self.engine.is_running())


# ═══════════════════════════════════════════════════════════════════════════════
# 28. Singleton
# ═══════════════════════════════════════════════════════════════════════════════

class TestSingleton(unittest.TestCase):

    def setUp(self):
        reset_news_engine()

    def tearDown(self):
        reset_news_engine()

    def test_same_instance(self):
        e1 = get_news_engine()
        e2 = get_news_engine()
        self.assertIs(e1, e2)

    def test_reset_creates_new(self):
        e1 = get_news_engine()
        reset_news_engine()
        e2 = get_news_engine()
        self.assertIsNot(e1, e2)

    def test_not_running_initially(self):
        e = get_news_engine()
        self.assertFalse(e.is_running())

    def test_auto_start(self):
        e = get_news_engine(auto_start=True)
        self.assertTrue(e.is_running())

    def test_reset_and_auto_start_cycle(self):
        e1 = get_news_engine(auto_start=True)
        reset_news_engine()
        e2 = get_news_engine(auto_start=True)
        self.assertIsNot(e1, e2)
        self.assertTrue(e2.is_running())


# ═══════════════════════════════════════════════════════════════════════════════
# 29. NewsMonitor
# ═══════════════════════════════════════════════════════════════════════════════

class TestNewsMonitor(unittest.TestCase):

    def setUp(self):
        self.monitor = NewsMonitor(poll_interval_sec=1)

    def tearDown(self):
        self.monitor.stop()

    def test_register_provider(self):
        p = PaperNewsProvider()
        self.monitor.register(p)
        self.assertIsNone(self.monitor.get_health("paper_news"))  # not polled yet

    def test_poll_health(self):
        p = PaperNewsProvider()
        _run(p.connect())
        self.monitor.register(p)
        # Manually trigger a poll
        self.monitor._poll_all()
        h = self.monitor.get_health("paper_news")
        self.assertIsNotNone(h)

    def test_all_health(self):
        p = PaperNewsProvider()
        _run(p.connect())
        self.monitor.register(p)
        self.monitor._poll_all()
        all_h = self.monitor.all_health()
        self.assertIn("paper_news", all_h)

    def test_unregister(self):
        p = PaperNewsProvider()
        self.monitor.register(p)
        self.monitor.unregister("paper_news")
        # Should not appear in all_health
        all_h = self.monitor.all_health()
        self.assertNotIn("paper_news", all_h)

    def test_stats(self):
        p = PaperNewsProvider()
        _run(p.connect())
        self.monitor.register(p)
        self.monitor._poll_all()
        s = self.monitor.stats()
        self.assertGreater(s["polls"], 0)


# ═══════════════════════════════════════════════════════════════════════════════
# 30. NewsEventPublisher
# ═══════════════════════════════════════════════════════════════════════════════

class TestNewsEventPublisher(unittest.TestCase):

    def test_publish_all(self):
        pub = NewsEventPublisher()
        received = []
        pub.subscribe_all(received.append)
        art = NewsArticle(title="Breaking news today!", body="Something happened.")
        seq = pub.publish(art)
        self.assertGreater(seq, 0)
        self.assertEqual(len(received), 1)

    def test_subscribe_company(self):
        pub = NewsEventPublisher()
        received = []
        pub.subscribe_company("AAPL", received.append)
        art = NewsArticle(title="Apple rally", body="AAPL stock rose.")
        art.companies = ["AAPL"]
        pub.publish(art)
        self.assertEqual(len(received), 1)

    def test_subscribe_breaking(self):
        pub = NewsEventPublisher()
        received = []
        pub.subscribe_breaking(received.append)
        art = NewsArticle(title="BREAKING: Market crash!", body="Stocks fell 5%.")
        art.is_breaking = True
        pub.publish(art)
        self.assertEqual(len(received), 1)

    def test_sequence_increments(self):
        pub = NewsEventPublisher()
        a1 = NewsArticle(title="Article one today", body="Body one")
        a2 = NewsArticle(title="Article two today", body="Body two")
        s1 = pub.publish(a1)
        s2 = pub.publish(a2)
        self.assertGreater(s2, s1)

    def test_subscription_count(self):
        pub = NewsEventPublisher()
        pub.subscribe_all(lambda x: None)
        pub.subscribe_all(lambda x: None)
        self.assertGreaterEqual(pub.subscription_count(), 2)


if __name__ == "__main__":
    unittest.main()
