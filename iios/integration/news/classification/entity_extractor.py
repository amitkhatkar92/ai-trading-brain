"""iios/integration/news/classification/entity_extractor.py

Rule-based entity extractor for news articles.

Extracts:
- Company names / ticker symbols (from a registered symbol list)
- Country names
- Sector names

No NLP/NER models — purely deterministic lookup tables.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

# ── Default entity tables ─────────────────────────────────────────────────────

_DEFAULT_TICKERS: dict[str, str] = {
    "AAPL": "Apple", "MSFT": "Microsoft", "GOOG": "Alphabet", "GOOGL": "Alphabet",
    "AMZN": "Amazon", "META": "Meta", "TSLA": "Tesla", "NVDA": "Nvidia",
    "RELIANCE": "Reliance Industries", "TCS": "Tata Consultancy Services",
    "INFY": "Infosys", "HDFC": "HDFC Bank", "ICICIBANK": "ICICI Bank",
    "WIPRO": "Wipro", "TATAMOTORS": "Tata Motors", "TATASTEEL": "Tata Steel",
    "NIFTY": "Nifty 50", "BANKNIFTY": "Bank Nifty", "SENSEX": "BSE Sensex",
}

_DEFAULT_COUNTRIES: set[str] = {
    "india", "china", "us", "usa", "united states", "uk", "united kingdom",
    "europe", "japan", "germany", "france", "australia", "canada", "brazil",
    "russia", "saudi arabia", "uae", "singapore", "hong kong",
}

_DEFAULT_SECTORS: set[str] = {
    "technology", "finance", "healthcare", "energy", "consumer", "industrials",
    "materials", "utilities", "real estate", "communication", "banking",
    "pharma", "auto", "retail", "media",
}


@dataclass
class ExtractedEntities:
    companies:  list[str] = field(default_factory=list)   # ticker symbols
    countries:  list[str] = field(default_factory=list)
    sectors:    list[str] = field(default_factory=list)
    persons:    list[str] = field(default_factory=list)    # placeholder
    other:      list[str] = field(default_factory=list)


class EntityExtractor:
    """
    Extracts named entities from news text using lookup tables.
    """

    def __init__(
        self,
        ticker_map: dict[str, str] | None = None,
        countries:  set[str] | None = None,
        sectors:    set[str] | None = None,
    ) -> None:
        self._tickers   = ticker_map or _DEFAULT_TICKERS
        self._countries = {c.lower() for c in (countries or _DEFAULT_COUNTRIES)}
        self._sectors   = {s.lower() for s in (sectors or _DEFAULT_SECTORS)}
        self._stats: dict[str, int] = {"extracted": 0}

    def extract(self, text: str) -> ExtractedEntities:
        """Extract all entities from the given text."""
        result   = ExtractedEntities()
        lower    = text.lower()
        upper_text = text.upper()

        # ── Tickers ────────────────────────────────────────────────────────────
        for ticker, company_name in self._tickers.items():
            pattern = r'\b' + re.escape(ticker) + r'\b'
            if re.search(pattern, upper_text) or company_name.lower() in lower:
                result.companies.append(ticker)

        # ── Countries ──────────────────────────────────────────────────────────
        for country in self._countries:
            if country in lower:
                result.countries.append(country.title())

        # ── Sectors ────────────────────────────────────────────────────────────
        for sector in self._sectors:
            if sector in lower:
                result.sectors.append(sector.title())

        self._stats["extracted"] += 1
        return result

    def register_ticker(self, ticker: str, company_name: str) -> None:
        self._tickers[ticker.upper()] = company_name

    def register_country(self, country: str) -> None:
        self._countries.add(country.lower())

    def stats(self) -> dict[str, Any]:
        return dict(self._stats)
