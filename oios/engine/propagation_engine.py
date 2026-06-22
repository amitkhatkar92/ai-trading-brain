"""
oios/engine/propagation_engine.py

Phase E1 (Shadow Mode) — Cause Propagation Engine.

For a given event on symbol A, this engine traces the company relationship
graph (max_hops hops) to find downstream symbols that have live opportunities.
It then computes a propagation score for those opportunities.

Example:
    HAL wins a defence contract (ORDER_WIN, POSITIVE, HIGH)
    HAL → SUPPLIER_TO → BEL → SUPPLIER_TO → Astra Microwave
    BEL receives propagation score; Astra Microwave receives 2-hop score.

Shadow mode contract (absolute):
  - NEVER modifies opportunities.conviction_score
  - NEVER modifies opportunities.re_score / effective_ttl_days
  - NEVER calls any state machine transition
  - All outputs go to propagation_paths and propagation_scores ONLY
"""

from __future__ import annotations

import json
import logging
import sqlite3
import uuid
from collections import deque
from datetime import date, timedelta

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_MAX_HOPS: int   = 2    # maximum hop depth when tracing propagation
_MIN_STRENGTH: float = 0.2  # minimum link strength to traverse
# Strength decay per hop (multiplicative)
_HOP_DECAY: float = 0.6
# Minimum final propagation score to bother storing
_MIN_PROP_SCORE: float = 0.5

# Event types that can propagate
_PROPAGATING_EVENT_TYPES = frozenset({
    "ORDER_WIN", "POLICY", "EARNINGS", "GUIDANCE", "CAPEX",
})

# Relationship types that carry propagation
_PROPAGATING_REL_TYPES = frozenset({
    "SUPPLIER", "CUSTOMER", "PEER", "POLICY_BENEFICIARY", "SECTOR_LINKAGE",
})


# ---------------------------------------------------------------------------
# Path building
# ---------------------------------------------------------------------------

def build_propagation_paths(
    conn: sqlite3.Connection,
    source_event_id: str,
    source_symbol: str,
    *,
    max_hops: int = _MAX_HOPS,
    min_strength: float = _MIN_STRENGTH,
) -> list[str]:
    """
    BFS from source_symbol through company_relationships.
    For each reachable (symbol, path) within max_hops, insert a propagation_paths row.

    Returns list of path_ids created.
    """
    path_ids: list[str] = []

    # BFS: queue item = (symbol, hops, strength_product, path_so_far, rel_chain)
    visited: set[str] = {source_symbol.upper()}
    queue: deque[tuple[str, int, float, list[str], list[str]]] = deque()
    queue.append((source_symbol.upper(), 0, 1.0, [source_symbol.upper()], []))

    while queue:
        current_sym, hops, strength_prod, path, rel_chain = queue.popleft()

        if hops >= max_hops:
            continue

        # Fetch direct relationships FROM current_sym
        rels = conn.execute("""
            SELECT to_symbol, relationship_type, strength
            FROM company_relationships
            WHERE from_symbol = ? AND is_active = 1
              AND strength >= ? AND relationship_type IN ({})
        """.format(",".join("?" * len(_PROPAGATING_REL_TYPES))),
            [current_sym, min_strength, *_PROPAGATING_REL_TYPES]
        ).fetchall()

        # Also BIDIRECTIONAL relationships where current_sym is the "to" side
        rels_bi = conn.execute("""
            SELECT from_symbol AS to_symbol, relationship_type, strength
            FROM company_relationships
            WHERE to_symbol = ? AND is_active = 1 AND link_direction = 'BIDIRECTIONAL'
              AND strength >= ? AND relationship_type IN ({})
        """.format(",".join("?" * len(_PROPAGATING_REL_TYPES))),
            [current_sym, min_strength, *_PROPAGATING_REL_TYPES]
        ).fetchall()

        for rel in list(rels) + list(rels_bi):
            target = rel["to_symbol"]
            if target in visited:
                continue
            visited.add(target)

            new_strength = round(strength_prod * rel["strength"] * _HOP_DECAY, 4)
            if new_strength < _MIN_STRENGTH * (_HOP_DECAY ** hops):
                continue

            new_path = path + [target]
            new_chain = rel_chain + [rel["relationship_type"]]
            new_hops  = hops + 1

            # Insert path record
            path_id = str(uuid.uuid4())
            conn.execute("""
                INSERT OR IGNORE INTO propagation_paths
                    (path_id, source_event_id, source_symbol, target_symbol,
                     path_hops, path_description, relationship_chain,
                     strength_product, computed_at)
                VALUES (?,?,?,?,?,?,?,?,datetime('now'))
            """, (
                path_id, source_event_id, source_symbol.upper(), target,
                new_hops,
                json.dumps(new_path),
                json.dumps(new_chain),
                new_strength,
            ))
            path_ids.append(path_id)

            # Enqueue for deeper traversal
            queue.append((target, new_hops, new_strength, new_path, new_chain))

    return path_ids


# ---------------------------------------------------------------------------
# Propagation score computation
# ---------------------------------------------------------------------------

