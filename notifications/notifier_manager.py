"""
Notification Manager
=====================
Unified notification system. Sends alerts via:
  • Telegram (primary — instant, free)
  • Console log (always active, no config needed)

Telegram setup:
  1. Message @BotFather on Telegram → /newbot → get BOT_TOKEN
  2. Message your bot once → get CHAT_ID via:
     curl https://api.telegram.org/bot<TOKEN>/getUpdates
  3. Add to .env:
       TELEGRAM_BOT_TOKEN=123456:ABCdef...
       TELEGRAM_CHAT_ID=987654321

Alert categories with auto-formatting:
  TRADE_OPENED    — green ✅
  TRADE_CLOSED    — blue 💰 / red 🔴
  RISK_TRIGGERED  — orange ⚠️
  SYSTEM_ERROR    — red 🚨
  STRATEGY_UPDATE — info 📊
  MARKET_ALERT    — yellow 📈
"""

from __future__ import annotations
import os
import queue
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional

from utils import get_logger

log = get_logger(__name__)


def _get_nifty_str() -> str:
    """Return '\nNIFTY: ₹XX,XXX.XX' string or empty string if unavailable."""
    try:
        from data_feeds import get_feed_manager
        q = get_feed_manager().get_quote("NIFTY")
        if q and getattr(q, "ltp", None):
            return f"\nNIFTY: ₹{float(q.ltp):,.2f}"
    except Exception:
        pass
    return ""


class AlertType(str, Enum):
    TRADE_OPENED    = "trade_opened"
    TRADE_CLOSED    = "trade_closed"
    TRADE_REJECTED  = "trade_rejected"
    RISK_TRIGGERED  = "risk_triggered"
    SYSTEM_ERROR    = "system_error"
    SYSTEM_START    = "system_start"
    SYSTEM_STOP     = "system_stop"
    STRATEGY_UPDATE = "strategy_update"
    MARKET_ALERT    = "market_alert"
    EDGE_DISCOVERED = "edge_discovered"
    EOD_SUMMARY     = "eod_summary"


# Icons per alert type
_ICONS = {
    AlertType.TRADE_OPENED:    "✅",
    AlertType.TRADE_CLOSED:    "💰",
    AlertType.TRADE_REJECTED:  "❌",
    AlertType.RISK_TRIGGERED:  "⚠️",
    AlertType.SYSTEM_ERROR:    "🚨",
    AlertType.SYSTEM_START:    "🚀",
    AlertType.SYSTEM_STOP:     "🛑",
    AlertType.STRATEGY_UPDATE: "📊",
    AlertType.MARKET_ALERT:    "📈",
    AlertType.EDGE_DISCOVERED: "🔬",
    AlertType.EOD_SUMMARY:     "📋",
}


@dataclass
class Alert:
    alert_type: AlertType
    title:      str
    body:       str
    priority:   int   = 1     # 1=normal 2=high 3=critical
    timestamp:  str   = field(default_factory=lambda: datetime.now().strftime("%H:%M:%S"))

    def to_telegram_message(self) -> str:
        icon  = _ICONS.get(self.alert_type, "ℹ️")
        lines = [
            f"{icon} *{self.title}*",
            f"🕐 {self.timestamp}",
            "",
            self.body,
        ]
        return "\n".join(lines)

    def to_log_message(self) -> str:
        icon = _ICONS.get(self.alert_type, "ℹ️")
        return f"[Alert] {icon} {self.title} | {self.body}"


class TelegramNotifier:
    """
    Sends alerts to a Telegram bot.
    Messages are queued and sent asynchronously to avoid blocking the brain.
    """

    def __init__(self, bot_token: str, chat_id: str) -> None:
        self._token    = bot_token
        self._chat_id  = chat_id
        self._queue: queue.Queue[Alert] = queue.Queue()
        self._running  = False
        self._thread:  Optional[threading.Thread] = None
        self._requests = None
        self._available= False
        self._try_import()

    def _try_import(self) -> None:
        try:
            import requests
            self._requests = requests
            self._available = True
        except ImportError:
            log.warning("[TelegramNotifier] requests not installed — "
                        "Telegram alerts disabled. pip install requests")

    def start(self) -> None:
        if not self._available or not self._token or not self._chat_id:
            log.info("[TelegramNotifier] Not configured — alerts logged only.")
            return
        self._running = True
        self._thread  = threading.Thread(target=self._worker, daemon=True)
        self._thread.start()
        log.info("[TelegramNotifier] Started. Chat ID=%s", self._chat_id)

    def stop(self) -> None:
        self._running = False

    def send(self, alert: Alert) -> None:
        self._queue.put_nowait(alert)

    def _worker(self) -> None:
        url = f"https://api.telegram.org/bot{self._token}/sendMessage"
        while self._running:
            try:
                alert = self._queue.get(timeout=2)
                msg   = alert.to_telegram_message()
                resp  = self._requests.post(url, json={
                    "chat_id":    self._chat_id,
                    "text":       msg,
                    "parse_mode": "Markdown",
                }, timeout=10)
                if not resp.ok:
                    log.warning("[TelegramNotifier] Send failed: %s", resp.text[:100])
            except queue.Empty:
                continue
            except Exception as exc:
                log.error("[TelegramNotifier] Error: %s", exc)
                time.sleep(5)


