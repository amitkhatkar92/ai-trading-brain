"""
oios/data/sector_conviction_writer.py

Layer 1.5 — Sector Conviction Engine
  Sub-A: Consensus Shift Intelligence (participation rates, RS, volume trend)
  Sub-B: Capital Flow Intelligence (bulk/block deal quality)
  Sub-C: Theme Phase Engine (EMERGENCE → ACCELERATION → CONSENSUS → CROWDING → EXHAUSTION)

Writers:
  run_sector_conviction(conn, trade_date, regime) — writes to sector_conviction_daily
  Theme Phase Engine writes to theme_phase_history on detected transitions

Data quality gate:
  If stocks_with_data / stocks_total < 0.80 → data_quality = "PARTIAL"
  PARTIAL rows suppress all Sub-A/B/C output fields (set to NULL)
  PARTIAL rows do NOT trigger theme phase transitions

Theme Phase Engine history guard:
  Requires >= 30 rows in sector_conviction_daily for a sector before activating.
  A phase detector without history degenerates into a threshold classifier.

Phase B defaults (until archetype_outcome_distributions active):
  expected_move_pct = 8.0 per MAS Section 5
"""

from __future__ import annotations
import logging
import sqlite3
import uuid
from datetime import date
from typing import Optional

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants from MAS Section 5, Layer 1.5
# ---------------------------------------------------------------------------

MIN_SECTOR_COVERAGE         = 0.80   # stocks_with_data / stocks_total threshold
CAPITAL_FLOW_NEUTRAL        = 0.50   # when data quality UNAVAILABLE
CAPITAL_FLOW_WEIGHT         = 0.40
CONSENSUS_WEIGHT            = 0.60

CONVICTION_FORMULA = (
    "0.40 × capital_flow_score + 0.60 × consensus_score"
)

# Theme Phase Engine requires minimum history before activating
THEME_PHASE_MIN_HISTORY     = 30     # rows in sector_conviction_daily

# Capital flow tiers (MAS Section 5, Layer 1.5 Sub-B)
CAPITAL_FLOW_FULL_THRESHOLD   = 3   # >= 3 deals in last 5 trading days → "FULL"
CAPITAL_FLOW_SPARSE_THRESHOLD = 1   # 1-2 deals → "SPARSE"; 0 → "UNAVAILABLE"

# NIFTY/BANKNIFTY/INDIAVIX are benchmarks — excluded from participation calculations
_BENCHMARK_SYMBOLS = {"^NSEI", "^NSEBANK", "NIFTY50", "BANKNIFTY", "INDIAVIX"}


# ---------------------------------------------------------------------------
# Sub-A: Consensus Shift Intelligence
# ---------------------------------------------------------------------------

