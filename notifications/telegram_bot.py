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
            "/pause":     self._cmd_pause,
            "/resume":    self._cmd_resume,
            "/report":    self._cmd_report,
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
            "/pause        — Pause signal generation\n"
            "/resume       — Resume signal generation\n"
            "/help         — This message"
        )

    # ── /status ────────────────────────────────────────────────────────────

    def _cmd_status(self, msg: dict) -> str:
        try:
            import config as cfg
            mode    = "🧪 PAPER" if getattr(cfg, "PAPER_TRADING", True) else "💵 LIVE"
            capital = f"₹{getattr(cfg, 'PILOT_CAPITAL', 20000):,.0f}"
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

    # ── /pause / /resume ───────────────────────────────────────────────────

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
