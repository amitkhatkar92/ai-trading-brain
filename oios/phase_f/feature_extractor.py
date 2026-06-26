"""
oios/phase_f/feature_extractor.py
Phase F Step F1.3 — Leader Feature Extraction Engine

For each captured leader, compute 12 features across three groups:

  Technical (6):
    above_20dma      1.0 if close > 20-day SMA, else 0.0
    above_50dma      1.0 if close > 50-day SMA, else 0.0
    above_200dma     1.0 if close > 200-day SMA, else 0.0
    rs_score         relative strength vs universe median return (20d)
    volume_ratio     today_vol / 20d_avg_vol  (already on LeaderRow, reused)
    atr_expansion    today ATR / 20d avg ATR

  OIOS (4):
    theme_phase_score  numeric mapping of current sector theme phase
    sector_conviction  from sector_conviction_daily.sector_conviction_score
    active_archetypes  count of ACTIVE/WATCHING signals in signal_births for this symbol
    cause_score        most recent cause_score for any ACTIVE opportunity on this symbol

  Structural (2):
    sector_rank      conviction rank of this symbol's sector vs all sectors today
    sector_purity    sector_purity_score from universe_stocks

All features stored in market_leader_features (one row per feature).
NULL stored when data is genuinely unavailable (not an error).

ISOLATION CONTRACT
------------------
Reads:   ohlcv_daily, universe_stocks, sector_conviction_daily,
         signal_births, cause_scores, opportunities
Writes:  market_leader_features
No writes to any A–E table.
"""

from __future__ import annotations

import logging
import sqlite3
import uuid
from datetime import datetime
from typing import Optional

log = logging.getLogger(__name__)

# Theme phase → numeric score (higher = more mature / riskier)
_THEME_PHASE_SCORE: dict[str, float] = {
    "EMERGENCE":     1.0,
    "ACCELERATION":  2.0,
    "CONSENSUS":     3.0,
    "CROWDING":      4.0,
    "EXHAUSTION":    5.0,
}

# Features extracted per leader
_TECHNICAL_FEATURES   = ("above_20dma", "above_50dma", "above_200dma",
                          "rs_score", "volume_ratio", "atr_expansion")
_OIOS_FEATURES        = ("theme_phase_score", "sector_conviction",
                          "active_archetypes", "cause_score")
_STRUCTURAL_FEATURES  = ("sector_rank", "sector_purity")
ALL_FEATURES          = _TECHNICAL_FEATURES + _OIOS_FEATURES + _STRUCTURAL_FEATURES


def extract_features(
    leader_id: str,
    symbol: str,
    trade_date: str,
    sector: str,
    conn: sqlite3.Connection,
) -> dict[str, Optional[float]]:
    """
    Compute all 12 features for a single leader and persist to
    market_leader_features.

    Returns the feature dict (feature_name → value or None).
    """
    now = datetime.utcnow().isoformat(timespec="seconds")

    # Pre-load OHLCV history once (200 days for all DMA calculations)
    history = _load_ohlcv(symbol, trade_date, 210, conn)
    close_series = [r["close"] for r in history]
    vol_series   = [r["volume"] for r in history]
    high_series  = [r["high"] for r in history]
    low_series   = [r["low"] for r in history]

    today_close = close_series[0] if close_series else None

    features: dict[str, Optional[float]] = {}

    # ── Technical ─────────────────────────────────────────────────────────────
    features["above_20dma"]   = _above_sma(close_series, today_close, 20)
    features["above_50dma"]   = _above_sma(close_series, today_close, 50)
    features["above_200dma"]  = _above_sma(close_series, today_close, 200)
    features["rs_score"]      = _rs_score(symbol, trade_date, conn)
    features["volume_ratio"]  = _volume_ratio(vol_series)
    features["atr_expansion"] = _atr_expansion(high_series, low_series, close_series)

    # ── OIOS ──────────────────────────────────────────────────────────────────
    scd = _load_scd(trade_date, sector, conn)
    features["theme_phase_score"] = _THEME_PHASE_SCORE.get(
        scd.get("theme_phase", ""), None
    ) if scd else None
    features["sector_conviction"] = scd.get("sector_conviction_score") if scd else None
    features["active_archetypes"] = _count_active_archetypes(symbol, trade_date, conn)
    features["cause_score"]       = _latest_cause_score(symbol, trade_date, conn)

    # ── Structural ────────────────────────────────────────────────────────────
    features["sector_rank"]   = _sector_rank(sector, trade_date, conn)
    features["sector_purity"] = _sector_purity(symbol, conn)

    # Persist
    _upsert_features(leader_id, features, now, conn)
    return features


