"""
oios/phase_f/failure_analyzer.py
Phase F Step F4.1 — Failure Attribution Engine

When a control stock matched a winner fingerprint but failed to deliver a
comparable move, this engine assigns candidate failure reasons with confidence
scores.

Candidate Reasons
-----------------
CROWDING          volume_ratio >> winner's ratio → too many participants
WEAK_BREADTH      sector breadth collapsed on the same day
LOW_DELIVERY      delivery_pct < 0.40 → speculative flow, no institutional follow
NO_FLOW           no bulk/block deal evidence within 5 days
NEGATIVE_EARNINGS earnings miss within 30-day window
SECTOR_DIVERGENCE stock moved against sector direction
MARKET_WEAKNESS   market (NIFTY) sold off > 1% on the day

Each reason is scored independently (0.0–1.0) based on available evidence.
Multiple reasons can apply to the same failure.

ISOLATION CONTRACT
------------------
Reads:   market_leaders_daily, market_research_controls, market_leader_features,
         sector_conviction_daily, bhav_daily, bulk_block_deals,
         daily_events, ohlcv_daily
Writes:  failure_attribution
No writes to any A–E table.
"""

from __future__ import annotations

import json
import logging
import sqlite3
import uuid
from datetime import datetime
from typing import Optional

log = logging.getLogger(__name__)

CANDIDATE_REASONS = (
    "CROWDING",
    "WEAK_BREADTH",
    "LOW_DELIVERY",
    "NO_FLOW",
    "NEGATIVE_EARNINGS",
    "SECTOR_DIVERGENCE",
    "MARKET_WEAKNESS",
)

# Minimum confidence threshold to store an attribution
MIN_CONFIDENCE = 0.30

# NIFTY proxy symbol in ohlcv_daily
NIFTY_SYMBOL = "^NSEI"


def analyze_failures(trade_date: str, conn: sqlite3.Connection) -> int:
    """
    Run failure attribution for all control stocks on trade_date that
    underperformed their matched winner.

    Returns number of attribution rows inserted.
    """
    pairs = _get_winner_control_pairs(trade_date, conn)
    if not pairs:
        log.info("[FailureAnalyzer] No winner/control pairs for %s", trade_date)
        return 0

    inserted = 0
    for winner, control in pairs:
        reasons = _analyze(winner, control, trade_date, conn)
        inserted += _persist(control["symbol"], trade_date,
                             winner["leader_id"], reasons, conn)

    log.info("[FailureAnalyzer] %s: inserted %d attribution rows", trade_date, inserted)
    return inserted


# ── Core analysis ─────────────────────────────────────────────────────────────

def _analyze(
    winner: dict,
    control: dict,
    trade_date: str,
    conn: sqlite3.Connection,
) -> dict[str, tuple[float, dict]]:
    """
    Returns {reason: (confidence, evidence_dict)}.
    """
    sym = control["symbol"]
    sec = winner["sector"]
    results: dict[str, tuple[float, dict]] = {}

    # ── CROWDING ──────────────────────────────────────────────────────────────
    ctrl_vol = _get_feature(sym, "volume_ratio", trade_date, conn)
    win_vol  = _get_leader_feature(winner["leader_id"], "volume_ratio", conn)
    if ctrl_vol is not None and win_vol is not None and ctrl_vol > 0:
        ratio = ctrl_vol / win_vol if win_vol else 0
        # if control had much higher volume than winner → crowding risk
        if ctrl_vol > 2.5:
            conf = min(1.0, (ctrl_vol - 2.5) / 2.5)
            results["CROWDING"] = (round(conf, 3), {"ctrl_vol_ratio": ctrl_vol, "win_vol_ratio": win_vol})

    # ── WEAK_BREADTH ──────────────────────────────────────────────────────────
    scd = conn.execute("""
        SELECT consensus_score, participation_rate_1d
        FROM sector_conviction_daily
        WHERE record_date = ? AND sector = ?
    """, (trade_date, sec)).fetchone()
    if scd:
        consensus = scd[0] or 0
        if consensus < 4.0:
            conf = round((4.0 - consensus) / 4.0, 3)
            results["WEAK_BREADTH"] = (conf, {"consensus_score": consensus})

    # ── LOW_DELIVERY ──────────────────────────────────────────────────────────
    bhav = conn.execute("""
        SELECT delivery_pct FROM bhav_daily
        WHERE symbol = ? AND trade_date = ?
    """, (sym, trade_date)).fetchone()
    if bhav and bhav[0] is not None:
        delivery = bhav[0]
        if delivery < 0.40:
            conf = round((0.40 - delivery) / 0.40, 3)
            results["LOW_DELIVERY"] = (conf, {"delivery_pct": delivery})

    # ── NO_FLOW ───────────────────────────────────────────────────────────────
    flow_rows = conn.execute("""
        SELECT COUNT(*) FROM bulk_block_deals
        WHERE symbol = ? AND trade_date BETWEEN date(?, '-5 days') AND ?
          AND buy_sell = 'B'
    """, (sym, trade_date, trade_date)).fetchone()
    flow_count = flow_rows[0] if flow_rows else 0
    if flow_count == 0:
        results["NO_FLOW"] = (0.60, {"bulk_block_buy_count_5d": 0})

    # ── NEGATIVE_EARNINGS ─────────────────────────────────────────────────────
    try:
        earnings = conn.execute("""
            SELECT COUNT(*) FROM daily_events
            WHERE symbol = ?
              AND event_type = 'EARNINGS'
              AND direction  = 'NEGATIVE'
              AND event_date BETWEEN date(?, '-30 days') AND ?
        """, (sym, trade_date, trade_date)).fetchone()
        if earnings and earnings[0] > 0:
            results["NEGATIVE_EARNINGS"] = (0.80, {"negative_earnings_count_30d": earnings[0]})
    except Exception:
        pass  # daily_events table may not yet have data

    # ── SECTOR_DIVERGENCE ─────────────────────────────────────────────────────
    # Symbol return vs sector average
    sym_ret  = _day_return(sym, trade_date, conn)
    win_ret  = winner.get("day_return_pct", 0)
    if sym_ret is not None:
        sector_avg = _sector_avg_return(sec, trade_date, conn)
        if sector_avg is not None and sym_ret < 0 and sector_avg > 0:
            conf = round(min(1.0, abs(sym_ret) / max(0.1, abs(sector_avg))), 3)
            results["SECTOR_DIVERGENCE"] = (conf, {"symbol_return": sym_ret, "sector_avg": sector_avg})

    # ── MARKET_WEAKNESS ───────────────────────────────────────────────────────
    nifty_ret = _day_return(NIFTY_SYMBOL, trade_date, conn)
    if nifty_ret is not None and nifty_ret < -1.0:
        conf = round(min(1.0, abs(nifty_ret + 1.0) / 2.0), 3)
        results["MARKET_WEAKNESS"] = (conf, {"nifty_return": nifty_ret})

    return {r: v for r, v in results.items() if v[0] >= MIN_CONFIDENCE}


