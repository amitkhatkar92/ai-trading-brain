"""
analysis/real_options_tracker.py
=====================================
REAL_OPTIONS_AUDIT_002 — SQLite persistence for backtested real-data records.

DB: data/real_options_audit.db
No production DB is touched.
"""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone
from typing import Dict, List, Optional

from analysis.options_backtester import BacktestRecord, StrategyStats

_ROOT   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(_ROOT, "data", "real_options_audit.db")

_DDL = """
CREATE TABLE IF NOT EXISTS real_options_backtest (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id       TEXT    NOT NULL,
    date         TEXT    NOT NULL,
    strategy     TEXT    NOT NULL,
    underlying   TEXT    NOT NULL,
    regime       TEXT    NOT NULL,
    vix          REAL    NOT NULL,
    vix_bucket   TEXT    NOT NULL,
    direction    TEXT    NOT NULL,
    entry_price  REAL    NOT NULL,
    ret_5d       REAL,
    ret_10d      REAL,
    band_pct     REAL,
    win_loss     TEXT    NOT NULL,
    pnl_r        REAL    NOT NULL,
    holding_days INTEGER,
    breach_pct   REAL
);

CREATE INDEX IF NOT EXISTS idx_rob_strategy  ON real_options_backtest(strategy);
CREATE INDEX IF NOT EXISTS idx_rob_regime    ON real_options_backtest(regime);
CREATE INDEX IF NOT EXISTS idx_rob_run       ON real_options_backtest(run_id);
CREATE INDEX IF NOT EXISTS idx_rob_underlying ON real_options_backtest(underlying);
"""

_NOW = lambda: datetime.now(timezone.utc).isoformat()


