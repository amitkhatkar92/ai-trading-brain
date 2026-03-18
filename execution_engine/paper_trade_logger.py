"""
Paper Trade Logger
==================
Writes every simulated trade to ``data/paper_trade_log.csv`` and prints a
concise daily summary to the terminal.

Integration
-----------
Instantiated and wired in ``run_live.py``.  It works by:

  1. Subscribing to the EventBus ``ORDER_PLACED`` event — fired by the
     Orchestrator each time ``OrderManager.execute()`` successfully places a
     simulated order.  This writes an OPEN row immediately.

  2. On each ``CYCLE_COMPLETE`` event (via ``scan_for_closes``) the logger
     inspects ``OrderManager._orders`` for positions that have transitioned
     to status="closed" since the last scan, and appends CLOSED rows.

  3. On ``LEARNING_CYCLE_COMPLETE`` (EOD at 15:35), it calls
     ``print_daily_summary`` and resets intra-day counters.

CSV format (``data/paper_trade_log.csv``)
-----------------------------------------
date | symbol | strategy | entry_price | stop_price | target_price |
quantity | status | pnl

Rules
-----
* Never modifies OrderManager, StrategyLab, RiskControl, BacktestingAI or
  any other protected module.
* All writes are append-only; no rows are ever deleted or back-patched.
* Thread-safe: uses a threading.Lock around all CSV writes.
"""

from __future__ import annotations

import csv
import os
import threading
from datetime import date, datetime
from typing import TYPE_CHECKING, Dict, Optional, Set

from utils import get_logger

if TYPE_CHECKING:
    from execution_engine.order_manager import OrderManager
    from communication.event_bus import EventBus
    from communication.events import Event

log = get_logger(__name__)

# ── CSV config ────────────────────────────────────────────────────────────────
_DATA_DIR        = os.path.join(os.path.dirname(__file__), "..", "data")
PAPER_TRADE_LOG  = os.path.join(_DATA_DIR, "paper_trade_log.csv")
_CSV_HEADER      = [
    "date", "symbol", "strategy",
    "entry_price", "stop_price", "target_price",
    "quantity", "status", "pnl",
]