# ── Persist ───────────────────────────────────────────────────────────────────

def _persist(
    symbol: str,
    trade_date: str,
    leader_id: str,
    reasons: dict[str, tuple[float, dict]],
    conn: sqlite3.Connection,
) -> int:
    if not reasons:
        return 0
    now = datetime.utcnow().isoformat(timespec="seconds")
    rows = []
    for reason, (conf, evidence) in reasons.items():
        fid = f"FA_{trade_date.replace('-','')}_{symbol}_{reason}"
        rows.append((
            fid, symbol, trade_date, leader_id,
            reason, round(conf, 4), json.dumps(evidence), now
        ))
    sql = """
        INSERT OR REPLACE INTO failure_attribution
            (failure_id, symbol, trade_date, matched_leader_id,
             candidate_reason, confidence, supporting_evidence, recorded_at)
        VALUES (?,?,?,?,?,?,?,?)
    """
    with conn:
        conn.executemany(sql, rows)
    return len(rows)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_feature(
    symbol: str, feature_name: str, trade_date: str, conn: sqlite3.Connection
) -> Optional[float]:
    """Read a feature from market_leader_features for a given symbol on date."""
    row = conn.execute("""
        SELECT mlf.feature_value
        FROM market_leader_features mlf
        JOIN market_leaders_daily mld ON mlf.leader_id = mld.leader_id
        WHERE mld.symbol = ? AND mld.trade_date = ? AND mlf.feature_name = ?
        LIMIT 1
    """, (symbol, trade_date, feature_name)).fetchone()
    return float(row[0]) if row and row[0] is not None else None


def _get_leader_feature(
    leader_id: str, feature_name: str, conn: sqlite3.Connection
) -> Optional[float]:
    row = conn.execute("""
        SELECT feature_value FROM market_leader_features
        WHERE leader_id = ? AND feature_name = ?
    """, (leader_id, feature_name)).fetchone()
    return float(row[0]) if row and row[0] is not None else None


def _day_return(symbol: str, trade_date: str, conn: sqlite3.Connection) -> Optional[float]:
    rows = conn.execute("""
        SELECT close FROM ohlcv_daily
        WHERE symbol = ? AND trade_date <= ?
        ORDER BY trade_date DESC LIMIT 2
    """, (symbol, trade_date)).fetchall()
    if len(rows) < 2 or not rows[1][0]:
        return None
    return (rows[0][0] - rows[1][0]) / rows[1][0] * 100


def _sector_avg_return(sector: str, trade_date: str, conn: sqlite3.Connection) -> Optional[float]:
    """Average 1-day return of all active stocks in sector."""
    symbols = conn.execute("""
        SELECT symbol FROM universe_stocks WHERE sector = ? AND is_active = 1
    """, (sector,)).fetchall()
    returns = []
    for (sym,) in symbols:
        r = _day_return(sym, trade_date, conn)
        if r is not None:
            returns.append(r)
    if not returns:
        return None
    return sum(returns) / len(returns)


def _get_winner_control_pairs(trade_date: str, conn: sqlite3.Connection) -> list[tuple[dict, dict]]:
    """Return list of (winner_dict, control_dict) tuples where control underperformed."""
    rows = conn.execute("""
        SELECT
            mld.leader_id, mld.symbol AS win_sym, mld.sector, mld.day_return_pct,
            mrc.control_id, mrc.symbol AS ctrl_sym, mrc.return_1d
        FROM market_research_controls mrc
        JOIN market_leaders_daily mld ON mrc.matched_leader_id = mld.leader_id
        WHERE mrc.trade_date = ?
    """, (trade_date,)).fetchall()

    pairs = []
    for r in rows:
        winner  = {"leader_id": r[0], "symbol": r[1], "sector": r[2], "day_return_pct": r[3]}
        control = {"control_id": r[4], "symbol": r[5], "return_1d": r[6]}
        # Analyze failure only if control clearly underperformed
        win_ret  = winner.get("day_return_pct") or 0
        ctrl_ret = control.get("return_1d") or 0
        if win_ret > 0 and (ctrl_ret is None or ctrl_ret < win_ret * 0.5):
            pairs.append((winner, control))
    return pairs
