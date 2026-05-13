"""
Fix 1: Add /token command to register_handlers + add _cmd_token method
Fix 2: Replace _cmd_positions to show paper-trade unrealized P&L in sim mode
Fix 3: Replace _cmd_pnl to show paper-trade P&L in sim mode
"""
import sys

FILE = "/app/notifications/telegram_bot.py"
with open(FILE, "r") as f:
    src = f.read()

# ── Fix 1a: register /token in handler dict ──────────────────────────────
OLD_HANDLERS = '''            "/pause":     self._cmd_pause,
            "/resume":    self._cmd_resume,
            "/report":    self._cmd_report,
            "/eod":       self._cmd_eod,
            "/analytics": self._cmd_analytics,
            "/backlog":   self._cmd_backlog,
        }'''
NEW_HANDLERS = '''            "/pause":     self._cmd_pause,
            "/resume":    self._cmd_resume,
            "/report":    self._cmd_report,
            "/eod":       self._cmd_eod,
            "/analytics": self._cmd_analytics,
            "/backlog":   self._cmd_backlog,
            "/token":     self._cmd_token,
        }'''
if OLD_HANDLERS not in src:
    print("ERROR: handler dict anchor not found"); sys.exit(1)
src = src.replace(OLD_HANDLERS, NEW_HANDLERS, 1)
print("Fix 1a: /token registered in handler dict")

# ── Fix 1b: add _cmd_token method before _cmd_pause ─────────────────────
OLD_PAUSE = '''    # ── /pause / /resume ───────────────────────────────────────────────────

    def _cmd_pause(self, msg: dict) -> str:'''
NEW_PAUSE = '''    # ── /token ────────────────────────────────────────────────────────────

    def _cmd_token(self, msg: dict) -> str:
        """Update Dhan access token from Telegram command: /token <jwt>"""
        import re, os
        text = msg.get("text", "").strip()
        parts = text.split(None, 1)
        if len(parts) < 2 or not parts[1].strip():
            return (
                "⚠️ <b>Usage:</b> <code>/token eyJhbGci...</code>\n"
                "Paste your Dhan access token after the command."
            )
        new_jwt = parts[1].strip()
        # Basic JWT sanity check (3 base64url parts separated by dots)
        if new_jwt.count(".") < 2:
            return "❌ That doesn't look like a valid JWT. Check the token and try again."
        # Update .env file
        env_path = "/app/.env"
        try:
            if os.path.exists(env_path):
                with open(env_path, "r") as f:
                    env_text = f.read()
                if re.search(r"^DHAN_ACCESS_TOKEN\s*=", env_text, re.MULTILINE):
                    env_text = re.sub(
                        r"^(DHAN_ACCESS_TOKEN\s*=\s*).*",
                        rf"\g<1>{new_jwt}",
                        env_text, flags=re.MULTILINE
                    )
                else:
                    env_text += f"\nDHAN_ACCESS_TOKEN={new_jwt}\n"
                with open(env_path, "w") as f:
                    f.write(env_text)
            else:
                with open(env_path, "w") as f:
                    f.write(f"DHAN_ACCESS_TOKEN={new_jwt}\n")
            # Also set in current process env for immediate effect
            os.environ["DHAN_ACCESS_TOKEN"] = new_jwt
            # Reconnect the feed
            try:
                from data_feeds.data_feed_manager import get_feed_manager
                get_feed_manager().reconnect()
                feed_status = "Feed reconnected ✅"
            except Exception as fe:
                feed_status = f"Feed reconnect failed: {fe}"
            short = new_jwt[:12] + "..." + new_jwt[-6:]
            log.info("[TelegramBot] Dhan token updated via /token command. %s", feed_status)
            return (
                f"✅ <b>Dhan token updated!</b>\n"
                f"Token: <code>{short}</code>\n"
                f"{feed_status}\n"
                f"🕐 {datetime.now().strftime('%H:%M:%S IST')}"
            )
        except Exception as exc:
            log.error("[TelegramBot] /token update failed: %s", exc)
            return f"❌ Token update failed: {_esc(str(exc))}"

    # ── /pause / /resume ───────────────────────────────────────────────────

    def _cmd_pause(self, msg: dict) -> str:'''
