"""
oios/engine/event_normalizer.py

Phase E0 — Event Normalization Framework.

Normalizes raw event data into canonical OIOS event representations.
Maps free-text or broker-sourced event descriptions to canonical event types,
magnitude bands, and direction signals.

This module is stateless (no DB writes). Consumers call normalize_raw_event()
and then pass the result to event_ingestion.ingest_event().
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

# ---------------------------------------------------------------------------
# Canonical mappings
# ---------------------------------------------------------------------------

# Keywords → canonical EVENT_TYPE
_EVENT_TYPE_KEYWORDS: list[tuple[str, list[str]]] = [
    ("EARNINGS",     ["earnings", "result", "quarterly", "annual result", "profit", "ebitda", "revenue", "q1", "q2", "q3", "q4"]),
    ("ORDER_WIN",    ["order win", "order inflow", "contract win", "bag order", "secured order", "letter of intent", "loi", "work order"]),
    ("POLICY",       ["policy", "budget", "government", "ministry", "regulation", "niti aayog", "pli scheme", "incentive scheme", "defence policy"]),
    ("GUIDANCE",     ["guidance", "outlook", "management commentary", "revised target", "forecast", "commentary"]),
    ("CAPEX",        ["capex", "capital expenditure", "expansion", "greenfield", "brownfield", "plant", "capacity addition"]),
    ("PROMOTER",     ["promoter", "insider buy", "insider sell", "promoter holding", "creeping acquisition"]),
    ("BULK",         ["bulk deal", "block deal", "fii buy", "fii sell", "dii buy", "institutional buy"]),
]

# Keywords → magnitude
_MAGNITUDE_HIGH: list[str] = [
    "record", "highest ever", "significant", "major", "large", "huge",
    "beat", "miss", "surge", "jump", "collapse", "plunge", "strong beat",
    "blowout", "multi-year high", "all-time",
]
_MAGNITUDE_LOW: list[str] = [
    "minor", "marginal", "slight", "small", "modest", "inline",
    "in-line", "as expected", "nominal",
]

# Keywords → direction
_DIRECTION_POSITIVE: list[str] = [
    "beat", "growth", "rise", "increase", "wins", "win", "secured",
    "positive", "upgrade", "outperform", "strong", "record",
    "acquisition", "expand", "promoter buy", "insider buy", "fii buy",
    "inflow", "order book growth", "margin expansion",
]
_DIRECTION_NEGATIVE: list[str] = [
    "miss", "decline", "fall", "loss", "weak", "downgrade", "underperform",
    "reduce", "promoter sell", "insider sell", "fii sell", "write-off",
    "margin compression", "order cancel", "renegotiate", "default",
]


def _to_lower(text: str) -> str:
    return text.lower().strip() if text else ""


def normalize_event_type(raw_type: str) -> str:
    """
    Map a raw event description or type label to a canonical EVENT_TYPE.
    Falls back to "OTHER" if no match.
    """
    raw_lower = _to_lower(raw_type)
    for canonical, keywords in _EVENT_TYPE_KEYWORDS:
        for kw in keywords:
            if kw in raw_lower:
                return canonical
    return "OTHER"


def normalize_magnitude(text: str) -> str:
    """
    Determine magnitude band from a text blob.
    Returns "HIGH" | "MEDIUM" | "LOW".
    """
    lower = _to_lower(text)
    if any(kw in lower for kw in _MAGNITUDE_HIGH):
        return "HIGH"
    if any(kw in lower for kw in _MAGNITUDE_LOW):
        return "LOW"
    return "MEDIUM"


def normalize_direction(text: str) -> str:
    """
    Determine direction from a text blob.
    Returns "POSITIVE" | "NEGATIVE" | "NEUTRAL".
    """
    lower = _to_lower(text)
    pos_hits = sum(1 for kw in _DIRECTION_POSITIVE if kw in lower)
    neg_hits = sum(1 for kw in _DIRECTION_NEGATIVE if kw in lower)
    if pos_hits > neg_hits:
        return "POSITIVE"
    if neg_hits > pos_hits:
        return "NEGATIVE"
    return "NEUTRAL"


def normalize_confidence(source: str | None, verified: bool = False) -> float:
    """
    Heuristic confidence score based on source quality.
    Exchange filings → 0.95; analyst reports → 0.70; news → 0.55; unknown → 0.40.
    Bumped by 0.05 if verified.
    """
    _SOURCE_CONFIDENCE: dict[str, float] = {
        "bse":        0.95,
        "nse":        0.95,
        "exchange":   0.95,
        "drhp":       0.90,
        "annual_report": 0.90,
        "analyst":    0.70,
        "broker":     0.65,
        "news":       0.55,
        "social":     0.35,
    }
    base = 0.40
    if source:
        src_lower = _to_lower(source)
        for key, score in _SOURCE_CONFIDENCE.items():
            if key in src_lower:
                base = score
                break
    return min(1.0, base + (0.05 if verified else 0.0))


# ---------------------------------------------------------------------------
# NormalizedEvent dataclass
# ---------------------------------------------------------------------------

@dataclass
class NormalizedEvent:
    symbol:       str
    event_date:   str           # YYYY-MM-DD
    event_type:   str
    headline:     str | None
    magnitude:    str           # HIGH | MEDIUM | LOW
    direction:    str           # POSITIVE | NEGATIVE | NEUTRAL
    source:       str | None
    confidence:   float
    raw_data:     dict[str, Any] = field(default_factory=dict)

    # Entity links (populated by normalizer when detectable from raw_data)
    entity_links: list[dict[str, str]] = field(default_factory=list)
    # Each item: {"entity_type": "SECTOR", "entity_id": "IT", "link_type": "PRIMARY"}


def normalize_raw_event(raw: dict[str, Any]) -> NormalizedEvent:
    """
    Convert a raw dict (from broker feed, news scraper, etc.) into a
    NormalizedEvent ready for ingest_event().

    Expected raw keys (all optional except symbol and event_date):
        symbol, event_date, event_type, headline, body, source,
        magnitude, direction, confidence, sector, theme
    """
    symbol     = str(raw.get("symbol", "")).upper()
    event_date = str(raw.get("event_date", ""))

    # Derive text blob for classification
    headline = raw.get("headline") or raw.get("title") or ""
    body     = raw.get("body") or raw.get("description") or ""
    combined = f"{headline} {body}"

    # Event type
    event_type = raw.get("event_type") or ""
    event_type = normalize_event_type(event_type or combined)

    # Magnitude + direction
    magnitude = raw.get("magnitude") or normalize_magnitude(combined)
    if magnitude not in {"HIGH", "MEDIUM", "LOW"}:
        magnitude = normalize_magnitude(magnitude)

    direction = raw.get("direction") or normalize_direction(combined)
    if direction not in {"POSITIVE", "NEGATIVE", "NEUTRAL"}:
        direction = normalize_direction(direction)

    # Source + confidence
    source     = raw.get("source")
    verified   = bool(raw.get("verified", False))
    confidence = float(raw.get("confidence", normalize_confidence(source, verified)))

    # Entity links
    entity_links: list[dict[str, str]] = []
    if raw.get("sector"):
        entity_links.append({
            "entity_type": "SECTOR", "entity_id": str(raw["sector"]),
            "link_type": "PRIMARY",
        })
    if raw.get("theme"):
        entity_links.append({
            "entity_type": "THEME", "entity_id": str(raw["theme"]),
            "link_type": "SECONDARY",
        })

    # Raw data for auditability
    raw_clean = {k: v for k, v in raw.items() if k != "raw_data"}

    return NormalizedEvent(
        symbol       = symbol,
        event_date   = event_date,
        event_type   = event_type,
        headline     = headline or None,
        magnitude    = magnitude,
        direction    = direction,
        source       = source,
        confidence   = confidence,
        raw_data     = raw_clean,
        entity_links = entity_links,
    )


def ingest_normalized_event(
    conn,
    event: NormalizedEvent,
) -> str:
    """
    Convenience wrapper: normalize → ingest_event → link_event_to_entity.
    Returns event_id.
    """
    from .event_ingestion import ingest_event, link_event_to_entity

    event_id = ingest_event(
        conn,
        symbol     = event.symbol,
        event_date = event.event_date,
        event_type = event.event_type,
        headline   = event.headline,
        magnitude  = event.magnitude,
        direction  = event.direction,
        source     = event.source,
        confidence = event.confidence,
        raw_data   = event.raw_data,
    )
    for lnk in event.entity_links:
        link_event_to_entity(
            conn, event_id,
            entity_type      = lnk["entity_type"],
            entity_id        = lnk["entity_id"],
            link_type        = lnk["link_type"],
            impact_direction = event.direction,
            impact_magnitude = event.magnitude,
        )
    return event_id
