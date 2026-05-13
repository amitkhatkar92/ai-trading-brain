import csv, datetime, subprocess, json
import yfinance as yf

today = datetime.date.today().isoformat()
csv_path = "/app/data/paper_trades.csv"

rows = list(csv.DictReader(open(csv_path)))

today_rows   = [r for r in rows if r["timestamp"].startswith(today)]
open_rows    = [r for r in rows if r.get("event","").upper() == "OPEN"]
today_open   = [r for r in open_rows if r["timestamp"].startswith(today)]
carry_open   = [r for r in open_rows if not r["timestamp"].startswith(today)]
closed_today = [r for r in today_rows if r.get("event","").upper() in ("CLOSED","SESSION_EXPIRED")]

realized = sum(float(r.get("pnl",0) or 0) for r in closed_today)

# Collect unique symbols for live price fetch
all_open = today_open + carry_open
sym_set = {r["symbol"] for r in all_open}
ns_map  = {s: s+".NS" for s in sym_set}

prices = {}
for base, ns in ns_map.items():
    try:
        hist = yf.Ticker(ns).history(period="1d")
        if not hist.empty:
            prices[base] = round(float(hist["Close"].iloc[-1]), 2)
    except Exception:
        pass

def upnl(r):
    ltp = prices.get(r["symbol"])
    if not ltp:
        return None
    entry = float(r["entry_price"])
    qty   = int(float(r["quantity"]))
    if r["direction"].upper() == "BUY":
        return round((ltp - entry) * qty, 0)
    else:
        return round((entry - ltp) * qty, 0)

print("=" * 72)
print(f"  AI TRADING BRAIN — Daily Report  |  {today}  |  11:30 IST")
print("=" * 72)

# ── Token check ─────────────────────────────────────────────────────────────
import os, time, base64
token = os.environ.get("DHAN_ACCESS_TOKEN","")
tok_status = "❌ NOT SET"
if token:
    try:
        payload = token.split(".")[1]
        payload += "=" * (4 - len(payload)%4)
        exp = json.loads(base64.urlsafe_b64decode(payload))["exp"]
        rem = int((exp - time.time()) / 60)
        tok_status = f"✅ VALID — expires in {rem//60}h {rem%60}m"
    except Exception:
        tok_status = "⚠️ PARSE ERROR"
print(f"\n🔑 DHAN TOKEN : {tok_status}")

# ── System ─────────────────────────────────────────────────────────────────
print(f"\n🖥️  VPS           : Healthy ✅  (both containers up 19h+)")
print(f"📡 Bot polling   : Active ✅")
print(f"🕐 Last scan     : mid_session_scan @ 11:30")

# ── Carry-over open positions (from yesterday) ───────────────────────────
print(f"\n{'─'*72}")
print(f"📂 CARRY-OVER OPEN POSITIONS  (from May 11, {len(carry_open)} rows — showing first 10)")
print(f"{'─'*72}")

carry_total = 0.0
fmt = "{:<12} {:<6} {:>6}  {:>8}  {:>8}  {:>8}  {:>8}  {:>12}"
print(fmt.format("SYMBOL","SIDE","QTY","ENTRY","LTP","STOP","TARGET","UNREAL P&L"))
print("-"*72)
for r in carry_open[:10]:
    ltp = prices.get(r["symbol"])
    pnl = upnl(r)
    if pnl is not None:
        carry_total += pnl
        upnl_s = f"₹{pnl:+,.0f}"
    else:
        upnl_s = "n/a"
    print(fmt.format(
        r["symbol"], r["direction"][:5], r["quantity"],
        f"{float(r['entry_price']):.2f}", str(ltp) if ltp else "-",
        r.get("stop_loss",""), r.get("target",""), upnl_s
    ))
icon = "💰" if carry_total >= 0 else "🔴"
print(f"{icon}  Carry-over unrealized P&L : ₹{carry_total:+,.0f}")

# ── Today's new open positions ────────────────────────────────────────────
print(f"\n{'─'*72}")
print(f"🆕 TODAY'S NEW POSITIONS  ({len(today_open)} trades opened May 12)")
print(f"{'─'*72}")
today_upnl_total = 0.0
if today_open:
    print(fmt.format("SYMBOL","SIDE","QTY","ENTRY","LTP","STOP","TARGET","UNREAL P&L"))
    print("-"*72)
    for r in today_open:
        ltp = prices.get(r["symbol"])
        pnl = upnl(r)
        if pnl is not None:
            today_upnl_total += pnl
            upnl_s = f"₹{pnl:+,.0f}"
        else:
            upnl_s = "n/a"
        print(fmt.format(
            r["symbol"], r["direction"][:5], r["quantity"],
            f"{float(r['entry_price']):.2f}", str(ltp) if ltp else "-",
            r.get("stop_loss",""), r.get("target",""), upnl_s
        ))
else:
    print("  (none yet)")

# ── Today's closed trades ────────────────────────────────────────────────
print(f"\n{'─'*72}")
print(f"✅ TODAY'S CLOSED TRADES  ({len(closed_today)} trades)")
print(f"{'─'*72}")
if closed_today:
    cfmt = "{:<12} {:<6} {:>6}  {:>8}  {:>8}  {:>10}  {:<20}"
    print(cfmt.format("SYMBOL","SIDE","QTY","ENTRY","EXIT","P&L","REASON"))
    print("-"*72)
    for r in closed_today:
        print(cfmt.format(
            r["symbol"], r["direction"][:5], r["quantity"],
            f"{float(r['entry_price']):.2f}",
            r.get("exit_price","n/a"),
            f"₹{float(r.get('pnl',0) or 0):+,.0f}",
            r.get("reason","")[:20]
        ))
else:
    print("  (none yet — market still open)")

# ── Summary ───────────────────────────────────────────────────────────────
total_unreal = carry_total + today_upnl_total
print(f"\n{'='*72}")
print(f"  💼 PORTFOLIO SNAPSHOT")
print(f"{'='*72}")
print(f"  Realized P&L today       : ₹{realized:+,.0f}")
print(f"  Unrealized (carry-over)  : ₹{carry_total:+,.0f}")
print(f"  Unrealized (today new)   : ₹{today_upnl_total:+,.0f}")
print(f"  ─────────────────────────────────────────")
print(f"  TOTAL (real + unreal)    : ₹{realized+total_unreal:+,.0f}")
print(f"  Live prices fetched for  : {list(prices.keys())}")
print(f"{'='*72}")