class PaperTradeLogger:
    """
    Passive observer that records all paper-trade events and
    prints a daily performance summary.

    Parameters
    ----------
    order_manager : OrderManager
        Reference to the live OrderManager instance so that closed
        positions can be detected without modifying the OrderManager.
    """

    def __init__(self, order_manager: "OrderManager") -> None:
        self._om           = order_manager
        self._lock         = threading.Lock()
        self._seen_open:   Set[str] = set()   # order_ids logged as OPEN
        self._seen_closed: Set[str] = set()   # order_ids logged as CLOSED

        # ── Daily counters (reset each EOD) ──────────────────────────────
        self._day_str        = str(date.today())
        self._signals_today  = 0     # total signals seen (incremented by caller)
        self._executions_today = 0   # orders placed today
        self._closed_today   = 0     # positions closed today
        self._daily_pnl      = 0.0   # realised PnL today
        self._cumulative_pnl = 0.0   # running total (persists across EOD resets)

        # Ensure the CSV exists with the correct header
        os.makedirs(_DATA_DIR, exist_ok=True)
        if not os.path.exists(PAPER_TRADE_LOG):
            with open(PAPER_TRADE_LOG, "w", newline="", encoding="utf-8") as fh:
                csv.DictWriter(fh, fieldnames=_CSV_HEADER).writeheader()
            log.info("[PaperTradeLogger] Created %s", os.path.abspath(PAPER_TRADE_LOG))

        log.info("[PaperTradeLogger] Initialised — journal: %s",
                 os.path.abspath(PAPER_TRADE_LOG))

    # ─────────────────────────────────────────────────────────────────
    # EVENT BUS SUBSCRIPTION
    # ─────────────────────────────────────────────────────────────────

    # ─────────────────────────────────────────────────────────────────
    # TELEGRAM PUSH HELPER
    # ─────────────────────────────────────────────────────────────────

    def _push(self, text: str) -> None:
        """Fire-and-forget Telegram push — never raises."""
        try:
            from notifications.telegram_bot import get_telegram_bot
            get_telegram_bot().push(text)
        except Exception as exc:
            log.debug("[PaperTradeLogger] Telegram push failed: %s", exc)

    # ─────────────────────────────────────────────────────────────────
    # EVENT BUS SUBSCRIPTION
    # ─────────────────────────────────────────────────────────────────

    def subscribe(self, bus: "EventBus") -> None:
        """Wire this logger into the shared EventBus."""
        from communication.events import EventType

        bus.subscribe(
            EventType.ORDER_PLACED,
            self._on_order_placed,
            agent_name="PaperTradeLogger",
        )
        bus.subscribe(
            EventType.CYCLE_COMPLETE,
            self._on_cycle_complete,
            agent_name="PaperTradeLogger",
        )
        bus.subscribe(
            EventType.LEARNING_CYCLE_COMPLETE,
            self._on_eod,
            agent_name="PaperTradeLogger",
        )
        log.info("[PaperTradeLogger] Subscribed to ORDER_PLACED / "
                 "CYCLE_COMPLETE / LEARNING_CYCLE_COMPLETE.")

    # ─────────────────────────────────────────────────────────────────
    # EVENT HANDLERS
    # ─────────────────────────────────────────────────────────────────

    def _on_order_placed(self, event: "Event") -> None:
        """Called when Orchestrator publishes ORDER_PLACED."""
        p = event.payload or {}
        order_id = str(p.get("order_id", ""))
        if not order_id or order_id in self._seen_open:
            return

        row = {
            "date":         str(date.today()),
            "symbol":       str(p.get("symbol", "")),
            "strategy":     str(p.get("strategy", "")),
            "entry_price":  float(p.get("entry_price", 0.0)),
            "stop_price":   float(p.get("stop_loss", 0.0)),
            "target_price": float(p.get("target_price", 0.0)),
            "quantity":     int(p.get("quantity", 0)),
            "status":       "OPEN",
            "pnl":          0.0,
        }
        self._append_row(row)
        self._seen_open.add(order_id)
        self._executions_today += 1
        log.info("[PaperTradeLogger] Logged OPEN  %-12s  %s @ %.2f",
                 row["symbol"], row["strategy"], row["entry_price"])

        # ── Telegram ENTRY alert ──────────────────────────────────────
        entry  = row["entry_price"]
        stop   = row["stop_price"]
        target = row["target_price"]
        qty    = row["quantity"]
        risk   = entry - stop if entry > stop else stop - entry
        reward = abs(target - entry)
        rr_str = f"{reward / risk:.1f}x" if risk > 0 else "N/A"
        self._push(
            f"\U0001f7e2 <b>TRADE ENTRY</b>\n"
            f"\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\n"
            f"Symbol    : <b>{row['symbol']}</b>\n"
            f"Strategy  : {row['strategy']}\n"
            f"Entry     : \u20b9{entry:,.2f}\n"
            f"Stop      : \u20b9{stop:,.2f}\n"
            f"Target    : \u20b9{target:,.2f}\n"
            f"Qty       : {qty}\n"
            f"R:R       : {rr_str}\n"
            f"\U0001f550 {datetime.now().strftime('%H:%M:%S')}  [PAPER]"
        )

    def _on_cycle_complete(self, event: "Event") -> None:
        """Called after every full analysis cycle — scan for newly closed positions."""
        self.scan_for_closes()
        # Accumulate signals from payload
        n = (event.payload or {}).get("signals_processed", 0)
        if isinstance(n, int):
            self._signals_today += n

    def _on_eod(self, event: "Event") -> None:
        """Called at EOD learning cycle — print daily summary then reset counters."""
        self.scan_for_closes()
        self.print_daily_summary()
        self._reset_daily_counters()

    # ─────────────────────────────────────────────────────────────────
    # SCAN FOR NEWLY CLOSED POSITIONS
    # ─────────────────────────────────────────────────────────────────

    def scan_for_closes(self) -> None:
        """
        Check OrderManager's internal order dict for positions that have
        transitioned to 'closed' since the last scan.  Append a CLOSED row
        for each one.
        """
        try:
            all_orders: dict = getattr(self._om, "_orders", {})
        except Exception:
            return

        for order_id, rec in list(all_orders.items()):
            if getattr(rec, "status", "") != "closed":
                continue
            if order_id in self._seen_closed:
                continue

            row = {
                "date":         (rec.closed_at.strftime("%Y-%m-%d")
                                 if rec.closed_at else str(date.today())),
                "symbol":       rec.symbol,
                "strategy":     rec.strategy,
                "entry_price":  round(rec.entry_price, 2),
                "stop_price":   round(rec.stop_loss, 2),
                "target_price": round(rec.target, 2),
                "quantity":     rec.quantity,
                "status":       "CLOSED",
                "pnl":          round(rec.pnl, 2),
            }
            self._append_row(row)
            self._seen_closed.add(order_id)
            self._closed_today  += 1
            self._daily_pnl     += rec.pnl
            self._cumulative_pnl += rec.pnl
            log.info("[PaperTradeLogger] Logged CLOSED %-12s  PnL=₹%+,.0f",
                     rec.symbol, rec.pnl)
            # ── Telegram EXIT alert ───────────────────────────────────
            win     = rec.pnl >= 0
            icon    = "\u2705" if win else "\u274c"
            result  = "WIN" if win else "LOSS"
            exit_px = round(rec.target if win else rec.stop_loss, 2)
            self._push(
                f"{icon} <b>TRADE EXIT \u2014 {result}</b>\n"
                f"\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\n"
                f"Symbol    : <b>{rec.symbol}</b>\n"
                f"Strategy  : {rec.strategy}\n"
                f"Entry     : \u20b9{rec.entry_price:,.2f}\n"
                f"Exit      : \u20b9{exit_px:,.2f}\n"
                f"PnL       : <b>\u20b9{rec.pnl:+,.0f}</b>\n"
                f"\U0001f550 {datetime.now().strftime('%H:%M:%S')}  [PAPER]"
            )
    # ─────────────────────────────────────────────────────────────────
    # DAILY SUMMARY
    # ─────────────────────────────────────────────────────────────────

    def print_daily_summary(self) -> None:
        """Print the EOD paper-trading summary to the terminal."""
        try:
            open_positions = len(self._om.get_open_orders())
        except Exception:
            open_positions = 0

        width = 55
        print()
        print("═" * width)
        print(f"  📋  Paper Trading Summary  —  {self._day_str}")
        print("═" * width)
        print(f"  Total signals today  : {self._signals_today}")
        print(f"  Trades executed      : {self._executions_today}")
        print(f"  Open positions       : {open_positions}")
        print(f"  Closed positions     : {self._closed_today}")
        print(f"  Daily PnL            : ₹{self._daily_pnl:+,.0f}")
        print(f"  Cumulative PnL       : ₹{self._cumulative_pnl:+,.0f}")
        print("═" * width)
        print(f"  Journal              : {os.path.basename(PAPER_TRADE_LOG)}")
        print("═" * width)
        print()

        # ── Telegram EOD summary (locked format) ──────────────────────────
        self._push(
            f"📋 <b>EOD Summary — {self._day_str}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"Signals today  : {self._signals_today}\n"
            f"Executed       : {self._executions_today}\n"
            f"Open positions : {open_positions}\n"
            f"Closed         : {self._closed_today}\n"
            f"Daily PnL      : <b>₹{self._daily_pnl:+,.0f}</b>\n"
            f"Cumulative     : <b>₹{self._cumulative_pnl:+,.0f}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"[PAPER MODE]"
        )

    # ─────────────────────────────────────────────────────────────────
    # INTERNAL HELPERS
    # ─────────────────────────────────────────────────────────────────

    def _append_row(self, row: dict) -> None:
        """Thread-safe append of one row to the CSV journal."""
        with self._lock:
            try:
                with open(PAPER_TRADE_LOG, "a", newline="",
                          encoding="utf-8") as fh:
                    csv.DictWriter(fh, fieldnames=_CSV_HEADER).writerow(row)
            except Exception as exc:
                log.warning("[PaperTradeLogger] Write error: %s", exc)

    def _reset_daily_counters(self) -> None:
        """Reset intra-day counters after printing the EOD summary."""
        self._day_str          = str(date.today())
        self._signals_today    = 0
        self._executions_today = 0
        self._closed_today     = 0
        self._daily_pnl        = 0.0
        # _cumulative_pnl intentionally NOT reset — it accumulates lifetime

    def increment_signals(self, n: int) -> None:
        """External call to add to today's signal count (from run_live.py)."""
        self._signals_today += max(0, n)
