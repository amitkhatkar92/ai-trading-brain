"""
oios/engine/velocity_engine.py

Sub-C: Velocity Engine — d(RE)/dt with attribution.
Layer 5, Phase D.

Computes the 3-day velocity of RE change for a live opportunity and attributes
the dominant cause of that change to one of four classes:

    THESIS_WORKING    — RE declining because EC_path is rising (stock moving as expected)
    REGIME_PRESSURE   — RE declining because regime multiplier dropped (regime worsened)
    CROWDING          — RE declining because C_crowding is rising (abnormal volume)
    MECHANICAL_DECAY  — RE declining from time decay only; all other factors stable

velocity_3d = (RE_today − RE_3d_ago) / 3

Attribution logic:
    Decompose the RE change into contributions from each factor:
        ΔRE_ec_path    = RE(ec_path_today) − RE(ec_path_3d_ago)      holding others constant
        ΔRE_regime     = RE(regime_today) − RE(regime_3d_ago)         holding others constant
        ΔRE_crowding   = RE(crowding_today) − RE(crowding_3d_ago)     holding others constant
        ΔRE_decay      = RE(age_today) − RE(age_3d_ago)               holding others constant

    Dominant cause = factor with the largest |ΔRE| contribution.

Shadow mode discipline:
    Velocity writes to opportunities.velocity_3d and opportunities.velocity_class.
    Also writes velocity fields to opportunity_re_snapshots.
    No Phase C tables modified.
"""

from __future__ import annotations
import logging
import sqlite3
import uuid
from datetime import date, timedelta
from typing import Optional

from .re_calculator import compute_re, get_half_life, BASE_HALF_LIFE

log = logging.getLogger(__name__)

# Velocity class labels (MAS_v1.2.md Layer 5 Sub-C)
THESIS_WORKING    = "THESIS_WORKING"
REGIME_PRESSURE   = "REGIME_PRESSURE"
CROWDING          = "CROWDING"
MECHANICAL_DECAY  = "MECHANICAL_DECAY"

_VELOCITY_WINDOW = 3   # 3 trading-day look-back


# ---------------------------------------------------------------------------
# RE snapshot writer
# ---------------------------------------------------------------------------

def record_re_snapshot(
    conn: sqlite3.Connection,
    opportunity_id: str,
    snapshot_date: str,
    re_score: Optional[float],
    ec_path: float,
    c_crowding: float,
    regime: str,
    age_trading_days: int,
) -> None:
    """
    Insert one daily RE snapshot row for an opportunity.
    Called by ELE each cycle after computing RE.

    Idempotent: if a row for (opportunity_id, snapshot_date) already exists it is
    replaced (last write wins — same-day RE recomputation is normal).
    """
    snap_id = str(uuid.uuid4())
    conn.execute("""
        INSERT OR REPLACE INTO opportunity_re_snapshots
            (snapshot_id, opportunity_id, snapshot_date,
             re_score, ec_path, c_crowding, regime, age_trading_days)
        VALUES (?,?,?,?,?,?,?,?)
    """, (snap_id, opportunity_id, snapshot_date,
          re_score, ec_path, c_crowding, regime, age_trading_days))


# ---------------------------------------------------------------------------
# Velocity computation
# ---------------------------------------------------------------------------

def _get_snapshots_window(
    conn: sqlite3.Connection,
    opportunity_id: str,
    snapshot_date: str,
    window: int = _VELOCITY_WINDOW,
) -> list[sqlite3.Row]:
    """
    Return the last `window + 1` RE snapshots (oldest → newest).
    Needs at least (window + 1) rows to compute velocity.
    """
    rows = conn.execute("""
        SELECT snapshot_date, re_score, ec_path, c_crowding, regime, age_trading_days
        FROM opportunity_re_snapshots
        WHERE opportunity_id = ?
          AND snapshot_date <= ?
        ORDER BY snapshot_date DESC
        LIMIT ?
    """, (opportunity_id, snapshot_date, window + 1)).fetchall()
    return list(reversed(rows))   # oldest first


