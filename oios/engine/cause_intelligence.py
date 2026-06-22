"""
oios/engine/cause_intelligence.py

Phase E1 (Shadow Mode) — Cause Intelligence Engine.

For every opportunity, this engine:
  1. Identifies candidate causes by matching recent daily_events for the symbol
     against the opportunity's birth date and signal type.
  2. Ranks candidates by confidence.
  3. Stores results in opportunity_causes (one row per candidate).
  4. Computes a composite cause_score (0–10) stored in cause_scores.

Shadow mode contract (absolute, non-negotiable):
  - This module NEVER modifies opportunities.conviction_score
  - This module NEVER modifies opportunities.re_score
  - This module NEVER modifies opportunities.effective_ttl_days
  - This module NEVER calls state machine transitions
  - All outputs land in cause_scores and opportunity_causes ONLY
  - The shadow OS (cause-augmented score) is written by shadow_scorer.py
"""

from __future__ import annotations

import json
import logging
import sqlite3
import uuid
from datetime import date, timedelta

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# How many calendar days before the opportunity birth date to look back for causes
_LOOKBACK_DAYS = 30

# Scoring weights by event type and direction
_EVENT_TYPE_BASE_SCORE: dict[str, float] = {
    "ORDER_WIN":  8.0,
    "EARNINGS":   7.0,
    "GUIDANCE":   6.5,
    "CAPEX":      5.5,
    "POLICY":     5.0,
    "PROMOTER":   4.5,
    "BULK":       4.0,
    "OTHER":      3.0,
}
_DIRECTION_MULTIPLIER: dict[str, float] = {
    "POSITIVE": 1.0,
    "NEUTRAL":  0.5,
    "NEGATIVE": 0.0,  # negative-direction events don't cause LONG opportunities
}
_MAGNITUDE_MULTIPLIER: dict[str, float] = {
    "HIGH":   1.0,
    "MEDIUM": 0.70,
    "LOW":    0.40,
}
# Recency decay: events older than 15 days get a 0.6x multiplier
_RECENCY_CUTOFF_DAYS = 15
_RECENCY_DECAY = 0.6


def _cause_confidence(event: dict, opp_direction: str) -> float:
    """
    Compute a [0, 1] confidence that this event caused the opportunity.
    Formula: base_score/10 * direction_mult * magnitude_mult * [recency_decay]
    For SHORT opportunities, direction multipliers are inverted.
    """
    base   = _EVENT_TYPE_BASE_SCORE.get(event["event_type"], 3.0) / 10.0
    dir_   = event.get("direction", "NEUTRAL")
    mag_   = event.get("magnitude", "MEDIUM")

    # For SHORT opps, NEGATIVE events are the cause
    if opp_direction == "SHORT":
        dir_mult = _DIRECTION_MULTIPLIER.get(
            "POSITIVE" if dir_ == "NEGATIVE" else
            ("NEGATIVE" if dir_ == "POSITIVE" else "NEUTRAL"),
            0.5
        )
    else:
        dir_mult = _DIRECTION_MULTIPLIER.get(dir_, 0.5)

    mag_mult = _MAGNITUDE_MULTIPLIER.get(mag_, 0.70)

    # Incorporate event's own confidence
    ev_conf = float(event.get("confidence", 0.5))

    score = base * dir_mult * mag_mult * ev_conf
    return min(1.0, score)


def _recency_factor(event_date_str: str, opp_birth_str: str) -> float:
    """Return 1.0 if within cutoff, else _RECENCY_DECAY."""
    try:
        ev_date  = date.fromisoformat(event_date_str)
        opp_date = date.fromisoformat(opp_birth_str)
        delta = (opp_date - ev_date).days
        return _RECENCY_DECAY if delta > _RECENCY_CUTOFF_DAYS else 1.0
    except (ValueError, TypeError):
        return 1.0


def identify_causes_for_opportunity(
    conn: sqlite3.Connection,
    opportunity_id: str,
    today: str,  # ISO-8601 date (used as computation timestamp)
) -> list[dict]:
    """
    Query daily_events for the opportunity's symbol within the lookback window,
    score each event as a potential cause, and persist results to
    opportunity_causes.

    Returns list of cause dicts (ranked, highest confidence first).
    Already-computed causes (same opportunity) are deleted before re-computing
    so this function is safe to call multiple times (re-compute on demand).
    """
    # Fetch opportunity details
    opp = conn.execute("""
        SELECT opportunity_id, symbol, direction, created_at
        FROM opportunities WHERE opportunity_id = ?
    """, (opportunity_id,)).fetchone()
    if not opp:
        log.warning("[E1] identify_causes: unknown opportunity %s", opportunity_id)
        return []

    symbol      = opp["symbol"]
    direction   = opp["direction"]
    birth_date  = opp["created_at"][:10]

    # Lookback window
    try:
        birth_dt = date.fromisoformat(birth_date)
    except ValueError:
        log.warning("[E1] identify_causes: bad created_at '%s'", birth_date)
        return []
    window_start = (birth_dt - timedelta(days=_LOOKBACK_DAYS)).isoformat()

    # Fetch candidate events
    events = conn.execute("""
        SELECT * FROM daily_events
        WHERE symbol = ? AND event_date >= ? AND event_date <= ?
        ORDER BY event_date DESC
    """, (symbol, window_start, birth_date)).fetchall()

    if not events:
        return []

    # Score each event
    candidates: list[dict] = []
    for ev in events:
        ev_dict = dict(ev)
        conf = _cause_confidence(ev_dict, direction)
        rec  = _recency_factor(ev_dict["event_date"], birth_date)
        final_conf = round(conf * rec, 4)
        if final_conf < 0.05:
            continue  # skip negligible candidates
        candidates.append({
            "event_id":    ev_dict["event_id"],
            "cause_type":  "DIRECT",
            "cause_description": f"{ev_dict['event_type']} ({ev_dict['direction']}, {ev_dict['magnitude']}) on {ev_dict['event_date']}",
            "confidence":  final_conf,
        })

    # Sort by confidence descending, assign ranks
    candidates.sort(key=lambda x: x["confidence"], reverse=True)
    for rank, c in enumerate(candidates, start=1):
        c["rank"] = rank

    # Persist — delete stale rows first
    with conn:
        conn.execute(
            "DELETE FROM opportunity_causes WHERE opportunity_id = ?",
            (opportunity_id,)
        )
        for c in candidates:
            conn.execute("""
                INSERT INTO opportunity_causes
                    (cause_id, opportunity_id, event_id, cause_type,
                     cause_description, confidence, rank, computed_at)
                VALUES (?,?,?,?,?,?,?,datetime('now'))
            """, (str(uuid.uuid4()), opportunity_id, c["event_id"],
                  c["cause_type"], c["cause_description"],
                  c["confidence"], c["rank"]))

    log.debug("[E1] identify_causes: %s → %d causes", opportunity_id, len(candidates))
    return candidates


