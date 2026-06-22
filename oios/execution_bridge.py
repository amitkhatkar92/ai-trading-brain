"""
oios/execution_bridge.py
========================
Shadow-safe execution feedback bridge.

Subscribes to EventBus execution events and writes position state back into
the OIOS opportunities table.  OIOS remains purely read-only to the execution
system — this bridge only writes to the OIOS DB; it never reads from the
execution system's state, and it never influences order decisions.

Architecture guarantee
----------------------
- All writes are wrapped in try/except.  A DB failure here NEVER propagates
  to the calling thread (EventBus handler isolation).
- The bridge holds no references to OrderManager, DecisionEngine, or any
  upstream component.  It is a passive observer, not a participant.
- Thread-safety: SQLite WAL mode + per-call connections (same pattern used
  by the rest of the OIOS layer).

Subscribed events
-----------------
  ORDER_PLACED    → _on_trade_opened()   : set position_exists=1
  POSITION_CLOSED → _on_trade_closed()  : set position_exists=0, trade_pnl_pct

Outcome attribution table
--------------------------
  execution_trade_links (in OIOS DB)
    order_id       TEXT PRIMARY KEY
    opportunity_id TEXT
    symbol         TEXT
    direction_exec TEXT    -- BUY / SELL (execution system convention)
    direction_oios TEXT    -- LONG / SHORT (OIOS convention)
    entry_price    REAL
    linked_at      TEXT
    close_reason   TEXT
    realized_pnl   REAL
    pnl_pct        REAL
"""

from __future__ import annotations

import sqlite3
import threading
import logging
from datetime import datetime
from typing import TYPE_CHECKING, Dict, Optional

if TYPE_CHECKING:
    from communication.event_bus import EventBus
    from communication.events import Event

log = logging.getLogger(__name__)

# ── Direction mapping: execution → OIOS ────────────────────────────────────
_DIR_MAP: Dict[str, str] = {
    "BUY":   "LONG",
    "SELL":  "SHORT",
    "SHORT": "SHORT",
    "LONG":  "LONG",
}

# ── Close-reason → human label ──────────────────────────────────────────────
_CLOSE_LABEL: Dict[str, str] = {
    "SL_HIT":           "STOP_LOSS_HIT",
    "sl_hit":           "STOP_LOSS_HIT",
    "TARGET_HIT":       "TARGET_HIT",
    "target_hit":       "TARGET_HIT",
    "REPLACEMENT":      "TRADE_CLOSED",
    "SYSTEM_CLEANUP":   "SYSTEM_CLEANUP",
    "emergency_close":  "TRADE_CLOSED",
    "CARRY_EXPIRED":    "TRADE_CLOSED",
    "manual":           "MANUAL_EXIT",
}


def _exec_direction_to_oios(direction: str) -> str:
    """Map execution-system direction string to OIOS convention."""
    return _DIR_MAP.get(str(direction).upper(), "LONG")


# ── Link table DDL ───────────────────────────────────────────────────────────
_LINK_TABLE_DDL = """
CREATE TABLE IF NOT EXISTS execution_trade_links (
    order_id        TEXT    PRIMARY KEY,
    opportunity_id  TEXT,
    symbol          TEXT    NOT NULL,
    direction_exec  TEXT    NOT NULL,
    direction_oios  TEXT    NOT NULL,
    entry_price     REAL    NOT NULL,
    linked_at       TEXT    NOT NULL,
    close_reason    TEXT,
    realized_pnl    REAL,
    pnl_pct         REAL
);
"""
_LINK_IDX_DDL = (
    "CREATE INDEX IF NOT EXISTS idx_etl_symbol ON execution_trade_links(symbol);",
    "CREATE INDEX IF NOT EXISTS idx_etl_opp    ON execution_trade_links(opportunity_id);",
)


