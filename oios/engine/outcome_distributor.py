"""
oios/engine/outcome_distributor.py

Weekly archetype outcome distribution recomputation.
Layer 4 Self-Audit — populates archetype_outcome_distributions.

Decay weighting rule (MAS_v1.2.md Table 10):
    0–24 months:  weight = 1.00
    24–48 months: weight = 0.50
    48+ months:   weight = 0.10

is_distribution_active logic:
    Shadow mode ON  → always 0 (never activates adaptive consumption)
    Shadow mode OFF → 1 when observation_count_weighted >= MIN_DISTRIBUTION_OBSERVATIONS

Call run_weekly_distribution_update() once per week (typically Sunday EOD or Monday pre-market).
"""

from __future__ import annotations
import json
import logging
import sqlite3
from datetime import date, datetime

from .shadow_mode import SHADOW_MODE, MIN_DISTRIBUTION_OBSERVATIONS

log = logging.getLogger(__name__)

# Decay weight age boundaries (in months)
_WEIGHT_FULL = 24    # <= 24 months: weight 1.0
_WEIGHT_HALF = 48    # 24–48 months: weight 0.5
# 48+ months: weight 0.1

# Win threshold: actual_move_pct >= expected_move_pct × 0.5 = "winner"
_WIN_THRESHOLD_FRACTION = 0.5

# Minimum raw observations to write a distribution row
_MIN_RAW_OBS = 5


# ---------------------------------------------------------------------------
# Decay weight helper
# ---------------------------------------------------------------------------

def _decay_weight(detected_at: str, today: str) -> float:
    """Return the decay weight for a signal based on its age in months."""
    try:
        d_det = date.fromisoformat(detected_at[:10])
        d_now = date.fromisoformat(today[:10])
        age_months = ((d_now - d_det).days) / 30.44
    except (ValueError, TypeError):
        return 1.0

    if age_months <= _WEIGHT_FULL:
        return 1.0
    elif age_months <= _WEIGHT_HALF:
        return 0.5
    else:
        return 0.1


# ---------------------------------------------------------------------------
# Distribution computation for one (archetype, regime) pair
# ---------------------------------------------------------------------------

def _weighted_median(values: list[float], weights: list[float]) -> float | None:
    """Compute weighted median of a list of (value, weight) pairs."""
    if not values:
        return None
    pairs = sorted(zip(values, weights), key=lambda x: x[0])
    total_w = sum(w for _, w in pairs)
    if total_w == 0:
        return None
    cumulative = 0.0
    for v, w in pairs:
        cumulative += w
        if cumulative >= total_w / 2:
            return v
    return pairs[-1][0]


def _weighted_percentile(
    values: list[float], weights: list[float], pct: float
) -> float | None:
    """pct in [0, 100]."""
    if not values:
        return None
    pairs = sorted(zip(values, weights), key=lambda x: x[0])
    total_w = sum(w for _, w in pairs)
    if total_w == 0:
        return None
    target = total_w * pct / 100.0
    cumulative = 0.0
    for v, w in pairs:
        cumulative += w
        if cumulative >= target:
            return v
    return pairs[-1][0]


def _classify_path_shape(
    day_3_med: float | None,
    day_7_med: float | None,
    day_14_med: float | None,
) -> str:
    """Classify the outcome curve shape from milestone medians."""
    if None in (day_3_med, day_7_med, day_14_med):
        return "UNKNOWN"
    if day_3_med > 4.0:
        return "EXPLOSIVE"
    slope_early = (day_7_med - day_3_med)
    slope_late  = (day_14_med - day_7_med)
    if slope_early > 1.5 and slope_late > 1.5:
        return "SLOW_BUILDER"
    if abs(slope_early - slope_late) < 0.5:
        return "SMOOTH_DRIFT"
    if slope_early > slope_late * 2:
        return "STAIRCASE"
    return "SMOOTH_DRIFT"


