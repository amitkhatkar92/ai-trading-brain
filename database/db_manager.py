"""
Database Manager — Persistent Storage Layer
=============================================
Provides SQLite storage for the entire trading system.

Tables:
  market_data   — historical price snapshots per symbol
  signals       — all generated trade signals (approved + rejected)
  trades        — executed trades with outcomes
  strategies    — per-strategy performance rolling stats
  system_logs   — structured log entries for post-mortem analysis
  edges         — EDE discovered edges snapshot

Design: single SQLite file at data/trading_brain.db
Thread-safe via WAL mode + per-call connections.
"""

from __future__ import annotations
import json
import os
import sqlite3
import threading
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Dict, Generator, List, Optional

from utils import get_logger

log = get_logger(__name__)

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "trading_brain.db")
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

# ── Schema DDL ─────────────────────────────────────────────────────────────

_SCHEMA = """
-- Historical price bars
CREATE TABLE IF NOT EXISTS market_data (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol      TEXT    NOT NULL,
    ts          TEXT    NOT NULL,
    interval    TEXT    DEFAULT '1d',
    open        REAL,
    high        REAL,
    low         REAL,
    close       REAL,
    volume      REAL,
    change_pct  REAL,
    source      TEXT    DEFAULT 'simulation',
    created_at  TEXT    DEFAULT (datetime('now')),
    UNIQUE(symbol, ts, interval)
);

-- All generated signals (pre-execution)
CREATE TABLE IF NOT EXISTS signals (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    ts              TEXT    NOT NULL,
    symbol          TEXT    NOT NULL,
    direction       TEXT,
    signal_type     TEXT,
    strategy        TEXT,
    entry_price     REAL,
    stop_loss       REAL,
    target_price    REAL,
    rr_ratio        REAL,
    confidence      REAL,
    decision        TEXT,   -- APPROVED | REJECTED
    reject_reason   TEXT,
    regime          TEXT,
    volatility      TEXT,
    cycle_id        TEXT,
    created_at      TEXT    DEFAULT (datetime('now'))
);

-- Executed / paper trades
CREATE TABLE IF NOT EXISTS trades (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    trade_id        TEXT    UNIQUE,
    ts_open         TEXT    NOT NULL,
    ts_close        TEXT,
    symbol          TEXT    NOT NULL,
    direction       TEXT,
    strategy        TEXT,
    entry_price     REAL,
    exit_price      REAL    DEFAULT 0,
    stop_loss       REAL,
    target          REAL,
    quantity        INTEGER,
    pnl             REAL    DEFAULT 0,
    pnl_pct         REAL    DEFAULT 0,
    r_multiple      REAL    DEFAULT 0,
    won             INTEGER DEFAULT 0,   -- 0/1
    status          TEXT    DEFAULT 'open',  -- open|closed|stopped
    mode            TEXT    DEFAULT 'paper', -- paper|live
    brokerage       REAL    DEFAULT 0,
    slippage        REAL    DEFAULT 0,
    net_pnl         REAL    DEFAULT 0,
    cycle_id        TEXT,
    notes           TEXT,
    created_at      TEXT    DEFAULT (datetime('now'))
);

-- Rolling strategy performance
CREATE TABLE IF NOT EXISTS strategies (
    strategy_name   TEXT    PRIMARY KEY,
    total_trades    INTEGER DEFAULT 0,
    wins            INTEGER DEFAULT 0,
    losses          INTEGER DEFAULT 0,
    total_pnl       REAL    DEFAULT 0,
    avg_r_multiple  REAL    DEFAULT 0,
    sharp_ratio     REAL    DEFAULT 0,
    profit_factor   REAL    DEFAULT 0,
    expectancy_r    REAL    DEFAULT 0,
    last_updated    TEXT    DEFAULT (datetime('now'))
);

-- Structured system logs for post-mortem analysis
CREATE TABLE IF NOT EXISTS system_logs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    ts          TEXT    NOT NULL,
    level       TEXT    DEFAULT 'INFO',
    component   TEXT,
    event_type  TEXT,
    message     TEXT,
    payload     TEXT,   -- JSON
    cycle_id    TEXT,
    created_at  TEXT    DEFAULT (datetime('now'))
);

-- Discovered edges snapshot
CREATE TABLE IF NOT EXISTS edges (
    name            TEXT    PRIMARY KEY,
    category        TEXT,
    status          TEXT,
    expectancy_r    REAL,
    sharpe_ratio    REAL,
    oos_win_rate    REAL,
    live_trades     INTEGER DEFAULT 0,
    live_wins       INTEGER DEFAULT 0,
    composite_score REAL,
    created_at      TEXT,
    last_updated    TEXT    DEFAULT (datetime('now'))
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_market_data_symbol ON market_data(symbol, ts);
CREATE INDEX IF NOT EXISTS idx_signals_ts         ON signals(ts);
CREATE INDEX IF NOT EXISTS idx_trades_symbol      ON trades(symbol, ts_open);
CREATE INDEX IF NOT EXISTS idx_syslog_component   ON system_logs(component, ts);
"""


