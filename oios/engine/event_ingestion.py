"""
oios/engine/event_ingestion.py

Phase E0 — Event Ingestion Framework.

Responsibilities:
  - Store corporate events (earnings, order wins, policy, guidance, capex, etc.)
  - Store company-to-company relationships (supplier/customer/peer/...)
  - Store knowledge graph metadata for companies, sectors, and themes
  - Link events to entities (company / sector / theme)

Shadow mode contract:
  This module is purely additive — it writes to Phase E0 tables ONLY.
  It never touches opportunities, signal_births, RE scores, TTL, or state
  transitions. E1 engines consume this data; decisions do not.
"""

from __future__ import annotations

import json
import logging
import sqlite3
import uuid
from datetime import datetime

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Valid canonical values
# ---------------------------------------------------------------------------

EVENT_TYPES = frozenset({
    "EARNINGS", "ORDER_WIN", "POLICY", "GUIDANCE",
    "CAPEX", "PROMOTER", "BULK", "OTHER",
})
MAGNITUDES   = frozenset({"HIGH", "MEDIUM", "LOW"})
DIRECTIONS   = frozenset({"POSITIVE", "NEGATIVE", "NEUTRAL"})
REL_TYPES    = frozenset({
    "SUPPLIER", "CUSTOMER", "PEER", "POLICY_BENEFICIARY", "SECTOR_LINKAGE",
})
LINK_TYPES   = frozenset({"PRIMARY", "SECONDARY", "DOWNSTREAM"})
ENTITY_TYPES = frozenset({"COMPANY", "SECTOR", "THEME"})


# ---------------------------------------------------------------------------
# Event ingestion
# ---------------------------------------------------------------------------

def ingest_event(
    conn: sqlite3.Connection,
    symbol: str,
    event_date: str,           # YYYY-MM-DD
    event_type: str,           # must be in EVENT_TYPES
    *,
    headline: str | None = None,
    magnitude: str = "MEDIUM",
    direction: str = "NEUTRAL",
    source: str | None = None,
    confidence: float = 0.5,
    raw_data: dict | None = None,
) -> str:
    """
    Insert a new event into daily_events.
    Returns the event_id (UUID).
    """
    if event_type not in EVENT_TYPES:
        raise ValueError(f"Unknown event_type '{event_type}'. Valid: {EVENT_TYPES}")
    if magnitude not in MAGNITUDES:
        raise ValueError(f"Unknown magnitude '{magnitude}'. Valid: {MAGNITUDES}")
    if direction not in DIRECTIONS:
        raise ValueError(f"Unknown direction '{direction}'. Valid: {DIRECTIONS}")
    if not (0.0 <= confidence <= 1.0):
        raise ValueError(f"confidence must be 0.0–1.0, got {confidence}")

    event_id = str(uuid.uuid4())
    conn.execute("""
        INSERT INTO daily_events
            (event_id, symbol, event_date, event_type, headline,
             magnitude, direction, source, confidence, raw_data,
             normalized_at, created_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,datetime('now'))
    """, (
        event_id, symbol.upper(), event_date, event_type, headline,
        magnitude, direction, source, confidence,
        json.dumps(raw_data) if raw_data else None,
        datetime.now().isoformat(timespec="seconds"),
    ))
    log.debug("[E0] ingest_event: %s %s %s %s", symbol, event_date, event_type, magnitude)
    return event_id


def get_events_for_symbol(
    conn: sqlite3.Connection,
    symbol: str,
    *,
    days_back: int = 30,
    event_type: str | None = None,
    min_magnitude: str | None = None,
) -> list[dict]:
    """
    Return events for a symbol within the last `days_back` calendar days.
    Optional filters: event_type, min_magnitude (HIGH > MEDIUM > LOW).
    """
    _MAG_RANK = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}
    rows = conn.execute("""
        SELECT * FROM daily_events
        WHERE symbol = ?
          AND date(event_date) >= date('now', ? || ' days')
        ORDER BY event_date DESC
    """, (symbol.upper(), f"-{days_back}")).fetchall()

    result = []
    for r in rows:
        d = dict(r)
        if event_type and d["event_type"] != event_type:
            continue
        if min_magnitude:
            if _MAG_RANK.get(d["magnitude"], 0) < _MAG_RANK.get(min_magnitude, 0):
                continue
        if d["raw_data"]:
            try:
                d["raw_data"] = json.loads(d["raw_data"])
            except (json.JSONDecodeError, TypeError):
                pass
        result.append(d)
    return result


