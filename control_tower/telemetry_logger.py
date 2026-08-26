"""
Telemetry Logger — Control Tower Module 1
==========================================
Subscribes to ALL events on the shared EventBus via a wildcard ("*")
subscription and persists every event to a local SQLite database.

Responsibilities:
  - Create and maintain the SQLite schema on first run
  - Accept any Event and store it with full JSON payload
  - Maintain an in-memory ring-buffer of the last MAX_MEMORY events
    so the dashboard can read recent data without a DB hit

Schema:
  ct_events   — one row per published event (audit log)
  ct_cycles   — one row per trading cycle (aggregated stats)
  ct_decisions — one row per trade decision (for decision trace UI)
"""

from __future__ import annotations

import json
import os
import sqlite3
import threading
from collections import deque
from datetime import datetime
from typing import Any, Deque, Dict, List, Optional

from communication.events import Event, EventType
from utils import get_logger

log = get_logger(__name__)

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "control_tower.db")
MAX_MEMORY = 1_000      # ring-buffer size for in-process dashboard access

_CREATE_EVENTS = """
CREATE TABLE IF NOT EXISTS ct_events (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    ts            TEXT    NOT NULL,
    cycle_id      TEXT,
    event_type    TEXT    NOT NULL,
    source_agent  TEXT,
    payload       TEXT
);
"""

_CREATE_CYCLES = """
CREATE TABLE IF NOT EXISTS ct_cycles (
    cycle_id          TEXT PRIMARY KEY,
    started_at        TEXT,
    completed_at      TEXT,
    had_error         INTEGER DEFAULT 0,
    regime            TEXT,
    vix               REAL,
    breadth           REAL,
    pcr               REAL,
    signals_generated INTEGER DEFAULT 0,
    strategies_assigned INTEGER DEFAULT 0,
    risk_approved     INTEGER DEFAULT 0,
    sim_approved      INTEGER DEFAULT 0,
    trades_executed   INTEGER DEFAULT 0,
    cycle_ms          INTEGER DEFAULT 0,
    risk_rejection_summary TEXT
);
"""

_CREATE_DECISIONS = """
CREATE TABLE IF NOT EXISTS ct_decisions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    cycle_id        TEXT,
    symbol          TEXT,
    strategy        TEXT,
    confidence      REAL,
    decision        TEXT,
    rejection_reason TEXT,
    technical_score REAL,
    risk_score      REAL,
    macro_score     REAL,
    sentiment_score REAL,
    regime_score    REAL,
    position_modifier REAL,
    ts              TEXT
);
"""