def _compute_participation_rates(
    conn: sqlite3.Connection,
    sector: str,
    trade_date: str,
) -> Optional[dict]:
    """
    Compute weighted participation rates for a sector on a given date.

    Participation rate = SUM(purity_score WHERE return > 0) / SUM(purity_score)

    Returns a dict with:
      stocks_total, stocks_with_data,
      participation_rate_1d, participation_rate_5d,
      volume_trend_10d, rs_vs_market_20d

    Returns None if data_quality is PARTIAL (< 80% coverage).
    """
    # Get active sector stocks (exclude benchmarks)
    peers = conn.execute("""
        SELECT symbol, sector_purity_score
        FROM universe_stocks
        WHERE sector = ? AND is_active = 1
    """, (sector,)).fetchall()

    stocks_total = len(peers)
    if stocks_total == 0:
        return None

    purity = {row[0]: row[1] for row in peers
              if row[0] not in _BENCHMARK_SYMBOLS}

    # For each stock: load today's close and 5d/20d closes
    participation_1d_num  = 0.0
    participation_5d_num  = 0.0
    participation_denom   = 0.0
    volume_today_total    = 0.0
    volume_10d_total      = 0.0
    volume_count          = 0
    rs_stock_20d_weighted = 0.0
    rs_weight_total       = 0.0
    stocks_with_data      = 0

    for sym, w in purity.items():
        rows = conn.execute("""
            SELECT trade_date, close, volume
            FROM ohlcv_daily
            WHERE symbol = ? AND trade_date <= ?
            ORDER BY trade_date DESC LIMIT 25
        """, (sym, trade_date)).fetchall()

        if len(rows) < 2:
            continue
        stocks_with_data += 1

        closes  = [r[1] for r in rows]
        volumes = [r[2] for r in rows]

        # 1-day return: today vs yesterday
        ret_1d = (closes[0] / closes[1] - 1.0) if closes[1] > 0 else 0.0
        participation_denom += w
        if ret_1d > 0:
            participation_1d_num += w

        # 5-day return
        if len(rows) >= 6:
            ret_5d = (closes[0] / closes[5] - 1.0) if closes[5] > 0 else 0.0
            if ret_5d > 0:
                participation_5d_num += w

        # Volume trend (today vs 10-day avg)
        if len(rows) >= 11:
            avg_vol_10d = sum(volumes[1:11]) / 10
            volume_today_total += volumes[0]
            volume_10d_total   += avg_vol_10d
            volume_count       += 1

        # RS vs market (20-day return, weighted by purity)
        if len(rows) >= 21:
            ret_20d = (closes[0] / closes[20] - 1.0) * 100 if closes[20] > 0 else 0.0
            rs_stock_20d_weighted += ret_20d * w
            rs_weight_total       += w

    if participation_denom == 0 and stocks_with_data == 0:
        # No data at all — return PARTIAL (0% coverage)
        return {
            "stocks_total":           stocks_total,
            "stocks_with_data":       0,
            "data_quality":           "PARTIAL",
            "participation_rate_1d":  None,
            "participation_rate_5d":  None,
            "participation_expansion": None,
            "volume_trend_10d":       None,
            "rs_vs_market_20d":       None,
        }

    # Data quality gate
    coverage = stocks_with_data / stocks_total
    if coverage < MIN_SECTOR_COVERAGE:
        return {
            "stocks_total":         stocks_total,
            "stocks_with_data":     stocks_with_data,
            "data_quality":         "PARTIAL",
            "participation_rate_1d": None,
            "participation_rate_5d": None,
            "participation_expansion": None,
            "volume_trend_10d":     None,
            "rs_vs_market_20d":     None,
        }

    part_1d = participation_1d_num / participation_denom
    part_5d = participation_5d_num / participation_denom if participation_denom > 0 else None

    # Volume trend: ratio of average today vs 10d average across sector
    volume_trend = (volume_today_total / volume_10d_total) if volume_10d_total > 0 and volume_count > 0 else None

    # RS vs market: sector 20d avg return vs NIFTY 20d return
    rs_sector = (rs_stock_20d_weighted / rs_weight_total) if rs_weight_total > 0 else 0.0
    market_rows = conn.execute("""
        SELECT close FROM ohlcv_daily
        WHERE symbol IN ('^NSEI', 'NIFTY50', '^NSEINDICES')
          AND trade_date <= ?
        ORDER BY trade_date DESC LIMIT 21
    """, (trade_date,)).fetchall()
    rs_market = 0.0
    if len(market_rows) >= 21:
        rs_market = (market_rows[0][0] / market_rows[20][0] - 1.0) * 100 if market_rows[20][0] > 0 else 0.0
    rs_vs_market = rs_sector - rs_market

    return {
        "stocks_total":           stocks_total,
        "stocks_with_data":       stocks_with_data,
        "data_quality":           "FULL",
        "participation_rate_1d":  round(part_1d, 4),
        "participation_rate_5d":  round(part_5d, 4) if part_5d is not None else None,
        "participation_expansion": None,   # computed after retrieving prior history
        "volume_trend_10d":       round(volume_trend, 4) if volume_trend else None,
        "rs_vs_market_20d":       round(rs_vs_market, 4),
    }


