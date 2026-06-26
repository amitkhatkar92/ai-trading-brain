"""
oios/phase_f/control_population.py
Phase F Step F3.1 — Control Group Builder

For every WINNER captured on a given day, find 3–10 stocks from the
universe that:
  - were NOT winners on that day
  - had a similar feature fingerprint (theme_phase, sector_conviction,
    volume_ratio, DMA status, delivery pct)

These control stocks are stored in market_research_controls so that
outcome_tracker can fill in their forward returns and failure_analyzer
can study what went differently.

Fingerprint Construction
------------------------
Five input features are discretised and hashed:
  theme_phase        : raw text (EMERGENCE / ACCELERATION / ...)
  sector_conviction  : bucketed LOW / MED / HIGH
  volume_ratio       : bucketed LOW (<0.8) / NORMAL (0.8-1.5) / HIGH (>1.5)
  dma_status         : above_20dma + above_50dma concatenated ("11", "10", "01", "00")
  delivery_pct       : bucketed LOW (<40%) / MED (40–70%) / HIGH (>70%)

SHA-256 of the concatenated string provides the fingerprint_hash.
Stocks with matching hash that did NOT appear in market_leaders_daily
for that date are candidates.

ISOLATION CONTRACT
------------------
Reads:   market_leaders_daily, market_leader_features, universe_stocks,
         bhav_daily, ohlcv_daily
Writes:  market_research_controls
No writes to any A–E table.
"""

from __future__ import annotations

import hashlib
import logging
import sqlite3
import uuid
from datetime import datetime
from typing import Optional

log = logging.getLogger(__name__)

# Number of controls to find per winner
MIN_CONTROLS = 3
MAX_CONTROLS = 10

# Same-sector weighting: prefer controls in the same sector as the winner
SAME_SECTOR_BONUS = 2.0  # multiply fingerprint match score


def build_controls_for_date(trade_date: str, conn: sqlite3.Connection) -> int:
    """
    Build control group for all WINNER rows on trade_date.

    Returns number of control rows inserted.
    """
    winners = _get_winners(trade_date, conn)
    if not winners:
        log.info("[ControlPop] No winners found for %s", trade_date)
        return 0

    already_leaders = _get_all_leader_symbols(trade_date, conn)
    universe = _get_universe(conn)
    non_leaders = [s for s in universe if s not in already_leaders]

    # Explicit degradation notice — bhav_daily is always empty on non-India VPS
    # (NSE Akamai CDN blocks foreign IPs).  delivery_pct will default to
    # bucket "?" for all symbols; fingerprint matching still works correctly.
    _bhav_count = conn.execute(
        "SELECT COUNT(*) FROM bhav_daily WHERE trade_date = ?", (trade_date,)
    ).fetchone()[0]
    if _bhav_count == 0:
        log.info(
            "[ControlPop] bhav_daily has 0 rows for %s — "
            "delivery_pct will default to bucket '?' (non-India VPS or weekend).",
            trade_date,
        )

    if len(non_leaders) < MIN_CONTROLS:
        log.warning("[ControlPop] Universe too small to build controls (%d non-leaders)", len(non_leaders))
        return 0

    inserted = 0
    for winner in winners:
        inserted += _build_for_winner(winner, non_leaders, trade_date, conn)

    log.info("[ControlPop] %s: inserted %d control rows for %d winners",
             trade_date, inserted, len(winners))
    return inserted


# ── Core matching logic ───────────────────────────────────────────────────────

