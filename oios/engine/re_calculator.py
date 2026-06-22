"""
oios/engine/re_calculator.py

Sub-A: Remaining Edge (RE) Calculator
Layer 5 — Edge Lifecycle Engine

Implements the Phase-0 simplified RE formula from MAS v1.2 Section 5:

    RE = E0 × D_time × (1 - EC_path) × (1 - C_crowding)

Where:
    E0          = base_score at signal birth
    D_time      = 0.5 ^ (age_trading_days / half_life)
    EC_path     = actual_move_pct / expected_move_pct  (linear, capped 0–1)
    C_crowding  = 0.0 when current volume < 3× 20-day avg; rises above that

Phase-0 simplifications (per PHASE_C_ACCEPTANCE.md):
    - EC_path is a linear ratio, NOT a percentile position in historical distributions
    - half_life uses fixed regime priors (not learned distributions)
    - C_crowding = 0.0 below the 3× threshold; linear ramp 0.0–1.0 from 3× to 10× avg

Regime map:
    The replay uses TRENDING_UP / SIDEWAYS / TRENDING_DOWN.
    MAS uses BULL / RANGE / BEAR / PANIC.
    This module maps between them — no other module should be aware of this.

NO DB WRITES in this module. Pure computation.
"""

from __future__ import annotations
import logging
import sqlite3
from typing import Optional

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Fixed regime half-life priors (MAS v1.2 Section 5, Layer 5 Table)
# ---------------------------------------------------------------------------

# base_half_life_days[signal_type] — the unmodified half-life before regime multiplier
BASE_HALF_LIFE: dict[str, float] = {
    "1A":  10.0,   # matches EXPECTED_TTL_DAYS for 1A
    "1B":  18.0,   # matches EXPECTED_TTL_DAYS for 1B
    "1.5": 20.0,   # sector conviction signals have longest natural half-life
    "2":   12.0,
    "3":   8.0,
}

# Regime multipliers on half-life
# (signal_type → regime_label → multiplier)
HALF_LIFE_MULTIPLIERS: dict[str, dict[str, float]] = {
    "1B": {
        "BULL":  1.8,
        "RANGE": 0.5,
        "BEAR":  0.7,
        "PANIC": 0.1,
    },
    "1A": {
        "BULL":  1.3,
        "RANGE": 0.7,
        "BEAR":  0.6,
        "PANIC": 0.1,
    },
    "1.5": {
        "BULL":  2.0,
        "RANGE": 0.4,
        "BEAR":  0.5,
        "PANIC": 0.0,
    },
}
# Default multiplier for signal types not in the table
_DEFAULT_MULTIPLIERS: dict[str, float] = {
    "BULL":  1.2,
    "RANGE": 0.7,
    "BEAR":  0.6,
    "PANIC": 0.1,
}

# Regime label mapping: operational labels → MAS canonical labels
_REGIME_LABEL_MAP: dict[str, str] = {
    "TRENDING_UP":   "BULL",
    "BULL":          "BULL",
    "SIDEWAYS":      "RANGE",
    "RANGE":         "RANGE",
    "TRENDING_DOWN": "BEAR",
    "BEAR":          "BEAR",
    "PANIC":         "PANIC",
    "CRISIS":        "PANIC",
}

# Crowding thresholds
_CROWDING_ZERO_MULTIPLE   = 3.0    # C_crowding = 0.0 below this
_CROWDING_FULL_MULTIPLE   = 10.0   # C_crowding = 1.0 at and above this
_CROWDING_VOL_LOOKBACK    = 20     # 20-day average volume window

# RE floor — never go negative
_RE_FLOOR = 0.0

# Volume lookback for crowding proxy
_VOL_WINDOW_ROWS = _CROWDING_VOL_LOOKBACK + 1


# ---------------------------------------------------------------------------
# Half-life computation
# ---------------------------------------------------------------------------