class ExecutionFeedbackBridge:
    """
    Passive EventBus subscriber that feeds execution outcomes back into OIOS.

    Parameters
    ----------
    total_capital : float
        Used to compute ``position_size_pct``.  Defaults to TOTAL_CAPITAL from
        config; callers may override for testing.
    """

    def __init__(self, total_capital: Optional[float] = None) -> None:
        if total_capital is None:
            try:
                from config import TOTAL_CAPITAL
                total_capital = float(TOTAL_CAPITAL)
            except Exception:
                total_capital = 10_000_000.0
        self._total_capital = max(total_capital, 1.0)
        self._lock = threading.Lock()
        # In-memory map: order_id → opportunity_id (populated on trade open)
        self._order_opp_map: Dict[str, str] = {}
        self._ensure_link_table()

    # ─────────────────────────────────────────────────────────────────
    # SCHEMA BOOTSTRAP
    # ─────────────────────────────────────────────────────────────────

    def _ensure_link_table(self) -> None:
        """Create the execution_trade_links table in the OIOS DB if absent."""
        try:
            conn = self._connect()
            conn.execute(_LINK_TABLE_DDL)
            for idx in _LINK_IDX_DDL:
                conn.execute(idx)
            conn.commit()
            conn.close()
        except Exception as exc:
            log.debug("[ExecutionBridge] Link table bootstrap failed: %s", exc)

    # ─────────────────────────────────────────────────────────────────
    # CONNECTION
    # ─────────────────────────────────────────────────────────────────

    def _connect(self) -> sqlite3.Connection:
        """Open a connection to the OIOS database."""
        from oios.db.connection import get_connection
        return get_connection()

    # ─────────────────────────────────────────────────────────────────
    # EVENTBUS SUBSCRIPTION
    # ─────────────────────────────────────────────────────────────────

    def subscribe(self, bus: "EventBus") -> None:
        """Wire this bridge into the shared EventBus.  Call once at startup."""
        from communication.events import EventType
        bus.subscribe(
            EventType.ORDER_PLACED,
            self._on_trade_opened,
            agent_name="OIOSExecutionBridge",
        )
        bus.subscribe(
            EventType.POSITION_CLOSED,
            self._on_trade_closed,
            agent_name="OIOSExecutionBridge",
        )
        log.info("[ExecutionBridge] Subscribed to ORDER_PLACED + POSITION_CLOSED.")

    # ─────────────────────────────────────────────────────────────────
    # HANDLERS
    # ─────────────────────────────────────────────────────────────────

    def _on_trade_opened(self, event: "Event") -> None:
        """
        Called when the orchestrator publishes ORDER_PLACED.

        Updates the matching OIOS opportunity:
          position_exists    = 1
          position_size_pct  = (qty * entry_price) / total_capital * 100
          position_open_date = today (ISO-8601)
          last_updated_at    = now

        Also inserts a row into execution_trade_links.
        """
        try:
            p = event.payload or {}
            order_id    = str(p.get("order_id", ""))
            symbol      = str(p.get("symbol", ""))
            direction   = str(p.get("direction", "BUY"))
            entry_price = float(p.get("entry_price", 0.0))
            quantity    = int(p.get("quantity", 0))
            strategy    = str(p.get("strategy", ""))

            if not order_id or not symbol:
                return

            oios_dir = _exec_direction_to_oios(direction)
            today    = datetime.now().strftime("%Y-%m-%d")
            now_ts   = datetime.now().isoformat()

            # Compute position size as % of total capital
            notional = entry_price * quantity
            size_pct = round(notional / self._total_capital * 100.0, 4) if notional > 0 else 0.0

            with self._lock:
                conn = None
                try:
                    conn = self._connect()

                    # ── Find matching OIOS opportunity (safe — returns None on error) ──
                    opp_id = self._find_opportunity(conn, symbol, oios_dir)

                    # ── Update opportunity ───────────────────────────────────
                    if opp_id:
                        try:
                            conn.execute("""
                                UPDATE opportunities
                                   SET position_exists     = 1,
                                       position_size_pct   = ?,
                                       position_open_date  = ?,
                                       last_updated_at     = ?
                                 WHERE opportunity_id = ?
                            """, (size_pct, today, now_ts, opp_id))
                            log.info(
                                "[ExecutionBridge] ✅ OPEN: %s %s → opp_id=%s  "
                                "size_pct=%.2f%%",
                                symbol, direction, opp_id, size_pct,
                            )
                        except Exception as opp_exc:
                            log.debug("[ExecutionBridge] Opp update failed: %s", opp_exc)
                    else:
                        log.debug(
                            "[ExecutionBridge] No live OIOS opportunity for %s %s "
                            "(trade still recorded in link table).",
                            symbol, oios_dir,
                        )

                    # ── Record in link table (always, even if no opp match) ──
                    self._order_opp_map[order_id] = opp_id or ""
                    conn.execute("""
                        INSERT OR IGNORE INTO execution_trade_links
                            (order_id, opportunity_id, symbol,
                             direction_exec, direction_oios,
                             entry_price, linked_at)
                        VALUES (?,?,?,?,?,?,?)
                    """, (order_id, opp_id or None, symbol,
                          direction, oios_dir,
                          entry_price, now_ts))
                    conn.commit()

                except Exception as inner_exc:
                    log.debug("[ExecutionBridge] OPEN write error: %s", inner_exc)
                finally:
                    if conn:
                        conn.close()

        except Exception as exc:
            log.debug("[ExecutionBridge] _on_trade_opened failed: %s", exc)

    def _on_trade_closed(self, event: "Event") -> None:
        """
        Called when OrderManager publishes POSITION_CLOSED.

        Updates the matching OIOS opportunity:
          position_exists = 0
          trade_pnl_pct   = realized pnl as % of notional
          last_updated_at = now

        Also updates the link table row with exit data.
        """
        try:
            p = event.payload or {}
            order_id     = str(p.get("order_id", ""))
            symbol       = str(p.get("symbol", ""))
            direction    = str(p.get("direction", "BUY"))
            pnl          = float(p.get("pnl", 0.0))
            pnl_pct      = float(p.get("pnl_pct", 0.0))
            close_reason = str(p.get("close_reason", "unknown"))
            exit_price   = float(p.get("exit_price", 0.0))

            if not order_id and not symbol:
                return

            oios_dir  = _exec_direction_to_oios(direction)
            now_ts    = datetime.now().isoformat()
            close_lbl = _CLOSE_LABEL.get(close_reason, "TRADE_CLOSED")

            with self._lock:
                conn = None
                try:
                    conn = self._connect()

                    # ── Resolve opportunity id (memory → DB fallback) ────────
                    opp_id = self._order_opp_map.get(order_id)
                    if not opp_id and order_id:
                        try:
                            row = conn.execute(
                                "SELECT opportunity_id FROM execution_trade_links WHERE order_id=?",
                                (order_id,),
                            ).fetchone()
                            if row and row[0]:
                                opp_id = row[0]
                        except Exception:
                            pass

                    # If still no opp_id, try live lookup by symbol+direction
                    if not opp_id:
                        opp_id = self._find_opportunity(conn, symbol, oios_dir)

                    # ── Update opportunity ───────────────────────────────────
                    if opp_id:
                        try:
                            conn.execute("""
                                UPDATE opportunities
                                   SET position_exists  = 0,
                                       trade_pnl_pct    = ?,
                                       last_updated_at  = ?
                                 WHERE opportunity_id = ?
                            """, (pnl_pct, now_ts, opp_id))
                            log.info(
                                "[ExecutionBridge] ✅ CLOSE: %s %s → opp_id=%s  "
                                "pnl_pct=%.4f%%  reason=%s  label=%s",
                                symbol, direction, opp_id,
                                pnl_pct, close_reason, close_lbl,
                            )
                        except Exception as opp_exc:
                            log.debug("[ExecutionBridge] Opp close-update failed: %s", opp_exc)
                    else:
                        log.debug(
                            "[ExecutionBridge] No opportunity found for CLOSE %s %s.",
                            symbol, direction,
                        )

                    # ── Update link table row ────────────────────────────────
                    conn.execute("""
                        UPDATE execution_trade_links
                           SET close_reason    = ?,
                               realized_pnl    = ?,
                               pnl_pct         = ?
                         WHERE order_id = ?
                    """, (close_lbl, round(pnl, 2), pnl_pct, order_id))
                    # If no row existed (e.g. position opened before bridge was wired),
                    # insert a minimal record for audit completeness.
                    conn.execute("""
                        INSERT OR IGNORE INTO execution_trade_links
                            (order_id, opportunity_id, symbol,
                             direction_exec, direction_oios,
                             entry_price, linked_at, close_reason, realized_pnl, pnl_pct)
                        VALUES (?,?,?,?,?,?,?,?,?,?)
                    """, (order_id, opp_id or None, symbol,
                          direction, oios_dir,
                          exit_price, now_ts,
                          close_lbl, round(pnl, 2), pnl_pct))

                    conn.commit()

                    # Clean up in-memory map
                    self._order_opp_map.pop(order_id, None)

                except Exception as inner_exc:
                    log.debug("[ExecutionBridge] CLOSE write error: %s", inner_exc)
                finally:
                    if conn:
                        conn.close()

        except Exception as exc:
            log.debug("[ExecutionBridge] _on_trade_closed failed: %s", exc)

    # ─────────────────────────────────────────────────────────────────
    # HELPERS
    # ─────────────────────────────────────────────────────────────────

    def _find_opportunity(
        self,
        conn: sqlite3.Connection,
        symbol: str,
        oios_direction: str,
    ) -> Optional[str]:
        """
        Return the opportunity_id of the most recent live (ACTIVE / WATCHING /
        DISCOVERED) opportunity for (symbol, direction), or None if not found
        or if the opportunities table does not exist yet.

        Looks for ACTIVE first, then WATCHING, then DISCOVERED, to prefer the
        most mature match when multiple live opportunities exist.
        """
        try:
            row = conn.execute("""
                SELECT opportunity_id
                  FROM opportunities
                 WHERE symbol = ?
                   AND direction = ?
                   AND current_state IN ('ACTIVE','WATCHING','DISCOVERED')
                 ORDER BY
                   CASE current_state
                     WHEN 'ACTIVE'     THEN 1
                     WHEN 'WATCHING'   THEN 2
                     WHEN 'DISCOVERED' THEN 3
                   END,
                   created_at DESC
                 LIMIT 1
            """, (symbol, oios_direction)).fetchone()
            return row[0] if row else None
        except Exception:
            # opportunities table may not exist yet (OIOS engine never run)
            return None

    # ─────────────────────────────────────────────────────────────────
    # DIAGNOSTICS
    # ─────────────────────────────────────────────────────────────────

    def get_link_count(self) -> int:
        """Return total rows in execution_trade_links (for health checks)."""
        try:
            conn = self._connect()
            cnt  = conn.execute("SELECT COUNT(*) FROM execution_trade_links").fetchone()[0]
            conn.close()
            return cnt
        except Exception:
            return -1

    def get_linked_trades(self, limit: int = 50) -> list:
        """Return the most recent trade link records (for reporting/debugging)."""
        try:
            conn = self._connect()
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT * FROM execution_trade_links
                 ORDER BY linked_at DESC
                 LIMIT ?
            """, (limit,)).fetchall()
            conn.close()
            return [dict(r) for r in rows]
        except Exception:
            return []


# ── Module-level singleton ───────────────────────────────────────────────────
_BRIDGE_INSTANCE: Optional[ExecutionFeedbackBridge] = None


def get_execution_bridge(total_capital: Optional[float] = None) -> ExecutionFeedbackBridge:
    """Return (or create) the module-level bridge singleton."""
    global _BRIDGE_INSTANCE
    if _BRIDGE_INSTANCE is None:
        _BRIDGE_INSTANCE = ExecutionFeedbackBridge(total_capital=total_capital)
    return _BRIDGE_INSTANCE