def _build_for_winner(
    winner: dict,
    candidates: list[str],
    trade_date: str,
    conn: sqlite3.Connection,
) -> int:
    winner_fp   = _compute_fingerprint(winner["leader_id"], winner["sector"], trade_date, conn)
    winner_hash = _hash_fingerprint(winner_fp)

    # Score every candidate by fingerprint similarity
    scored: list[tuple[str, float]] = []
    for sym in candidates:
        if sym == winner["symbol"]:
            continue
        cand_fp   = _compute_fingerprint_for_symbol(sym, trade_date, conn)
        cand_hash = _hash_fingerprint(cand_fp)
        score = _similarity_score(winner_fp, cand_fp, winner["sector"], sym, conn)
        scored.append((sym, score))

    # Sort by similarity descending, take top MAX_CONTROLS
    scored.sort(key=lambda x: x[1], reverse=True)
    controls = scored[:MAX_CONTROLS]

    if not controls:
        return 0

    now = datetime.utcnow().isoformat(timespec="seconds")
    rows = []
    for sym, _ in controls:
        cand_fp   = _compute_fingerprint_for_symbol(sym, trade_date, conn)
        cand_hash = _hash_fingerprint(cand_fp)
        cid = f"CTRL_{winner['leader_id']}_{sym}"
        rows.append((
            cid, trade_date, sym, cand_hash,
            winner["leader_id"], "UNKNOWN", now
        ))

    sql = """
        INSERT OR IGNORE INTO market_research_controls
            (control_id, trade_date, symbol, fingerprint_hash,
             matched_leader_id, outcome_class, captured_at)
        VALUES (?,?,?,?,?,?,?)
    """
    with conn:
        conn.executemany(sql, rows)
    return len(rows)


# ── Fingerprint computation ───────────────────────────────────────────────────

def _compute_fingerprint(
    leader_id: str, sector: str, trade_date: str, conn: sqlite3.Connection
) -> dict:
    """Load feature values for a captured leader from market_leader_features."""
    rows = conn.execute("""
        SELECT feature_name, feature_value
        FROM market_leader_features
        WHERE leader_id = ?
    """, (leader_id,)).fetchall()
    feat = {r[0]: r[1] for r in rows}

    # Also load delivery pct from bhav_daily
    symbol = conn.execute(
        "SELECT symbol FROM market_leaders_daily WHERE leader_id = ?", (leader_id,)
    ).fetchone()
    delivery = _get_delivery_pct(symbol[0] if symbol else "", trade_date, conn) if symbol else None

    return {
        "theme_phase":        _get_feature(feat, "theme_phase_score"),
        "sector_conviction":  _get_feature(feat, "sector_conviction"),
        "volume_ratio":       _get_feature(feat, "volume_ratio"),
        "above_20dma":        _get_feature(feat, "above_20dma"),
        "above_50dma":        _get_feature(feat, "above_50dma"),
        "delivery_pct":       delivery,
        "delivery_available": 1.0 if delivery is not None else 0.0,
        "sector":             sector,
    }


def _compute_fingerprint_for_symbol(
    symbol: str, trade_date: str, conn: sqlite3.Connection
) -> dict:
    """Compute fingerprint for a non-leader candidate directly from raw data."""
    # Volume ratio
    vols = conn.execute("""
        SELECT volume FROM ohlcv_daily
        WHERE symbol = ? AND trade_date <= ?
        ORDER BY trade_date DESC LIMIT 21
    """, (symbol, trade_date)).fetchall()
    if len(vols) >= 2:
        today_vol = vols[0][0] or 0
        avg_vol = sum(r[0] for r in vols[1:] if r[0]) / max(1, len(vols) - 1)
        vol_ratio = today_vol / avg_vol if avg_vol else 1.0
    else:
        vol_ratio = None

    # DMA status
    closes = conn.execute("""
        SELECT close FROM ohlcv_daily
        WHERE symbol = ? AND trade_date <= ?
        ORDER BY trade_date DESC LIMIT 201
    """, (symbol, trade_date)).fetchall()
    close_series = [r[0] for r in closes]
    today_close  = close_series[0] if close_series else None

    above_20 = _above_sma(close_series, today_close, 20)
    above_50 = _above_sma(close_series, today_close, 50)

    # Sector
    sec_row = conn.execute(
        "SELECT sector FROM universe_stocks WHERE symbol = ?", (symbol,)
    ).fetchone()
    sector = sec_row[0] if sec_row else "UNKNOWN"

    # Sector conviction
    scd = conn.execute("""
        SELECT sector_conviction_score, theme_phase
        FROM sector_conviction_daily
        WHERE record_date = ? AND sector = ?
    """, (trade_date, sector)).fetchone()

    delivery = _get_delivery_pct(symbol, trade_date, conn)

    return {
        "theme_phase":        float(scd[1] and 1.0) if scd else None,
        "sector_conviction":  float(scd[0]) if scd and scd[0] else None,
        "volume_ratio":       vol_ratio,
        "above_20dma":        above_20,
        "above_50dma":        above_50,
        "delivery_pct":       delivery,
        "delivery_available": 1.0 if delivery is not None else 0.0,
        "sector":             sector,
    }