def _compute_participation_expansion(
    conn: sqlite3.Connection,
    sector: str,
    trade_date: str,
    participation_rate_5d: float,
) -> Optional[float]:
    """
    participation_expansion = participation_rate_5d today − participation_rate_5d 5 trading days ago.

    We look up the most recent prior FULL row for this sector.
    Returns None if no prior row exists.
    """
    prior_rows = conn.execute("""
        SELECT participation_rate_5d
        FROM sector_conviction_daily
        WHERE sector = ?
          AND record_date < ?
          AND data_quality = 'FULL'
          AND participation_rate_5d IS NOT NULL
        ORDER BY record_date DESC
        LIMIT 5
    """, (sector, trade_date)).fetchall()

    if not prior_rows:
        return None

    prior_5d = prior_rows[-1][0]   # oldest of the last-5 prior rows
    return round(participation_rate_5d - prior_5d, 4)


def _compute_consensus_score(
    participation_rate_5d: Optional[float],
    participation_expansion: Optional[float],
    rs_vs_market_20d: Optional[float],
    volume_trend_10d: Optional[float],
) -> Optional[float]:
    """
    consensus_score ∈ [0.0, 10.0]

    Combines:
    - participation_rate_5d     (0–4 pts)
    - participation_expansion   (0–2 pts, penalises contracting)
    - rs_vs_market_20d          (0–2 pts)
    - volume_trend_10d          (0–2 pts)

    None components contribute 0 pts and are noted in the score.
    """
    if participation_rate_5d is None:
        return None

    # Participation base: 0 → 0 pts; 1.0 → 4 pts
    part_pts = min(4.0, participation_rate_5d * 4.0)

    # Expansion: max 2 pts; negative expansion reduces score
    exp_pts = 0.0
    if participation_expansion is not None:
        exp_pts = max(-2.0, min(2.0, participation_expansion * 20.0))

    # RS: max 2 pts; neutral at 0%, -2 if -10%
    rs_pts = 0.0
    if rs_vs_market_20d is not None:
        rs_pts = max(-2.0, min(2.0, rs_vs_market_20d / 5.0))

    # Volume trend: max 2 pts; 1.0× = neutral; 2.0× = max
    vol_pts = 0.0
    if volume_trend_10d is not None:
        vol_pts = max(0.0, min(2.0, (volume_trend_10d - 0.5) / 1.5 * 2.0))

    raw = part_pts + exp_pts + rs_pts + vol_pts
    # Clamp to [0, 10]
    return round(max(0.0, min(10.0, raw)), 4)


# ---------------------------------------------------------------------------
# Sub-B: Capital Flow Intelligence
# ---------------------------------------------------------------------------

def _get_capital_flow(
    conn: sqlite3.Connection,
    sector: str,
    trade_date: str,
    lookback_days: int = 5,
) -> tuple[float, str]:
    """
    Returns (capital_flow_score, data_quality_tier).

    data_quality_tier: "FULL" | "SPARSE" | "UNAVAILABLE"

    When UNAVAILABLE: score = CAPITAL_FLOW_NEUTRAL (0.5)
    When SPARSE:      score = CAPITAL_FLOW_NEUTRAL (0.5)
    When FULL:        score computed from buy/sell balance

    Lookback is last `lookback_days` trading days.
    """
    # Get the lookback start date using trading_calendar
    cal_rows = conn.execute("""
        SELECT calendar_date
        FROM trading_calendar
        WHERE calendar_date <= ? AND is_trading_day = 1
        ORDER BY calendar_date DESC
        LIMIT ?
    """, (trade_date, lookback_days + 1)).fetchall()

    if len(cal_rows) < 2:
        # Calendar not populated enough — use raw date arithmetic fallback
        from datetime import datetime, timedelta
        dt = datetime.strptime(trade_date, "%Y-%m-%d")
        from_date = (dt - timedelta(days=lookback_days * 2)).strftime("%Y-%m-%d")
    else:
        from_date = cal_rows[-1][0]

    deals = conn.execute("""
        SELECT buy_sell, quantity, price
        FROM bulk_block_deals
        WHERE sector = ?
          AND trade_date >= ?
          AND trade_date <= ?
    """, (sector, from_date, trade_date)).fetchall()

    deal_count = len(deals)

    if deal_count == 0:
        return CAPITAL_FLOW_NEUTRAL, "UNAVAILABLE"

    if deal_count < CAPITAL_FLOW_FULL_THRESHOLD:
        return CAPITAL_FLOW_NEUTRAL, "SPARSE"

    # FULL: compute buy/sell balance
    buy_value  = sum((q or 0) * (p or 0) for bs, q, p in deals if bs == "B")
    sell_value = sum((q or 0) * (p or 0) for bs, q, p in deals if bs == "S")
    total      = buy_value + sell_value

    if total == 0:
        return CAPITAL_FLOW_NEUTRAL, "FULL"

    # Score: 0.5 = balanced; > 0.5 = net buying; < 0.5 = net selling
    score = buy_value / total
    return round(score, 4), "FULL"


