"""
oios/data/sector_classifier.py

Give every active symbol in ``universe_stocks`` a real sector from the OIOS vocabulary.

Why: ``universe_stocks.sector`` was written once, at insert time, and never updated.
278 of the 573 active symbols (48%) were ``UNKNOWN`` and about 30 more sat in tiny
duplicate buckets (BANKING, FINANCIAL, HEALTHCARE...), because the symbols were added
before any classification existed. Sector breadth, sector conviction and the sector
archetypes all need real peer groups; ``UNKNOWN`` is not one.

Source: yfinance ``info['industry']`` / ``['sector']`` (the same library and fixed cache
pattern already used for sector enrichment), mapped to the OIOS labels by a fixed keyword
table. Rules:
  * curated labels are never overwritten; only ``UNKNOWN``/empty rows are classified;
  * a symbol with no confident mapping stays ``UNKNOWN`` (the scanners treat that as
    "no sector"), never a guess;
  * results, including failures, are cached with a date so each symbol is fetched at most
    once per retry window and a run is bounded;
  * a few clear duplicate labels are merged into the label OIOS already uses.
Never raises.
"""
from __future__ import annotations

import json
import logging
import os
import sqlite3
import time
from datetime import date, datetime, timedelta
from typing import Any, Callable, Optional

log = logging.getLogger(__name__)

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CACHE_PATH = os.path.join(ROOT, "data", "sector_classification_cache.json")
UNCLASSIFIED = ("UNKNOWN", "", None)
MAX_FETCHES_PER_RUN = 150
RETRY_AFTER_DAYS = 14
FETCH_PAUSE_S = 0.25

# Labels already in use that duplicate an OIOS sector.
ALIASES = {"BANKING": "BANKING_FINANCE", "FINANCIAL": "BANKING_FINANCE",
           "FINTECH": "BANKING_FINANCE", "HEALTHCARE": "PHARMA"}

# (keywords matched against the lower-cased industry, OIOS sector); first match wins.
_INDUSTRY_RULES: tuple[tuple[tuple[str, ...], str], ...] = (
    (("aerospace", "defense"), "DEFENCE"),
    (("bank", "mortgage finance", "credit services", "asset management", "capital markets",
      "insurance", "financial", "shell compan"), "BANKING_FINANCE"),
    (("drug manufactur", "biotech", "medical", "diagnostic", "pharma", "health information",
      "healthcare"), "PHARMA"),
    (("software", "information technology", "it services", "computer", "semiconductor"), "IT"),
    (("airline", "airport"), "AVIATION"),
    (("auto manufactur", "auto parts", "auto & truck", "recreational vehicle", "truck manufactur"), "AUTO"),
    (("steel", "aluminum", "copper", "gold", "silver", "metal", "coking coal", "mining"), "METALS"),
    (("chemical", "agricultural inputs", "fertilizer"), "CHEMICALS"),
    (("oil & gas", "thermal coal", "uranium", "coal"), "ENERGY"),
    (("utilities",), "POWER"),
    (("telecom",), "TELECOM"),
    (("packaged foods", "beverages", "tobacco", "confectioner", "household & personal",
      "food distribution", "farm products", "grocery", "discount stores"), "FMCG"),
    (("building materials", "cement"), "CEMENT"),
    (("real estate",), "REALESTATE"),
    (("textile", "apparel manufactur", "footwear", "leather"), "TEXTILES"),
    (("entertainment", "broadcasting", "publishing", "advertising", "internet content",
      "electronic gaming"), "MEDIA"),
    (("retail", "department stores", "specialty retail", "internet retail", "apparel retail"), "RETAIL"),
    (("furnishings", "appliances", "luxury goods", "consumer electronics", "electronic components",
      "communication equipment", "packaging & containers", "household durables"), "CONSUMER_DURABLES"),
    (("lodging", "restaurants", "travel services", "leisure", "resorts", "gambling",
      "personal services", "residential construction", "education & training"), "CONSUMER_SERVICES"),
    (("engineering & construction", "infrastructure", "electrical equipment", "machinery",
      "industrial", "tools", "conglomerates", "specialty business", "waste", "pollution",
      "security & protection", "staffing", "consulting", "rental & leasing", "railroads",
      "trucking", "marine shipping", "integrated freight"), "INFRA"),
)