def extract_features_batch(
    leaders: list[dict],  # list of {"leader_id", "symbol", "trade_date", "sector"}
    conn: sqlite3.Connection,
) -> None:
    """Convenience wrapper for processing a full day's leaders in one call."""
    for ldr in leaders:
        try:
            extract_features(
                ldr["leader_id"], ldr["symbol"],
                ldr["trade_date"], ldr["sector"], conn
            )
        except Exception as exc:
            log.warning("[FeatureExtractor] %s on %s: %s",
                        ldr["symbol"], ldr["trade_date"], exc)


# ── OHLCV helpers ─────────────────────────────────────────────────────────────

def _load_ohlcv(
    symbol: str, trade_date: str, days: int, conn: sqlite3.Connection
) -> list[dict]:
    rows = conn.execute("""
        SELECT trade_date, open, high, low, close, volume
        FROM ohlcv_daily
        WHERE symbol = ? AND trade_date <= ?
        ORDER BY trade_date DESC
        LIMIT ?
    """, (symbol, trade_date, days)).fetchall()
    return [dict(r) for r in rows]


def _sma(series: list[float], period: int) -> Optional[float]:
    if len(series) < period:
        return None
    return sum(series[:period]) / period


def _above_sma(
    close_series: list[float], today_close: Optional[float], period: int
) -> Optional[float]:
    if today_close is None or len(close_series) < period + 1:
        return None
    # Exclude today from the SMA calculation (use prior period closes)
    sma = _sma(close_series[1:], period)
    if sma is None:
        return None
    return 1.0 if today_close > sma else 0.0


def _volume_ratio(vol_series: list[float]) -> Optional[float]:
    if len(vol_series) < 2:
        return None
    today_vol = vol_series[0]
    prev_vols = [v for v in vol_series[1:21] if v and v > 0]
    if not prev_vols:
        return None
    return round(today_vol / (sum(prev_vols) / len(prev_vols)), 3)


def _atr(highs: list[float], lows: list[float], closes: list[float], period: int) -> Optional[float]:
    """Average True Range over period using prior close."""
    if len(highs) < period + 1:
        return None
    trs = []
    for i in range(period):
        h, l, pc = highs[i], lows[i], closes[i + 1]
        trs.append(max(h - l, abs(h - pc), abs(l - pc)))
    return sum(trs) / len(trs) if trs else None


def _atr_expansion(
    highs: list[float], lows: list[float], closes: list[float]
) -> Optional[float]:
    """Today ATR / 20-day average ATR."""
    if len(highs) < 22:
        return None
    today_atr = _atr(highs, lows, closes, 1)
    avg_atr   = _atr(highs[1:], lows[1:], closes[1:], 20)
    if today_atr is None or avg_atr is None or avg_atr == 0:
        return None
    return round(today_atr / avg_atr, 3)


# ── RS score ──────────────────────────────────────────────────────────────────

def _rs_score(symbol: str, trade_date: str, conn: sqlite3.Connection) -> Optional[float]:
    """
    Relative Strength vs universe median 20-day return.
    rs_score > 1.0  → outperforming; < 1.0 → underperforming.
    """
    # Symbol's 20d return
    rows = conn.execute("""
        SELECT close FROM ohlcv_daily
        WHERE symbol = ? AND trade_date <= ?
        ORDER BY trade_date DESC LIMIT 21
    """, (symbol, trade_date)).fetchall()
    if len(rows) < 21:
        return None
    sym_return = (rows[0][0] - rows[20][0]) / rows[20][0] if rows[20][0] else None
    if sym_return is None:
        return None

    # Universe median 20d return
    all_returns = conn.execute("""
        WITH latest AS (
            SELECT symbol, close, ROW_NUMBER() OVER (PARTITION BY symbol ORDER BY trade_date DESC) rn
            FROM ohlcv_daily WHERE trade_date <= ?
        ),
        d20 AS (
            SELECT symbol, close, ROW_NUMBER() OVER (PARTITION BY symbol ORDER BY trade_date DESC) rn
            FROM ohlcv_daily WHERE trade_date <= ?
            AND trade_date > date(?, '-30 days')
        )
        SELECT l.close, d.close
        FROM (SELECT symbol, close FROM latest WHERE rn=1) l
        JOIN (SELECT symbol, close FROM (
            SELECT symbol, close, ROW_NUMBER() OVER (PARTITION BY symbol ORDER BY trade_date) rn2
            FROM ohlcv_daily WHERE trade_date <= date(?, '-20 days') AND trade_date > date(?, '-40 days')
        ) WHERE rn2=1) d ON l.symbol = d.symbol
        WHERE d.close > 0
    """, (trade_date, trade_date, trade_date, trade_date, trade_date)).fetchall()

    if not all_returns:
        return None
    universe_returns = [(r[0] - r[1]) / r[1] for r in all_returns if r[1]]
    if not universe_returns:
        return None
    universe_returns.sort()
    mid = len(universe_returns) // 2
    median_ret = universe_returns[mid]
    if median_ret == 0:
        return None
    return round(sym_return / abs(median_ret), 3)