class TelemetryLogger:
    """
    Passive observer — subscribes with wildcard and stores every event.

    Usage:
        logger = TelemetryLogger(bus)
        # Everything is automatic from here
    """

    def __init__(self, bus) -> None:
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        self._lock         = threading.Lock()   # guards both ring buffer AND db connection
        self._db_conn: Optional[sqlite3.Connection] = None   # single persistent connection
        self._ring: Deque[Dict[str, Any]] = deque(maxlen=MAX_MEMORY)
        self._current_cycle: Optional[str] = None

        self._init_db()
        bus.subscribe("*", self._on_event, agent_name="ControlTower.TelemetryLogger",
                      priority=99)   # last to receive so agents get priority
        log.info("[TelemetryLogger] Initialised. DB=%s", DB_PATH)

    # ── Public read API (used by in-process dashboard + SignalVisualizer) ──

    def get_recent_events(self, n: int = 100) -> List[Dict[str, Any]]:
        """Return up to n most-recent events from the ring buffer."""
        with self._lock:
            items = list(self._ring)
        return items[-n:]

    def get_current_cycle_id(self) -> Optional[str]:
        return self._current_cycle

    # ── SQLite helpers ─────────────────────────────────────────────────────

    def _connect(self) -> sqlite3.Connection:
        """Return the single persistent connection, creating it on first call.

        Using a single connection eliminates the file-descriptor leak that
        occurs when a new connection is opened per event (SQLite's context
        manager only manages transactions, not connection lifetime).
        WAL mode is enabled so the read-only dashboard container can query
        concurrently without blocking writes.
        Auto-recovers if the on-disk file is malformed: closes the corrupt
        connection, deletes the file, and opens a fresh one.
        """
        if self._db_conn is None:
            conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=30)
            try:
                conn.execute("PRAGMA integrity_check")
            except sqlite3.DatabaseError:
                # Corrupt file — drop connection, delete file, start fresh
                try:
                    conn.close()
                except Exception:
                    pass
                try:
                    import os as _os
                    _os.remove(DB_PATH)
                except Exception:
                    pass
                conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=30)
                log.warning("[TelemetryLogger] Corrupt DB detected — recreated fresh: %s", DB_PATH)
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            self._db_conn = conn
        return self._db_conn

    def _init_db(self) -> None:
        with self._lock:
            conn = self._connect()
            conn.execute(_CREATE_EVENTS)
            conn.execute(_CREATE_CYCLES)
            conn.execute(_CREATE_DECISIONS)
            # Migration: add risk_rejection_summary if not present (idempotent)
            try:
                conn.execute(
                    "ALTER TABLE ct_cycles ADD COLUMN risk_rejection_summary TEXT"
                )
            except Exception:
                pass  # Column already exists
            conn.commit()

    # ── Event handler ──────────────────────────────────────────────────────

    def _on_event(self, event: Event) -> None:
        try:
            payload = event.payload if isinstance(event.payload, dict) else {}
            et      = event.event_type.value if hasattr(event.event_type, "value") else str(event.event_type)
            row = {
                "ts":           event.timestamp.isoformat(),
                "cycle_id":     self._current_cycle or "",
                "event_type":   et,
                "source_agent": event.source_agent,
                "payload":      json.dumps(payload, default=str),
            }

            # All state mutation and DB writes are serialised under self._lock
            # to prevent concurrent connection opens that cause
            # "unable to open database file" when many events fire at once.
            with self._lock:
                conn = self._connect()

                # Update cycle tracking
                if et == EventType.CYCLE_STARTED.value:
                    self._current_cycle = event.correlation_id or event.timestamp.strftime("%Y%m%d_%H%M%S_%f")
                    row["cycle_id"] = self._current_cycle
                    self._upsert_cycle_locked(conn, self._current_cycle, {"started_at": event.timestamp.isoformat()})
                elif et == EventType.CYCLE_COMPLETE.value:
                    if self._current_cycle:
                        self._upsert_cycle_locked(conn, self._current_cycle, {
                            "completed_at": event.timestamp.isoformat(),
                            "had_error": 0,
                        })
                elif et == EventType.MARKET_DATA_READY.value:
                    if self._current_cycle:
                        self._upsert_cycle_locked(conn, self._current_cycle, {
                            "regime":  payload.get("regime", ""),
                            "vix":     payload.get("vix", 0),
                            "breadth": payload.get("breadth", 0),
                            "pcr":     payload.get("pcr", 0),
                        })
                elif et == EventType.SCAN_COMPLETE.value:
                    if self._current_cycle:
                        total = (payload.get("equity", 0)
                                 + payload.get("options", 0)
                                 + payload.get("arb", 0))
                        self._upsert_cycle_locked(conn, self._current_cycle, {"signals_generated": total})
                elif et == EventType.STRATEGY_LAB_COMPLETE.value:
                    if self._current_cycle:
                        self._upsert_cycle_locked(conn, self._current_cycle,
                                                   {"strategies_assigned": payload.get("assigned", 0)})
                elif et == EventType.RISK_CHECK_PASSED.value:
                    if self._current_cycle:
                        self._upsert_cycle_locked(conn, self._current_cycle,
                                                   {"risk_approved": payload.get("approved", 0)})
                elif et == EventType.RISK_CHECK_FAILED.value:
                    if self._current_cycle:
                        summary = payload.get("rejection_summary")
                        if summary is not None:
                            self._upsert_cycle_locked(
                                conn,
                                self._current_cycle,
                                {"risk_rejection_summary": json.dumps(summary)},
                            )
                elif et == EventType.SIMULATION_COMPLETE.value:
                    if self._current_cycle:
                        self._upsert_cycle_locked(conn, self._current_cycle,
                                                   {"sim_approved": payload.get("approved", 0)})
                elif et == EventType.TRADE_APPROVED.value:
                    self._store_decision_locked(conn, event, payload, approved=True)
                elif et == EventType.TRADE_REJECTED.value:
                    self._store_decision_locked(conn, event, payload, approved=False)
                elif et == EventType.ORDER_PLACED.value:
                    if self._current_cycle:
                        conn.execute(
                            "UPDATE ct_cycles SET trades_executed = trades_executed + 1 WHERE cycle_id=?",
                            (self._current_cycle,)
                        )

                # Ring buffer
                self._ring.append(row)

                # Persist event row
                conn.execute(
                    "INSERT INTO ct_events(ts,cycle_id,event_type,source_agent,payload) VALUES(?,?,?,?,?)",
                    (row["ts"], row["cycle_id"], row["event_type"],
                     row["source_agent"], row["payload"])
                )
                conn.commit()

        except sqlite3.DatabaseError as exc:
            # Connection became corrupt mid-run — reset so next event auto-recovers
            log.warning("[TelemetryLogger] DB error, resetting connection: %s", exc)
            try:
                if self._db_conn:
                    self._db_conn.close()
            except Exception:
                pass
            self._db_conn = None
        except Exception as exc:
            log.debug("[TelemetryLogger] Error processing event: %s", exc)

    def _upsert_cycle(self, cycle_id: str, fields: Dict[str, Any]) -> None:
        """Public helper kept for any callers outside _on_event."""
        try:
            with self._lock:
                conn = self._connect()
                self._upsert_cycle_locked(conn, cycle_id, fields)
                conn.commit()
        except Exception as exc:
            log.debug("[TelemetryLogger] Cycle upsert error: %s", exc)

    def _upsert_cycle_locked(self, conn: sqlite3.Connection, cycle_id: str, fields: Dict[str, Any]) -> None:
        """Execute an upsert using an already-open connection (caller holds self._lock)."""
        sets   = ", ".join(f"{k}=?" for k in fields)
        values = list(fields.values())
        conn.execute(
            "INSERT OR IGNORE INTO ct_cycles(cycle_id) VALUES(?)", (cycle_id,))
        conn.execute(
            f"UPDATE ct_cycles SET {sets} WHERE cycle_id=?",
            values + [cycle_id]
        )

    def _store_decision(self, event: Event, payload: Dict, approved: bool) -> None:
        """Public helper kept for any callers outside _on_event."""
        try:
            with self._lock:
                conn = self._connect()
                self._store_decision_locked(conn, event, payload, approved)
                conn.commit()
        except Exception as exc:
            log.debug("[TelemetryLogger] Decision store error: %s", exc)

    def _store_decision_locked(self, conn: sqlite3.Connection, event: Event,
                                payload: Dict, approved: bool) -> None:
        """Execute a decision insert using an already-open connection (caller holds self._lock)."""
        from datetime import timedelta
        symbol   = payload.get("symbol", "")
        strategy = payload.get("strategy", "")
        decision = "APPROVED" if approved else "REJECTED"
        votes    = payload.get("votes", {})

        # Dedup: skip if same symbol+strategy+decision stored in last 10 min
        window_start = (event.timestamp - timedelta(minutes=10)).isoformat()
        dup = conn.execute(
            "SELECT 1 FROM ct_decisions "
            "WHERE symbol=? AND strategy=? AND decision=? AND ts >= ? LIMIT 1",
            (symbol, strategy, decision, window_start),
        ).fetchone()
        if dup:
            log.debug(
                "[TelemetryLogger] Dedup: skipping %s %s %s (already recorded in last 10 min)",
                decision, symbol, strategy,
            )
            return

        conn.execute(
            "INSERT INTO ct_decisions"
            "(cycle_id,symbol,strategy,confidence,decision,rejection_reason,"
            "technical_score,risk_score,macro_score,sentiment_score,regime_score,"
            "position_modifier,ts)"
            " VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                self._current_cycle or "",
                symbol,
                strategy,
                payload.get("score", 0),
                decision,
                payload.get("reason", "") if not approved else "",
                votes.get("TechnicalAnalystAI", 0),
                votes.get("RiskDebateAI", 0),
                votes.get("MacroAnalystAI", 0),
                votes.get("SentimentAI", 0),
                votes.get("RegimeDebateAI", 0),
                payload.get("modifier", 1.0),
                event.timestamp.isoformat(),
            )
        )