class RealOptionsTracker:

    def __init__(self, db_path: str = DB_PATH) -> None:
        self.db_path = db_path
        os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript(_DDL)
            conn.commit()

    def run_exists(self, run_id: str) -> bool:
        with sqlite3.connect(self.db_path) as conn:
            n = conn.execute(
                "SELECT COUNT(*) FROM real_options_backtest WHERE run_id=?", (run_id,)
            ).fetchone()[0]
        return n > 0

    def store_batch(self, records: List[BacktestRecord], run_id: str) -> int:
        rows = [
            (run_id, r.date, r.strategy, r.underlying, r.regime,
             r.vix, r.vix_bucket, r.direction, r.entry_price,
             r.ret_5d, r.ret_10d, r.band_pct, r.win_loss,
             r.pnl_r, r.holding_days, r.breach_pct)
            for r in records
        ]
        with sqlite3.connect(self.db_path) as conn:
            conn.executemany(
                """INSERT INTO real_options_backtest
                   (run_id, date, strategy, underlying, regime, vix, vix_bucket,
                    direction, entry_price, ret_5d, ret_10d, band_pct, win_loss,
                    pnl_r, holding_days, breach_pct)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                rows,
            )
            conn.commit()
        return len(rows)

    def clear_run(self, run_id: str) -> int:
        with sqlite3.connect(self.db_path) as conn:
            n = conn.execute(
                "DELETE FROM real_options_backtest WHERE run_id=?", (run_id,)
            ).rowcount
            conn.commit()
        return n

    # ── Query methods ─────────────────────────────────────────────────────────

    def stats_by_strategy(self, run_id: Optional[str] = None) -> List[dict]:
        where = "WHERE run_id=?" if run_id else ""
        params = (run_id,) if run_id else ()
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            sql = f"""
                SELECT strategy,
                       COUNT(*)                                       AS n,
                       SUM(CASE WHEN win_loss='WIN' THEN 1 ELSE 0 END) AS wins,
                       AVG(pnl_r)                                    AS avg_pnl_r
                FROM real_options_backtest {where}
                GROUP BY strategy
                ORDER BY strategy
            """
            rows = [dict(r) for r in conn.execute(sql, params).fetchall()]

        for r in rows:
            n    = r["n"]
            wins = r["wins"]
            r["win_rate"]     = round(wins / n * 100, 1) if n else 0.0
            r["avg_pnl_r"]    = round(r["avg_pnl_r"], 3)

            # Profit factor from raw data
            with sqlite3.connect(self.db_path) as conn2:
                gp = conn2.execute(
                    f"SELECT COALESCE(SUM(pnl_r),0) FROM real_options_backtest "
                    f"WHERE strategy=? AND win_loss='WIN' "
                    + ("AND run_id=?" if run_id else ""),
                    (r["strategy"], run_id) if run_id else (r["strategy"],),
                ).fetchone()[0]
                gl = conn2.execute(
                    f"SELECT COALESCE(SUM(ABS(pnl_r)),0.001) FROM real_options_backtest "
                    f"WHERE strategy=? AND win_loss='LOSS' "
                    + ("AND run_id=?" if run_id else ""),
                    (r["strategy"], run_id) if run_id else (r["strategy"],),
                ).fetchone()[0]
            r["profit_factor"] = round(gp / gl, 3) if gl else 0.0
        return rows

    def stats_by_strategy_regime(self, run_id: Optional[str] = None) -> List[dict]:
        where  = "WHERE run_id=?" if run_id else ""
        params = (run_id,) if run_id else ()
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            sql = f"""
                SELECT strategy, regime,
                       COUNT(*)                                        AS n,
                       SUM(CASE WHEN win_loss='WIN' THEN 1 ELSE 0 END) AS wins,
                       AVG(pnl_r)                                     AS avg_pnl_r
                FROM real_options_backtest {where}
                GROUP BY strategy, regime
                ORDER BY strategy, regime
            """
            rows = [dict(r) for r in conn.execute(sql, params).fetchall()]
        for r in rows:
            n = r["n"]
            r["win_rate"] = round(r["wins"] / n * 100, 1) if n else 0.0
        return rows

    def stats_by_vix_bucket(self, run_id: Optional[str] = None) -> List[dict]:
        where  = "WHERE run_id=?" if run_id else ""
        params = (run_id,) if run_id else ()
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            sql = f"""
                SELECT strategy, vix_bucket,
                       COUNT(*)                                        AS n,
                       SUM(CASE WHEN win_loss='WIN' THEN 1 ELSE 0 END) AS wins
                FROM real_options_backtest {where}
                GROUP BY strategy, vix_bucket
                ORDER BY strategy, vix_bucket
            """
            rows = [dict(r) for r in conn.execute(sql, params).fetchall()]
        for r in rows:
            r["win_rate"] = round(r["wins"] / r["n"] * 100, 1) if r["n"] else 0.0
        return rows

    def underlying_summary(self, run_id: Optional[str] = None) -> List[dict]:
        where  = "WHERE run_id=?" if run_id else ""
        params = (run_id,) if run_id else ()
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            sql = f"""
                SELECT underlying, strategy,
                       COUNT(*) AS n,
                       SUM(CASE WHEN win_loss='WIN' THEN 1 ELSE 0 END) AS wins
                FROM real_options_backtest {where}
                GROUP BY underlying, strategy
                ORDER BY underlying, strategy
            """
            rows = [dict(r) for r in conn.execute(sql, params).fetchall()]
        for r in rows:
            r["win_rate"] = round(r["wins"] / r["n"] * 100, 1) if r["n"] else 0.0
        return rows

    def total_records(self, run_id: Optional[str] = None) -> int:
        params = (run_id,) if run_id else ()
        where  = "WHERE run_id=?" if run_id else ""
        with sqlite3.connect(self.db_path) as conn:
            return conn.execute(
                f"SELECT COUNT(*) FROM real_options_backtest {where}", params
            ).fetchone()[0]

    def date_range(self, run_id: Optional[str] = None) -> tuple:
        params = (run_id,) if run_id else ()
        where  = "WHERE run_id=?" if run_id else ""
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                f"SELECT MIN(date), MAX(date) FROM real_options_backtest {where}",
                params,
            ).fetchone()
        return (row[0] or "", row[1] or "")


# ── Singleton ─────────────────────────────────────────────────────────────────

_instance: Optional[RealOptionsTracker] = None


def get_real_options_tracker(db_path: str = DB_PATH) -> RealOptionsTracker:
    global _instance
    if _instance is None or _instance.db_path != db_path:
        _instance = RealOptionsTracker(db_path)
    return _instance
