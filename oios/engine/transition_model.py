"""
oios/engine/transition_model.py

Sub-E: Transition Probability Model.
Layer 5, Phase D.

Builds Markov transition probability estimates for every (archetype, regime) pair.

Dormant per pair until signal_state_transitions contains >= 20
WATCHING→(ACTIVE|INVALID) sequences for that pair. Below threshold, fixed
regime-level priors apply (MAS_v1.2.md Section 5, Layer 5 Sub-E).

Shadow mode discipline:
    This module is read-only during shadow mode. It populates
    transition_probability_cache and serves probability estimates, but those
    estimates are NOT used to modify Phase C's deterministic state machine.
    They are diagnostic outputs only until Phase D shadow period completes.
"""

from __future__ import annotations
import logging
import sqlite3
from datetime import date
from typing import Optional

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# MAS_v1.2.md regime-level priors (Section 5, Layer 5 Sub-E)
# ---------------------------------------------------------------------------

_WATCHING_PRIORS: dict[str, dict[str, float]] = {
    "BULL":  {"to_active": 0.45, "to_invalid": 0.30},
    "RANGE": {"to_active": 0.28, "to_invalid": 0.48},
    "BEAR":  {"to_active": 0.20, "to_invalid": 0.58},
    "PANIC": {"to_active": 0.08, "to_invalid": 0.80},
}
_DEFAULT_PRIOR = {"to_active": 0.28, "to_invalid": 0.48}  # fallback = RANGE

# Active→WATCHING priors (complementary — empirically derived from replay)
_ACTIVE_PRIORS: dict[str, dict[str, float]] = {
    "BULL":  {"to_watching": 0.15, "to_invalid": 0.20},
    "RANGE": {"to_watching": 0.25, "to_invalid": 0.35},
    "BEAR":  {"to_watching": 0.30, "to_invalid": 0.45},
    "PANIC": {"to_watching": 0.40, "to_invalid": 0.55},
}

# Minimum WATCHING→(ACTIVE|INVALID) sequences before switching to empirical
MIN_EMPIRICAL_OBS = 20

# Normalize MAS regime labels to the prior table keys
_REGIME_LABEL_MAP = {
    "TRENDING_UP": "BULL", "BULL": "BULL",
    "SIDEWAYS": "RANGE", "RANGE": "RANGE",
    "TRENDING_DOWN": "BEAR", "BEAR": "BEAR",
    "PANIC": "PANIC", "CRISIS": "PANIC",
}


def _normalize_regime(regime: str) -> str:
    return _REGIME_LABEL_MAP.get(regime.upper(), "RANGE")


# ---------------------------------------------------------------------------
# Empirical probability computation
# ---------------------------------------------------------------------------

def _compute_empirical(
    conn: sqlite3.Connection,
    archetype_id: str,
    regime_norm: str,
) -> Optional[dict]:
    """
    Compute empirical transition probabilities from signal_state_transitions.
    Only called when observation count >= MIN_EMPIRICAL_OBS.

    Returns None if insufficient data.
    """
    # Count WATCHING→ACTIVE and WATCHING→INVALID for this archetype×regime
    rows = conn.execute("""
        SELECT sst.to_state, COUNT(*) AS cnt
        FROM signal_state_transitions sst
        JOIN signal_births sb ON sb.signal_id = sst.signal_id
        WHERE sst.from_state = 'WATCHING'
          AND sst.to_state IN ('ACTIVE', 'INVALID')
          AND sb.archetype_id = ?
          AND sst.regime_at_transition = ?
        GROUP BY sst.to_state
    """, (archetype_id, regime_norm)).fetchall()

    counts = {r["to_state"]: r["cnt"] for r in rows}
    total_watching = sum(counts.values())
    if total_watching < MIN_EMPIRICAL_OBS:
        return None

    p_wa = counts.get("ACTIVE", 0) / total_watching
    p_wi = counts.get("INVALID", 0) / total_watching

    # ACTIVE→WATCHING and ACTIVE→INVALID
    rows2 = conn.execute("""
        SELECT sst.to_state, COUNT(*) AS cnt
        FROM signal_state_transitions sst
        JOIN signal_births sb ON sb.signal_id = sst.signal_id
        WHERE sst.from_state = 'ACTIVE'
          AND sst.to_state IN ('WATCHING', 'INVALID')
          AND sb.archetype_id = ?
          AND sst.regime_at_transition = ?
        GROUP BY sst.to_state
    """, (archetype_id, regime_norm)).fetchall()

    counts2 = {r["to_state"]: r["cnt"] for r in rows2}
    total_active = sum(counts2.values())
    p_aw = counts2.get("WATCHING", 0) / total_active if total_active else 0.0
    p_ai = counts2.get("INVALID", 0) / total_active if total_active else 0.0

    return {
        "observation_count":      total_watching,
        "is_empirical":           True,
        "p_watching_to_active":   round(p_wa, 4),
        "p_watching_to_invalid":  round(p_wi, 4),
        "p_active_to_watching":   round(p_aw, 4),
        "p_active_to_invalid":    round(p_ai, 4),
    }


