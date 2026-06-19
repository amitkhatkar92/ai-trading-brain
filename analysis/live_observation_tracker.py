"""
analysis/live_observation_tracker.py
==========================================
LIVE_OBSERVATION_FRAMEWORK_001 — SQLite persistence for enriched live trades.

DB: data/live_observations.db

Every real/paper trade that passes through the execution engine
gets stored here with its full context snapshot:
    quality_tier, sft_class, regime, vix_bucket, news_type,
    was_rejected (False for executed trades),
    outcome (WIN/LOSS/OPEN) once closed.

This is the forward-validation database — the only source of real evidence
for the learning engine's 62 pending recommendations.
"""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone
from typing import List, Optional

_ROOT   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(_ROOT, "data", "live_observations.db")

_DDL = """
CREATE TABLE IF NOT EXISTS live_observations (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    observed_at      TEXT    NOT NULL,
    order_id         TEXT    NOT NULL UNIQUE,
    symbol           TEXT    NOT NULL,
    strategy         TEXT    NOT NULL,
    direction        TEXT,
    trade_date       TEXT    NOT NULL,

    -- Entry context
    entry_price      REAL,
    stop_loss        REAL,
    target           REAL,
    confidence       REAL,           -- raw confidence score from decision engine
    rr               REAL,           -- planned risk-reward

    -- Enriched quality context
    quality_score    REAL,
    quality_tier     TEXT,           -- PREMIUM / HIGH / MEDIUM / LOW
    is_high_conviction INTEGER DEFAULT 0,

    -- SFT context
    sft_class        TEXT,           -- HIGH_SFT / MEDIUM_SFT / LOW_SFT
    sft_score        REAL,

    -- Regime context (at time of trade)
    market_regime    TEXT,           -- RANGING / TRENDING / HIGH_VOL
    vix              REAL,
    vix_bucket       TEXT,           -- LOW / MEDIUM / HIGH

    -- News context (manual or auto-detected)
    news_type        TEXT DEFAULT 'NONE',
    news_sentiment   TEXT DEFAULT 'NEUTRAL',

    -- Outcome (filled post-trade)
    outcome          TEXT DEFAULT 'OPEN',   -- OPEN / WIN / LOSS / CANCELLED
    exit_price       REAL,
    pnl              REAL,
    r_multiple       REAL,           -- actual R achieved
    closed_at        TEXT,
    close_reason     TEXT,

    -- Regime transition context (at time of trade)
    transition_probability REAL DEFAULT 0.0,  -- 0–100 from regime_transition_engine
    transition_alert TEXT DEFAULT 'STABLE',   -- STABLE/WATCH/ALERT/IMMINENT

    -- Meta
    data_source      TEXT DEFAULT 'PAPER',  -- PAPER / LIVE
    notes            TEXT
);

CREATE INDEX IF NOT EXISTS idx_lo_symbol    ON live_observations(symbol);
CREATE INDEX IF NOT EXISTS idx_lo_strategy  ON live_observations(strategy);
CREATE INDEX IF NOT EXISTS idx_lo_outcome   ON live_observations(outcome);
CREATE INDEX IF NOT EXISTS idx_lo_regime    ON live_observations(market_regime);
CREATE INDEX IF NOT EXISTS idx_lo_date      ON live_observations(trade_date);
CREATE INDEX IF NOT EXISTS idx_lo_tier      ON live_observations(quality_tier);
"""

_NOW = lambda: datetime.now(timezone.utc).isoformat()


