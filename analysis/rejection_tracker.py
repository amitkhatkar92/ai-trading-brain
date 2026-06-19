"""
analysis/rejection_tracker.py
=================================
REJECTION_AUDIT_001 — SQLite-backed rejection tracker.

Shadow mode guarantees
----------------------
- Reads price data from yfinance only (read-only, no auth required).
- Writes ONLY to data/rejection_audit.db.
- Zero imports from execution_engine, risk_control, decision_ai,
  opportunity_engine, or any other live-trading module.

Integration hook (future, forward path):
    from analysis.rejection_tracker import get_rejection_tracker
    tracker = get_rejection_tracker()
    row_id = tracker.ingest_rejection(
        symbol="RELIANCE",
        strategy="Equity_Breakout",
        decision_score=6.2,
        quality_score=6.8,
        rejected_reason=RejectionReason.LOW_DECISION_SCORE,
        price_at_rejection=2850.0,
        direction="LONG",
    )
    # 5 trading days later, background job calls:
    tracker.update_price_follow(row_id)
"""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone
from typing import Dict, List, Optional

from analysis.rejection_classifier import (
    RejectionReason,
    RejectionOutcome,
    classify_outcome,
    favorable_move_pct,
    hypothetical_pnl,
    compute_accuracy_stats,
    accuracy_by_reason,
    accuracy_by_quality_tier,
    missed_winner_analysis,
)

# ── Paths ─────────────────────────────────────────────────────────────────────

_ROOT   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(_ROOT, "data", "rejection_audit.db")


# ── Schema ────────────────────────────────────────────────────────────────────

