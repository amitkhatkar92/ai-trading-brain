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
import json
import os
import queue
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
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
        self._session  = None   # persistent Session — prevents FD exhaustion on burst sends
        self._available= False
        self._try_import()

    def _try_import(self) -> None:
        try:
            import requests
            import requests.adapters as _req_adapters
            self._requests = requests
            self._available = True
            # Persistent session reuses the underlying TCP connection so that a
            # burst of notifications (e.g. emergency_close closing 9 positions)
            # does not open 9 separate SSL sockets, which can exhaust OS FD limits.
            _sess = requests.Session()
            _adapter = _req_adapters.HTTPAdapter(
                pool_connections=1, pool_maxsize=1, max_retries=1
            )
            _sess.mount("https://", _adapter)
            self._session = _sess
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
                # Attempt 1: send with Markdown formatting.
                # Attempt 2: if Markdown parse fails (e.g. unmatched _ from
                # dynamic content like RECONCILIATION_SUSPECT or Bull_Call_Spread),
                # retry without parse_mode so the alert is never silently dropped.
                _sent = False
                for _parse_mode in ("Markdown", None):
                    _payload = {"chat_id": self._chat_id, "text": msg}
                    if _parse_mode:
                        _payload["parse_mode"] = _parse_mode
                    try:
                        if self._session is not None:
                            resp = self._session.post(url, json=_payload, timeout=10)
                        elif self._requests is not None:
                            resp = self._requests.post(url, json=_payload, timeout=10)
                        else:
                            break
                        if resp.ok:
                            _sent = True
                            break
                        # 400 = parse error → retry without parse_mode
                        if resp.status_code == 400 and _parse_mode:
                            log.debug(
                                "[TelegramMarkdownFallback] Markdown parse failed "
                                "(likely unescaped _ or *) — retrying as plain text. "
                                "Error: %s", resp.text[:80],
                            )
                            continue   # try again without parse_mode
                        # Other error — log and stop
                        log.warning("[TelegramNotifier] Send failed: %s", resp.text[:120])
                        break
                    except Exception as _send_exc:
                        log.error("[TelegramNotifier] Error: %s", _send_exc)
                        time.sleep(5)
                        break
                if not _sent:
                    log.warning(
                        "[TelegramAlertFailed] Alert dropped after all retries. "
                        "First 120 chars: %s", msg[:120],
                    )
            except queue.Empty:
                continue
            except Exception as exc:
                log.error("[TelegramNotifier] Worker error: %s", exc)
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

    # Per-alert-category cooldown in seconds.
    # Prevents operator Telegram spam from multiple governance paths firing in the same cycle.
    _ALERT_COOLDOWNS: dict = {
        "OPTIONS_CHAIN":   300.0,   # 5 min
        "EQUITY_TRUTH":    120.0,   # 2 min
        "FULL_MARKET":      60.0,   # 1 min
        "DRIFT":           900.0,   # 15 min
        "TOKEN":          1800.0,   # 30 min
    }
    _DEFAULT_COOLDOWN: float = 60.0   # 60s default for uncategorised market alerts
    # Persist dedup state here so restarts don't reset the cooldown clock.
    _ALERT_STATE_PATH: Path = Path("data/alert_governance_state.json")

    def __init__(self) -> None:
        token   = os.getenv("TELEGRAM_BOT_TOKEN", "")
        chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
        self._telegram = TelegramNotifier(token, chat_id)
        self._telegram.start()
        self._enabled  = bool(token and chat_id)
        # Alert deduplication — fingerprint-based with per-category cooldown.
        # _alert_sent[fingerprint] = wall-clock timestamp (time.time()) of last send.
        # _category_state[category] = last fingerprint sent, or "CLEAR" when recovered.
        self._alert_sent: dict  = {}
        self._category_state: dict = {}
        self._dedup_lock = threading.Lock()
        self._load_alert_state()
        log.info("[NotifierManager] Telegram=%s",
                 "enabled" if self._enabled else "disabled (set TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID)")

    # ── Alert deduplication helpers ────────────────────────────────────────

    def _load_alert_state(self) -> None:
        """Restore dedup state from disk on startup so cooldowns survive restarts."""
        try:
            if self._ALERT_STATE_PATH.exists():
                raw  = json.loads(self._ALERT_STATE_PATH.read_text())
                now  = time.time()
                # Max plausible cooldown — prune anything older than that
                max_cd = max(self._ALERT_COOLDOWNS.values(), default=self._DEFAULT_COOLDOWN)
                self._alert_sent = {
                    k: v for k, v in raw.get("alert_sent", {}).items()
                    if isinstance(v, (int, float)) and now - v < max_cd
                }
                # Only restore category fingerprints that are still in the fresh window
                for cat, fp in raw.get("category_state", {}).items():
                    if fp == "CLEAR" or fp in self._alert_sent:
                        self._category_state[cat] = fp
                log.info(
                    "[AlertGovernance] Restored %d fingerprints from state file",
                    len(self._alert_sent),
                )
        except Exception as exc:
            log.debug("[AlertGovernance] Could not load state file: %s", exc)

    def _save_alert_state(self) -> None:
        """Persist current dedup state to disk (called inside _dedup_lock)."""
        try:
            self._ALERT_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
            _tmp = self._ALERT_STATE_PATH.with_suffix(".tmp")
            _tmp.write_text(json.dumps({
                "alert_sent":      self._alert_sent,
                "category_state":  self._category_state,
            }))
            _tmp.replace(self._ALERT_STATE_PATH)
        except Exception as exc:
            log.debug("[AlertGovernance] Could not save state file: %s", exc)

    @staticmethod
    def _alert_category(title: str) -> str:
        """Normalise alert title to a logical category key."""
        t = title.upper()
        if "OPTIONS CHAIN" in t or "OPTIONS" in t and "DEGRADED" in t:
            return "OPTIONS_CHAIN"
        if "EQUITY TRUTH" in t or "EQUITY SYNTHETIC" in t:
            return "EQUITY_TRUTH"
        if "FULL_MARKET" in t or ("EQUITY" in t and "OPTIONS" in t and "SYNTHETIC" in t):
            return "FULL_MARKET"
        if "DRIFT" in t:
            return "DRIFT"
        if "TOKEN" in t and "EXPIR" in t:
            return "TOKEN"
        return title  # unique title = its own category (e.g. trade alerts)

    def mark_alert_cleared(self, category: str) -> None:
        """Signal that a governance category has recovered to a healthy state.
        The next alert in this category will bypass cooldown (state-change override)."""
        with self._dedup_lock:
            prev = self._category_state.get(category, "CLEAR")
            if prev != "CLEAR":
                log.debug("[AlertDedup] category=%s state→CLEAR (was %s)", category, prev)
            self._category_state[category] = "CLEAR"
            self._save_alert_state()

    def _should_dispatch(self, alert: Alert) -> bool:
        """Return True if the alert should be sent to Telegram.
        Applies fingerprint dedup + cooldown for MARKET_ALERT type only.
        Trade/risk/system alerts always pass through."""
        if alert.alert_type not in (AlertType.MARKET_ALERT,):
            return True

        category    = self._alert_category(alert.title)
        body_prefix = (alert.body or "")[:50].strip().replace("\n", " ")
        fingerprint = f"{alert.alert_type.value}|{alert.title}|{body_prefix}"
        cooldown    = self._ALERT_COOLDOWNS.get(category, self._DEFAULT_COOLDOWN)
        now         = time.time()   # wall-clock: JSON-serializable for state persistence

        with self._dedup_lock:
            last_cat_fp = self._category_state.get(category, "CLEAR")
            last_sent   = self._alert_sent.get(fingerprint)

            # ── State-change override: category had a different/clear fingerprint ─
            if last_cat_fp != fingerprint:
                self._category_state[category] = fingerprint
                self._alert_sent[fingerprint]  = now
                self._save_alert_state()
                log.info(
                    "[AlertGovernance] type=%s sent=True reason=STATE_CHANGE "
                    "fingerprint=%s",
                    category, fingerprint[:80],
                )
                return True

            # ── Same state: apply cooldown ─────────────────────────────────────
            if last_sent is not None:
                age = now - last_sent
                if age < cooldown:
                    log.info(
                        "[AlertDedup] suppressed=True fingerprint=%s age=%.1fs cooldown=%.0fs",
                        fingerprint[:80], age, cooldown,
                    )
                    return False

            # Cooldown expired or first send
            self._category_state[category] = fingerprint
            self._alert_sent[fingerprint]  = now
            self._save_alert_state()
            log.info(
                "[AlertGovernance] type=%s sent=True cooldown=%.0fs fingerprint=%s",
                category, cooldown, fingerprint[:80],
            )
            return True

    # ── Helper dispatch ────────────────────────────────────────────────────

    def _dispatch(self, alert: Alert) -> None:
        log.info(alert.to_log_message())
        if self._enabled and self._should_dispatch(alert):
            self._telegram.send(alert)

    # ── Typed alert constructors ───────────────────────────────────────────

    def limit_order_placed(
        self,
        symbol: str, direction: str,
        entry: float, stop: float, target: float,
        strategy: str, mode: str = "paper",
    ) -> None:
        """Fire when a LIMIT order is placed but NOT yet filled (paper mode)."""
        rr    = abs(target - entry) / abs(entry - stop) if entry != stop else 0
        _nifty = _get_nifty_str()
        body  = (f"Symbol: `{symbol}`\n"
                 f"Direction: {direction}\n"
                 f"Limit: ₹{entry:.2f}  SL: ₹{stop:.2f}  Target: ₹{target:.2f}\n"
                 f"R:R = {rr:.1f}  Strategy: `{strategy}`\n"
                 f"Mode: {'🧪 PAPER' if mode == 'paper' else '💵 LIVE'}\n"
                 f"⚠️ Pending fill — waiting for price to reach limit"
                 f"{_nifty}")
        self._dispatch(Alert(AlertType.TRADE_OPENED, f"⏳ Limit Pending: {symbol}", body))

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
        stability_streak: int = 0,
        stability_required: int = 10,
        official_trades: int = 0,
        official_target: int = 30,
    ) -> None:
        wr   = wins / total_trades * 100 if total_trades else 0
        ret  = net_pnl / capital * 100 if capital else 0
        # ── Stability progress header (most important daily metric) ──────────
        streak_bar   = "▓" * stability_streak + "░" * max(0, stability_required - stability_streak)
        official_bar = "▓" * min(official_trades, official_target) + "░" * max(0, official_target - official_trades)
        if stability_streak >= stability_required:
            streak_line = f"✅ Stability Streak: {stability_streak}/{stability_required}  BASELINE CONFIRMED"
        else:
            streak_line = f"🔄 Stability Streak: {stability_streak}/{stability_required}  [{streak_bar}]"
        if official_trades >= official_target:
            trades_line = f"✅ Official Trades:  {official_trades}/{official_target}  OPTIMISE NOW"
        else:
            trades_line = f"📈 Official Trades:  {official_trades}/{official_target}  [{official_bar}]"
        body = (f"{streak_line}\n"
                f"{trades_line}\n"
                f"────────────────────────\n"
                f"Trades: {total_trades} ({wins}W / {losses}L)\n"
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