class NotifierManager:
    """
    Central alert dispatcher.
    All AI agents call this instead of directly using Telegram.

    Usage::
        from notifications import get_notifier
        notifier = get_notifier()
        notifier.trade_opened("RELIANCE", "BUY", 2880, 2820, 2960, "Breakout_Volume")
        notifier.risk_triggered("Portfolio heat > 5%")
        notifier.eod_summary(4, 3, 1, 1250.0)
    """

    def __init__(self) -> None:
        token   = os.getenv("TELEGRAM_BOT_TOKEN", "")
        chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
        self._telegram = TelegramNotifier(token, chat_id)
        self._telegram.start()
        self._enabled  = bool(token and chat_id)
        log.info("[NotifierManager] Telegram=%s",
                 "enabled" if self._enabled else "disabled (set TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID)")

    # ── Helper dispatch ────────────────────────────────────────────────────

    def _dispatch(self, alert: Alert) -> None:
        log.info(alert.to_log_message())
        if self._enabled:
            self._telegram.send(alert)

    # ── Typed alert constructors ───────────────────────────────────────────

    def trade_opened(
        self,
        symbol: str, direction: str,
        entry: float, stop: float, target: float,
        strategy: str, mode: str = "paper",
    ) -> None:
        rr    = abs(target - entry) / abs(entry - stop) if entry != stop else 0
        _nifty = _get_nifty_str()
        body  = (f"Symbol: `{symbol}`\n"
                 f"Direction: {direction}\n"
                 f"Entry: ₹{entry:.2f}  SL: ₹{stop:.2f}  Target: ₹{target:.2f}\n"
                 f"R:R = {rr:.1f}  Strategy: `{strategy}`\n"
                 f"Mode: {'🧪 PAPER' if mode == 'paper' else '💵 LIVE'}"
                 f"{_nifty}")
        self._dispatch(Alert(AlertType.TRADE_OPENED, f"Trade Opened: {symbol}", body))

    def trade_closed(
        self,
        symbol: str, pnl: float, r_multiple: float,
        strategy: str, mode: str = "paper",
    ) -> None:
        won   = pnl > 0
        icon  = "💰" if won else "🔴"
        _nifty = _get_nifty_str()
        body  = (f"Symbol: `{symbol}`\n"
                 f"Net P&L: {'₹' + f'{pnl:+,.0f}'}\n"
                 f"R-Multiple: {r_multiple:+.2f}R\n"
                 f"Strategy: `{strategy}`  Mode: {'🧪 PAPER' if mode == 'paper' else '💵 LIVE'}"
                 f"{_nifty}")
        title = f"{icon} Trade Closed: {symbol} ({'WIN' if won else 'LOSS'})"
        self._dispatch(Alert(AlertType.TRADE_CLOSED, title, body,
                             priority=2 if abs(r_multiple) >= 2 else 1))

    def trade_rejected(self, symbol: str, reason: str) -> None:
        body = f"Symbol: `{symbol}`\nReason: {reason}"
        self._dispatch(Alert(AlertType.TRADE_REJECTED, "Signal Rejected", body))

    def risk_triggered(self, reason: str, details: str = "") -> None:
        body = f"Trigger: {reason}\n{details}"
        self._dispatch(Alert(AlertType.RISK_TRIGGERED, "⚠️ Risk Limit Hit",
                             body, priority=3))

    def system_start(self, capital: float, mode: str) -> None:
        body = (f"Capital: ₹{capital:,.0f}\n"
                f"Mode: {'🧪 PAPER' if mode == 'paper' else '💵 LIVE'}\n"
                f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        self._dispatch(Alert(AlertType.SYSTEM_START, "🚀 AI Brain Started", body))

    def system_error(self, component: str, error: str) -> None:
        body = f"Component: `{component}`\nError: {error[:300]}"
        self._dispatch(Alert(AlertType.SYSTEM_ERROR, "🚨 System Error",
                             body, priority=3))

    def edge_discovered(self, name: str, category: str, expectancy_r: float) -> None:
        exp_sign = "+" if expectancy_r >= 0 else ""
        body = (f"Edge: `{name}`\n"
                f"Category: {category}\n"
                f"Expectancy: {exp_sign}{expectancy_r:.3f}R")
        self._dispatch(Alert(AlertType.EDGE_DISCOVERED, "🔬 New Edge Discovered", body))

    def eod_summary(
        self, total_trades: int, wins: int, losses: int,
        net_pnl: float, capital: float,
    ) -> None:
        wr   = wins / total_trades * 100 if total_trades else 0
        ret  = net_pnl / capital * 100 if capital else 0
        body = (f"Trades: {total_trades} ({wins}W / {losses}L)\n"
                f"Win Rate: {wr:.0f}%\n"
                f"Net P&L: ₹{net_pnl:+,.0f} ({ret:+.2f}%)")
        self._dispatch(Alert(AlertType.EOD_SUMMARY, "📋 EOD Summary", body))

    def market_alert(self, title: str, body: str) -> None:
        self._dispatch(Alert(AlertType.MARKET_ALERT, title, body))

    def send_alert(self, message: str) -> None:
        """Single-argument convenience wrapper used by MasterOrchestrator."""
        self._dispatch(Alert(AlertType.MARKET_ALERT, "⚠️ Market Alert", message))


# ── Singleton ──────────────────────────────────────────────────────────────
_INSTANCE: Optional[NotifierManager] = None

def get_notifier() -> NotifierManager:
    global _INSTANCE
    if _INSTANCE is None:
        _INSTANCE = NotifierManager()
    return _INSTANCE