def get_half_life(signal_type: str, regime: str) -> float:
    """
    Return the effective half-life in trading days for a given signal type
    and regime label.

    Uses fixed regime priors (Phase-0; Phase D will learn these from outcomes).
    Regime label is normalised through _REGIME_LABEL_MAP.
    """
    canonical_regime = _REGIME_LABEL_MAP.get(regime.upper() if regime else "", "RANGE")

    base = BASE_HALF_LIFE.get(signal_type, BASE_HALF_LIFE["1A"])
    type_multipliers = HALF_LIFE_MULTIPLIERS.get(signal_type, _DEFAULT_MULTIPLIERS)
    multiplier = type_multipliers.get(canonical_regime, 1.0)

    effective = base * multiplier
    # Enforce a hard floor so half-life never reaches 0 (prevents division by zero)
    return max(effective, 0.1)


# ---------------------------------------------------------------------------
# Edge-consumed (EC_path) computation — linear Phase-0 version
# ---------------------------------------------------------------------------

def compute_ec_path(
    actual_move_pct: float,
    expected_move_pct: float,
) -> float:
    """
    Phase-0 linear EC_path = actual_move / expected_move, capped [0, 1].

    A negative actual_move (stock moved against direction) → EC_path = 0.
    EC_path = 1.0 means the full expected edge has been consumed.
    """
    if expected_move_pct <= 0:
        return 0.0
    raw = actual_move_pct / expected_move_pct
    return max(0.0, min(1.0, raw))


def compute_actual_move_pct(
    conn: sqlite3.Connection,
    symbol: str,
    direction: str,
    birth_price: float,
    as_of_date: str,
) -> float:
    """
    Compute how much of the expected move has actually occurred.

    For LONG:  (current_price - birth_price) / birth_price × 100
    For SHORT: (birth_price - current_price) / birth_price × 100

    Returns 0.0 when no current price data exists.
    Negative values (stock moved against direction) are clamped to 0.0 in
    compute_ec_path — this function returns the raw signed value.
    """
    row = conn.execute("""
        SELECT close FROM ohlcv_daily
        WHERE symbol = ? AND trade_date <= ?
        ORDER BY trade_date DESC LIMIT 1
    """, (symbol, as_of_date)).fetchone()

    if not row or birth_price <= 0:
        return 0.0

    current = row[0]
    if direction == "LONG":
        return (current - birth_price) / birth_price * 100.0
    else:
        return (birth_price - current) / birth_price * 100.0


# ---------------------------------------------------------------------------
# Crowding proxy (C_crowding)
# ---------------------------------------------------------------------------

def compute_crowding(
    conn: sqlite3.Connection,
    symbol: str,
    as_of_date: str,
) -> float:
    """
    C_crowding proxy based on current volume vs. 20-day average volume.

    C_crowding = 0.0 when today_vol < 3× avg_vol
    C_crowding = linear ramp 0.0–1.0 from 3× to 10× avg_vol
    C_crowding = 1.0 when today_vol >= 10× avg_vol

    Returns 0.0 when volume data is unavailable.
    """
    rows = conn.execute("""
        SELECT volume FROM ohlcv_daily
        WHERE symbol = ? AND trade_date <= ?
        ORDER BY trade_date DESC
        LIMIT ?
    """, (symbol, as_of_date, _VOL_WINDOW_ROWS)).fetchall()

    if len(rows) < 2:
        return 0.0

    today_vol = rows[0][0]
    # Average over the prior 20 days (exclude today)
    prior_vols = [r[0] for r in rows[1:]]
    if not prior_vols:
        return 0.0

    avg_vol = sum(prior_vols) / len(prior_vols)
    if avg_vol <= 0:
        return 0.0

    ratio = today_vol / avg_vol

    if ratio < _CROWDING_ZERO_MULTIPLE:
        return 0.0
    if ratio >= _CROWDING_FULL_MULTIPLE:
        return 1.0

    # Linear ramp between 3× and 10×
    span = _CROWDING_FULL_MULTIPLE - _CROWDING_ZERO_MULTIPLE
    return (ratio - _CROWDING_ZERO_MULTIPLE) / span


