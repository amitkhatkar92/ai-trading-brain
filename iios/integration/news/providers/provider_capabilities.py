"""iios/integration/news/providers/provider_capabilities.py

Capability declaration for a news/alternative-data provider.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from iios.integration.news.news_constants import (
    AlternativeDataType,
    NewsCategory,
    NewsLanguage,
    NewsRegion,
)


@dataclass
class NewsProviderCapabilities:
    """Describes what a news provider supports."""

    # ── Content ───────────────────────────────────────────────────────────────
    categories:          list[NewsCategory]         = field(default_factory=list)
    languages:           list[NewsLanguage]         = field(default_factory=list)
    regions:             list[NewsRegion]            = field(default_factory=list)

    # ── Capabilities ──────────────────────────────────────────────────────────
    supports_articles:   bool = True
    supports_events:     bool = False
    supports_streaming:  bool = False
    supports_alerts:     bool = False
    supports_search:     bool = False
    supports_historical: bool = False
    historical_depth_days: int = 0

    # ── Alternative data ──────────────────────────────────────────────────────
    alt_data_types:      list[AlternativeDataType]  = field(default_factory=list)

    # ── Rate limits ───────────────────────────────────────────────────────────
    requires_authentication: bool = False
    requests_per_minute:  int = 0   # 0 = unlimited
    max_articles_per_fetch: int = 100

    # ── Extra ──────────────────────────────────────────────────────────────────
    extra: dict[str, Any] = field(default_factory=dict)

    def supports_category(self, cat: NewsCategory) -> bool:
        return not self.categories or cat in self.categories

    def supports_language(self, lang: NewsLanguage) -> bool:
        return not self.languages or lang in self.languages

    def supports_region(self, region: NewsRegion) -> bool:
        return (
            not self.regions
            or region in self.regions
            or NewsRegion.GLOBAL in self.regions
        )