def compute_distribution_for_pair(
    conn: sqlite3.Connection,
    archetype_id: str,
    regime: str,
    today: str,
) -> dict | None:
    """
    Compute decay-weighted outcome distribution stats for one (archetype, regime) pair.
    Returns dict to insert into archetype_outcome_distributions, or None if insufficient data.
    """
    rows = conn.execute("""
        SELECT sb.detected_at,
               sb.final_state,
               sb.final_age_trading_days,
               sb.peak_move_pct,
               sb.days_to_peak,
               sb.expected_move_pct,
               sb.actual_move_pct,
               sb.expected_ttl_days,
               COALESCE(sb.archetype_version, 1) AS archetype_version
        FROM signal_births sb
        WHERE sb.archetype_id = ?
          AND sb.regime_at_birth = ?
          AND sb.final_state IS NOT NULL
    """, (archetype_id, regime)).fetchall()

    if len(rows) < _MIN_RAW_OBS:
        return None

    # Compute weights
    weights = [_decay_weight(r["detected_at"], today) for r in rows]
    obs_w   = sum(weights)

    # Win rate (weighted)
    winner_w = sum(
        w for r, w in zip(rows, weights)
        if r["peak_move_pct"] and r["expected_move_pct"]
        and r["peak_move_pct"] >= r["expected_move_pct"] * _WIN_THRESHOLD_FRACTION
    )
    win_rate = winner_w / obs_w if obs_w > 0 else None

    # Final move distribution
    final_moves  = [r["peak_move_pct"] or 0.0 for r in rows]
    days_to_peak = [r["days_to_peak"] or r["final_age_trading_days"] or 0 for r in rows]

    med_final_move = _weighted_median(final_moves, weights)
    med_days_to_pk = _weighted_median([float(d) for d in days_to_peak], weights)

    # Path milestones: estimate what move % was achieved by day N
    # Use days_to_peak and peak_move_pct with linear interpolation
    def _move_at_day(target_day: int) -> tuple[float | None, float | None, float | None]:
        vals = []
        ws   = []
        for r, w in zip(rows, weights):
            dtpk = r["days_to_peak"] or r["final_age_trading_days"] or 0
            peak = r["peak_move_pct"] or 0.0
            if dtpk == 0:
                est = 0.0
            else:
                est = min(peak, peak * target_day / dtpk)
            vals.append(est)
            ws.append(w)
        return (
            _weighted_median(vals, ws),
            _weighted_percentile(vals, ws, 25),
            _weighted_percentile(vals, ws, 75),
        )

    d3_med,  d3_p25,  d3_p75  = _move_at_day(3)
    d7_med,  d7_p25,  d7_p75  = _move_at_day(7)
    d14_med, d14_p25, d14_p75 = _move_at_day(14)
    d21_med, d21_p25, d21_p75 = _move_at_day(21)
    d30_med, d30_p25, d30_p75 = _move_at_day(30)

    # Estimate half-life: median days to achieve 50% of expected_move_pct
    expected_moves = [r["expected_move_pct"] or 8.0 for r in rows]
    half_thresh    = [em * 0.5 for em in expected_moves]
    hl_days = []
    hl_ws   = []
    for r, w, ht in zip(rows, weights, half_thresh):
        dtpk = r["days_to_peak"] or r["final_age_trading_days"] or 0
        peak = r["peak_move_pct"] or 0.0
        if dtpk > 0 and peak > 0:
            approx_hl = dtpk * ht / peak
            hl_days.append(approx_hl)
            hl_ws.append(w)
    hl_estimate = _weighted_median(hl_days, hl_ws) if hl_days else None

    # Most recent archetype_version
    arch_version = max(r["archetype_version"] for r in rows)

    # Shadow mode gate
    is_active = 0
    if not SHADOW_MODE and obs_w >= MIN_DISTRIBUTION_OBSERVATIONS:
        is_active = 1

    return {
        "archetype_id":              archetype_id,
        "archetype_version":         arch_version,
        "regime":                    regime,
        "computed_at":               today,
        "observation_count_raw":     len(rows),
        "observation_count_weighted": round(obs_w, 2),
        "is_distribution_active":    is_active,
        "day_3_median":   d3_med,  "day_3_p25":  d3_p25,  "day_3_p75":  d3_p75,
        "day_7_median":   d7_med,  "day_7_p25":  d7_p25,  "day_7_p75":  d7_p75,
        "day_14_median":  d14_med, "day_14_p25": d14_p25, "day_14_p75": d14_p75,
        "day_21_median":  d21_med, "day_21_p25": d21_p25, "day_21_p75": d21_p75,
        "day_30_median":  d30_med, "day_30_p25": d30_p25, "day_30_p75": d30_p75,
        "win_rate":                  win_rate,
        "median_final_move_pct":     med_final_move,
        "median_days_to_peak":       med_days_to_pk,
        "path_shape":               _classify_path_shape(d3_med, d7_med, d14_med),
        "half_life_trading_days":    hl_estimate,
    }


# ---------------------------------------------------------------------------
# Weekly batch update
# ---------------------------------------------------------------------------

def run_weekly_distribution_update(
    conn: sqlite3.Connection,
    today: str,
) -> int:
    """
    Recompute archetype_outcome_distributions for all (archetype, regime) pairs
    that have at least _MIN_RAW_OBS completed signal_births.

    In shadow mode: rows are written but is_distribution_active is always 0.
    In live mode:   is_distribution_active is set to 1 when obs >= 20.

    Returns number of (archetype, regime) pairs updated.
    """
    pairs = conn.execute("""
        SELECT DISTINCT archetype_id, regime_at_birth AS regime
        FROM signal_births
        WHERE final_state IS NOT NULL
    """).fetchall()

    updated = 0
    for p in pairs:
        archetype_id = p["archetype_id"] if isinstance(p, sqlite3.Row) else p[0]
        regime       = p["regime"]       if isinstance(p, sqlite3.Row) else p[1]
        dist = compute_distribution_for_pair(conn, archetype_id, regime, today)
        if dist is None:
            continue

        conn.execute("""
            INSERT OR REPLACE INTO archetype_outcome_distributions (
                archetype_id, archetype_version, regime, computed_at,
                observation_count_raw, observation_count_weighted, is_distribution_active,
                day_3_median, day_3_p25, day_3_p75,
                day_7_median, day_7_p25, day_7_p75,
                day_14_median, day_14_p25, day_14_p75,
                day_21_median, day_21_p25, day_21_p75,
                day_30_median, day_30_p25, day_30_p75,
                win_rate, median_final_move_pct, median_days_to_peak,
                path_shape, half_life_trading_days
            ) VALUES (
                :archetype_id, :archetype_version, :regime, :computed_at,
                :observation_count_raw, :observation_count_weighted, :is_distribution_active,
                :day_3_median, :day_3_p25, :day_3_p75,
                :day_7_median, :day_7_p25, :day_7_p75,
                :day_14_median, :day_14_p25, :day_14_p75,
                :day_21_median, :day_21_p25, :day_21_p75,
                :day_30_median, :day_30_p25, :day_30_p75,
                :win_rate, :median_final_move_pct, :median_days_to_peak,
                :path_shape, :half_life_trading_days
            )
        """, dist)
        updated += 1

    shadow_note = " [SHADOW — is_distribution_active=0]" if SHADOW_MODE else " [LIVE]"
    log.info("[OutcomeDistributor] Updated %d (archetype, regime) pairs on %s%s",
             updated, today, shadow_note)
    return updated