def get_events_by_type(
    conn: sqlite3.Connection,
    event_type: str,
    *,
    from_date: str | None = None,
    to_date: str | None = None,
) -> list[dict]:
    """Return events of a given type optionally bounded by [from_date, to_date]."""
    q = "SELECT * FROM daily_events WHERE event_type = ?"
    params: list = [event_type]
    if from_date:
        q += " AND event_date >= ?"
        params.append(from_date)
    if to_date:
        q += " AND event_date <= ?"
        params.append(to_date)
    q += " ORDER BY event_date DESC"
    return [dict(r) for r in conn.execute(q, params).fetchall()]


# ---------------------------------------------------------------------------
# Company relationship ingestion
# ---------------------------------------------------------------------------

def ingest_relationship(
    conn: sqlite3.Connection,
    from_symbol: str,
    to_symbol: str,
    relationship_type: str,   # must be in REL_TYPES
    *,
    strength: float = 0.5,
    link_direction: str = "DIRECTIONAL",
    source: str | None = None,
    confidence: float = 0.5,
    last_verified: str | None = None,
) -> str:
    """
    Insert a company relationship. Returns relationship_id.
    Deduplication: same (from, to, type) updates strength and confidence
    rather than inserting a duplicate.
    """
    if relationship_type not in REL_TYPES:
        raise ValueError(f"Unknown relationship_type '{relationship_type}'.")
    if not (0.0 <= strength <= 1.0):
        raise ValueError(f"strength must be 0.0–1.0, got {strength}")
    if link_direction not in ("DIRECTIONAL", "BIDIRECTIONAL"):
        raise ValueError(f"link_direction must be DIRECTIONAL or BIDIRECTIONAL.")

    # Check for existing
    existing = conn.execute("""
        SELECT relationship_id FROM company_relationships
        WHERE from_symbol=? AND to_symbol=? AND relationship_type=? AND is_active=1
    """, (from_symbol.upper(), to_symbol.upper(), relationship_type)).fetchone()

    if existing:
        conn.execute("""
            UPDATE company_relationships
               SET strength=?, confidence=?, last_verified=?
             WHERE relationship_id=?
        """, (strength, confidence,
              last_verified or datetime.now().date().isoformat(),
              existing["relationship_id"]))
        return existing["relationship_id"]

    rel_id = str(uuid.uuid4())
    conn.execute("""
        INSERT INTO company_relationships
            (relationship_id, from_symbol, to_symbol, relationship_type,
             strength, link_direction, source, confidence, last_verified,
             is_active, created_at)
        VALUES (?,?,?,?,?,?,?,?,?,1,datetime('now'))
    """, (rel_id, from_symbol.upper(), to_symbol.upper(), relationship_type,
          strength, link_direction, source, confidence,
          last_verified or datetime.now().date().isoformat()))
    log.debug("[E0] ingest_relationship: %s -[%s]-> %s", from_symbol, relationship_type, to_symbol)
    return rel_id


def get_relationships_for_symbol(
    conn: sqlite3.Connection,
    symbol: str,
    *,
    direction: str = "FROM",       # "FROM" | "TO" | "BOTH"
    rel_type: str | None = None,
    min_strength: float = 0.0,
    max_hops: int = 1,
) -> list[dict]:
    """
    Return relationships involving `symbol`.
    direction="FROM"  → symbol is the source (e.g. HAL is supplier TO ...)
    direction="TO"    → symbol is the target (e.g. BEL receives FROM ...)
    direction="BOTH"  → either end
    max_hops=1 (direct only). For multi-hop use propagation_engine.
    """
    if direction == "FROM":
        cond = "from_symbol = ?"
    elif direction == "TO":
        cond = "to_symbol = ?"
    else:
        cond = "(from_symbol = ? OR to_symbol = ?)"

    params: list = [symbol.upper()]
    if direction == "BOTH":
        params = [symbol.upper(), symbol.upper()]

    q = f"""
        SELECT * FROM company_relationships
        WHERE {cond} AND is_active=1 AND strength >= ?
    """
    params.append(min_strength)
    if rel_type:
        q += " AND relationship_type = ?"
        params.append(rel_type)
    return [dict(r) for r in conn.execute(q, params).fetchall()]


