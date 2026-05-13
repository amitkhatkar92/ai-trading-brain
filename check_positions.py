import base64, json, datetime as dt, csv, os

# ── Token expiry ──────────────────────────────────────────────────────────
env_path = "/app/.env"
token = ""
with open(env_path) as f:
    for line in f:
        if line.startswith("DHAN_ACCESS_TOKEN="):
            token = line.split("=", 1)[1].strip()
            break

payload_b64 = token.split(".")[1] if token.count(".") >= 2 else ""
if payload_b64:
    payload_b64 += "=" * (-len(payload_b64) % 4)
    d = json.loads(base64.b64decode(payload_b64))
    IST = dt.timezone(dt.timedelta(hours=5, minutes=30))
    exp = dt.datetime.fromtimestamp(d["exp"], tz=dt.timezone.utc).astimezone(IST)
    iat = dt.datetime.fromtimestamp(d["iat"], tz=dt.timezone.utc).astimezone(IST)
    now = dt.datetime.now(IST)
    left = exp - now
    h, rem = divmod(int(left.total_seconds()), 3600)
    m = rem // 60
    status = "✅ VALID" if left.total_seconds() > 0 else "❌ EXPIRED"
    print("=" * 50)
    print("DHAN TOKEN")
    print(f"  Issued  : {iat.strftime('%Y-%m-%d %H:%M IST')}")
    print(f"  Expires : {exp.strftime('%Y-%m-%d %H:%M IST')}")
    print(f"  Time left: {h}h {m}m  |  {status}")
else:
    print("ERROR: No token found in .env")

# ── Open positions with unrealized P&L ──────────────────────────────────
import datetime as _dt2
today_str = _dt2.date.today().strftime("%Y-%m-%d")
csv_path = "/app/data/paper_trades.csv"
all_open = []
with open(csv_path, newline="") as f:
    for row in csv.DictReader(f):
        if row.get("event", "").upper() == "OPEN":
            all_open.append(row)

today_open = [r for r in all_open if r.get("timestamp", "").startswith(today_str)]
stale_count = len(all_open) - len(today_open)

print(f"\n{'=' * 55}")
print(f"TODAY'S OPEN POSITIONS  ({today_str})")
print(f"  Today: {len(today_open)}   |   Stale orphans (older dates): {stale_count}")
print("=" * 55)

symbols = list({t["symbol"] for t in today_open})

# Fetch live LTP — add .NS for yfinance
ltp_map = {}
ns_symbols = [s + ".NS" for s in symbols]
try:
    import sys; sys.path.insert(0, "/app")
    from data_feeds.data_feed_manager import get_feed_manager
    quotes = get_feed_manager().get_multiple_quotes(symbols)
    ltp_map = {s: q.ltp for s, q in quotes.items() if q and q.ltp}
except Exception as e:
    print(f"[Feed] {e}")

total_upnl = 0.0
rows = []
for t in today_open:
    sym   = t["symbol"]
    side  = t.get("direction", "BUY").upper()
    qty   = int(float(t.get("quantity", 0)))
    entry = float(t.get("entry_price", 0))
    stop  = float(t.get("stop_loss", 0))
    tgt   = float(t.get("target", 0))
    strat = t.get("strategy", "?")
    ts    = t.get("timestamp", "")[:16]
    ltp   = ltp_map.get(sym, 0)
    if ltp and entry:
        upnl = (ltp - entry) * qty if side == "BUY" else (entry - ltp) * qty
        upnl_str = f"{upnl:+,.0f}"
        total_upnl += upnl
        rr   = (ltp - entry) / (entry - stop) if side == "BUY" and (entry - stop) else 0
        rr_s = f"{rr:+.2f}R"
    else:
        upnl_str = "n/a"
        rr_s = "n/a"
    rows.append((sym, side, qty, entry, ltp, stop, tgt, upnl_str, rr_s, strat, ts))

# Print table
fmt = "{:<12} {:<6} {:>6} {:>8} {:>8} {:>8} {:>8} {:>12} {:>8}  {}"
print(fmt.format("SYMBOL", "SIDE", "QTY", "ENTRY", "LTP", "STOP", "TARGET", "UNREAL P&L", "R", "STRATEGY"))
print("-" * 110)
for r in rows:
    sym, side, qty, entry, ltp, stop, tgt, upnl_str, rr_s, strat, ts = r
    ltp_s = f"{ltp:.2f}" if ltp else "-"
    print(fmt.format(sym, side, qty, f"{entry:.2f}", ltp_s, f"{stop:.2f}", f"{tgt:.2f}", f"₹{upnl_str}", rr_s, strat))
print("-" * 110)
icon = "💰" if total_upnl >= 0 else "🔴"
print(f"{icon} TOTAL UNREALIZED P&L: ₹{total_upnl:+,.0f}")
print(f"\nNow (IST): {dt.datetime.now(dt.timezone(dt.timedelta(hours=5,minutes=30))).strftime('%Y-%m-%d %H:%M:%S')}")