def _attribute_velocity(
    base_score: float,
    age_old: int,   age_new: int,
    signal_type: str,
    regime_old: str, regime_new: str,
    ec_path_old: float, ec_path_new: float,
    crowding_old: float, crowding_new: float,
) -> str:
    """
    Compute the dominant cause of RE change using single-factor decomposition.

    We compute RE at the old point and then re-compute RE changing one factor
    at a time, holding all others at the OLD value. The factor producing the
    largest |ΔRE| is the dominant cause.
    """
    re_base = compute_re(base_score, age_old, signal_type, regime_old,
                         0.0, 1.0, crowding_old)  # ec_path=0 → (1-EC)=1, expected_move=1
    # Use a neutral expected_move=1.0 and actual_move=0.0 so EC_path=0 for decomposition.
    # The decomposition only needs relative magnitude, not absolute RE values.

    def _re(age, regime, ec, crowd):
        return compute_re(base_score, age, signal_type, regime,
                          ec * 1.0, 1.0, crowd)
        # actual_move = ec * expected_move_pct; here we set expected_move=1 so ec_path=ec directly.
        # This is a consistent normalised decomposition.

    re_ref      = _re(age_old, regime_old, ec_path_old, crowding_old)
    re_ec       = _re(age_old, regime_old, ec_path_new, crowding_old)
    re_regime   = _re(age_old, regime_new, ec_path_old, crowding_old)
    re_crowd    = _re(age_old, regime_old, ec_path_old, crowding_new)
    re_age      = _re(age_new, regime_old, ec_path_old, crowding_old)

    delta_ec     = abs(re_ec     - re_ref)
    delta_regime = abs(re_regime - re_ref)
    delta_crowd  = abs(re_crowd  - re_ref)
    delta_age    = abs(re_age    - re_ref)

    best = max(delta_ec, delta_regime, delta_crowd, delta_age)

    # Ties broken by spec priority order
    if best == 0.0:
        return MECHANICAL_DECAY
    if delta_ec == best:
        return THESIS_WORKING
    if delta_regime == best:
        return REGIME_PRESSURE
    if delta_crowd == best:
        return CROWDING
    return MECHANICAL_DECAY


def compute_velocity(
    conn: sqlite3.Connection,
    opportunity_id: str,
    today: str,
    base_score: float = 6.0,
    signal_type: str = "1A",
) -> tuple[Optional[float], Optional[str]]:
    """
    Compute velocity_3d and velocity_class for an opportunity.

    Returns (velocity_3d, velocity_class) or (None, None) if insufficient
    snapshot history.

    velocity_3d = (RE_today − RE_3d_ago) / 3

    Caller is responsible for persisting results to opportunities table and
    updating the latest re_snapshots row.
    """
    rows = _get_snapshots_window(conn, opportunity_id, today, _VELOCITY_WINDOW)
    if len(rows) < _VELOCITY_WINDOW + 1:
        return None, None   # not enough history yet

    oldest = rows[0]
    newest = rows[-1]

    re_old = oldest["re_score"]
    re_new = newest["re_score"]
    if re_old is None or re_new is None:
        return None, None

    velocity_3d = (re_new - re_old) / _VELOCITY_WINDOW

    # Attribution
    velocity_class = _attribute_velocity(
        base_score  = base_score,
        age_old     = oldest["age_trading_days"] or 0,
        age_new     = newest["age_trading_days"] or 0,
        signal_type = signal_type,
        regime_old  = oldest["regime"] or "RANGE",
        regime_new  = newest["regime"] or "RANGE",
        ec_path_old = oldest["ec_path"] or 0.0,
        ec_path_new = newest["ec_path"] or 0.0,
        crowding_old = oldest["c_crowding"] or 0.0,
        crowding_new = newest["c_crowding"] or 0.0,
    )

    return velocity_3d, velocity_class


def update_velocity(
    conn: sqlite3.Connection,
    opportunity_id: str,
    today: str,
    base_score: float = 6.0,
    signal_type: str = "1A",
) -> tuple[Optional[float], Optional[str]]:
    """
    Compute velocity and persist results to:
      1. opportunities.velocity_3d, opportunities.velocity_class
      2. The latest opportunity_re_snapshots row for (opportunity_id, today)

    Returns (velocity_3d, velocity_class).
    """
    velocity_3d, velocity_class = compute_velocity(
        conn, opportunity_id, today, base_score, signal_type
    )

    if velocity_3d is not None:
        conn.execute("""
            UPDATE opportunities
            SET velocity_3d   = ?,
                velocity_class = ?,
                last_updated_at = datetime('now')
            WHERE opportunity_id = ?
        """, (velocity_3d, velocity_class, opportunity_id))

        conn.execute("""
            UPDATE opportunity_re_snapshots
            SET velocity_3d    = ?,
                velocity_class = ?
            WHERE opportunity_id = ?
              AND snapshot_date  = ?
        """, (velocity_3d, velocity_class, opportunity_id, today))

    return velocity_3d, velocity_class


# ---------------------------------------------------------------------------
# Daily state snapshot (for D-Ready-5 concentration check)
# ---------------------------------------------------------------------------

def record_daily_state_snapshot(conn: sqlite3.Connection, snapshot_date: str) -> None:
    """
    Aggregate current state distribution into opportunity_daily_state_snapshot.
    Call once per trading day after all ELE cycles complete.
    """
    rows = conn.execute("""
        SELECT current_state, COUNT(*) AS cnt
        FROM opportunities
        GROUP BY current_state
    """).fetchall()

    for row in rows:
        conn.execute("""
            INSERT OR REPLACE INTO opportunity_daily_state_snapshot
                (snapshot_date, current_state, opp_count)
            VALUES (?, ?, ?)
        """, (snapshot_date, row["current_state"], row["cnt"]))
