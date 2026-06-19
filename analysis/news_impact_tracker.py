"""
analysis/news_impact_tracker.py
==================================
NEWS_AUDIT_001 — SQLite-backed news impact tracker.

Shadow mode guarantees
----------------------
- Writes ONLY to data/news_audit.db.
- Zero imports from execution_engine, risk_control, decision_ai,
  opportunity_engine, or any other live-trading module.

Each row stores one (news_event × trade) observation.
A trade can have zero, one, or multiple news events associated.

Integration hook (future, forward path):
    from analysis.news_impact_tracker import get_news_tracker
    tracker = get_news_tracker()
    row_id = tracker.ingest_observation(
        symbol="TCS",
        news_type=NewsType.EARNINGS,
        sentiment=NewsSentiment.POSITIVE,
        trade_taken=True,
        direction="LONG",
        price_at_event=3800.0,
    )
    # 5 days later:
    tracker.update_follow_through(row_id, price_5d=4050.0, outcome="WIN", pnl=24500)
"""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone
from typing import Dict, List, Optional

from analysis.news_classifier import (
    NewsType,
    NewsSentiment,
    ImpactHorizon,
    impact_by_news_type,
    compute_news_win_rates,
    classify_news_impact,
)

# ── Paths ─────────────────────────────────────────────────────────────────────

_ROOT   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(_ROOT, "data", "news_audit.db")

# ── Schema ────────────────────────────────────────────────────────────────────

