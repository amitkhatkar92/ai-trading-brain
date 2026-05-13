"""
Telegram Command Bot — @Amitkhatkarbot
=======================================
Interactive command bot that lets you query and control the AI Trading Brain
from your Telegram app in real time.

Setup
------
1. Add TELEGRAM_BOT_TOKEN to .env (already done from BotFather)
2. Start the bot:  python main.py --telegram
3. Open Telegram → search @Amitkhatkarbot → send  /start
4. The bot replies with your Chat ID — paste it into .env as TELEGRAM_CHAT_ID
5. Restart:  python main.py --telegram   (now fully private/secured)

Commands
---------
/start        — Register your Chat ID + welcome message
/help         — All available commands
/status       — System status (mode, feeds, uptime)
/nifty        — NIFTY + BANKNIFTY live LTP from Dhan
/vix          — India VIX + USD/INR live
/market       — Full mini market snapshot
/positions    — Open paper/live positions
/pnl          — Today's P&L summary
/edges        — Active trading edges with expectancy
/pause        — Pause signal generation (owner only)
/resume       — Resume signal generation (owner only)
/snapshot     — Live indices + options strike ladder right now
/perf         — Strategy leaderboard (win%, expectancy, status)
/learn        — Learning stage + regime→strategy map

Security
---------
Once TELEGRAM_CHAT_ID is set, only messages from that chat_id are processed.
All other messages receive a "Unauthorized" reply.
"""

from __future__ import annotations

import os
import sys
import threading
import time
from datetime import datetime
from typing import Callable, Dict, Optional

# Ensure project root is searchable
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from utils import get_logger

log = get_logger(__name__)

# ── Helpers ────────────────────────────────────────────────────────────────