_DDL = """
CREATE TABLE IF NOT EXISTS rejection_log (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    recorded_at           TEXT    NOT NULL,
    symbol                TEXT    NOT NULL,
    strategy              TEXT    NOT NULL DEFAULT 'UNKNOWN',
    trade_date            TEXT    NOT NULL,
    direction             TEXT    NOT NULL DEFAULT 'LONG',

    market_regime         TEXT    NOT NULL DEFAULT 'UNKNOWN',
    vix_bucket            TEXT    NOT NULL DEFAULT 'UNKNOWN',
    vix                   REAL    NOT NULL DEFAULT 0.0,

    decision_score        REAL    NOT NULL DEFAULT 0.0,
    quality_score         REAL    NOT NULL DEFAULT 0.0,
    quality_tier          TEXT    NOT NULL DEFAULT 'UNKNOWN',
    sft_class             TEXT    NOT NULL DEFAULT 'UNKNOWN',

    rejected_reason       TEXT    NOT NULL DEFAULT 'UNKNOWN',
    rejected_at_threshold REAL    NOT NULL DEFAULT 6.5,

    price_at_rejection    REAL    NOT NULL DEFAULT 0.0,
    price_1d              REAL,
    price_3d              REAL,
    price_5d              REAL,

    move_1d_pct           REAL,
    move_3d_pct           REAL,
    move_5d_pct           REAL,

    max_favorable_move    REAL,
    max_adverse_move      REAL,

    rejection_outcome     TEXT    NOT NULL DEFAULT 'PENDING',
    hypothetical_pnl_est  REAL,

    is_backfill           INTEGER NOT NULL DEFAULT 0,
    notes                 TEXT
);

CREATE INDEX IF NOT EXISTS idx_rl_outcome ON rejection_log(rejection_outcome);
CREATE INDEX IF NOT EXISTS idx_rl_reason  ON rejection_log(rejected_reason);
CREATE INDEX IF NOT EXISTS idx_rl_symbol  ON rejection_log(symbol);
CREATE INDEX IF NOT EXISTS idx_rl_date    ON rejection_log(trade_date);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Tracker ───────────────────────────────────────────────────────────────────

class RejectionTracker:
    """
    Records trade candidates that were rejected and tracks their
    subsequent price movement to determine if the rejection was correct.
    """

    def __init__(self, db_path: str = DB_PATH) -> None:
        self.db_path = db_path
        os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript(_DDL)
            conn.commit()

    # ── Write ──────────────────────────────────────────────────────────────────

    def ingest_rejection(
        self,
        symbol:                str,
        strategy:              str,
        trade_date:            str,
        decision_score:        float,
        quality_score:         float,
        quality_tier:          str,
        rejected_reason:       str,
        price_at_rejection:    float,
        direction:             str            = "LONG",
        sft_class:             str            = "UNKNOWN",
        market_regime:         str            = "UNKNOWN",
        vix_bucket:            str            = "UNKNOWN",
        vix:                   float          = 0.0,
        rejected_at_threshold: float          = 6.5,
        price_1d:              Optional[float] = None,
        price_3d:              Optional[float] = None,
        price_5d:              Optional[float] = None,
        is_backfill:           bool            = False,
        notes:                 Optional[str]  = None,
    ) -> int:
        """
        Record a rejected trade candidate.

        If price_5d is supplied immediately (e.g. in backfill mode),
        outcome classification is done at insert time.

        Returns the row id.
        """
        move_1d = move_3d = move_5d = None
        max_fav = max_adv = None
        outcome        = RejectionOutcome.PENDING.value
        hyp_pnl        = None

        if price_1d:
            move_1d = round(
                (price_1d - price_at_rejection) / price_at_rejection * 100, 3
            )
        if price_3d:
            move_3d = round(
                (price_3d - price_at_rejection) / price_at_rejection * 100, 3
            )
        if price_5d and price_at_rejection > 0:
            move_5d = round(
                (price_5d - price_at_rejection) / price_at_rejection * 100, 3
            )
            outcome = classify_outcome(
                price_at_rejection, price_5d, direction
            ).value
            max_fav = favorable_move_pct(price_at_rejection, price_5d, direction)
            max_adv = -max_fav
            hyp_pnl = hypothetical_pnl(
                price_at_rejection, price_5d, direction
            )

        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute(
                """
                INSERT INTO rejection_log
                  (recorded_at, symbol, strategy, trade_date, direction,
                   market_regime, vix_bucket, vix,
                   decision_score, quality_score, quality_tier, sft_class,
                   rejected_reason, rejected_at_threshold, price_at_rejection,
                   price_1d, price_3d, price_5d,
                   move_1d_pct, move_3d_pct, move_5d_pct,
                   max_favorable_move, max_adverse_move,
                   rejection_outcome, hypothetical_pnl_est,
                   is_backfill, notes)
                VALUES
                  (?,?,?,?,?,  ?,?,?,  ?,?,?,?,  ?,?,?,  ?,?,?,  ?,?,?,  ?,?,  ?,?,  ?,?)
                """,
                (
                    _now(), symbol, strategy, trade_date, direction,
                    market_regime, vix_bucket, vix,
                    decision_score, quality_score, quality_tier, sft_class,
                    rejected_reason, rejected_at_threshold, price_at_rejection,
                    price_1d, price_3d, price_5d,
                    move_1d, move_3d, move_5d,
                    max_fav, max_adv,
                    outcome, hyp_pnl,
                    int(is_backfill), notes,
                ),
            )
            conn.commit()
            return cur.lastrowid

    def update_price_follow(
        self,
        row_id:   int,
        price_1d: Optional[float] = None,
        price_3d: Optional[float] = None,
        price_5d: Optional[float] = None,
    ) -> bool:
        """
        Update follow-through prices for a PENDING rejection.

        Automatically reclassifies outcome when price_5d is supplied.

        Returns True if row was found and updated.
        """
        row = self._query_one("SELECT * FROM rejection_log WHERE id=?", (row_id,))
        if row is None:
            return False

        ref   = row["price_at_rejection"]
        direc = row["direction"]

        updates: dict = {}
        if price_1d is not None:
            updates["price_1d"]    = price_1d
            updates["move_1d_pct"] = round((price_1d - ref) / ref * 100, 3) if ref else None
        if price_3d is not None:
            updates["price_3d"]    = price_3d
            updates["move_3d_pct"] = round((price_3d - ref) / ref * 100, 3) if ref else None
        if price_5d is not None:
            updates["price_5d"]    = price_5d
            updates["move_5d_pct"] = round((price_5d - ref) / ref * 100, 3) if ref else None
            updates["rejection_outcome"] = classify_outcome(ref, price_5d, direc).value
            updates["max_favorable_move"] = favorable_move_pct(ref, price_5d, direc)
            updates["max_adverse_move"]   = -updates["max_favorable_move"]
            updates["hypothetical_pnl_est"] = hypothetical_pnl(ref, price_5d, direc)

        if not updates:
            return False

        set_clause = ", ".join(f"{k}=?" for k in updates)
        values     = list(updates.values()) + [row_id]
        with sqlite3.connect(self.db_path) as conn:
            affected = conn.execute(
                f"UPDATE rejection_log SET {set_clause} WHERE id=?", values
            ).rowcount
            conn.commit()
        return affected > 0

    # ── Read ───────────────────────────────────────────────────────────────────

    def get_all(self) -> List[dict]:
        return self._query("SELECT * FROM rejection_log ORDER BY trade_date")

    def get_classified(self) -> List[dict]:
        return self._query(
            "SELECT * FROM rejection_log "
            "WHERE rejection_outcome != 'PENDING' ORDER BY trade_date"
        )

    def get_pending(self) -> List[dict]:
        return self._query(
            "SELECT * FROM rejection_log WHERE rejection_outcome='PENDING'"
        )

    def get_false_rejections(self) -> List[dict]:
        return self._query(
            "SELECT * FROM rejection_log WHERE rejection_outcome='FALSE_REJECTION'"
        )

    def count_total(self) -> int:
        with sqlite3.connect(self.db_path) as conn:
            return conn.execute("SELECT COUNT(*) FROM rejection_log").fetchone()[0]

    # ── Analysis ───────────────────────────────────────────────────────────────

    def overall_accuracy(self) -> dict:
        return compute_accuracy_stats(self.get_all())

    def accuracy_by_reason(self) -> Dict[str, dict]:
        return accuracy_by_reason(self.get_all())

    def accuracy_by_quality_tier(self) -> Dict[str, dict]:
        return accuracy_by_quality_tier(self.get_all())

    def missed_winner_analysis(self) -> dict:
        return missed_winner_analysis(self.get_all())

    def hypothetical_total_pnl(self) -> float:
        """
        Sum of hypothetical_pnl_est across ALL classified rejections.
        Negative = good (rejections saved money overall).
        Positive = bad (rejections cost money overall — we rejected more winners than losers).
        """
        with sqlite3.connect(self.db_path) as conn:
            val = conn.execute(
                "SELECT SUM(hypothetical_pnl_est) FROM rejection_log "
                "WHERE rejection_outcome != 'PENDING'"
            ).fetchone()[0]
        return round(val or 0.0, 0)

    # ── Internal ───────────────────────────────────────────────────────────────

    def _query(self, sql: str, params: tuple = ()) -> List[dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            return [dict(r) for r in conn.execute(sql, params).fetchall()]

    def _query_one(self, sql: str, params: tuple = ()) -> Optional[dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(sql, params).fetchone()
            return dict(row) if row else None


# ── Singleton ─────────────────────────────────────────────────────────────────

_tracker: Optional[RejectionTracker] = None


def get_rejection_tracker(db_path: str = DB_PATH) -> RejectionTracker:
    """
    Module-level lazy singleton.

    Future integration hook (call from orchestrator when rejecting a trade):
        from analysis.rejection_tracker import get_rejection_tracker
        get_rejection_tracker().ingest_rejection(
            symbol="RELIANCE", strategy="Equity_Breakout",
            decision_score=6.1, quality_score=6.7,
            quality_tier="MEDIUM", rejected_reason="LOW_DECISION_SCORE",
            price_at_rejection=2850.0, direction="LONG",
        )
    """
    global _tracker
    if _tracker is None or _tracker.db_path != db_path:
        _tracker = RejectionTracker(db_path)
    return _tracker