def _get_feature(feat: dict, name: str) -> Optional[float]:
    return feat.get(name)


def _above_sma(series: list[float], today: Optional[float], period: int) -> Optional[float]:
    if today is None or len(series) < period + 1:
        return None
    sma = sum(series[1:period + 1]) / period
    return 1.0 if today > sma else 0.0


def _get_delivery_pct(symbol: str, trade_date: str, conn: sqlite3.Connection) -> Optional[float]:
    row = conn.execute("""
        SELECT delivery_pct FROM bhav_daily
        WHERE symbol = ? AND trade_date = ?
    """, (symbol, trade_date)).fetchone()
    return float(row[0]) if row and row[0] is not None else None


def _bucket_vol(v: Optional[float]) -> str:
    if v is None:
        return "?"
    if v < 0.8:
        return "LOW"
    if v < 1.5:
        return "NORM"
    return "HIGH"


def _bucket_conviction(v: Optional[float]) -> str:
    if v is None:
        return "?"
    if v < 4.0:
        return "LOW"
    if v < 7.0:
        return "MED"
    return "HIGH"


def _bucket_delivery(v: Optional[float]) -> str:
    if v is None:
        return "?"
    if v < 0.40:
        return "LOW"
    if v < 0.70:
        return "MED"
    return "HIGH"


def _hash_fingerprint(fp: dict) -> str:
    parts = [
        str(int(fp.get("theme_phase") or 0)),
        _bucket_conviction(fp.get("sector_conviction")),
        _bucket_vol(fp.get("volume_ratio")),
        f"{int(fp.get('above_20dma') or 0)}{int(fp.get('above_50dma') or 0)}",
        _bucket_delivery(fp.get("delivery_pct")),
    ]
    raw = "|".join(parts)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _similarity_score(
    winner_fp: dict,
    cand_fp: dict,
    winner_sector: str,
    cand_sym: str,
    conn: sqlite3.Connection,
) -> float:
    """Simple ordinal match score 0–5, with same-sector bonus."""
    score = 0.0
    if _bucket_vol(winner_fp.get("volume_ratio")) == _bucket_vol(cand_fp.get("volume_ratio")):
        score += 1.0
    if _bucket_conviction(winner_fp.get("sector_conviction")) == _bucket_conviction(cand_fp.get("sector_conviction")):
        score += 1.0
    if winner_fp.get("above_20dma") == cand_fp.get("above_20dma"):
        score += 1.0
    if winner_fp.get("above_50dma") == cand_fp.get("above_50dma"):
        score += 1.0
    if _bucket_delivery(winner_fp.get("delivery_pct")) == _bucket_delivery(cand_fp.get("delivery_pct")):
        score += 1.0
    if cand_fp.get("sector") == winner_sector:
        score += SAME_SECTOR_BONUS
    return score


# ── DB helpers ────────────────────────────────────────────────────────────────

def _get_winners(trade_date: str, conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute("""
        SELECT leader_id, symbol, sector
        FROM market_leaders_daily
        WHERE trade_date = ? AND leader_type = 'WINNER'
    """, (trade_date,)).fetchall()
    return [{"leader_id": r[0], "symbol": r[1], "sector": r[2]} for r in rows]


def _get_all_leader_symbols(trade_date: str, conn: sqlite3.Connection) -> set[str]:
    rows = conn.execute(
        "SELECT symbol FROM market_leaders_daily WHERE trade_date = ?", (trade_date,)
    ).fetchall()
    return {r[0] for r in rows}


def _get_universe(conn: sqlite3.Connection) -> list[str]:
    rows = conn.execute(
        "SELECT symbol FROM universe_stocks WHERE is_active = 1"
    ).fetchall()
    return [r[0] for r in rows]