def _prior_dict(regime_norm: str) -> dict:
    watch = _WATCHING_PRIORS.get(regime_norm, _DEFAULT_PRIOR)
    active = _ACTIVE_PRIORS.get(regime_norm, {"to_watching": 0.25, "to_invalid": 0.35})
    return {
        "observation_count":      0,
        "is_empirical":           False,
        "p_watching_to_active":   watch["to_active"],
        "p_watching_to_invalid":  watch["to_invalid"],
        "p_active_to_watching":   active["to_watching"],
        "p_active_to_invalid":    active["to_invalid"],
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_transition_probability(
    conn: sqlite3.Connection,
    archetype_id: str,
    regime: str,
) -> dict:
    """
    Return transition probability dict for the given (archetype, regime).

    Result is served from transition_probability_cache if it was populated
    today. Otherwise recomputed, cached, and returned.

    Keys:
        p_watching_to_active, p_watching_to_invalid,
        p_active_to_watching, p_active_to_invalid,
        observation_count, is_empirical
    """
    regime_norm = _normalize_regime(regime)
    today_str   = date.today().isoformat()

    # Try cache first
    cached = conn.execute("""
        SELECT * FROM transition_probability_cache
        WHERE archetype_id = ? AND regime = ? AND computed_at = ?
        ORDER BY computed_at DESC LIMIT 1
    """, (archetype_id, regime_norm, today_str)).fetchone()

    if cached:
        return {
            "p_watching_to_active":  cached["p_watching_to_active"],
            "p_watching_to_invalid": cached["p_watching_to_invalid"],
            "p_active_to_watching":  cached["p_active_to_watching"],
            "p_active_to_invalid":   cached["p_active_to_invalid"],
            "observation_count":     cached["observation_count"],
            "is_empirical":          bool(cached["is_empirical"]),
        }

    # Compute
    empirical = _compute_empirical(conn, archetype_id, regime_norm)
    result    = empirical if empirical else _prior_dict(regime_norm)

    # Cache
    conn.execute("""
        INSERT OR REPLACE INTO transition_probability_cache
            (archetype_id, regime, computed_at, observation_count, is_empirical,
             p_watching_to_active, p_watching_to_invalid,
             p_active_to_watching, p_active_to_invalid)
        VALUES (?,?,?,?,?,?,?,?,?)
    """, (
        archetype_id, regime_norm, today_str,
        result["observation_count"], 1 if result["is_empirical"] else 0,
        result["p_watching_to_active"], result["p_watching_to_invalid"],
        result["p_active_to_watching"], result["p_active_to_invalid"],
    ))

    return result


def refresh_transition_cache(conn: sqlite3.Connection, today: str) -> int:
    """
    Recompute transition probabilities for all active archetypes and cache.
    Call weekly after archetype_outcome_distributions update.

    Returns number of (archetype, regime) pairs refreshed.
    """
    archetypes = conn.execute(
        "SELECT DISTINCT archetype_id FROM signal_births"
    ).fetchall()

    regimes = ["BULL", "RANGE", "BEAR", "PANIC"]
    refreshed = 0

    for arch_row in archetypes:
        archetype_id = arch_row["archetype_id"] if isinstance(arch_row, sqlite3.Row) else arch_row[0]
        for regime_norm in regimes:
            empirical = _compute_empirical(conn, archetype_id, regime_norm)
            result    = empirical if empirical else _prior_dict(regime_norm)

            conn.execute("""
                INSERT OR REPLACE INTO transition_probability_cache
                    (archetype_id, regime, computed_at, observation_count, is_empirical,
                     p_watching_to_active, p_watching_to_invalid,
                     p_active_to_watching, p_active_to_invalid)
                VALUES (?,?,?,?,?,?,?,?,?)
            """, (
                archetype_id, regime_norm, today,
                result["observation_count"], 1 if result["is_empirical"] else 0,
                result["p_watching_to_active"], result["p_watching_to_invalid"],
                result["p_active_to_watching"], result["p_active_to_invalid"],
            ))
            refreshed += 1

    log.info("[TransitionModel] Refreshed %d (archetype, regime) pairs on %s", refreshed, today)
    return refreshed