# ---------------------------------------------------------------------------
# Sub-C: Theme Phase Engine
# ---------------------------------------------------------------------------

def _detect_theme_phase(
    participation_rate_5d: float,
    participation_expansion: Optional[float],
    volume_trend_10d: Optional[float],
) -> Optional[str]:
    """
    Classify the current theme phase for a sector using MAS Section 5, Layer 1.5 Sub-C:

    EMERGENCE    — participation 30–50%, week-over-week delta > 0
    ACCELERATION — participation 50–65%, delta still positive
    CONSENSUS    — participation 65–80%, delta flat or decelerating
    CROWDING     — participation > 80% OR (high participation AND volume declining)
    EXHAUSTION   — participation declining from peak AND volume asymmetric to downside

    Returns None when conditions are ambiguous.
    """
    p = participation_rate_5d
    exp = participation_expansion if participation_expansion is not None else 0.0
    vol_trend = volume_trend_10d if volume_trend_10d is not None else 1.0

    # CROWDING: check first (most critical risk state)
    if p > 0.80:
        return "CROWDING"
    if p > 0.65 and vol_trend < 0.85:
        # High participation but volume is declining per participant
        return "CROWDING"

    # EXHAUSTION: participation declining from peak
    if p < 0.65 and exp < -0.05 and vol_trend < 0.90:
        return "EXHAUSTION"

    # CONSENSUS: 65–80%, decelerating
    if 0.65 <= p <= 0.80:
        return "CONSENSUS"

    # ACCELERATION: 50–65%, still rising
    if 0.50 <= p <= 0.65 and exp >= 0:
        return "ACCELERATION"

    # EMERGENCE: 30–50%, rising
    if 0.30 <= p <= 0.50 and exp > 0:
        return "EMERGENCE"

    return None


def _update_theme_phase_history(
    conn: sqlite3.Connection,
    sector: str,
    new_phase: Optional[str],
    trade_date: str,
    data_quality: str,
    peak_participation_rate: Optional[float],
    amplitude_pct: Optional[float],
    avg_volume_ratio: Optional[float],
    regime: Optional[str],
) -> None:
    """
    Write to theme_phase_history on detected phase transitions.
    PARTIAL data rows never trigger a transition.

    Rules:
    - If current open phase == new_phase: no write (same phase continues)
    - If current open phase != new_phase: close old record, open new record
    - If no open phase and new_phase is not None: open new record
    """
    if data_quality == "PARTIAL" or new_phase is None:
        return

    # Find current open phase record (exited_at IS NULL)
    current = conn.execute("""
        SELECT record_id, phase, entered_at
        FROM theme_phase_history
        WHERE sector = ? AND exited_at IS NULL
        ORDER BY entered_at DESC
        LIMIT 1
    """, (sector,)).fetchone()

    if current is None:
        # No open phase — open a new record
        _open_phase_record(conn, sector, new_phase, trade_date, regime,
                           peak_participation_rate, amplitude_pct, avg_volume_ratio)
        return

    current_record_id, current_phase, entered_at = current

    if current_phase == new_phase:
        # Same phase — no transition needed
        return

    # Phase transition: close the old record and open a new one
    # Compute duration in trading days
    duration = _count_trading_days_between(conn, entered_at, trade_date)
    conn.execute("""
        UPDATE theme_phase_history
        SET exited_at = ?,
            duration_trading_days = ?
        WHERE record_id = ?
    """, (trade_date, duration, current_record_id))

    _open_phase_record(conn, sector, new_phase, trade_date, regime,
                       peak_participation_rate, amplitude_pct, avg_volume_ratio)
    log.info(
        "[Layer1.5] %s: phase transition %s → %s (duration: %s trading days)",
        sector, current_phase, new_phase, duration,
    )