if OLD_PAUSE not in src:
    print("ERROR: _cmd_pause anchor not found"); sys.exit(1)
src = src.replace(OLD_PAUSE, NEW_PAUSE, 1)
print("Fix 1b: _cmd_token method added")

# ── Fix 2: _cmd_positions — show paper unrealized P&L in sim mode ────────
OLD_POS = '''            else:
                return "ℹ️ Running in simulation mode — no live positions."
        except Exception as exc:
            return f"⚠️ Positions error: {_esc(str(exc))}"'''
NEW_POS = '''            else:
                # Paper trading — read open trades from CSV and compute unrealized P&L
                return self._paper_positions()
        except Exception as exc:
            return f"⚠️ Positions error: {_esc(str(exc))}"

    def _paper_positions(self) -> str:
        """Read paper_trades.csv, show OPEN positions with live unrealized P&L."""
        import csv, os
        csv_path = "/app/data/paper_trades.csv"
        if not os.path.exists(csv_path):
            return "📂 <b>Paper Positions</b>\n━━━━━━━━━━━━━━━━━━━━━\nNo paper_trades.csv found."
        open_trades = []
        try:
            with open(csv_path, newline="") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row.get("status", "").upper() == "OPEN":
                        open_trades.append(row)
        except Exception as exc:
            return f"⚠️ CSV read error: {_esc(str(exc))}"
        if not open_trades:
            return "📂 <b>Paper Positions</b>\n━━━━━━━━━━━━━━━━━━━━━\nNo open positions."
        # Fetch live prices for all open symbols
        symbols = list({t["symbol"] for t in open_trades if t.get("symbol")})
        ltp_map: dict = {}
        try:
            from data_feeds.data_feed_manager import get_feed_manager
            quotes = get_feed_manager().get_multiple_quotes(symbols)
            ltp_map = {s: q.ltp for s, q in quotes.items() if q and q.ltp}
        except Exception:
            pass  # show without live P&L if feed unavailable
        lines = ["📂 <b>Paper Positions (Open)</b>", "━━━━━━━━━━━━━━━━━━━━━"]
        total_upnl = 0.0
        for t in open_trades:
            sym    = t.get("symbol", "?")
            side   = t.get("side", "BUY").upper()
            qty    = int(float(t.get("quantity", 0)))
            entry  = float(t.get("entry_price", 0))
            stop   = float(t.get("stop_loss", 0))
            target = float(t.get("target", 0))
            strat  = t.get("strategy", "?")
            ltp    = ltp_map.get(sym, 0)
            if ltp and entry:
                upnl = (ltp - entry) * qty if side == "BUY" else (entry - ltp) * qty
                upnl_str = f"{'▲' if upnl >= 0 else '▼'} ₹{upnl:+,.0f}"
                total_upnl += upnl
            else:
                upnl_str = "LTP unavailable"
            side_icon = "🟢" if side == "BUY" else "🔴"
            lines.append(
                f"{side_icon} <b>{_esc(sym)}</b> {side} ×{qty} @ ₹{entry:.2f}\n"
                f"   SL: ₹{stop:.2f} | T: ₹{target:.2f} | <b>{upnl_str}</b>\n"
                f"   Strategy: {_esc(strat)}"
            )
        upnl_icon = "💰" if total_upnl >= 0 else "🔴"
        lines.append(f"━━━━━━━━━━━━━━━━━━━━━")
        lines.append(f"{upnl_icon} <b>Total Unrealized: ₹{total_upnl:+,.0f}</b>  ({len(open_trades)} positions)")
        lines.append(f"🕐 {datetime.now().strftime('%H:%M:%S')}")
        return "\n".join(lines)'''
if OLD_POS not in src:
    print("ERROR: positions sim-mode anchor not found"); sys.exit(1)
src = src.replace(OLD_POS, NEW_POS, 1)
print("Fix 2: _cmd_positions + _paper_positions with unrealized P&L added")