class LiveObservationTracker:

    def __init__(self, db_path: str = DB_PATH) -> None:
        self.db_path = db_path
        os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript(_DDL)
            # Migrate: add columns that may not exist in older DB files
            for col, definition in [
                ("transition_probability", "REAL DEFAULT 0.0"),
                ("transition_alert",       "TEXT DEFAULT 'STABLE'"),
            ]:
                try:
                    conn.execute(f"ALTER TABLE live_observations ADD COLUMN {col} {definition}")
                    conn.commit()
                except sqlite3.OperationalError:
                    pass  # column already exists

    # ── Write ─────────────────────────────────────────────────────────────────

    def ingest(
        self,
        order_id:          str,
        symbol:            str,
        strategy:          str,
        direction:         str,
        trade_date:        str,
        entry_price:       float,
        stop_loss:         float,
        target:            float,
        confidence:        float,
        rr:                float,
        quality_score:     float,
        quality_tier:      str,
        is_high_conviction: bool,
        sft_class:         str,
        sft_score:         float,
        market_regime:     str,
        vix:               float,
        vix_bucket:        str,
        news_type:             str   = "NONE",
        news_sentiment:        str   = "NEUTRAL",
        transition_probability: float = 0.0,
        transition_alert:      str   = "STABLE",
        data_source:           str   = "PAPER",
        notes:                 str   = "",
    ) -> Optional[int]:
        """
        Store one trade observation.
        Returns row_id, or None if order_id already exists (idempotent).
        """
        with sqlite3.connect(self.db_path) as conn:
            exists = conn.execute(
                "SELECT id FROM live_observations WHERE order_id=?", (order_id,)
            ).fetchone()
            if exists:
                return None
            cur = conn.execute(
                """
                INSERT INTO live_observations
                  (observed_at, order_id, symbol, strategy, direction, trade_date,
                   entry_price, stop_loss, target, confidence, rr,
                   quality_score, quality_tier, is_high_conviction,
                   sft_class, sft_score,
                   market_regime, vix, vix_bucket,
                   news_type, news_sentiment,
                   transition_probability, transition_alert,
                   data_source, notes)
                VALUES
                  (?,?,?,?,?,?, ?,?,?,?,?, ?,?,?, ?,?, ?,?,?, ?,?, ?,?, ?,?)
                """,
                (
                    _NOW(), order_id, symbol, strategy, direction, trade_date,
                    entry_price, stop_loss, target, confidence, rr,
                    quality_score, quality_tier, int(is_high_conviction),
                    sft_class, sft_score,
                    market_regime, vix, vix_bucket,
                    news_type, news_sentiment,
                    transition_probability, transition_alert,
                    data_source, notes,
                ),
            )
            conn.commit()
            return cur.lastrowid

    def mark_outcome(
        self,
        order_id:    str,
        outcome:     str,       # WIN / LOSS / CANCELLED
        exit_price:  float,
        pnl:         float,
        close_reason: str = "",
    ) -> bool:
        """Update outcome for a previously ingested trade."""
        entry_row = None
        with sqlite3.connect(self.db_path) as conn:
            entry_row = conn.execute(
                "SELECT entry_price, stop_loss FROM live_observations WHERE order_id=?",
                (order_id,),
            ).fetchone()
        if entry_row is None:
            return False

        entry, sl = entry_row
        risk       = abs(entry - sl) if sl and sl != entry else 1.0
        r_multiple = (exit_price - entry) / risk if risk else 0.0

        with sqlite3.connect(self.db_path) as conn:
            n = conn.execute(
                """UPDATE live_observations SET
                   outcome=?, exit_price=?, pnl=?, r_multiple=?,
                   closed_at=?, close_reason=?
                   WHERE order_id=?
                """,
                (outcome, exit_price, pnl, round(r_multiple, 3), _NOW(), close_reason, order_id),
            ).rowcount
            conn.commit()
        return n > 0

    # ── Read ──────────────────────────────────────────────────────────────────

    def get_all(self, outcome: str = "") -> List[dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            if outcome:
                rows = conn.execute(
                    "SELECT * FROM live_observations WHERE outcome=? ORDER BY trade_date DESC",
                    (outcome,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM live_observations ORDER BY trade_date DESC"
                ).fetchall()
        return [dict(r) for r in rows]

    def get_closed(self) -> List[dict]:
        return self.get_all()  # filter on outcome != 'OPEN'

    def summary(self) -> dict:
        with sqlite3.connect(self.db_path) as conn:
            total  = conn.execute("SELECT COUNT(*) FROM live_observations").fetchone()[0]
            open_  = conn.execute("SELECT COUNT(*) FROM live_observations WHERE outcome='OPEN'").fetchone()[0]
            wins   = conn.execute("SELECT COUNT(*) FROM live_observations WHERE outcome='WIN'").fetchone()[0]
            losses = conn.execute("SELECT COUNT(*) FROM live_observations WHERE outcome='LOSS'").fetchone()[0]
            tiers  = {r[0]: r[1] for r in conn.execute(
                "SELECT quality_tier, COUNT(*) FROM live_observations GROUP BY quality_tier"
            ).fetchall()}
            regimes= {r[0]: r[1] for r in conn.execute(
                "SELECT market_regime, COUNT(*) FROM live_observations GROUP BY market_regime"
            ).fetchall()}

        closed = wins + losses
        wr     = round(wins / closed * 100, 1) if closed else 0.0
        return {
            "total": total, "open": open_, "wins": wins, "losses": losses,
            "win_rate": wr, "tiers": tiers, "regimes": regimes,
        }

    def tier_win_rates(self) -> dict:
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                """SELECT quality_tier,
                          COUNT(*) AS n,
                          SUM(CASE WHEN outcome='WIN' THEN 1 ELSE 0 END) AS wins
                   FROM live_observations
                   WHERE outcome IN ('WIN','LOSS')
                   GROUP BY quality_tier"""
            ).fetchall()
        result = {}
        for tier, n, wins in rows:
            result[tier] = {
                "n":        n,
                "win_rate": round(wins / n * 100, 1) if n else 0.0,
            }
        return result


# ── Singleton ─────────────────────────────────────────────────────────────────

_instance: Optional[LiveObservationTracker] = None


def get_live_tracker(db_path: str = DB_PATH) -> LiveObservationTracker:
    global _instance
    if _instance is None or _instance.db_path != db_path:
        _instance = LiveObservationTracker(db_path)
    return _instance