# yfinance's coarse sector, used only where it maps to one OIOS sector unambiguously.
_COARSE_SECTOR = {
    "Financial Services": "BANKING_FINANCE", "Technology": "IT", "Healthcare": "PHARMA",
    "Energy": "ENERGY", "Utilities": "POWER", "Real Estate": "REALESTATE",
    "Consumer Defensive": "FMCG", "Industrials": "INFRA", "Communication Services": "MEDIA",
}


def classify(industry: Optional[str], coarse_sector: Optional[str] = None) -> Optional[str]:
    """OIOS sector for a yfinance industry (falling back to its coarse sector), or ``None``."""
    text = (industry or "").strip().lower()
    if text:
        for keywords, sector in _INDUSTRY_RULES:
            if any(keyword in text for keyword in keywords):
                return sector
    return _COARSE_SECTOR.get((coarse_sector or "").strip())


def _load_cache(path: str) -> dict[str, dict[str, Any]]:
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _save_cache(path: str, cache: dict[str, dict[str, Any]]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as handle:
        json.dump(cache, handle, sort_keys=True)
    os.replace(tmp, path)


def _yfinance_fetch(symbol: str) -> tuple[Optional[str], Optional[str]]:
    import yfinance as yf
    info = yf.Ticker(symbol).info
    return info.get("industry"), info.get("sector")


def _due(entry: Optional[dict[str, Any]], today: date) -> bool:
    """Fetch when never tried, or when an earlier attempt found nothing and the retry window passed."""
    if entry is None:
        return True
    if entry.get("industry") or entry.get("yf_sector"):
        return False
    try:
        tried = date.fromisoformat(str(entry.get("fetched_at", ""))[:10])
    except ValueError:
        return True
    return today - tried >= timedelta(days=RETRY_AFTER_DAYS)


def run_sector_classification(
    conn: sqlite3.Connection,
    max_fetches: int = MAX_FETCHES_PER_RUN,
    fetch_fn: Optional[Callable[[str], tuple[Optional[str], Optional[str]]]] = None,
    cache_path: Optional[str] = None,
    today: Optional[date] = None,
) -> dict[str, Any]:
    """Classify ``UNKNOWN`` active symbols and merge duplicate labels. Never raises."""
    summary: dict[str, Any] = {"aliased": 0, "classified": 0, "fetched": 0, "still_unknown": 0}
    try:
        today = today or date.today()
        path = cache_path or CACHE_PATH
        fetch = fetch_fn or _yfinance_fetch
        cache = _load_cache(path)

        with conn:
            for old, new in ALIASES.items():
                summary["aliased"] += conn.execute(
                    "UPDATE universe_stocks SET sector = ? WHERE sector = ? AND is_active = 1", (new, old)
                ).rowcount

        unknown = [r[0] for r in conn.execute(
            "SELECT symbol FROM universe_stocks WHERE is_active = 1 AND (sector IS NULL OR sector IN ('', 'UNKNOWN'))"
        ).fetchall()]

        fetches = 0
        for symbol in unknown:
            entry = cache.get(symbol)
            if _due(entry, today) and fetches < max_fetches:
                fetches += 1
                try:
                    industry, coarse = fetch(symbol)
                except Exception as exc:
                    log.debug("[SectorClassifier] fetch failed for %s: %s", symbol, exc)
                    industry, coarse = None, None
                entry = {"industry": industry, "yf_sector": coarse,
                         "fetched_at": datetime.now().isoformat(timespec="seconds")}
                cache[symbol] = entry
                if fetch_fn is None:
                    time.sleep(FETCH_PAUSE_S)
            sector = classify((entry or {}).get("industry"), (entry or {}).get("yf_sector"))
            if sector is None:
                summary["still_unknown"] += 1
                continue
            entry["oios_sector"] = sector
            with conn:
                conn.execute(
                    "UPDATE universe_stocks SET sector = ? WHERE symbol = ? "
                    "AND (sector IS NULL OR sector IN ('', 'UNKNOWN'))", (sector, symbol))
            summary["classified"] += 1
        summary["fetched"] = fetches
        if fetches:
            _save_cache(path, cache)
    except Exception as exc:
        log.warning("[SectorClassifier] failed (non-critical): %s", exc, exc_info=True)
        summary["error"] = str(exc)
    return summary