# ── OIOS read helpers ─────────────────────────────────────────────────────────

def _load_scd(trade_date: str, sector: str, conn: sqlite3.Connection) -> Optional[dict]:
    row = conn.execute("""
        SELECT theme_phase, sector_conviction_score
        FROM sector_conviction_daily
        WHERE record_date = ? AND sector = ?
    """, (trade_date, sector)).fetchone()
    return dict(row) if row else None


def _count_active_archetypes(symbol: str, trade_date: str, conn: sqlite3.Connection) -> Optional[float]:
    try:
        row = conn.execute("""
            SELECT COUNT(*) FROM signal_births
            WHERE symbol = ?
              AND current_state IN ('ACTIVE', 'WATCHING')
              AND detected_at <= ?
        """, (symbol, trade_date)).fetchone()
        return float(row[0]) if row else 0.0
    except Exception:
        return None


def _latest_cause_score(symbol: str, trade_date: str, conn: sqlite3.Connection) -> Optional[float]:
    """Latest cause_score for any ACTIVE opportunity on this symbol."""
    try:
        row = conn.execute("""
            SELECT cs.cause_score
            FROM cause_scores cs
            JOIN opportunities o ON cs.opportunity_id = o.opportunity_id
            WHERE o.symbol = ?
              AND cs.score_date <= ?
              AND o.current_state IN ('ACTIVE', 'WATCHING')
            ORDER BY cs.score_date DESC
            LIMIT 1
        """, (symbol, trade_date)).fetchone()
        return float(row[0]) if row and row[0] is not None else None
    except Exception:
        return None


# ── Structural helpers ────────────────────────────────────────────────────────

def _sector_rank(sector: str, trade_date: str, conn: sqlite3.Connection) -> Optional[float]:
    """Rank of this sector by sector_conviction_score on trade_date (1 = highest)."""
    try:
        rows = conn.execute("""
            SELECT sector, sector_conviction_score
            FROM sector_conviction_daily
            WHERE record_date = ?
              AND sector_conviction_score IS NOT NULL
            ORDER BY sector_conviction_score DESC
        """, (trade_date,)).fetchall()
        for i, r in enumerate(rows, start=1):
            if r[0] == sector:
                return float(i)
        return None
    except Exception:
        return None


def _sector_purity(symbol: str, conn: sqlite3.Connection) -> Optional[float]:
    row = conn.execute(
        "SELECT sector_purity_score FROM universe_stocks WHERE symbol = ?", (symbol,)
    ).fetchone()
    return float(row[0]) if row else None


# ── Persist ───────────────────────────────────────────────────────────────────

def _upsert_features(
    leader_id: str,
    features: dict[str, Optional[float]],
    captured_at: str,
    conn: sqlite3.Connection,
) -> None:
    from datetime import datetime as _dt
    _updated_at = _dt.utcnow().isoformat(timespec="seconds")
    sql = """
        INSERT OR REPLACE INTO market_leader_features
            (feature_id, leader_id, feature_name, feature_value, captured_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """
    rows = []
    for name, value in features.items():
        fid = f"FT_{leader_id}_{name}"
        rows.append((fid, leader_id, name, value, captured_at, _updated_at))
    with conn:
        conn.executemany(sql, rows)