def _esc(text: str) -> str:
    """Escape HTML special characters for Telegram HTML parse mode."""
    return (text
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;"))


# ── Bot class ──────────────────────────────────────────────────────────────

class TelegramCommandBot:
    """
    Long-polling Telegram bot using only the `requests` library.
    Runs in a background daemon thread — never blocks the trading brain.
    """

    POLL_TIMEOUT = 30        # long-poll seconds (Telegram holds the connection)
    RETRY_DELAY  = 10        # seconds to wait after a network error

    def __init__(self) -> None:
        from dotenv import load_dotenv
        load_dotenv()

        self._token    = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
        self._chat_id  = os.getenv("TELEGRAM_CHAT_ID",  "").strip()
        self._running  = False
        self._thread:  Optional[threading.Thread] = None
        self._paused   = False
        self._start_ts = datetime.now()
        self._reqs     = None
        self._update_id = 0            # last processed update id
        self._pending_register: Optional[str] = None  # chat_id awaiting .env write

        # Lazy command handlers — registered after __init__ via _register_handlers
        self._handlers: Dict[str, Callable[[dict], str]] = {}
        self._register_handlers()

        try:
            import requests as _r
            self._reqs = _r
        except ImportError:
            log.error("[TelegramBot] `requests` not installed — bot disabled. "
                      "Run: pip install requests")

    # ── Life-cycle ─────────────────────────────────────────────────────────

    def is_configured(self) -> bool:
        return bool(self._token and self._reqs)

    def start(self) -> None:
        if not self.is_configured():
            log.warning("[TelegramBot] Not started — missing token or requests package.")
            return
        if self._running:
            return
        self._running = True
        self._thread  = threading.Thread(target=self._poll_loop, daemon=True,
                                         name="TelegramBot")
        self._thread.start()
        threading.Thread(target=self._reminder_loop, daemon=True,
                         name="TelegramTokenReminder").start()
        log.info("[TelegramBot] Started polling. Bot: @Amitkhatkarbot")
        if not self._chat_id:
            log.info("[TelegramBot] No TELEGRAM_CHAT_ID set yet. "
                     "Send /start to @Amitkhatkarbot to register your Chat ID.")

    def stop(self) -> None:
        self._running = False
        log.info("[TelegramBot] Stopped.")

    # ── Push helpers (called by NotifierManager) ───────────────────────────

    def push(self, text: str, parse_mode: str = "HTML") -> None:
        """Fire-and-forget push to the registered chat."""
        if not self._chat_id or not self._reqs:
            return
        try:
            self._send(self._chat_id, text, parse_mode)
        except Exception as exc:
            log.warning("[TelegramBot] Push failed: %s", exc)

    # ── Token reminder loop ────────────────────────────────────────────────

    def _reminder_loop(self) -> None:
        """
        Every weekday morning, send a reminder to paste the fresh Dhan token.

        Schedule (IST = UTC+5:30):
          Startup    → immediate ping if Dhan feed is not live (also useful for testing)
          07:30 IST  → daily reminder if Dhan feed is not live
          09:15 IST  → second nudge if still not live and market open approaching

        The loop wakes every 60 s to check the clock, so it adds no real overhead.
        """
        _reminded_730: str = ""     # date string of last 07:30 reminder sent
        _reminded_915: str = ""     # date string of last 09:15 reminder sent
        _startup_done: bool = False  # one-time startup ping

        while self._running:
            try:
                time.sleep(10 if not _startup_done else 60)
                if not self._chat_id:
                    continue

                now_utc = datetime.utcnow()
                # IST = UTC + 5h30m
                import datetime as _dt_mod
                now_ist = now_utc + _dt_mod.timedelta(hours=5, minutes=30)
                today   = now_ist.strftime("%Y-%m-%d")
                weekday = now_ist.weekday()          # 0=Mon … 4=Fri
                h, m    = now_ist.hour, now_ist.minute

                # Check live status
                dhan_live = False
                try:
                    from data_feeds import get_feed_manager
                    dhan_live = get_feed_manager().dhan.is_live
                except Exception:
                    pass

                # ── Startup ping (once, immediately after bot starts) ──────
                if not _startup_done:
                    _startup_done = True
                    if not dhan_live:
                        self.push(
                            "🔑 <b>AI Trading Brain is online!</b>\n"
                            "━━━━━━━━━━━━━━━━━━━━━\n"
                            "Dhan API is in <b>simulation mode</b> — live market data is unavailable.\n\n"
                            "Please paste your fresh Dhan access token:\n\n"
                            "<code>/token YOUR_ACCESS_TOKEN</code>\n\n"
                            "Get it from: <code>developer.dhan.co</code>\n"
                            "My Profile → API → Access Token"
                        )
                        log.info("[TelegramBot] Startup Dhan token prompt sent.")
                    else:
                        self.push(
                            "✅ <b>AI Trading Brain is online!</b>\n"
                            "Dhan feed is <b>LIVE</b> — live data active. 📈"
                        )
                        log.info("[TelegramBot] Startup ping sent (Dhan already live).")
                    continue

                if weekday >= 5:                     # skip Sat/Sun for scheduled reminders
                    continue

                # ── 07:30 reminder ────────────────────────────────────────
                if h == 7 and 30 <= m < 45 and today != _reminded_730:
                    _reminded_730 = today
                    if not dhan_live:
                        self.push(
                            "🔑 <b>Good morning! Dhan token required.</b>\n"
                            "━━━━━━━━━━━━━━━━━━━━━\n"
                            "Dhan API is in <b>simulation mode</b> — live market data is unavailable.\n\n"
                            "Get your fresh token:\n"
                            "  1. Open <code>developer.dhan.co</code>\n"
                            "  2. My Profile → API → Access Token\n"
                            "  3. Copy the token and reply here:\n\n"
                            "<code>/token YOUR_ACCESS_TOKEN</code>\n\n"
                            "Market opens at <b>09:15 IST</b>. 🕘"
                        )
                        log.info("[TelegramBot] 07:30 Dhan token reminder sent.")
                    else:
                        self.push(
                            "✅ <b>Good morning!</b> Dhan feed is <b>LIVE</b> — no action needed.\n"
                            "Market opens at 09:15 IST. Have a great trading day! 📈"
                        )
                        log.info("[TelegramBot] 07:30 morning greeting sent (Dhan already live).")

                # ── 09:15 reminder (second nudge if still offline) ────────
                elif h == 9 and 15 <= m < 25 and today != _reminded_915:
                    _reminded_915 = today
                    if not dhan_live:
                        self.push(
                            "⚠️ <b>Market is NOW OPEN — Dhan still in simulation mode!</b>\n"
                            "Send your token immediately to switch to live data:\n\n"
                            "<code>/token YOUR_ACCESS_TOKEN</code>"
                        )
                        log.warning("[TelegramBot] 09:15 Dhan token nudge sent — feed still offline.")

            except Exception as exc:
                if self._running:
                    log.warning("[TelegramBot] Reminder loop error: %s", exc, exc_info=True)

    # ── Polling loop ───────────────────────────────────────────────────────

    def _poll_loop(self) -> None:
        url = f"https://api.telegram.org/bot{self._token}/getUpdates"
        while self._running:
            try:
                resp = self._reqs.get(
                    url,
                    params={"offset": self._update_id + 1,
                            "timeout": self.POLL_TIMEOUT,
                            "allowed_updates": ["message"]},
                    timeout=self.POLL_TIMEOUT + 5,
                )
                if not resp.ok:
                    if resp.status_code == 409:
                        # Another instance still holding the connection — wait it out
                        log.warning("[TelegramBot] 409 Conflict — another instance "
                                    "is polling. Waiting 15s for it to release…")
                        time.sleep(15)
                    else:
                        log.warning("[TelegramBot] getUpdates HTTP %s: %s",
                                    resp.status_code, resp.text[:120])
                        time.sleep(self.RETRY_DELAY)
                    continue

                data = resp.json()
                for update in data.get("result", []):
                    self._update_id = max(self._update_id, update["update_id"])
                    self._handle_update(update)

            except Exception as exc:
                if self._running:
                    log.warning("[TelegramBot] Poll error: %s — retrying in %ds.",
                                exc, self.RETRY_DELAY)
                    time.sleep(self.RETRY_DELAY)

    # ── Update handler ─────────────────────────────────────────────────────

    def _handle_update(self, update: dict) -> None:
        msg  = update.get("message", {})
        text = msg.get("text", "").strip()
        chat = msg.get("chat", {})
        incoming_id = str(chat.get("id", ""))
        first_name  = chat.get("first_name", "Trader")

        if not text or not incoming_id:
            return

        # ── /start always allowed (to register chat_id) ────────────────────
        if text.startswith("/start"):
            reply = self._cmd_start(incoming_id, first_name)
            self._send(incoming_id, reply)
            return

        # ── Security: reject if registered chat_id doesn't match ───────────
        if self._chat_id and incoming_id != self._chat_id:
            self._send(incoming_id,
                       "🔒 <b>Unauthorized.</b>\n"
                       "This bot is private and bound to its owner's account.")
            log.warning("[TelegramBot] Rejected msg from unknown chat_id=%s", incoming_id)
            return

        # ── Route command ───────────────────────────────────────────────────
        cmd = text.split()[0].lower().split("@")[0]   # strip @botname suffix
        handler = self._handlers.get(cmd)
        if handler:
            try:
                reply = handler(msg)
            except Exception as exc:
                log.error("[TelegramBot] Handler %s error: %s", cmd, exc)
                reply = f"🚨 Error running <code>{_esc(cmd)}</code>: {_esc(str(exc))}"
        else:
            reply = (f"Unknown command: <code>{_esc(cmd)}</code>\n"
                     "Send /help to see all commands.")

        self._send(incoming_id, reply)

    # ── Send ───────────────────────────────────────────────────────────────

    def _send(self, chat_id: str, text: str, parse_mode: str = "HTML") -> None:
        url = f"https://api.telegram.org/bot{self._token}/sendMessage"
        resp = self._reqs.post(url, json={
            "chat_id":    chat_id,
            "text":       text,
            "parse_mode": parse_mode,
        }, timeout=10)
        if not resp.ok:
            log.warning("[TelegramBot] sendMessage failed: %s", resp.text[:120])

    # ── Command registration ───────────────────────────────────────────────

    def _register_handlers(self) -> None:
        self._handlers = {
            "/help":      self._cmd_help,
            "/status":    self._cmd_status,
            "/nifty":     self._cmd_nifty,
            "/vix":       self._cmd_vix,
            "/market":    self._cmd_market,
            "/snapshot":  self._cmd_snapshot,
            "/positions": self._cmd_positions,
            "/pnl":       self._cmd_pnl,
            "/edges":     self._cmd_edges,
            "/perf":      self._cmd_perf,
            "/learn":     self._cmd_learn,
            "/token":     self._cmd_token,
            "/pause":     self._cmd_pause,
            "/resume":    self._cmd_resume,
            "/report":    self._cmd_report,
            "/eod":       self._cmd_eod,
            "/analytics": self._cmd_analytics,
            "/backlog":   self._cmd_backlog,
            "/build":     self._cmd_build,
        }

    # ── /start ─────────────────────────────────────────────────────────────

    def _cmd_start(self, incoming_id: str, first_name: str) -> str:
        # Auto-register if no chat_id yet
        if not self._chat_id:
            self._chat_id = incoming_id
            log.info("[TelegramBot] ✅ Chat ID registered: %s (%s). "
                     "Paste into .env → TELEGRAM_CHAT_ID=%s",
                     incoming_id, first_name, incoming_id)
            reg_note = (
                f"\n\n<b>📌 Your Chat ID:</b> <code>{incoming_id}</code>\n"
                f"Add to <code>.env</code>:\n"
                f"<code>TELEGRAM_CHAT_ID = {incoming_id}</code>\n"
                f"(Restart bot after saving to enforce security lock.)"
            )
        else:
            reg_note = f"\n\n<b>Registered Chat ID:</b> <code>{self._chat_id}</code>"

        return (
            f"🚀 <b>AI Trading Brain</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"Hello <b>{_esc(first_name)}</b>! I'm your personal trading assistant.\n\n"
            f"I will send you real-time alerts for:\n"
            f"  • Trade signals &amp; executions\n"
            f"  • Risk triggers &amp; circuit breakers\n"
            f"  • End-of-day P&amp;L summaries\n"
            f"  • New edge discoveries\n\n"
            f"Send /help to see all commands."
            f"{reg_note}"
        )

    # ── /help ──────────────────────────────────────────────────────────────

    def _cmd_help(self, msg: dict) -> str:
        return (
            "📖 <b>Available Commands</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━\n"
            "/status       — System status &amp; feed health\n"
            "/nifty        — NIFTY &amp; BANKNIFTY live price\n"
            "/vix          — India VIX &amp; USD/INR\n"
            "/market       — Full market snapshot\n"
            "/snapshot     — Live indices + NIFTY options now\n"
            "/perf         — Strategy leaderboard (win%, expectancy)\n"
            "/learn        — Learning stage + regime map\n"
            "/positions    — Open positions\n"
            "/pnl          — Today's P&amp;L\n"
            "/edges        — Active trading edges\n"
            "/eod          — Today's operational retrospective\n"
            "/report       — AI self-evaluation quality report\n"
            "/analytics    — Today's trade performance analytics\n"
            "/backlog      — Open improvement items (auto-tracked)\n"
            "/token        — Update Dhan API token (hot-reload, no restart)\n"
            "/build        — Deployment manifest, git commit, drift status\n"
            "/pause        — Pause signal generation\n"
            "/resume       — Resume signal generation\n"
            "/help         — This message"
        )

    # ── /status ────────────────────────────────────────────────────────────

    def _cmd_status(self, msg: dict) -> str:
        try:
            import config as cfg
            mode    = "🧪 PAPER" if getattr(cfg, "PAPER_TRADING", True) else "💵 LIVE"
            capital = f"₹{getattr(cfg, 'TOTAL_CAPITAL', 1_000_000):,.0f}"
        except Exception:
            mode    = "unknown"
            capital = "unknown"

        try:
            from data_feeds import get_feed_manager
            fm      = get_feed_manager()
            status  = fm.get_status()
            dhan_s  = "✅ LIVE" if status.dhan_live  else "⚡ SIM"
            yahoo_s = "✅ LIVE" if status.yahoo_live else "⚡ SIM"
            feed_line = f"Dhan: {dhan_s}  |  Yahoo: {yahoo_s}"
        except Exception:
            feed_line = "Feed status unavailable"

        uptime = datetime.now() - self._start_ts
        h, rem = divmod(int(uptime.total_seconds()), 3600)
        m, s   = divmod(rem, 60)
        paused = "⏸ PAUSED" if self._paused else "▶️ RUNNING"

        return (
            f"📊 <b>System Status</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"Brain:   {paused}\n"
            f"Mode:    {mode}\n"
            f"Capital: {capital}\n"
            f"Uptime:  {h}h {m}m {s}s\n"
            f"Feeds:   {_esc(feed_line)}\n"
            f"Time:    {datetime.now().strftime('%d-%b-%Y  %H:%M:%S')}"
        )

    # ── /nifty ─────────────────────────────────────────────────────────────

    def _cmd_nifty(self, msg: dict) -> str:
        try:
            from data_feeds import get_feed_manager
            fm = get_feed_manager()
            nifty = fm.get_quote("NIFTY")
            bnk   = fm.get_quote("BANKNIFTY")
            n_chg = f"{nifty.change_pct:+.2f}%" if nifty.change_pct else "—"
            b_chg = f"{bnk.change_pct:+.2f}%"   if bnk.change_pct   else "—"
            return (
                f"📈 <b>Live Indices</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━\n"
                f"NIFTY 50:      <b>₹{nifty.ltp:,.2f}</b>  ({n_chg})\n"
                f"BANK NIFTY:    <b>₹{bnk.ltp:,.2f}</b>  ({b_chg})\n"
                f"🕐 {datetime.now().strftime('%H:%M:%S')}"
            )
        except Exception as exc:
            return f"⚠️ Could not fetch NIFTY data: {_esc(str(exc))}"

    # ── /vix ───────────────────────────────────────────────────────────────

    def _cmd_vix(self, msg: dict) -> str:
        try:
            from data_feeds import get_feed_manager
            fm      = get_feed_manager()
            vix     = fm.get_ltp("INDIAVIX")
            usdinr  = fm.get_ltp("USDINR")
            sgx     = fm.get_ltp("SGXNIFTY")

            vix_icon  = "🟢" if vix < 15 else ("🟡" if vix < 20 else "🔴")
            return (
                f"📊 <b>Volatility &amp; FX</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━\n"
                f"India VIX:   {vix_icon} <b>{vix:.2f}</b>\n"
                f"USD/INR:     <b>₹{usdinr:.2f}</b>\n"
                f"SGX Nifty:   <b>{sgx:,.2f}</b>\n"
                f"🕐 {datetime.now().strftime('%H:%M:%S')}"
            )
        except Exception as exc:
            return f"⚠️ Could not fetch VIX data: {_esc(str(exc))}"

    # ── /market ────────────────────────────────────────────────────────────

    def _cmd_market(self, msg: dict) -> str:
        try:
            from data_feeds import get_feed_manager
            fm      = get_feed_manager()
            snap    = fm.get_global_snapshot()

            lines = [
                "🌍 <b>Market Snapshot</b>",
                "━━━━━━━━━━━━━━━━━━━━━",
            ]
            symbols = [
                ("NIFTY",    "NIFTY 50  "),
                ("BANKNIFTY","BankNifty "),
                ("INDIAVIX", "India VIX "),
                ("USDINR",   "USD/INR   "),
                ("GOLD",     "Gold      "),
            ]
            for sym, label in symbols:
                try:
                    ltp = fm.get_ltp(sym)
                    lines.append(f"{label}  <b>{ltp:,.2f}</b>")
                except Exception:
                    pass

            if snap:
                if snap.get("nikkei_chg"):
                    lines.append(f"Nikkei chg  {snap['nikkei_chg']:+.2f}%")
                if snap.get("crude"):
                    lines.append(f"Crude Oil   <b>{snap['crude']:,.2f}</b>")

            lines.append(f"🕐 {datetime.now().strftime('%H:%M:%S')}")
            return "\n".join(lines)
        except Exception as exc:
            return f"⚠️ Market snapshot error: {_esc(str(exc))}"

    # ── /positions ─────────────────────────────────────────────────────────

    def _cmd_positions(self, msg: dict) -> str:
        try:
            from data_feeds.dhan_feed import DhanFeed
            feed   = DhanFeed()
            if feed.is_live:
                positions = feed.get_positions()
                if not positions:
                    return "📂 <b>Positions</b>\n━━━━━━━━━━━━━━━━━━━━━\nNo open positions."
                lines = ["📂 <b>Open Positions</b>", "━━━━━━━━━━━━━━━━━━━━━"]
                for p in positions[:10]:
                    sym    = _esc(str(p.get("tradingSymbol", "?")))
                    qty    = p.get("netQty", 0)
                    avg    = p.get("avgCostPrice", 0)
                    pnl    = p.get("unrealizedProfit", 0)
                    pnl_s  = f"{'▲' if pnl >= 0 else '▼'} ₹{pnl:+,.0f}"
                    lines.append(f"<b>{sym}</b>  qty={qty}  avg=₹{avg:.2f}  {pnl_s}")
                return "\n".join(lines)
            else:
                return "ℹ️ Running in simulation mode — no live positions."
        except Exception as exc:
            return f"⚠️ Positions error: {_esc(str(exc))}"

    # ── /pnl ───────────────────────────────────────────────────────────────

    def _cmd_pnl(self, msg: dict) -> str:
        try:
            from data_feeds.dhan_feed import DhanFeed
            feed = DhanFeed()
            if feed.is_live:
                positions = feed.get_positions()
                realized   = sum(p.get("realizedProfit",   0) for p in positions)
                unrealized = sum(p.get("unrealizedProfit", 0) for p in positions)
                total      = realized + unrealized
                icon       = "💰" if total >= 0 else "🔴"
                return (
                    f"{icon} <b>Today's P&amp;L</b>\n"
                    f"━━━━━━━━━━━━━━━━━━━━━\n"
                    f"Realized:    ₹{realized:+,.0f}\n"
                    f"Unrealized:  ₹{unrealized:+,.0f}\n"
                    f"<b>Total:       ₹{total:+,.0f}</b>\n"
                    f"🕐 {datetime.now().strftime('%H:%M:%S')}"
                )
            else:
                return "ℹ️ Running in simulation mode — P&L from paper trades only."
        except Exception as exc:
            return f"⚠️ P&L error: {_esc(str(exc))}"

    # ── /edges ─────────────────────────────────────────────────────────────

    def _cmd_edges(self, msg: dict) -> str:
        try:
            from edge_discovery.edge_discovery_engine import EdgeDiscoveryEngine
            ede = EdgeDiscoveryEngine()
            edges = ede.get_active_edges()
            if not edges:
                return "📊 <b>Active Edges</b>\n━━━━━━━━━━━━━━━━━━━━━\nNo active edges."
            lines = ["🔬 <b>Active Trading Edges</b>", "━━━━━━━━━━━━━━━━━━━━━"]
            for e in sorted(edges, key=lambda x: x.get("expectancy_r", 0), reverse=True)[:8]:
                name = _esc(e.get("name", "?"))
                exp  = e.get("expectancy_r", 0)
                cat  = _esc(e.get("category", "?"))
                sign = "+" if exp >= 0 else ""
                lines.append(f"• <b>{name}</b>  {sign}{exp:.3f}R  [{cat}]")
            return "\n".join(lines)
        except Exception as exc:
            return f"⚠️ Edges error: {_esc(str(exc))}"

    # ── /snapshot ──────────────────────────────────────────────────────────

    def _cmd_snapshot(self, msg: dict) -> str:
        """Send live indices + NIFTY options strike ladder inline."""
        import os, sys
        _root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if _root not in sys.path:
            sys.path.insert(0, _root)

        from datetime import datetime as _dt
        now = _dt.now().strftime("%d-%b-%Y  %H:%M:%S")

        # ── Part 1: indices ────────────────────────────────────────────────
        try:
            from data_feeds.dhan_feed import DhanFeed
            feed   = DhanFeed()
            nifty  = feed.get_quote("NIFTY")
            bnk    = feed.get_quote("BANKNIFTY")
            vix    = feed.get_ltp("INDIAVIX")
            usdinr = feed.get_ltp("USDINR")

            def _chg(v):
                if v is None:
                    return "—"
                arr = "▲" if v >= 0 else "▼"
                return f"{arr} {v:+.2f}%"

            msg1 = (
                f"📈 <b>Live Market Data</b>  |  {now}\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"<b>NIFTY 50</b>\n"
                f"  LTP : ₹{nifty.ltp:,.2f}  {_chg(nifty.change_pct)}\n"
                f"  O/H/L : {nifty.open:,.0f} / {nifty.high:,.0f} / {nifty.low:,.0f}\n\n"
                f"<b>BANK NIFTY</b>\n"
                f"  LTP : ₹{bnk.ltp:,.2f}  {_chg(bnk.change_pct)}\n"
                f"  O/H/L : {bnk.open:,.0f} / {bnk.high:,.0f} / {bnk.low:,.0f}\n\n"
                f"{'🟢' if vix < 15 else ('🟡' if vix < 20 else '🔴')} "
                f"<b>India VIX</b>   {vix:.2f}\n"
                f"💱 <b>USD / INR</b>  ₹{usdinr:.4f}\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"<i>Source: Dhan Live Feed</i>"
            )
            if self._chat_id:
                self._send(self._chat_id, msg1)
            spot = nifty.ltp
        except Exception as exc:
            if self._chat_id:
                self._send(self._chat_id, f"⚠️ Indices fetch failed: {_esc(str(exc))}")
            spot = 22500.0

        # ── Part 2: NIFTY options (CSV strike ladder) ──────────────────────
        try:
            import pandas as pd
            import os as _os
            csv_path = _os.path.join(_root, "security_id_list.csv")
            df = pd.read_csv(csv_path, low_memory=False)
            opts = df[
                (df["SEM_SEGMENT"] == "D") &
                (df["SEM_INSTRUMENT_NAME"] == "OPTIDX") &
                (df["SEM_TRADING_SYMBOL"].astype(str).str.startswith("NIFTY-"))
            ].copy()
            opts["SEM_EXPIRY_DATE"] = pd.to_datetime(opts["SEM_EXPIRY_DATE"])
            nearest_exp = opts["SEM_EXPIRY_DATE"].dropna().min()
            week_opts = opts[opts["SEM_EXPIRY_DATE"] == nearest_exp].copy()
            week_opts["SEM_STRIKE_PRICE"] = pd.to_numeric(
                week_opts["SEM_STRIKE_PRICE"], errors="coerce")
            week_opts = week_opts.dropna(subset=["SEM_STRIKE_PRICE"])
            atm = round(spot / 50) * 50
            strikes = sorted(week_opts["SEM_STRIKE_PRICE"].unique())
            near = [s for s in strikes if atm - 300 <= s <= atm + 300]
            exp_str = nearest_exp.strftime("%d-%b-%Y") if hasattr(nearest_exp, "strftime") else str(nearest_exp)
            ladder = "\n".join(
                f"   {int(s):>6}{'  ◀ ATM' if s == atm else ''}" for s in near
            )
            msg2 = (
                f"📊 <b>NIFTY Options Info</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"<b>Expiry:</b> {exp_str}  |  "
                f"<b>Spot:</b> {spot:,.1f}  |  "
                f"<b>ATM:</b> {int(atm)}\n\n"
                f"<b>Available strike ladder:</b>\n"
                f"<pre>{ladder}</pre>\n\n"
                f"⚠️ <i>Live premiums &amp; OI require Dhan Data API:\n"
                f"  Dhan app → Profile → API → Activate Data API</i>\n"
                f"<i>{now}</i>"
            )
        except Exception as exc:
            msg2 = f"⚠️ Options info failed: {_esc(str(exc))}"

        return msg2

    # ── /perf ──────────────────────────────────────────────────────────

    def _cmd_perf(self, msg: dict) -> str:
        try:
            from learning_system.strategy_performance_tracker import get_performance_tracker
            tracker = get_performance_tracker()
            return tracker.get_table() or "No performance data yet — run some trades first."
        except Exception as exc:
            return f"⚠️ Performance data unavailable: {_esc(str(exc))}"
    # ── /analytics ──────────────────────────────────────────────

    def _cmd_analytics(self, msg: dict) -> str:
        """Today's trade performance analytics report — Block 1–4."""
        try:
            from trade_monitoring.trade_analytics import TradeAnalytics
            ana = TradeAnalytics()            # loads today's persisted data
            if ana.trade_count() == 0:
                return "No trades recorded today yet."
            return ana.telegram_report()
        except Exception as exc:
            return f"⚠️ Analytics unavailable: {_esc(str(exc))}"
    # ── /learn ─────────────────────────────────────────────────────────

    def _cmd_learn(self, msg: dict) -> str:
        try:
            from meta_learning.regime_strategy_map import get_regime_strategy_map
            rsm = get_regime_strategy_map()
            stage = rsm.learning_stage()
            table = rsm.get_regime_table()
            return (
                f"🧠 <b>Learning Status</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━\n"
                f"{stage}\n\n"
                f"{table}"
            )
        except Exception as exc:
            return f"⚠️ Learning data unavailable: {_esc(str(exc))}"

    # ── /report ────────────────────────────────────────────────────────────

    def _cmd_report(self, msg: dict) -> str:
        """Send the latest EOD self-evaluation report."""
        import os, glob
        try:
            pattern = os.path.join("data", "logs", "eod_report_*.txt")
            files = sorted(glob.glob(pattern))
            if not files:
                return (
                    "📭 No daily evaluation reports yet.\n"
                    "Reports are generated at market close (15:40).\n"
                    "Run some trades first!"
                )
            latest = files[-1]
            with open(latest, "r", encoding="utf-8") as fh:
                content = fh.read(4000)   # Telegram limit ~4096 chars
            fname = os.path.basename(latest)
            return f"<b>📊 {fname}</b>\n\n<pre>{_esc(content)}</pre>"
        except Exception as exc:
            return f"⚠️ Could not load report: {_esc(str(exc))}"

    # ── /backlog ───────────────────────────────────────────────────────────

    def _cmd_backlog(self, msg: dict) -> str:
        """Show open improvement items auto-tracked from daily retrospectives."""
        try:
            from learning_system.improvement_backlog import get_backlog
            return get_backlog().format_telegram()
        except Exception as exc:
            return f"⚠️ Backlog unavailable: {_esc(str(exc))}"

    # ── /eod ──────────────────────────────────────────────────────────────

    def _cmd_eod(self, msg: dict) -> str:
        """Return today's operational retrospective (cycle health, pipeline, flags)."""
        import os, glob
        try:
            # Try today's saved retrospective first
            from datetime import datetime as _dt
            today = _dt.now().strftime("%Y-%m-%d")
            pattern = os.path.join("data", f"eod_retro_{today}.txt")
            if os.path.exists(pattern):
                with open(pattern, "r", encoding="utf-8") as fh:
                    return f"<pre>{_esc(fh.read(3800))}</pre>"

            # Fall back to generating live
            from learning_system.eod_retrospective import run_eod_retrospective
            _, html = run_eod_retrospective()
            return html
        except Exception as exc:
            return f"⚠️ EOD retrospective unavailable: {_esc(str(exc))}"

    # ── /token ─────────────────────────────────────────────────────────────

    def _cmd_token(self, msg: dict) -> str:
        """Accept a fresh Dhan access token and hot-reload the feed — no restart needed."""
        text  = msg.get("text", "").strip()
        parts = text.split(None, 1)        # ["/token", "<the_token>"]
        if len(parts) < 2 or not parts[1].strip():
            return (
                "⚠️ <b>Usage:</b> <code>/token YOUR_DHAN_ACCESS_TOKEN</code>\n"
                "Get your token at <code>developer.dhan.co</code>\n"
                "→ My Profile → API → Create App → Get Access Token"
            )
        new_token = parts[1].strip()
        if len(new_token) < 20:
            return (
                "⚠️ Token looks too short.\n"
                "Please paste the <b>full</b> access token from developer.dhan.co"
            )
        try:
            from data_feeds import get_feed_manager
            fm      = get_feed_manager()
            success = fm.dhan.reload_token(new_token)
            if success:
                log.info("[TelegramBot] Dhan access token hot-swapped — feed is LIVE.")
                return (
                    "✅ <b>Dhan token updated — feed is LIVE.</b>\n"
                    "Live market data active from next trading cycle.\n"
                    "Paper trades only (no real orders placed)."
                )
            else:
                return (
                    "⚠️ <b>Token accepted but Dhan connect failed.</b>\n"
                    "Verify the token hasn't expired and your client ID is set.\n"
                    "System will keep using yfinance as fallback."
                )
        except Exception as exc:
            log.error("[TelegramBot] /token handler error: %s", exc)
            return f"🚨 Token update failed: {_esc(str(exc))}"

    # ── /pause / /resume ───────────────────────────────────────────────────

    # ── /build ─────────────────────────────────────────────────────────────

    def _cmd_build(self, msg: dict) -> str:  # noqa: C901
        try:
            from deployment.runtime_verifier import (
                get_manifest, get_deploy_record, verify, TRACKED_FILES,
            )
            manifest = get_manifest()
            deploy   = get_deploy_record()

            if not manifest:
                return (
                    "🔧 <b>Build Manifest</b>\n"
                    "━━━━━━━━━━━━━━━━━━━━━\n"
                    "⚠️ build_manifest.json not found.\n"
                    "Run deploy.sh to generate a fresh manifest."
                )

            commit  = _esc(manifest.get("commit", "?"))
            branch  = _esc(manifest.get("branch", "?"))
            cmsg    = _esc(manifest.get("commit_message", "")[:60])
            built   = _esc(manifest.get("build_timestamp", "?")[:19].replace("T", " "))
            deployed  = _esc(deploy.get("deploy_timestamp", "—")[:19].replace("T", " ")) if deploy else "—"
            image_sha = _esc(deploy.get("image_sha", "—")[:12]) if deploy else "—"

            # Run live drift check (no alert — called interactively)
            result = verify(send_alert=False)
            ok     = result["ok"]
            vcount = result["verified"]
            total  = result["total"]
            drift  = result["drift_files"]

            drift_icon  = "✅" if ok else "⚠️"
            drift_label = "NONE" if ok else f"{len(drift)} FILE(S) DRIFTED"
            drift_block = ""
            if drift:
                drift_block = "\n\n<b>Drifted files:</b>\n" + "\n".join(
                    f"  • {_esc(f)}" for f in drift
                )

            return (
                "🔧 <b>Deployment Build</b>\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"COMMIT   = <code>{commit}</code>  ({branch})\n"
                f"MESSAGE  = {cmsg}\n"
                f"BUILT    = {built} IST\n"
                f"DEPLOYED = {deployed} IST\n"
                f"IMAGE    = <code>{image_sha}</code>\n\n"
                "📦 <b>File Integrity</b>\n"
                f"VERIFIED = {vcount}/{total}\n"
                f"DRIFT    = {drift_icon} {drift_label}"
                f"{drift_block}"
            )
        except Exception as exc:
            log.warning("[TelegramBot] /build error: %s", exc)
            return f"⚠️ /build error: {_esc(str(exc))}"

    # ── /pause ─────────────────────────────────────────────────────────────

    def _cmd_pause(self, msg: dict) -> str:
        self._paused = True
        log.warning("[TelegramBot] Signal generation PAUSED by Telegram command.")
        return "⏸ <b>Signal generation paused.</b>\nSend /resume to re-enable."

    def _cmd_resume(self, msg: dict) -> str:
        self._paused = False
        log.info("[TelegramBot] Signal generation RESUMED by Telegram command.")
        return "▶️ <b>Signal generation resumed.</b>"

    # ── Property for brain to check pause state ────────────────────────────

    @property
    def is_paused(self) -> bool:
        return self._paused


# ── Singleton ──────────────────────────────────────────────────────────────
_BOT_INSTANCE: Optional[TelegramCommandBot] = None


def get_telegram_bot() -> TelegramCommandBot:
    global _BOT_INSTANCE
    if _BOT_INSTANCE is None:
        _BOT_INSTANCE = TelegramCommandBot()
    return _BOT_INSTANCE


# ── Standalone entry-point ─────────────────────────────────────────────────

def run_bot() -> None:
    """
    Start the bot and block until Ctrl+C.
    Called by:  python main.py --telegram
    """
    bot = get_telegram_bot()
    if not bot.is_configured():
        print("ERROR: TELEGRAM_BOT_TOKEN not set in .env")
        sys.exit(1)

    bot.start()
    print()
    print("=" * 60)
    print("  TELEGRAM BOT — @Amitkhatkarbot")
    print("=" * 60)
    print("  Status : polling for messages...")
    print("  To register your Chat ID, open Telegram")
    print("  and send /start  to  @Amitkhatkarbot")
    print("  Then paste the Chat ID into .env:")
    print("    TELEGRAM_CHAT_ID = <your_id>")
    print("=" * 60)
    print("  Press Ctrl+C to stop.")
    print()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        bot.stop()
        print("\nBot stopped.")