def _base_prop_score(event: dict, strength_product: float) -> float:
    """
    Derive a propagation score for a downstream opportunity.
    Formula: event_raw_score × direction_mult × magnitude_mult × strength_product × 10
    Capped at 10.
    """
    _ET_BASE = {
        "ORDER_WIN": 0.8, "POLICY": 0.7, "EARNINGS": 0.65,
        "GUIDANCE": 0.60, "CAPEX": 0.55,
    }
    _DIR_MULT = {"POSITIVE": 1.0, "NEUTRAL": 0.5, "NEGATIVE": 0.2}
    _MAG_MULT = {"HIGH": 1.0, "MEDIUM": 0.7, "LOW": 0.4}

    base = _ET_BASE.get(event.get("event_type", ""), 0.4)
    d    = _DIR_MULT.get(event.get("direction", "NEUTRAL"), 0.5)
    m    = _MAG_MULT.get(event.get("magnitude", "MEDIUM"), 0.7)
    ev_c = float(event.get("confidence", 0.5))

    raw  = base * d * m * ev_c * strength_product
    return min(10.0, round(raw * 10.0, 4))


def compute_propagation_scores_for_event(
    conn: sqlite3.Connection,
    source_event_id: str,
    source_symbol: str,
    today: str,
    *,
    max_hops: int = _MAX_HOPS,
) -> dict:
    """
    For a given source event:
      1. Build propagation paths from source_symbol
      2. For each path's target_symbol, check if there's a live opportunity
      3. Compute propagation_score for that opportunity
      4. Persist to propagation_scores

    Returns summary dict.
    """
    event = conn.execute(
        "SELECT * FROM daily_events WHERE event_id = ?", (source_event_id,)
    ).fetchone()
    if not event:
        return {"error": f"Event {source_event_id} not found"}

    event_dict = dict(event)
    if event_dict.get("event_type") not in _PROPAGATING_EVENT_TYPES:
        return {"skipped": True, "reason": "non-propagating event type"}

    # Build paths
    path_ids = build_propagation_paths(
        conn, source_event_id, source_symbol, max_hops=max_hops
    )

    # Score downstream opportunities
    scored = 0
    for path_id in path_ids:
        path_row = conn.execute(
            "SELECT * FROM propagation_paths WHERE path_id=?", (path_id,)
        ).fetchone()
        if not path_row:
            continue
        target_sym = path_row["target_symbol"]
        strength   = path_row["strength_product"]

        # Find live opportunities for target symbol
        opps = conn.execute("""
            SELECT opportunity_id FROM opportunities
            WHERE symbol = ? AND current_state IN ('ACTIVE', 'WATCHING', 'DISCOVERED')
        """, (target_sym,)).fetchall()

        for opp_row in opps:
            oid         = opp_row[0]
            prop_score  = _base_prop_score(event_dict, strength)

            if prop_score < _MIN_PROP_SCORE:
                continue

            conn.execute("""
                INSERT INTO propagation_scores
                    (prop_score_id, opportunity_id, source_event_id, path_id,
                     propagation_score, decay_factor, score_date, computed_at)
                VALUES (?,?,?,?,?,?,?,datetime('now'))
                ON CONFLICT(opportunity_id, source_event_id, score_date) DO UPDATE SET
                    propagation_score = MAX(excluded.propagation_score, propagation_score),
                    computed_at       = excluded.computed_at
            """, (
                str(uuid.uuid4()), oid, source_event_id, path_id,
                prop_score, strength, today,
            ))
            scored += 1

    log.debug("[E1] prop_engine: event %s → %d paths, %d opps scored",
              source_event_id, len(path_ids), scored)
    return {"paths_built": len(path_ids), "opportunities_scored": scored}


def run_propagation_cycle(
    conn: sqlite3.Connection,
    today: str,
    *,
    lookback_days: int = 7,
) -> dict:
    """
    Daily propagation cycle:
      For each high-confidence event in the last `lookback_days`:
        compute_propagation_scores_for_event()

    Returns summary.
    """
    window_start = (date.fromisoformat(today) - timedelta(days=lookback_days)).isoformat()

    events = conn.execute("""
        SELECT event_id, symbol, event_type, confidence
        FROM daily_events
        WHERE event_date >= ? AND event_date <= ?
          AND event_type IN ({})
          AND confidence >= 0.4
        ORDER BY event_date DESC
    """.format(",".join("?" * len(_PROPAGATING_EVENT_TYPES))),
        [window_start, today, *_PROPAGATING_EVENT_TYPES]
    ).fetchall()

    total_paths  = 0
    total_scored = 0

    for ev in events:
        try:
            result = compute_propagation_scores_for_event(
                conn, ev["event_id"], ev["symbol"], today
            )
            total_paths  += result.get("paths_built", 0)
            total_scored += result.get("opportunities_scored", 0)
        except Exception:
            log.exception("[E1] propagation error for event %s", ev["event_id"])

    return {
        "events_processed":      len(events),
        "paths_built":           total_paths,
        "opportunities_scored":  total_scored,
    }


def get_propagation_score_for_opportunity(
    conn: sqlite3.Connection,
    opportunity_id: str,
    score_date: str,
) -> float:
    """
    Return the best (max) propagation score for an opportunity on a given date.
    Returns 0.0 if none found.
    """
    row = conn.execute("""
        SELECT MAX(propagation_score) AS best
        FROM propagation_scores
        WHERE opportunity_id = ? AND score_date = ?
    """, (opportunity_id, score_date)).fetchone()
    return float(row["best"]) if row and row["best"] is not None else 0.0