# ---------------------------------------------------------------------------
# RE formula
# ---------------------------------------------------------------------------

def compute_re(
    base_score: float,
    age_trading_days: int,
    signal_type: str,
    regime: str,
    actual_move_pct: float,
    expected_move_pct: float,
    c_crowding: float = 0.0,
) -> float:
    """
    RE = E0 × D_time × (1 - EC_path) × (1 - C_crowding)

    Pure computation — no DB access. Callers supply all inputs.

    Returns RE clamped to [0, E0].
    Returns 0.0 when EC_path >= 1.0 (edge fully consumed).
    Never returns negative.
    """
    ec_path = compute_ec_path(actual_move_pct, expected_move_pct)

    # Edge fully consumed — RE collapses immediately
    if ec_path >= 1.0:
        return _RE_FLOOR

    half_life = get_half_life(signal_type, regime)
    d_time = 0.5 ** (age_trading_days / half_life)

    re = base_score * d_time * (1.0 - ec_path) * (1.0 - c_crowding)
    return max(_RE_FLOOR, re)


def compute_re_for_opportunity(
    conn: sqlite3.Connection,
    opportunity_id: str,
    as_of_date: str,
    regime: str,
) -> Optional[float]:
    """
    Convenience wrapper: loads signal birth data and computes RE for an opportunity.

    Queries ohlcv_daily for current price and crowding.
    Returns None if essential data is missing (no signal birth found, no OHLCV).
    """
    row = conn.execute("""
        SELECT sb.signal_id, sb.base_score, sb.signal_type,
               sb.birth_price, sb.expected_move_pct,
               sb.expected_move_direction,
               o.age_trading_days
        FROM opportunities o
        JOIN signal_births sb ON sb.signal_id = o.first_signal_id
        WHERE o.opportunity_id = ?
    """, (opportunity_id,)).fetchone()

    if not row:
        log.debug("[RE] No founding signal found for opportunity %s", opportunity_id)
        return None

    symbol_row = conn.execute(
        "SELECT symbol FROM opportunities WHERE opportunity_id = ?", (opportunity_id,)
    ).fetchone()
    if not symbol_row:
        return None

    symbol    = symbol_row[0]
    direction = row["expected_move_direction"]

    actual_move = compute_actual_move_pct(conn, symbol, direction, row["birth_price"], as_of_date)
    c_crowding  = compute_crowding(conn, symbol, as_of_date)

    return compute_re(
        base_score        = row["base_score"],
        age_trading_days  = row["age_trading_days"],
        signal_type       = row["signal_type"],
        regime            = regime,
        actual_move_pct   = actual_move,
        expected_move_pct = row["expected_move_pct"] or 8.0,
        c_crowding        = c_crowding,
    )


def compute_effective_ttl(
    birth_ttl_days: int,
    signal_type: str,
    regime: str,
) -> int:
    """
    Effective TTL = birth_ttl adjusted by the same regime multiplier as half-life.

    The regime multiplier on TTL is capped: a better regime can extend TTL,
    but never above the bull-market ceiling (birth_ttl × BULL_multiplier).
    Bear and panic regimes shorten the TTL.

    Returns an integer number of trading days (minimum 1).
    """
    canonical_regime = _REGIME_LABEL_MAP.get(regime.upper() if regime else "", "RANGE")
    type_multipliers = HALF_LIFE_MULTIPLIERS.get(signal_type, _DEFAULT_MULTIPLIERS)
    multiplier = type_multipliers.get(canonical_regime, 1.0)

    # Bull ceiling is the maximum — no regime improves beyond BULL
    bull_multiplier = type_multipliers.get("BULL", 1.3)
    multiplier = min(multiplier, bull_multiplier)

    return max(1, round(birth_ttl_days * multiplier))
