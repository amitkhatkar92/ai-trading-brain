"""iios/integration/news/distribution/news_event_publisher.py

Fan-out publisher for news objects.

Publishes NewsArticle, NewsEvent, and NewsHeadline to subscribed
handler callbacks organised by topic, company, sector, and priority.
"""
from __future__ import annotations

import logging
import threading
import time
from collections import defaultdict
from typing import Any, Callable

from iios.integration.news.core.news_article  import NewsArticle
from iios.integration.news.core.news_event    import NewsEvent
from iios.integration.news.core.news_headline import NewsHeadline
from iios.integration.news.news_constants     import NewsCategory, NewsImportance

logger = logging.getLogger(__name__)

AnyNewsObject = NewsArticle | NewsEvent | NewsHeadline
Handler = Callable[[AnyNewsObject], None]


class NewsEventPublisher:
    """
    Sequence-numbered fan-out publisher.

    Subscription types:
    - ``subscribe_all``       — all articles
    - ``subscribe_category``  — by NewsCategory
    - ``subscribe_company``   — by ticker string
    - ``subscribe_sector``    — by sector string
    - ``subscribe_breaking``  — breaking news only (importance >= threshold)
    """

    def __init__(self, breaking_threshold: NewsImportance = NewsImportance.HIGH) -> None:
        self._lock      = threading.RLock()
        self._seq       = 0
        self._breaking_threshold = breaking_threshold

        # Subscriber buckets
        self._all_handlers:       list[Handler]                       = []
        self._category_handlers:  defaultdict[str, list[Handler]]     = defaultdict(list)
        self._company_handlers:   defaultdict[str, list[Handler]]     = defaultdict(list)
        self._sector_handlers:    defaultdict[str, list[Handler]]     = defaultdict(list)
        self._breaking_handlers:  list[Handler]                       = []

        self._stats: dict[str, int] = {
            "published":   0,
            "dispatched":  0,
            "errors":      0,
        }

    # ── Subscriptions ─────────────────────────────────────────────────────────

    def subscribe_all(self, handler: Handler) -> None:
        with self._lock:
            self._all_handlers.append(handler)

    def subscribe_category(self, category: NewsCategory, handler: Handler) -> None:
        with self._lock:
            self._category_handlers[category.value].append(handler)

    def subscribe_company(self, ticker: str, handler: Handler) -> None:
        with self._lock:
            self._company_handlers[ticker.upper()].append(handler)

    def subscribe_sector(self, sector: str, handler: Handler) -> None:
        with self._lock:
            self._sector_handlers[sector.lower()].append(handler)

    def subscribe_breaking(self, handler: Handler) -> None:
        with self._lock:
            self._breaking_handlers.append(handler)

    def unsubscribe_all(self, handler: Handler) -> None:
        with self._lock:
            if handler in self._all_handlers:
                self._all_handlers.remove(handler)

    # ── Publishing ────────────────────────────────────────────────────────────

    def publish(self, obj: AnyNewsObject) -> int:
        """Publish one news object. Returns the sequence number assigned."""
        with self._lock:
            self._seq += 1
            seq = self._seq
            all_h    = list(self._all_handlers)
            cat_keys  = self._extract_categories(obj)
            comp_keys = self._extract_companies(obj)
            sect_keys = self._extract_sectors(obj)
            is_break  = self._is_breaking(obj)
            brk_h     = list(self._breaking_handlers) if is_break else []
            cat_h     = [h for k in cat_keys for h in self._category_handlers.get(k, [])]
            comp_h    = [h for k in comp_keys for h in self._company_handlers.get(k, [])]
            sect_h    = [h for k in sect_keys for h in self._sector_handlers.get(k, [])]

        handlers = list(dict.fromkeys(all_h + cat_h + comp_h + sect_h + brk_h))
        for h in handlers:
            try:
                h(obj)
                self._stats["dispatched"] += 1
            except Exception as exc:
                self._stats["errors"] += 1
                logger.warning("[NewsEventPublisher] Handler error: %s", exc)

        self._stats["published"] += 1
        return seq

    def subscription_count(self) -> int:
        with self._lock:
            total = (
                len(self._all_handlers)
                + sum(len(v) for v in self._category_handlers.values())
                + sum(len(v) for v in self._company_handlers.values())
                + sum(len(v) for v in self._sector_handlers.values())
                + len(self._breaking_handlers)
            )
            return total

    def stats(self) -> dict[str, Any]:
        return dict(self._stats)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _extract_categories(self, obj: AnyNewsObject) -> list[str]:
        if isinstance(obj, NewsArticle):
            return [c.value for c in obj.categories]
        return []

    def _extract_companies(self, obj: AnyNewsObject) -> list[str]:
        if isinstance(obj, NewsArticle):
            return [c.upper() for c in obj.companies]
        if isinstance(obj, NewsEvent):
            return [c.upper() for c in obj.companies]
        if isinstance(obj, NewsHeadline):
            return [c.upper() for c in obj.companies]
        return []

    def _extract_sectors(self, obj: AnyNewsObject) -> list[str]:
        if isinstance(obj, NewsArticle):
            return [s.lower() for s in obj.sectors]
        return []

    def _is_breaking(self, obj: AnyNewsObject) -> bool:
        if isinstance(obj, NewsArticle):
            return obj.is_breaking or obj.importance >= self._breaking_threshold
        if isinstance(obj, NewsHeadline):
            return obj.urgency is not None
        return False