# ---------------------------------------------------------------------------
# Knowledge graph metadata
# ---------------------------------------------------------------------------

def store_kg_metadata(
    conn: sqlite3.Connection,
    entity_type: str,     # COMPANY | SECTOR | THEME | POLICY
    entity_id: str,
    attribute: str,
    value: str,
    *,
    source: str | None = None,
    confidence: float = 0.5,
    last_verified: str | None = None,
    valid_from: str | None = None,
    valid_to: str | None = None,
) -> str:
    """
    Upsert a knowledge graph metadata entry.
    Returns metadata_id.
    """
    if entity_type not in {"COMPANY", "SECTOR", "THEME", "POLICY"}:
        raise ValueError(f"Unknown entity_type '{entity_type}'.")

    existing = conn.execute("""
        SELECT metadata_id FROM knowledge_graph_metadata
        WHERE entity_type=? AND entity_id=? AND attribute=?
    """, (entity_type, entity_id, attribute)).fetchone()

    if existing:
        conn.execute("""
            UPDATE knowledge_graph_metadata
               SET value=?, confidence=?, last_verified=?, valid_from=?, valid_to=?
             WHERE metadata_id=?
        """, (value, confidence,
              last_verified or datetime.now().date().isoformat(),
              valid_from, valid_to,
              existing["metadata_id"]))
        return existing["metadata_id"]

    meta_id = str(uuid.uuid4())
    conn.execute("""
        INSERT INTO knowledge_graph_metadata
            (metadata_id, entity_type, entity_id, attribute, value,
             source, confidence, last_verified, valid_from, valid_to,
             created_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,datetime('now'))
    """, (meta_id, entity_type, entity_id, attribute, value,
          source, confidence,
          last_verified or datetime.now().date().isoformat(),
          valid_from, valid_to))
    return meta_id


# ---------------------------------------------------------------------------
# Event-entity links
# ---------------------------------------------------------------------------

def link_event_to_entity(
    conn: sqlite3.Connection,
    event_id: str,
    entity_type: str,    # COMPANY | SECTOR | THEME
    entity_id: str,
    link_type: str,      # PRIMARY | SECONDARY | DOWNSTREAM
    *,
    impact_direction: str = "NEUTRAL",
    impact_magnitude: str = "MEDIUM",
) -> str:
    """
    Link an event to a company / sector / theme. Returns link_id.
    """
    if entity_type not in ENTITY_TYPES:
        raise ValueError(f"Unknown entity_type '{entity_type}'.")
    if link_type not in LINK_TYPES:
        raise ValueError(f"Unknown link_type '{link_type}'.")

    link_id = str(uuid.uuid4())
    conn.execute("""
        INSERT OR IGNORE INTO event_entity_links
            (link_id, event_id, entity_type, entity_id, link_type,
             impact_direction, impact_magnitude, created_at)
        VALUES (?,?,?,?,?,?,?,datetime('now'))
    """, (link_id, event_id, entity_type, entity_id, link_type,
          impact_direction, impact_magnitude))
    return link_id


def get_events_for_entity(
    conn: sqlite3.Connection,
    entity_type: str,
    entity_id: str,
    *,
    days_back: int = 30,
    link_type: str | None = None,
) -> list[dict]:
    """
    Return events linked to a given entity (company/sector/theme).
    Joins event_entity_links → daily_events.
    """
    q = """
        SELECT de.*, eel.link_type, eel.impact_direction, eel.impact_magnitude
        FROM event_entity_links eel
        JOIN daily_events de ON de.event_id = eel.event_id
        WHERE eel.entity_type = ?
          AND eel.entity_id   = ?
          AND date(de.event_date) >= date('now', ? || ' days')
    """
    params: list = [entity_type, entity_id, f"-{days_back}"]
    if link_type:
        q += " AND eel.link_type = ?"
        params.append(link_type)
    q += " ORDER BY de.event_date DESC"
    return [dict(r) for r in conn.execute(q, params).fetchall()]
