"""
oios/engine/adaptive_intelligence.py

Layer 6: Adaptive Intelligence — Shadow Mode.
Phase D.

SHADOW MODE CONTRACT (non-negotiable):
    This module may OBSERVE, ANALYZE, COMPUTE, RECOMMEND, and RECORD.
    It may NOT MODIFY, APPLY, RECALIBRATE, RETIRE, or ACTIVATE any parameter.

    ALL output goes to pending_adjustments only.
    pending_adjustments rows with status='PENDING' sit until human /approve or /reject.
    No runtime parameter is touched.

Proposal types (per MAS_v1.2.md pending_adjustments.adjustment_type):
    TTL_CHANGE       — extend or shorten expected_ttl_days for an archetype
    HALF_LIFE_CHANGE — adjust the RE decay half-life multiplier
    WEIGHT_CHANGE    — adjust evidence weight for signal type
    ARCHETYPE_RETIRE — mark archetype for retirement (requires_approval=TRUE always)

Guardrails (all mandatory, from MAS_v1.2.md Layer 6):
    TTL floor:   1A = 5d, 1B = 8d, 1.5 = 14d
    Max TTL change per cycle:        ±20%
    Max half-life change per cycle:  ±20%
    Max weight change per cycle:     ±15%
    Max one proposal per parameter per calendar quarter
    Minimum observation_count_weighted >= 30 before any proposal

Retirement conditions (all required simultaneously):
    observation_count_weighted >= 50
    win_rate < 0.35
    Consistent underperformance across >= 2 distinct regime periods
    requires_approval = TRUE (always)
"""

from __future__ import annotations
import json
import logging
import sqlite3
import uuid
from datetime import date, timedelta
from typing import Optional

from .shadow_mode import (
    SHADOW_MODE,
    MIN_OBS_FOR_PROPOSAL,
    TTL_FLOORS,
    MAX_TTL_CHANGE_PCT,
    MAX_WEIGHT_CHANGE_PCT,
    MAX_HL_CHANGE_PCT,
    PROPOSAL_TTL_DAYS,
)
from .counterfactual_engine import run_cf1_ttl_sensitivity, run_cf4_hold_duration_sensitivity
from ..engine.re_calculator import BASE_HALF_LIFE, HALF_LIFE_MULTIPLIERS

log = logging.getLogger(__name__)

# Retirement thresholds (MAS_v1.2.md Layer 1A archetype retirement conditions)
_RETIRE_WIN_RATE_THRESHOLD    = 0.35
_RETIRE_MIN_OBS               = 50.0
_RETIRE_MIN_REGIMES           = 2

# Weight baseline defaults per signal_type
_DEFAULT_WEIGHTS: dict[str, float] = {
    "1B":  1.00,
    "3":   0.70,
    "1A":  0.80,
    "1.5": 0.60,
    "2":   0.50,
}


# ---------------------------------------------------------------------------
# Quarter check — one proposal per (archetype, regime, type) per quarter
# ---------------------------------------------------------------------------

