"""iios/integration/news/classification/topic_classifier.py

Rule-based keyword-driven topic classifier.

No NLP or ML models — purely deterministic keyword matching.
Future providers can register their own category→keyword maps.
"""
from __future__ import annotations

from typing import Any

from iios.integration.news.news_constants import NewsCategory

# ── Default keyword taxonomy ──────────────────────────────────────────────────

_DEFAULT_KEYWORDS: dict[NewsCategory, list[str]] = {
    NewsCategory.EARNINGS: [
        "earnings", "revenue", "profit", "eps", "quarterly", "annual results",
        "beats", "misses", "guidance", "forecast", "q1", "q2", "q3", "q4",
    ],
    NewsCategory.DIVIDEND: [
        "dividend", "payout", "yield", "ex-dividend", "declared",
    ],
    NewsCategory.MERGER_ACQ: [
        "merger", "acquisition", "takeover", "buyout", "deal",
        "acquire", "acquired", "bid for", "offer to buy",
    ],
    NewsCategory.IPO: [
        "ipo", "initial public offering", "listing", "debut", "going public",
    ],
    NewsCategory.CENTRAL_BANK: [
        "federal reserve", "rbi", "ecb", "boe", "central bank",
        "fomc", "mpc", "monetary policy", "rate decision",
    ],
    NewsCategory.INTEREST_RATES: [
        "interest rate", "rate hike", "rate cut", "basis points", "bps",
        "repo rate", "fed funds", "yield",
    ],
    NewsCategory.INFLATION: [
        "inflation", "cpi", "ppi", "deflation", "price index", "consumer prices",
    ],
    NewsCategory.GDP: [
        "gdp", "gross domestic product", "economic growth", "contraction", "recession",
    ],
    NewsCategory.EMPLOYMENT: [
        "jobs", "unemployment", "nonfarm payrolls", "jobless claims", "hiring", "layoffs",
    ],
    NewsCategory.GEOPOLITICS: [
        "war", "conflict", "sanctions", "geopolitical", "election", "trade war",
        "tariff", "embargo",
    ],
    NewsCategory.REGULATORY: [
        "regulation", "sec", "sebi", "fca", "regulatory", "compliance",
        "fine", "penalty", "investigation",
    ],
    NewsCategory.TECHNOLOGY: [
        "ai", "artificial intelligence", "technology", "software", "semiconductor",
        "cloud", "cybersecurity", "tech",
    ],
    NewsCategory.HEALTHCARE: [
        "fda", "clinical trial", "drug", "pharma", "healthcare", "biotech",
        "vaccine", "approval",
    ],
    NewsCategory.COMMODITIES: [
        "oil", "crude", "gold", "silver", "copper", "wheat", "commodity",
        "brent", "wti", "opec",
    ],
    NewsCategory.ENERGY: [
        "energy", "electricity", "renewable", "solar", "wind", "nuclear",
        "natural gas", "lng",
    ],
    NewsCategory.CRYPTO: [
        "bitcoin", "ethereum", "crypto", "blockchain", "defi",
        "nft", "token",
    ],
    NewsCategory.ESG: [
        "esg", "sustainability", "carbon", "emission", "climate",
        "green", "social responsibility",
    ],
    NewsCategory.ANALYST_UPGRADE: [
        "upgrade", "outperform", "buy rating", "price target raised",
    ],
    NewsCategory.ANALYST_DOWNGRADE: [
        "downgrade", "underperform", "sell rating", "price target cut",
    ],
    NewsCategory.MANAGEMENT_CHANGE: [
        "ceo", "cfo", "coo", "resign", "appointed", "steps down",
        "chairman", "board member", "executive",
    ],
    NewsCategory.INSIDER_TRADING: [
        "insider", "insider trade", "form 4", "insider buying", "insider selling",
    ],
    NewsCategory.SEC_FILING: [
        "sec filing", "10-k", "10-q", "8-k", "13f", "proxy", "edgar",
    ],
    NewsCategory.MARKETS: [
        "market", "nifty", "sensex", "s&p", "dow", "nasdaq", "ftse",
        "rally", "selloff", "correction",
    ],
}


class TopicClassifier:
    """
    Rule-based topic classifier using keyword matching.

    Multiple categories can match a single article.
    """

    def __init__(
        self,
        keyword_map: dict[NewsCategory, list[str]] | None = None,
        max_topics:  int = 5,
    ) -> None:
        self._kw_map    = keyword_map or _DEFAULT_KEYWORDS
        self._max       = max_topics
        self._stats: dict[str, int] = {"classified": 0, "uncategorized": 0}

    def classify(self, text: str) -> list[NewsCategory]:
        """
        Return a list of matching NewsCategory for the given text.
        Categories are returned in order of match count (most specific first).
        """
        lower    = text.lower()
        scores:  dict[NewsCategory, int] = {}
        for cat, keywords in self._kw_map.items():
            hits = sum(1 for kw in keywords if kw in lower)
            if hits > 0:
                scores[cat] = hits

        self._stats["classified"] += 1
        if not scores:
            self._stats["uncategorized"] += 1
            return [NewsCategory.GENERAL]

        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return [cat for cat, _ in ranked[: self._max]]

    def add_keywords(self, category: NewsCategory, keywords: list[str]) -> None:
        self._kw_map.setdefault(category, []).extend(keywords)

    def stats(self) -> dict[str, Any]:
        return dict(self._stats)