# ── Fix 3: _cmd_pnl — also show paper P&L in sim mode ───────────────────
OLD_PNL = '''            else:
                return "ℹ️ Running in simulation mode — P&L from paper trades only."
        except Exception as exc:
            return f"⚠️ P&L error: {_esc(str(exc))}"'''
NEW_PNL = '''            else:
                # Paper trading — compute from CSV
                return self._paper_pnl()
        except Exception as exc:
            return f"⚠️ P&L error: {_esc(str(exc))}"

    def _paper_pnl(self) -> str:
        """Compute today's realized + unrealized P&L from paper_trades.csv."""
        import csv, os
        from datetime import datetime as _dt, date as _date
        csv_path = "/app/data/paper_trades.csv"
        today_str = _date.today().strftime("%Y-%m-%d")
        if not os.path.exists(csv_path):
            return "📊 <b>Paper P&L</b>\n━━━━━━━━━━━━━━━━━━━━━\nNo paper_trades.csv found."
        realized = 0.0
        open_trades = []
        try:
            with open(csv_path, newline="") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if not row.get("timestamp", "").startswith(today_str):
                        continue
                    status = row.get("status", "").upper()
                    if status in ("CLOSED", "SESSION_EXPIRED", "STOPPED"):
                        pnl_val = row.get("pnl", "0") or "0"
                        try:
                            realized += float(pnl_val)
                        except ValueError:
                            pass
                    elif status == "OPEN":
                        open_trades.append(row)
        except Exception as exc:
            return f"⚠️ CSV read error: {_esc(str(exc))}"
        # Fetch live prices for unrealized
        symbols = list({t["symbol"] for t in open_trades if t.get("symbol")})
        ltp_map: dict = {}
        if symbols:
            try:
                from data_feeds.data_feed_manager import get_feed_manager
                quotes = get_feed_manager().get_multiple_quotes(symbols)
                ltp_map = {s: q.ltp for s, q in quotes.items() if q and q.ltp}
            except Exception:
                pass
        unrealized = 0.0
        for t in open_trades:
            sym   = t.get("symbol", "")
            side  = t.get("side", "BUY").upper()
            qty   = int(float(t.get("quantity", 0)))
            entry = float(t.get("entry_price", 0))
            ltp   = ltp_map.get(sym, 0)
            if ltp and entry:
                unrealized += (ltp - entry) * qty if side == "BUY" else (entry - ltp) * qty
        total = realized + unrealized
        icon  = "💰" if total >= 0 else "🔴"
        ltp_note = "" if ltp_map else "\n⚠️ Live prices unavailable — unrealized is estimate"
        return (
            f"{icon} <b>Paper P&L — Today</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"Realized:      ₹{realized:+,.0f}  ({len([r for r in open_trades if r.get('status','').upper() not in ('OPEN',)])} closed)\n"
            f"Unrealized:    ₹{unrealized:+,.0f}  ({len(open_trades)} open)\n"
            f"<b>Total:         ₹{total:+,.0f}</b>\n"
            f"🕐 {datetime.now().strftime('%H:%M:%S')}{ltp_note}"
        )'''
if OLD_PNL not in src:
    print("ERROR: _cmd_pnl sim-mode anchor not found"); sys.exit(1)
src = src.replace(OLD_PNL, NEW_PNL, 1)
print("Fix 3: _cmd_pnl + _paper_pnl with realized+unrealized added")

# ── Fix 4: /token in /help output ────────────────────────────────────────
OLD_HELP = '            "/learn        — Learning stage + regime map\\n"'
NEW_HELP = ('            "/learn        — Learning stage + regime map\\n"'
            '\n            "/token &lt;jwt&gt; — Update Dhan access token\\n"')
if OLD_HELP in src:
    src = src.replace(OLD_HELP, NEW_HELP, 1)
    print("Fix 4: /token added to /help text")
else:
    print("WARN: /help text anchor not found (non-critical)")

with open(FILE, "w") as f:
    f.write(src)

import py_compile
try:
    py_compile.compile(FILE, doraise=True)
    print("\nSyntax: OK")
except py_compile.PyCompileError as e:
    print(f"\nSYNTAX ERROR: {e}")
    sys.exit(1)

print("All fixes applied to telegram_bot.py")