def _already_proposed_this_quarter(
    conn: sqlite3.Connection,
    archetype_id: str,
    regime: Optional[str],
    adj_type: str,
    today: str,
) -> bool:
    """True if an active/approved/applied proposal already exists this calendar quarter."""
    t = date.fromisoformat(today)
    quarter_start = date(t.year, ((t.month - 1) // 3) * 3 + 1, 1)

    count = conn.execute("""
        SELECT COUNT(*) FROM pending_adjustments
        WHERE archetype_id = ?
          AND adjustment_type = ?
          AND (regime IS NULL OR regime = ? OR ? IS NULL)
          AND proposed_at >= ?
          AND status IN ('PENDING', 'APPROVED', 'AUTO_APPLIED')
    """, (archetype_id, adj_type,
          regime, regime,
          quarter_start.isoformat())).fetchone()[0]
    return count > 0


# ---------------------------------------------------------------------------
# Core proposal writer
# ---------------------------------------------------------------------------

def _write_proposal(
    conn: sqlite3.Connection,
    archetype_id: str,
    regime: Optional[str],
    adj_type: str,
    current_value: float,
    proposed_value: float,
    evidence: dict,
    obs_count: Optional[int],
    win_rate_current: Optional[float],
    win_rate_projected: Optional[float],
    requires_approval: bool,
    today: str,
) -> str:
    """
    Write one proposal row to pending_adjustments.

    Always writes status='PENDING'. Shadow mode means no AUTO_APPLIED path exists.
    """
    adj_id     = str(uuid.uuid4())
    change_pct = (proposed_value - current_value) / current_value if current_value != 0 else 0.0
    expires    = (date.fromisoformat(today) + timedelta(days=PROPOSAL_TTL_DAYS)).isoformat()

    conn.execute("""
        INSERT INTO pending_adjustments (
            adjustment_id, proposed_at, archetype_id, regime, adjustment_type,
            current_value, proposed_value, change_pct, evidence_summary,
            observation_count, win_rate_current, win_rate_projected,
            status, requires_approval, expires_at
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,'PENDING',?,?)
    """, (
        adj_id, today, archetype_id, regime, adj_type,
        round(current_value, 4), round(proposed_value, 4), round(change_pct, 4),
        json.dumps(evidence, default=str),
        obs_count, win_rate_current, win_rate_projected,
        1 if requires_approval else 0,
        expires,
    ))

    log.info(
        "[Layer6] Proposal written: %s %s regime=%s type=%s current=%.3f proposed=%.3f",
        adj_id, archetype_id, regime, adj_type, current_value, proposed_value
    )
    return adj_id


# ---------------------------------------------------------------------------
# TTL proposals
# ---------------------------------------------------------------------------

def _propose_ttl_for_pair(
    conn: sqlite3.Connection,
    archetype_id: str,
    regime: str,
    dist: sqlite3.Row,
    cf1: dict,
    cf4: dict,
    today: str,
) -> Optional[str]:
    """
    Evaluate whether a TTL adjustment is warranted for one (archetype, regime) pair.

    Logic:
        EXTEND if:  CF-1 shows > 30% of TTL_EXHAUSTED peaked late
                    AND current TTL is above floor × 1.20 (room to adjust)
        SHORTEN if: CF-4 shows median utilization < 0.50
                    AND win_rate is healthy (>= 0.45)

    Returns adjustment_id if a proposal was written, else None.
    """
    obs_w = dist["observation_count_weighted"] or 0.0
    if obs_w < MIN_OBS_FOR_PROPOSAL:
        return None

    if _already_proposed_this_quarter(conn, archetype_id, regime, "TTL_CHANGE", today):
        return None

    # Determine current TTL from signal_births median
    ttl_row = conn.execute("""
        SELECT AVG(expected_ttl_days) AS avg_ttl
        FROM signal_births
        WHERE archetype_id = ? AND regime_at_birth = ?
          AND final_state IS NOT NULL
    """, (archetype_id, regime)).fetchone()
    current_ttl = ttl_row["avg_ttl"] if ttl_row and ttl_row["avg_ttl"] else None
    if current_ttl is None or current_ttl <= 0:
        return None

    # Signal-type for floor lookup
    sb_type = conn.execute(
        "SELECT signal_type FROM signal_births WHERE archetype_id = ? LIMIT 1",
        (archetype_id,)
    ).fetchone()
    sig_type = sb_type["signal_type"] if sb_type else "1A"
    floor = TTL_FLOORS.get(sig_type, 5)

    win_rate = dist["win_rate"] or 0.0
    cf4_arch = cf4.get("by_archetype", {}).get(archetype_id, {})
    util = cf4_arch.get("median_utilization") or 0.5

    proposed = None
    direction = None

    # Extension trigger
    arch_cf1 = cf1.get("by_archetype", {}).get(archetype_id, {})
    late_peak_pct = (arch_cf1.get("late_peak", 0) / arch_cf1.get("total", 1)
                     if arch_cf1.get("total", 0) > 0 else 0.0)
    if late_peak_pct >= 0.30:
        proposed_ttl = min(current_ttl * (1 + MAX_TTL_CHANGE_PCT),
                           current_ttl * 1.25)
        proposed = round(proposed_ttl)
        direction = "EXTEND"

    # Shortening trigger
    elif util < 0.50 and win_rate >= 0.45:
        proposed_ttl = max(float(floor), current_ttl * (1 - MAX_TTL_CHANGE_PCT * 0.5))
        proposed = round(proposed_ttl)
        direction = "SHORTEN"

    if proposed is None or proposed == round(current_ttl):
        return None

    # Guardrail: TTL floor
    if proposed < floor:
        log.debug("[Layer6] TTL proposal blocked: %d < floor %d for %s", proposed, floor, archetype_id)
        return None

    # Guardrail: ±20% cap
    actual_change = abs(proposed - current_ttl) / current_ttl
    if actual_change > MAX_TTL_CHANGE_PCT:
        proposed = (round(current_ttl * (1 + MAX_TTL_CHANGE_PCT)) if direction == "EXTEND"
                    else max(floor, round(current_ttl * (1 - MAX_TTL_CHANGE_PCT))))

    evidence = {
        "late_peak_pct":   round(late_peak_pct, 4),
        "ttl_utilization": round(util, 4),
        "win_rate":        round(win_rate, 4),
        "direction":       direction,
    }
    return _write_proposal(
        conn, archetype_id, regime, "TTL_CHANGE",
        current_ttl, float(proposed), evidence,
        obs_count=int(obs_w),
        win_rate_current=win_rate, win_rate_projected=None,
        requires_approval=False,
        today=today,
    )


# ---------------------------------------------------------------------------
# Half-life proposals
# ---------------------------------------------------------------------------

def _propose_half_life_for_pair(
    conn: sqlite3.Connection,
    archetype_id: str,
    regime: str,
    dist: sqlite3.Row,
    today: str,
) -> Optional[str]:
    """
    Compare the empirical half_life_trading_days from archetype_outcome_distributions
    to the current BASE_HALF_LIFE × regime_multiplier. If they diverge by > 25%,
    propose a half-life multiplier adjustment.
    """
    obs_w = dist["observation_count_weighted"] or 0.0
    if obs_w < MIN_OBS_FOR_PROPOSAL:
        return None

    if _already_proposed_this_quarter(conn, archetype_id, regime, "HALF_LIFE_CHANGE", today):
        return None

    empirical_hl = dist["half_life_trading_days"]
    if empirical_hl is None or empirical_hl <= 0:
        return None

    # Determine signal_type
    sb_type = conn.execute(
        "SELECT signal_type FROM signal_births WHERE archetype_id = ? LIMIT 1",
        (archetype_id,)
    ).fetchone()
    sig_type = sb_type["signal_type"] if sb_type else "1A"
    base_hl  = BASE_HALF_LIFE.get(sig_type, 10.0)

    # Normalize regime label
    regime_map = {
        "TRENDING_UP": "BULL", "BULL": "BULL",
        "SIDEWAYS": "RANGE", "RANGE": "RANGE",
        "TRENDING_DOWN": "BEAR", "BEAR": "BEAR",
        "PANIC": "PANIC",
    }
    regime_norm = regime_map.get(regime, "RANGE")
    mults = HALF_LIFE_MULTIPLIERS.get(sig_type, {})
    current_mult = mults.get(regime_norm, 1.0)
    current_hl   = base_hl * current_mult

    divergence = abs(empirical_hl - current_hl) / current_hl if current_hl > 0 else 0
    if divergence < 0.25:
        return None

    # Proposed multiplier: move 50% of the way toward empirical, capped at ±20%
    target_hl   = empirical_hl
    mid_hl      = current_hl + (target_hl - current_hl) * 0.50
    new_mult    = mid_hl / base_hl if base_hl > 0 else current_mult
    # Cap
    max_mult    = current_mult * (1 + MAX_HL_CHANGE_PCT)
    min_mult    = current_mult * (1 - MAX_HL_CHANGE_PCT)
    new_mult    = max(min_mult, min(max_mult, new_mult))
    proposed_hl = base_hl * new_mult

    if abs(proposed_hl - current_hl) / current_hl < 0.05:
        return None

    evidence = {
        "empirical_half_life": round(empirical_hl, 2),
        "current_half_life":   round(current_hl, 2),
        "divergence_pct":      round(divergence * 100, 2),
        "sig_type":            sig_type,
        "regime_norm":         regime_norm,
    }
    return _write_proposal(
        conn, archetype_id, regime, "HALF_LIFE_CHANGE",
        round(current_hl, 4), round(proposed_hl, 4), evidence,
        obs_count=int(obs_w),
        win_rate_current=dist["win_rate"], win_rate_projected=None,
        requires_approval=False,
        today=today,
    )


# ---------------------------------------------------------------------------
# Archetype weight proposals
# ---------------------------------------------------------------------------

def _propose_weight_for_type(
    conn: sqlite3.Connection,
    sig_type: str,
    today: str,
) -> Optional[str]:
    """
    Compare the win rate of confirming signals of this type to the baseline.
    If win rate is > 30% above baseline → increase weight (within +15%).
    If win rate is < 0.40              → decrease weight (within -15%).
    Uses evidence weight archetype_id = 'EVIDENCE_WEIGHT_' + sig_type.
    """
    archetype_id = f"EVIDENCE_WEIGHT_{sig_type}"
    if _already_proposed_this_quarter(conn, archetype_id, None, "WEIGHT_CHANGE", today):
        return None

    # Win rate for confirming signals of this type
    row = conn.execute("""
        SELECT COUNT(*) AS total,
               SUM(CASE WHEN sb.peak_move_pct >= sb.expected_move_pct * 0.5 THEN 1 ELSE 0 END) AS wins
        FROM signal_births sb
        JOIN opportunity_signals os ON os.signal_id = sb.signal_id
        WHERE sb.signal_type = ?
          AND os.signal_direction = 'CONFIRMING'
          AND sb.final_state IS NOT NULL
          AND sb.peak_move_pct IS NOT NULL
    """, (sig_type,)).fetchone()

    if not row or (row["total"] or 0) < 30:
        return None

    win_rate   = (row["wins"] or 0) / row["total"]
    default_w  = _DEFAULT_WEIGHTS.get(sig_type, 0.70)
    current_w  = default_w   # phase D has no DB-stored current weight yet

    if win_rate > 0.55:
        proposed_w = min(current_w * (1 + MAX_WEIGHT_CHANGE_PCT), 1.0)
    elif win_rate < 0.40:
        proposed_w = max(current_w * (1 - MAX_WEIGHT_CHANGE_PCT), 0.1)
    else:
        return None

    if abs(proposed_w - current_w) < 0.02:
        return None

    evidence = {
        "sig_type":    sig_type,
        "win_rate":    round(win_rate, 4),
        "sample_size": row["total"],
    }
    return _write_proposal(
        conn, archetype_id, None, "WEIGHT_CHANGE",
        round(current_w, 4), round(proposed_w, 4), evidence,
        obs_count=row["total"],
        win_rate_current=win_rate, win_rate_projected=None,
        requires_approval=False,
        today=today,
    )


# ---------------------------------------------------------------------------
# Archetype retirement proposals
# ---------------------------------------------------------------------------

def _propose_retirement_if_warranted(
    conn: sqlite3.Connection,
    archetype_id: str,
    today: str,
) -> Optional[str]:
    """
    Propose retirement when all retirement conditions are met simultaneously:
        1. observation_count_weighted >= 50
        2. win_rate < 0.35
        3. Consistent underperformance across >= 2 distinct regime periods
        4. requires_approval = TRUE always

    The "proposed_value" = 0.0 (indicating retirement / inactive weight).
    """
    if _already_proposed_this_quarter(conn, archetype_id, None, "ARCHETYPE_RETIRE", today):
        return None

    # Check distributions across all regimes
    dists = conn.execute("""
        SELECT regime, observation_count_weighted, win_rate
        FROM archetype_outcome_distributions
        WHERE archetype_id = ?
          AND observation_count_weighted >= ?
        ORDER BY computed_at DESC
    """, (archetype_id, _RETIRE_MIN_OBS)).fetchall()

    if not dists:
        return None

    # Must underperform in >= 2 distinct regime periods
    underperform_regimes = [d for d in dists if (d["win_rate"] or 1.0) < _RETIRE_WIN_RATE_THRESHOLD]
    if len(underperform_regimes) < _RETIRE_MIN_REGIMES:
        return None

    total_obs_w = sum(d["observation_count_weighted"] for d in underperform_regimes)
    avg_win_rate = sum(d["win_rate"] or 0 for d in underperform_regimes) / len(underperform_regimes)

    evidence = {
        "underperform_regimes": [d["regime"] for d in underperform_regimes],
        "avg_win_rate":         round(avg_win_rate, 4),
        "total_obs_weighted":   round(total_obs_w, 2),
    }
    return _write_proposal(
        conn, archetype_id, None, "ARCHETYPE_RETIRE",
        1.0, 0.0, evidence,
        obs_count=int(total_obs_w),
        win_rate_current=avg_win_rate, win_rate_projected=0.0,
        requires_approval=True,   # always
        today=today,
    )


# ---------------------------------------------------------------------------
# Main adaptive cycle
# ---------------------------------------------------------------------------

def run_adaptive_cycle(
    conn: sqlite3.Connection,
    today: str,
) -> dict:
    """
    Full Layer 6 observation-and-recommendation cycle.

    Steps:
        1. Gather archetype_outcome_distributions rows
        2. Run CF-1 and CF-4 for evidence
        3. For each (archetype, regime) pair with sufficient observations:
            a. Propose TTL adjustment
            b. Propose half-life adjustment
        4. For each signal_type: propose weight adjustment
        5. For each archetype: check retirement criteria
        6. Return summary

    Shadow mode: writes ONLY to pending_adjustments. No runtime changes.
    No pending_adjustments status is ever set to AUTO_APPLIED by this module.
    """
    summary = {
        "date": today,
        "shadow_mode": SHADOW_MODE,
        "ttl_proposals":        0,
        "half_life_proposals":  0,
        "weight_proposals":     0,
        "retirement_proposals": 0,
        "skipped_insufficient": 0,
    }

    # Pre-compute counterfactual evidence (lightweight)
    cf1 = run_cf1_ttl_sensitivity(conn)
    cf4 = run_cf4_hold_duration_sensitivity(conn)

    # Gather active distributions
    dist_rows = conn.execute("""
        SELECT d1.*
        FROM archetype_outcome_distributions d1
        INNER JOIN (
            SELECT archetype_id, regime, MAX(computed_at) AS latest
            FROM archetype_outcome_distributions
            GROUP BY archetype_id, regime
        ) d2 ON d1.archetype_id = d2.archetype_id
              AND d1.regime = d2.regime
              AND d1.computed_at = d2.latest
    """).fetchall()

    for dist in dist_rows:
        archetype_id = dist["archetype_id"]
        regime       = dist["regime"]
        obs_w        = dist["observation_count_weighted"] or 0.0

        if obs_w < MIN_OBS_FOR_PROPOSAL:
            summary["skipped_insufficient"] += 1
            continue

        if _propose_ttl_for_pair(conn, archetype_id, regime, dist, cf1, cf4, today):
            summary["ttl_proposals"] += 1

        if _propose_half_life_for_pair(conn, archetype_id, regime, dist, today):
            summary["half_life_proposals"] += 1

    # Weight proposals per signal type
    for sig_type in _DEFAULT_WEIGHTS:
        if _propose_weight_for_type(conn, sig_type, today):
            summary["weight_proposals"] += 1

    # Retirement proposals per archetype
    archetypes = {
        r[0] for r in conn.execute(
            "SELECT DISTINCT archetype_id FROM archetype_outcome_distributions"
        ).fetchall()
    }
    for aid in archetypes:
        if _propose_retirement_if_warranted(conn, aid, today):
            summary["retirement_proposals"] += 1

    total = (summary["ttl_proposals"] + summary["half_life_proposals"] +
             summary["weight_proposals"] + summary["retirement_proposals"])
    log.info(
        "[Layer6] Adaptive cycle %s: %d total proposals "
        "(ttl=%d hl=%d wt=%d retire=%d) [shadow=%s]",
        today, total,
        summary["ttl_proposals"], summary["half_life_proposals"],
        summary["weight_proposals"], summary["retirement_proposals"],
        SHADOW_MODE,
    )
    return summary