def compute_cause_score(
    conn: sqlite3.Connection,
    opportunity_id: str,
    today: str,
) -> dict:
    """
    Aggregate ranked causes into a composite cause_score in [0, 10].

    Algorithm:
      - Primary cause (rank=1) contributes at full weight
      - Each subsequent cause contributes at diminishing weight: 0.5^(rank-1)
      - Raw sum is capped and scaled to [0, 10]
      - Persisted to cause_scores (UNIQUE on opportunity_id, score_date)

    Returns the score dict (same shape as cause_scores row).
    Shadow mode: never writes to opportunities table.
    """
    causes = conn.execute("""
        SELECT * FROM opportunity_causes
        WHERE opportunity_id = ?
        ORDER BY rank ASC
    """, (opportunity_id,)).fetchall()

    if not causes:
        # No causes → score of 0, but still record the observation
        score_dict = {
            "opportunity_id":          opportunity_id,
            "score_date":              today,
            "cause_score":             0.0,
            "cause_count":             0,
            "primary_cause_type":      None,
            "primary_cause_confidence": None,
            "evidence_summary":        None,
        }
    else:
        causes_list = [dict(c) for c in causes]
        weighted_sum = sum(
            c["confidence"] * (0.5 ** (c["rank"] - 1))
            for c in causes_list
        )
        # Scale: max achievable ≈ 1.0 (rank-1 at conf=1.0); cap at 10
        cause_score = min(10.0, round(weighted_sum * 10.0, 4))
        primary     = causes_list[0]
        score_dict  = {
            "opportunity_id":           opportunity_id,
            "score_date":               today,
            "cause_score":              cause_score,
            "cause_count":              len(causes_list),
            "primary_cause_type":       primary["cause_type"],
            "primary_cause_confidence": primary["confidence"],
            "evidence_summary": json.dumps([
                {"rank": c["rank"], "confidence": c["confidence"],
                 "description": c["cause_description"]}
                for c in causes_list[:5]   # top-5 for summary
            ]),
        }

    # Upsert (UNIQUE on opportunity_id, score_date)
    conn.execute("""
        INSERT INTO cause_scores
            (score_id, opportunity_id, score_date, cause_score,
             cause_count, primary_cause_type, primary_cause_confidence,
             evidence_summary, computed_at)
        VALUES (?,?,?,?,?,?,?,?,datetime('now'))
        ON CONFLICT(opportunity_id, score_date) DO UPDATE SET
            cause_score              = excluded.cause_score,
            cause_count              = excluded.cause_count,
            primary_cause_type       = excluded.primary_cause_type,
            primary_cause_confidence = excluded.primary_cause_confidence,
            evidence_summary         = excluded.evidence_summary,
            computed_at              = excluded.computed_at
    """, (
        str(uuid.uuid4()),
        score_dict["opportunity_id"], score_dict["score_date"],
        score_dict["cause_score"], score_dict["cause_count"],
        score_dict["primary_cause_type"], score_dict["primary_cause_confidence"],
        score_dict["evidence_summary"],
    ))
    return score_dict


def run_cause_cycle(
    conn: sqlite3.Connection,
    today: str,
) -> dict:
    """
    Daily cause intelligence cycle:
      1. For every ACTIVE / WATCHING opportunity:
         a. identify_causes_for_opportunity()
         b. compute_cause_score()
      2. Returns summary: {processed, with_causes, avg_cause_score}

    Shadow mode: no modifications to any Phase A–D table.
    """
    opps = conn.execute("""
        SELECT opportunity_id FROM opportunities
        WHERE current_state IN ('ACTIVE', 'WATCHING', 'DISCOVERED')
    """).fetchall()

    processed     = 0
    with_causes   = 0
    score_sum     = 0.0

    for row in opps:
        oid = row[0]
        try:
            causes = identify_causes_for_opportunity(conn, oid, today)
            sd = compute_cause_score(conn, oid, today)
            processed  += 1
            if causes:
                with_causes += 1
            score_sum += sd["cause_score"] or 0.0
        except Exception:
            log.exception("[E1] cause_cycle error for opp %s", oid)

    return {
        "processed":        processed,
        "with_causes":      with_causes,
        "avg_cause_score":  round(score_sum / processed, 4) if processed else 0.0,
    }