# ── Public Dataclasses ─────────────────────────────────────────────────────

@dataclass
class TradeRecord:
    trade_id:    str
    ts_open:     str
    symbol:      str
    direction:   str
    strategy:    str
    entry_price: float
    stop_loss:   float
    target:      float
    quantity:    int
    mode:        str  = "paper"
    ts_close:    str  = ""
    exit_price:  float = 0.0
    pnl:         float = 0.0
    pnl_pct:     float = 0.0
    r_multiple:  float = 0.0
    won:         bool  = False
    status:      str   = "open"
    brokerage:   float = 0.0
    slippage:    float = 0.0
    net_pnl:     float = 0.0
    cycle_id:    str   = ""
    notes:       str   = ""


@dataclass
class SignalRecord:
    ts:            str
    symbol:        str
    direction:     str
    signal_type:   str
    strategy:      str
    entry_price:   float
    stop_loss:     float
    target_price:  float
    rr_ratio:      float
    confidence:    float
    decision:      str
    regime:        str    = ""
    volatility:    str    = ""
    reject_reason: str    = ""
    cycle_id:      str    = ""


# ── Database Manager ───────────────────────────────────────────────────────

class DBManager:
    """
    Thread-safe SQLite wrapper.

    Usage::
        from database import get_db
        db = get_db()
        db.insert_trade(trade_record)
        db.update_trade_close(trade_id, exit_price, pnl, ...)
        trades = db.get_trades(limit=50)
    """

    def __init__(self, db_path: str = DB_PATH) -> None:
        self._path = db_path
        self._lock = threading.Lock()
        self._init_schema()
        log.info("[DBManager] Initialised at %s", self._path)

    # ── Context manager ────────────────────────────────────────────────────

    @contextmanager
    def _conn(self) -> Generator[sqlite3.Connection, None, None]:
        con = sqlite3.connect(self._path, check_same_thread=False)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA journal_mode=WAL")
        con.execute("PRAGMA synchronous=NORMAL")
        try:
            yield con
            con.commit()
        except Exception:
            con.rollback()
            raise
        finally:
            con.close()

    def _init_schema(self) -> None:
        with self._conn() as con:
            con.executescript(_SCHEMA)

    # ── Market Data ────────────────────────────────────────────────────────

    def insert_price_bar(
        self,
        symbol: str, ts: str, interval: str,
        open: float, high: float, low: float,
        close: float, volume: float, change_pct: float = 0.0,
        source: str = "simulation",
    ) -> None:
        with self._lock, self._conn() as con:
            con.execute(
                """INSERT OR IGNORE INTO market_data
                   (symbol, ts, interval, open, high, low, close, volume, change_pct, source)
                   VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (symbol, ts, interval, open, high, low, close, volume, change_pct, source),
            )

    def get_price_history(
        self, symbol: str, limit: int = 252
    ) -> List[Dict]:
        with self._conn() as con:
            rows = con.execute(
                "SELECT * FROM market_data WHERE symbol=? ORDER BY ts DESC LIMIT ?",
                (symbol, limit),
            ).fetchall()
        return [dict(r) for r in rows]

    # ── Signals ────────────────────────────────────────────────────────────

    def insert_signal(self, s: SignalRecord) -> None:
        with self._lock, self._conn() as con:
            con.execute(
                """INSERT INTO signals
                   (ts, symbol, direction, signal_type, strategy,
                    entry_price, stop_loss, target_price, rr_ratio,
                    confidence, decision, reject_reason, regime, volatility, cycle_id)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (s.ts, s.symbol, s.direction, s.signal_type, s.strategy,
                 s.entry_price, s.stop_loss, s.target_price, s.rr_ratio,
                 s.confidence, s.decision, s.reject_reason,
                 s.regime, s.volatility, s.cycle_id),
            )

    def get_signals(self, limit: int = 100, decision: str = "") -> List[Dict]:
        with self._conn() as con:
            q = "SELECT * FROM signals"
            p: list = []
            if decision:
                q += " WHERE decision=?"; p.append(decision)
            q += " ORDER BY ts DESC LIMIT ?"
            p.append(limit)
            return [dict(r) for r in con.execute(q, p).fetchall()]

    # ── Trades ─────────────────────────────────────────────────────────────

    def insert_trade(self, t: TradeRecord) -> None:
        with self._lock, self._conn() as con:
            con.execute(
                """INSERT OR IGNORE INTO trades
                   (trade_id, ts_open, symbol, direction, strategy,
                    entry_price, stop_loss, target, quantity,
                    mode, status, brokerage, slippage, cycle_id, notes)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (t.trade_id, t.ts_open, t.symbol, t.direction, t.strategy,
                 t.entry_price, t.stop_loss, t.target, t.quantity,
                 t.mode, t.status, t.brokerage, t.slippage, t.cycle_id, t.notes),
            )

    def close_trade(
        self,
        trade_id:   str,
        exit_price: float,
        pnl:        float,
        net_pnl:    float,
        r_multiple: float,
        won:        bool,
        status:     str = "closed",
    ) -> None:
        ts_close = datetime.now().isoformat()
        with self._lock, self._conn() as con:
            con.execute(
                """UPDATE trades SET
                   ts_close=?, exit_price=?, pnl=?, net_pnl=?,
                   r_multiple=?, won=?, status=?
                   WHERE trade_id=?""",
                (ts_close, exit_price, pnl, net_pnl,
                 r_multiple, int(won), status, trade_id),
            )

    def get_trades(
        self, limit: int = 100, status: str = "", mode: str = ""
    ) -> List[Dict]:
        with self._conn() as con:
            clauses, p = [], []
            if status: clauses.append("status=?"); p.append(status)
            if mode:   clauses.append("mode=?");   p.append(mode)
            where = "WHERE " + " AND ".join(clauses) if clauses else ""
            p.append(limit)
            return [dict(r) for r in con.execute(
                f"SELECT * FROM trades {where} ORDER BY ts_open DESC LIMIT ?", p
            ).fetchall()]

    def get_open_trades(self) -> List[Dict]:
        return self.get_trades(status="open", limit=50)

    # ── Strategy Stats ─────────────────────────────────────────────────────

    def upsert_strategy_stats(
        self,
        strategy_name: str,
        total_trades: int, wins: int,
        total_pnl: float, avg_r: float,
        sharpe: float, pf: float, expectancy_r: float,
    ) -> None:
        with self._lock, self._conn() as con:
            con.execute(
                """INSERT INTO strategies
                   (strategy_name, total_trades, wins, losses, total_pnl,
                    avg_r_multiple, sharp_ratio, profit_factor, expectancy_r)
                   VALUES (?,?,?,?,?,?,?,?,?)
                   ON CONFLICT(strategy_name) DO UPDATE SET
                     total_trades=excluded.total_trades,
                     wins=excluded.wins,
                     losses=excluded.losses,
                     total_pnl=excluded.total_pnl,
                     avg_r_multiple=excluded.avg_r_multiple,
                     sharp_ratio=excluded.sharp_ratio,
                     profit_factor=excluded.profit_factor,
                     expectancy_r=excluded.expectancy_r,
                     last_updated=datetime('now')""",
                (strategy_name, total_trades, wins, total_trades - wins,
                 total_pnl, avg_r, sharpe, pf, expectancy_r),
            )

    def get_strategy_stats(self) -> List[Dict]:
        with self._conn() as con:
            return [dict(r) for r in con.execute(
                "SELECT * FROM strategies ORDER BY expectancy_r DESC"
            ).fetchall()]

    # ── System Logs ────────────────────────────────────────────────────────

    def log_event(
        self,
        component:  str,
        event_type: str,
        message:    str,
        level:      str = "INFO",
        payload:    Optional[Dict] = None,
        cycle_id:   str = "",
    ) -> None:
        ts = datetime.now().isoformat()
        payload_str = json.dumps(payload) if payload else ""
        with self._lock, self._conn() as con:
            con.execute(
                """INSERT INTO system_logs (ts, level, component, event_type, message, payload, cycle_id)
                   VALUES (?,?,?,?,?,?,?)""",
                (ts, level, component, event_type, message, payload_str, cycle_id),
            )

    def get_system_logs(
        self, limit: int = 200, component: str = "", level: str = ""
    ) -> List[Dict]:
        with self._conn() as con:
            clauses, p = [], []
            if component: clauses.append("component=?"); p.append(component)
            if level:     clauses.append("level=?");     p.append(level)
            where = "WHERE " + " AND ".join(clauses) if clauses else ""
            p.append(limit)
            return [dict(r) for r in con.execute(
                f"SELECT * FROM system_logs {where} ORDER BY ts DESC LIMIT ?", p
            ).fetchall()]

    # ── Edges snapshot ─────────────────────────────────────────────────────

    def upsert_edge(self, name: str, category: str, status: str,
                    expectancy_r: float, sharpe: float, oos_wr: float,
                    live_trades: int, live_wins: int, score: float,
                    created_at: str) -> None:
        with self._lock, self._conn() as con:
            con.execute(
                """INSERT INTO edges (name, category, status, expectancy_r,
                   sharpe_ratio, oos_win_rate, live_trades, live_wins,
                   composite_score, created_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?)
                   ON CONFLICT(name) DO UPDATE SET
                     status=excluded.status,
                     expectancy_r=excluded.expectancy_r,
                     sharpe_ratio=excluded.sharpe_ratio,
                     oos_win_rate=excluded.oos_win_rate,
                     live_trades=excluded.live_trades,
                     live_wins=excluded.live_wins,
                     composite_score=excluded.composite_score,
                     last_updated=datetime('now')""",
                (name, category, status, expectancy_r, sharpe, oos_wr,
                 live_trades, live_wins, score, created_at),
            )

    # ── Analytics helpers ──────────────────────────────────────────────────

    def get_daily_pnl(self, days: int = 30) -> List[Dict]:
        """Daily P&L summary for equity curve."""
        with self._conn() as con:
            return [dict(r) for r in con.execute(
                """SELECT date(ts_close) as date,
                   SUM(net_pnl) as pnl,
                   COUNT(*) as trades,
                   SUM(won) as wins
                   FROM trades
                   WHERE status='closed'
                     AND ts_close >= date('now', ?)
                   GROUP BY date(ts_close)
                   ORDER BY date""",
                (f"-{days} days",),
            ).fetchall()]

    def get_summary_stats(self) -> Dict:
        """Quick summary for dashboard."""
        with self._conn() as con:
            t = con.execute(
                "SELECT COUNT(*) tot, SUM(won) wins, SUM(net_pnl) pnl "
                "FROM trades WHERE status='closed'"
            ).fetchone()
            o = con.execute(
                "SELECT COUNT(*) FROM trades WHERE status='open'"
            ).fetchone()
        total  = t["tot"] or 0
        wins   = t["wins"] or 0
        pnl    = t["pnl"] or 0.0
        return {
            "total_trades": total,
            "wins":         wins,
            "losses":       total - wins,
            "win_rate":     round(wins / total * 100, 1) if total else 0.0,
            "total_pnl":    round(pnl, 2),
            "open_trades":  o[0] or 0,
        }


# ── Singleton ──────────────────────────────────────────────────────────────

_INSTANCE: Optional[DBManager] = None

def get_db() -> DBManager:
    global _INSTANCE
    if _INSTANCE is None:
        _INSTANCE = DBManager()
    return _INSTANCE