_DDL = """
CREATE TABLE IF NOT EXISTS news_impact_log (
    id                          INTEGER PRIMARY KEY AUTOINCREMENT,
    recorded_at                 TEXT    NOT NULL,
    event_date                  TEXT    NOT NULL,
    symbol                      TEXT    NOT NULL,
    strategy                    TEXT    NOT NULL DEFAULT 'UNKNOWN',

    news_type                   TEXT    NOT NULL DEFAULT 'NONE',
    sentiment                   TEXT    NOT NULL DEFAULT 'NEUTRAL',
    news_headline               TEXT,
    impact_horizon              TEXT    NOT NULL DEFAULT 'UNKNOWN',

    trade_taken                 INTEGER NOT NULL DEFAULT 0,
    direction                   TEXT    NOT NULL DEFAULT 'LONG',
    market_regime               TEXT    NOT NULL DEFAULT 'UNKNOWN',
    vix_bucket                  TEXT    NOT NULL DEFAULT 'UNKNOWN',
    vix                         REAL    NOT NULL DEFAULT 0.0,

    price_at_event              REAL    NOT NULL DEFAULT 0.0,
    price_1d                    REAL,
    price_3d                    REAL,
    price_5d                    REAL,

    move_1d_pct                 REAL,
    move_3d_pct                 REAL,
    move_5d_pct                 REAL,

    outcome                     TEXT    NOT NULL DEFAULT 'PENDING',
    pnl                         REAL,

    alignment                   TEXT    NOT NULL DEFAULT 'PENDING',
    sentiment_direction_matched INTEGER NOT NULL DEFAULT 0,
    beat_expected_move          INTEGER NOT NULL DEFAULT 0,

    is_backfill                 INTEGER NOT NULL DEFAULT 0,
    notes                       TEXT
);

CREATE INDEX IF NOT EXISTS idx_nil_news_type  ON news_impact_log(news_type);
CREATE INDEX IF NOT EXISTS idx_nil_sentiment  ON news_impact_log(sentiment);
CREATE INDEX IF NOT EXISTS idx_nil_outcome    ON news_impact_log(outcome);
CREATE INDEX IF NOT EXISTS idx_nil_symbol     ON news_impact_log(symbol);
CREATE INDEX IF NOT EXISTS idx_nil_date       ON news_impact_log(event_date);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Tracker ───────────────────────────────────────────────────────────────────

class NewsImpactTracker:
    """
    Records news events paired with trade outcomes.

    The central table answers:
        "When news type X occurs with sentiment Y, do our trades win?"
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

    def ingest_observation(
        self,
        symbol:             str,
        news_type:          str,
        sentiment:          str,
        event_date:         str,
        trade_taken:        bool,
        direction:          str              = "LONG",
        strategy:           str              = "UNKNOWN",
        market_regime:      str              = "UNKNOWN",
        vix_bucket:         str              = "UNKNOWN",
        vix:                float            = 0.0,
        price_at_event:     float            = 0.0,
        price_1d:           Optional[float]  = None,
        price_3d:           Optional[float]  = None,
        price_5d:           Optional[float]  = None,
        outcome:            str              = "PENDING",
        pnl:                Optional[float]  = None,
        impact_horizon:     str              = ImpactHorizon.UNKNOWN.value,
        news_headline:      Optional[str]    = None,
        is_backfill:        bool             = False,
        notes:              Optional[str]    = None,
    ) -> int:
        """
        Record a news event observation.

        If price_5d is provided at insert time (backfill mode), outcome
        classification is done immediately.

        Returns the row id.
        """
        move_1d = move_3d = move_5d = None
        alignment                   = "PENDING"
        direction_matched           = 0
        beat_expected               = 0

        if price_1d and price_at_event:
            move_1d = round((price_1d - price_at_event) / price_at_event * 100, 3)
        if price_3d and price_at_event:
            move_3d = round((price_3d - price_at_event) / price_at_event * 100, 3)
        if price_5d and price_at_event:
            move_5d = round((price_5d - price_at_event) / price_at_event * 100, 3)
            # Signed move in trade direction
            signed = move_5d if direction.upper() == "LONG" else -move_5d
            result = classify_news_impact(news_type, sentiment, direction, signed)
            alignment         = result.alignment
            direction_matched = int(result.direction_match)
            beat_expected     = int(result.beat_expected)

        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute(
                """
                INSERT INTO news_impact_log
                  (recorded_at, event_date, symbol, strategy,
                   news_type, sentiment, news_headline, impact_horizon,
                   trade_taken, direction, market_regime, vix_bucket, vix,
                   price_at_event, price_1d, price_3d, price_5d,
                   move_1d_pct, move_3d_pct, move_5d_pct,
                   outcome, pnl,
                   alignment, sentiment_direction_matched, beat_expected_move,
                   is_backfill, notes)
                VALUES
                  (?,?,?,?,  ?,?,?,?,  ?,?,?,?,?,  ?,?,?,?,  ?,?,?,  ?,?,  ?,?,?,  ?,?)
                """,
                (
                    _now(), event_date, symbol, strategy,
                    news_type, sentiment, news_headline, impact_horizon,
                    int(trade_taken), direction, market_regime, vix_bucket, vix,
                    price_at_event, price_1d, price_3d, price_5d,
                    move_1d, move_3d, move_5d,
                    outcome, pnl,
                    alignment, direction_matched, beat_expected,
                    int(is_backfill), notes,
                ),
            )
            conn.commit()
            return cur.lastrowid

    def update_follow_through(
        self,
        row_id:   int,
        price_5d: float,
        outcome:  Optional[str]   = None,
        pnl:      Optional[float] = None,
        price_1d: Optional[float] = None,
        price_3d: Optional[float] = None,
    ) -> bool:
        """Update follow-through prices and reclassify alignment."""
        row = self._query_one("SELECT * FROM news_impact_log WHERE id=?", (row_id,))
        if row is None:
            return False

        ref   = row["price_at_event"]
        direc = row["direction"]

        updates: dict = {"price_5d": price_5d}
        if ref:
            move_5d  = round((price_5d - ref) / ref * 100, 3)
            signed   = move_5d if direc.upper() == "LONG" else -move_5d
            result   = classify_news_impact(
                row["news_type"], row["sentiment"], direc, signed
            )
            updates["move_5d_pct"]               = move_5d
            updates["alignment"]                 = result.alignment
            updates["sentiment_direction_matched"] = int(result.direction_match)
            updates["beat_expected_move"]         = int(result.beat_expected)

        if price_1d:
            updates["price_1d"]    = price_1d
            updates["move_1d_pct"] = round((price_1d - ref) / ref * 100, 3) if ref else None
        if price_3d:
            updates["price_3d"]    = price_3d
            updates["move_3d_pct"] = round((price_3d - ref) / ref * 100, 3) if ref else None
        if outcome:
            updates["outcome"] = outcome
        if pnl is not None:
            updates["pnl"] = pnl

        set_clause = ", ".join(f"{k}=?" for k in updates)
        with sqlite3.connect(self.db_path) as conn:
            affected = conn.execute(
                f"UPDATE news_impact_log SET {set_clause} WHERE id=?",
                list(updates.values()) + [row_id],
            ).rowcount
            conn.commit()
        return affected > 0

    # ── Read ───────────────────────────────────────────────────────────────────

    def get_all(self) -> List[dict]:
        return self._query("SELECT * FROM news_impact_log ORDER BY event_date")

    def get_closed(self) -> List[dict]:
        return self._query(
            "SELECT * FROM news_impact_log WHERE outcome IN ('WIN','LOSS','BREAKEVEN')"
        )

    def count_total(self) -> int:
        with sqlite3.connect(self.db_path) as conn:
            return conn.execute("SELECT COUNT(*) FROM news_impact_log").fetchone()[0]

    # ── Analysis ───────────────────────────────────────────────────────────────

    def impact_by_type(self) -> Dict[str, dict]:
        return impact_by_news_type(self.get_all())

    def win_rates_by_combo(self) -> Dict[str, dict]:
        return compute_news_win_rates(self.get_all())

    def top_catalysts(self, top_n: int = 5) -> List[dict]:
        """Return top_n news types by win rate (min 5 observations)."""
        by_type = self.impact_by_type()
        ranked  = [
            {"news_type": k, **v}
            for k, v in by_type.items()
            if v.get("closed", 0) >= 5
        ]
        return sorted(ranked, key=lambda x: -x.get("win_rate", 0))[:top_n]

    def no_signal_types(self) -> List[str]:
        """News types that produce NO_SIGNAL verdict (candidates for ignoring)."""
        return [
            k for k, v in self.impact_by_type().items()
            if v.get("verdict") in ("NO_SIGNAL", "WEAK_SIGNAL")
            and v.get("closed", 0) >= 5
        ]

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

_tracker: Optional[NewsImpactTracker] = None


def get_news_tracker(db_path: str = DB_PATH) -> NewsImpactTracker:
    """
    Module-level lazy singleton.

    Future integration hook:
        from analysis.news_impact_tracker import get_news_tracker
        get_news_tracker().ingest_observation(
            symbol="TCS", news_type=NewsType.EARNINGS,
            sentiment=NewsSentiment.POSITIVE,
            event_date="2026-07-15", trade_taken=True,
            direction="LONG", price_at_event=3800.0,
        )
    """
    global _tracker
    if _tracker is None or _tracker.db_path != db_path:
        _tracker = NewsImpactTracker(db_path)
    return _tracker
