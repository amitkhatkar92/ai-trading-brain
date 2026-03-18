"""
send_live_snapshot.py
━━━━━━━━━━━━━━━━━━━━━
Fetch live NIFTY / BANKNIFTY / India VIX data + NIFTY options chain
from Dhan and push two formatted messages to your Telegram bot.

Usage:
    python send_live_snapshot.py
"""

import os
import sys
import time
sys.path.insert(0, os.path.dirname(__file__))

import requests
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()

from data_feeds.dhan_feed import DhanFeed

TOKEN   = os.getenv("TELEGRAM_BOT_TOKEN", "")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID",   "")


def send(text: str) -> None:
    url  = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    resp = requests.post(
        url,
        json={"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"},
        timeout=15,
    )
    status = "✅ OK" if resp.ok else f"❌ {resp.status_code}: {resp.text[:120]}"
    print(f"Telegram: {status}")


def chg_str(q) -> str:
    if q and q.change_pct:
        icon = "▲" if q.change_pct > 0 else "▼"
        return f"{icon} {q.change_pct:+.2f}%"
    return ""


def main():
    feed = DhanFeed()
    print(f"Dhan live: {feed.is_live}")

    now = datetime.now().strftime("%d-%b-%Y  %H:%M:%S")

    # ── 1. Live Index Snapshot ──────────────────────────────────────────
    print("Fetching NIFTY, BANKNIFTY, VIX, USDINR…")
    nifty  = feed.get_quote("NIFTY")
    bnk    = feed.get_quote("BANKNIFTY")
    vix    = feed.get_ltp("INDIAVIX")
    usdinr = feed.get_ltp("USDINR")

    vix_icon = "🟢" if vix < 15 else ("🟡" if vix < 20 else "🔴")

    msg1 = (
        f"📈 <b>Live Market Data</b>  |  {now}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"<b>NIFTY 50</b>\n"
        f"  LTP : ₹{nifty.ltp:,.2f}  {chg_str(nifty)}\n"
        f"  O/H/L : {nifty.open:,.0f} / {nifty.high:,.0f} / {nifty.low:,.0f}\n"
        f"\n"
        f"<b>BANK NIFTY</b>\n"
        f"  LTP : ₹{bnk.ltp:,.2f}  {chg_str(bnk)}\n"
        f"  O/H/L : {bnk.open:,.0f} / {bnk.high:,.0f} / {bnk.low:,.0f}\n"
        f"\n"
        f"{vix_icon} <b>India VIX</b>   {vix:.2f}\n"
        f"💱 <b>USD / INR</b>  ₹{usdinr:.4f}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"<i>Source: Yahoo Finance (Dhan Data API not active)</i>"
    )
    print(msg1)
    send(msg1)
    time.sleep(1)

    # ── 2. NIFTY Options Chain ──────────────────────────────────────────
    print("Fetching NIFTY options chain…")
    chain = feed.get_options_chain("NIFTY")
    atm   = round(nifty.ltp / 50) * 50   # nearest 50-point strike

    # ── 2. Options Chain (from Dhan instrument list + spot price) ─────────
    print("Fetching NIFTY options chain…")

    # Try Dhan option_chain first (requires Data API subscription)
    chain = feed.get_options_chain("NIFTY")

    if chain and chain.contracts:
        # Full chain available ————————————————————————————————
        pcr = chain.pcr or feed.get_pcr("NIFTY")
        expiry_str = getattr(chain, "expiry", "nearest weekly")
        atm = round(chain.spot_price / 50) * 50 if chain.spot_price else atm

        calls = {int(c.strike): c for c in chain.calls()}
        puts  = {int(c.strike): c for c in chain.puts()}

        all_strikes = sorted({int(c.strike) for c in chain.contracts},
                             key=lambda x: abs(x - atm))[:10]
        all_strikes = sorted(all_strikes)

        rows = []
        for s in all_strikes:
            c_obj = calls.get(s)
            p_obj = puts.get(s)
            c_ltp = c_obj.ltp if c_obj else 0.0
            p_ltp = p_obj.ltp if p_obj else 0.0
            c_oi  = int(c_obj.oi  or 0) // 1000 if c_obj else 0
            p_oi  = int(p_obj.oi  or 0) // 1000 if p_obj else 0
            c_iv  = f"{c_obj.iv:.0f}%" if c_obj and c_obj.iv else "  —"
            atm_m = " ◀" if s == atm else "  "
            rows.append(
                f"{c_ltp:>8.1f} {c_oi:>6}K {c_iv:>5} │{atm_m}{s:>7}{atm_m}│ {p_oi:<6}K {p_ltp:<8.1f}"
            )

        header = " CALL LTP  C-OI   IV   │  STRIKE  │  P-OI   PUT LTP"
        sep    = "─" * 54

        msg2 = (
            f"📊 <b>NIFTY Options Chain</b>\n"
            f"Expiry: <b>{expiry_str}</b>  |  ATM: <b>{atm}</b>  |  PCR: <b>{pcr:.2f}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"<pre>{header}\n{sep}\n"
            + "\n".join(rows)
            + f"\n{sep}</pre>\n"
            f"<i>Source: Dhan Live  |  {now}</i>"
        )

    else:
        # Dhan Data API not subscribed — build strike ladder from instrument list
        import pandas as pd, os

        csv_path = os.path.join(os.path.dirname(__file__), "security_id_list.csv")
        msg2_body = ""

        if os.path.exists(csv_path):
            df_all = pd.read_csv(csv_path, low_memory=False)

            # Find nearest NIFTY weekly expiry
            nifty_opts = df_all[
                (df_all["SEM_SEGMENT"] == "D") &
                (df_all["SEM_INSTRUMENT_NAME"] == "OPTIDX") &
                (df_all["SEM_TRADING_SYMBOL"].astype(str).str.startswith("NIFTY-"))
            ].copy()
            nifty_opts["EXP"] = pd.to_datetime(nifty_opts["SEM_EXPIRY_DATE"],
                                                errors="coerce")
            expiries_avail = sorted(nifty_opts["EXP"].dropna().unique())
            nearest_exp    = expiries_avail[0] if expiries_avail else None

            if nearest_exp is not None:
                exp_str = nearest_exp.strftime("%d-%b-%Y")
                # Pick strikes near ATM
                exp_chain = nifty_opts[
                    (nifty_opts["EXP"] == nearest_exp) &
                    (nifty_opts["SEM_STRIKE_PRICE"].between(atm - 300, atm + 300))
                ].copy()

                strikes_avail = sorted(
                    exp_chain["SEM_STRIKE_PRICE"].dropna().unique().tolist()
                )
                # Build display rows (no live premium — show N/A)
                rows = []
                for s in strikes_avail:
                    s_int = int(s)
                    mark  = " ◀ ATM" if s_int == atm else ""
                    rows.append(f"  {s_int:>6}{mark}")

                msg2_body = (
                    f"<b>Expiry:</b> {exp_str}  |  "
                    f"<b>Spot:</b> {nifty.ltp:,.1f}  |  "
                    f"<b>ATM:</b> {atm}\n\n"
                    f"<b>Available strike ladder:</b>\n"
                    f"<pre>" + "\n".join(rows) + "</pre>\n\n"
                    f"⚠️ <i>Live premiums &amp; OI require Dhan Data API:\n"
                    f"  Dhan app → Profile → API → Activate Data API</i>"
                )

        if not msg2_body:
            pcr = feed.get_pcr("NIFTY")
            msg2_body = (
                f"<b>ATM Strike:</b> {atm}\n"
                f"<b>PCR (default):</b> 0.85\n\n"
                f"⚠️ <i>Live data requires Dhan Data API subscription.\n"
                f"Enable at: Dhan app → Profile → API → Data API</i>"
            )

        msg2 = (
            f"📊 <b>NIFTY Options Info</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            + msg2_body
            + f"\n<i>{now}</i>"
        )

    print(msg2)
    send(msg2)
    print("Done.")


if __name__ == "__main__":
    main()