def _open_phase_record(
    conn: sqlite3.Connection,
    sector: str,
    phase: str,
    entered_at: str,
    regime: Optional[str],
    peak_participation_rate: Optional[float],
    amplitude_pct: Optional[float],
    avg_volume_ratio: Optional[float],
) -> None:
    conn.execute("""
        INSERT INTO theme_phase_history
            (record_id, sector, phase, entered_at, regime_during,
             peak_participation_rate, amplitude_pct, avg_volume_ratio)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        str(uuid.uuid4()),
        sector, phase, entered_at, regime,
        peak_participation_rate, amplitude_pct, avg_volume_ratio,
    ))


def _count_trading_days_between(
    conn: sqlite3.Connection,
    from_date: str,
    to_date: str,
) -> Optional[int]:
    """Count NSE trading days between two dates (inclusive of both endpoints)."""
    row = conn.execute("""
        SELECT COUNT(*) FROM trading_calendar
        WHERE calendar_date >= ? AND calendar_date <= ? AND is_trading_day = 1
    """, (from_date, to_date)).fetchone()
    if row and row[0] > 0:
        return row[0]
    # Fallback: use raw count of sector_conviction_daily rows
    row2 = conn.execute("""
        SELECT COUNT(*) FROM sector_conviction_daily
        WHERE sector = ? AND record_date >= ? AND record_date <= ?
    """, ("_ANY_", from_date, to_date)).fetchone()
    return row2[0] if row2 else None


# ---------------------------------------------------------------------------
# Theme history guard
# ---------------------------------------------------------------------------

def _has_sufficient_phase_history(
    conn: sqlite3.Connection,
    sector: str,
    trade_date: str,
) -> bool:
    """
    Theme Phase Engine requires >= 30 days of FULL sector_conviction_daily rows.
    A phase detector without history is a threshold classifier, not a phase detector.
    """
    row = conn.execute("""
        SELECT COUNT(*) FROM sector_conviction_daily
        WHERE sector = ?
          AND record_date < ?
          AND data_quality = 'FULL'
          AND participation_rate_5d IS NOT NULL
    """, (sector, trade_date)).fetchone()
    return (row[0] if row else 0) >= THEME_PHASE_MIN_HISTORY


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def run_sector_conviction(
    conn: sqlite3.Connection,
    trade_date: str,
    regime: str,
    sectors: Optional[list[str]] = None,
) -> dict:
    """
    Run Layer 1.5 Sub-A + Sub-B + Sub-C for all sectors on trade_date.

    Writes one row per sector to sector_conviction_daily.
    Writes to theme_phase_history on phase transitions (if 30+ day history).

    Returns a dict {sector: {"data_quality": ..., "theme_phase": ...}} for logging.
    """
    if sectors is None:
        rows = conn.execute(
            "SELECT DISTINCT sector FROM universe_stocks WHERE is_active = 1"
        ).fetchall()
        sectors = [r[0] for r in rows]

    summary = {}

    with conn:
        for sector in sectors:
            _process_sector(conn, sector, trade_date, regime, summary)

    return summary


def _process_sector(
    conn: sqlite3.Connection,
    sector: str,
    trade_date: str,
    regime: str,
    summary: dict,
) -> None:
    """Process one sector — compute all Sub-A/B/C fields and write the row."""

    # ------------------------------------------------------------------
    # Sub-A: Consensus Shift
    # ------------------------------------------------------------------
    part_data = _compute_participation_rates(conn, sector, trade_date)
    if part_data is None:
        log.warning("[Layer1.5] %s: no participation data for %s", sector, trade_date)
        return

    data_quality         = part_data["data_quality"]
    stocks_total         = part_data["stocks_total"]
    stocks_with_data     = part_data["stocks_with_data"]
    participation_rate_1d = part_data["participation_rate_1d"]
    participation_rate_5d = part_data["participation_rate_5d"]
    volume_trend_10d      = part_data["volume_trend_10d"]
    rs_vs_market_20d      = part_data["rs_vs_market_20d"]

    # Participation expansion — only computable if FULL row
    participation_expansion = None
    if data_quality == "FULL" and participation_rate_5d is not None:
        participation_expansion = _compute_participation_expansion(
            conn, sector, trade_date, participation_rate_5d
        )

    # Consensus score — None if PARTIAL
    consensus_score = None
    if data_quality == "FULL":
        consensus_score = _compute_consensus_score(
            participation_rate_5d,
            participation_expansion,
            rs_vs_market_20d,
            volume_trend_10d,
        )

    # ------------------------------------------------------------------
    # Sub-B: Capital Flow
    # ------------------------------------------------------------------
    if data_quality == "FULL":
        capital_flow_score, capital_flow_dq = _get_capital_flow(conn, sector, trade_date)
    else:
        # PARTIAL: suppress all outputs
        capital_flow_score, capital_flow_dq = CAPITAL_FLOW_NEUTRAL, "UNAVAILABLE"

    # ------------------------------------------------------------------
    # Sector conviction score
    # 0.4 × capital_flow + 0.6 × consensus
    # When capital_flow_dq == "UNAVAILABLE": pure consensus (weight → 1.0)
    # ------------------------------------------------------------------
    sector_conviction_score = None
    if consensus_score is not None and data_quality == "FULL":
        if capital_flow_dq == "UNAVAILABLE":
            sector_conviction_score = round(consensus_score / 10.0, 4)
        else:
            sector_conviction_score = round(
                CAPITAL_FLOW_WEIGHT * capital_flow_score
                + CONSENSUS_WEIGHT * (consensus_score / 10.0),
                4,
            )

    # ------------------------------------------------------------------
    # Sub-C: Theme Phase Engine
    # Only activates when 30+ days of history available
    # ------------------------------------------------------------------
    theme_phase = None
    if (
        data_quality == "FULL"
        and participation_rate_5d is not None
        and _has_sufficient_phase_history(conn, sector, trade_date)
    ):
        theme_phase = _detect_theme_phase(
            participation_rate_5d,
            participation_expansion,
            volume_trend_10d,
        )
        _update_theme_phase_history(
            conn,
            sector=sector,
            new_phase=theme_phase,
            trade_date=trade_date,
            data_quality=data_quality,
            peak_participation_rate=participation_rate_5d,
            amplitude_pct=None,   # amplitude computed on phase exit — set on open
            avg_volume_ratio=volume_trend_10d,
            regime=regime,
        )

    # ------------------------------------------------------------------
    # Write row to sector_conviction_daily (INSERT OR REPLACE)
    # ------------------------------------------------------------------
    conn.execute("""
        INSERT OR REPLACE INTO sector_conviction_daily (
            record_date, sector,
            participation_rate_1d, participation_rate_5d,
            participation_expansion, rs_vs_market_20d, volume_trend_10d,
            consensus_score,
            capital_flow_score, capital_flow_data_quality,
            sector_conviction_score,
            theme_phase,
            data_quality, stocks_with_data, stocks_total
        ) VALUES (
            ?, ?,
            ?, ?, ?, ?, ?,
            ?,
            ?, ?,
            ?,
            ?,
            ?, ?, ?
        )
    """, (
        trade_date, sector,
        participation_rate_1d, participation_rate_5d,
        participation_expansion, rs_vs_market_20d, volume_trend_10d,
        consensus_score,
        capital_flow_score, capital_flow_dq,
        sector_conviction_score,
        theme_phase,
        data_quality, stocks_with_data, stocks_total,
    ))

    summary[sector] = {
        "data_quality": data_quality,
        "theme_phase":  theme_phase,
        "participation_rate_5d": participation_rate_5d,
        "consensus_score": consensus_score,
        "sector_conviction_score": sector_conviction_score,
    }

    log.info(
        "[Layer1.5] %s %s: dq=%s part5d=%.2f theme=%s conviction=%.3f",
        trade_date, sector, data_quality,
        participation_rate_5d or 0,
        theme_phase or "—",
        sector_conviction_score or 0,
    )
