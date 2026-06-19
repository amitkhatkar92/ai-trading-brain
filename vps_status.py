"""Comprehensive VPS status check — Monday morning."""
import sqlite3, json, os, csv
from datetime import date, datetime

TODAY = date.today().isoformat()
print(f"=== STATUS CHECK: {TODAY} ===\n")

# 1. System logs today
conn = sqlite3.connect("/app/data/trading_brain.db")
logs = conn.execute(
    "SELECT ts, level, component, event_type, message FROM system_logs "
    "WHERE ts LIKE ? ORDER BY ts", (f"{TODAY}%",)
).fetchall()
print(f"[System Logs] Today: {len(logs)} entries")
for r in logs:
    print(f"  {r[0][:16]}  {r[1][:5]:5}  {r[3][:22]:23}  {str(r[4])[:70]}")
conn.close()

print()

# 2. Strategy performance state
perf_file = "/app/data/strategy_performance.json"
if os.path.exists(perf_file):
    with open(perf_file) as f:
        perf = json.load(f)
    print(f"[Strategy Status]")
    for name, s in perf.items():
        if name == "unknown":
            continue
        status = "ACTIVE" if s.get("enabled") else "DISABLED"
        print(f"  {name}: {status}  consec_losses={s.get('consec_losses',0)}  wins={s.get('wins',0)}/{s.get('total_trades',0)}")

print()

# 3. Scanner candidates
cand_file = "/app/data/daily_candidates.json"
if os.path.exists(cand_file):
    with open(cand_file) as f:
        cands = json.load(f)
    mtime = datetime.fromtimestamp(os.path.getmtime(cand_file))
    print(f"[Scanner] daily_candidates.json — last updated: {mtime.strftime('%Y-%m-%d %H:%M')}")
    all_c = []
    if isinstance(cands, list):
        all_c = cands
    elif isinstance(cands, dict):
        for k, v in cands.items():
            if isinstance(v, list):
                all_c.extend(v)
            elif isinstance(v, dict):
                all_c.append(v)
    top = sorted(all_c, key=lambda x: x.get("confidence", 0), reverse=True)[:10]
    for c in top:
        print(f"  {c.get('symbol','?'):15} conf={c.get('confidence',0):.3f}  strategy={c.get('strategy','?')}")
else:
    print("[Scanner] daily_candidates.json NOT FOUND")

print()

# 4. Universe
uni_file = "/app/data/nifty500_universe.json"
if os.path.exists(uni_file):
    mtime = datetime.fromtimestamp(os.path.getmtime(uni_file))
    with open(uni_file) as f:
        uni = json.load(f)
    count = len(uni) if isinstance(uni, list) else len(uni.get("symbols", uni.get("universe", [])))
    age_days = (datetime.now() - mtime).days
    print(f"[Universe] {count} symbols  last updated: {mtime.strftime('%Y-%m-%d %H:%M')}  age={age_days}d")
else:
    print("[Universe] nifty500_universe.json NOT FOUND")

# 5. SR levels
sr_file = "/app/data/sr_levels.json"
if os.path.exists(sr_file):
    mtime = datetime.fromtimestamp(os.path.getmtime(sr_file))
    with open(sr_file) as f:
        sr = json.load(f)
    count = len(sr) if isinstance(sr, dict) else 0
    age_days = (datetime.now() - mtime).days
    print(f"[SR Levels] {count} symbols  last updated: {mtime.strftime('%Y-%m-%d %H:%M')}  age={age_days}d")
else:
    print("[SR Levels] NOT FOUND")

print()

# 6. Paper trades today
trades_file = "/app/data/paper_trades.csv"
if os.path.exists(trades_file):
    today_trades = []
    all_open = []
    with open(trades_file) as f:
        reader = csv.DictReader(f)
        for row in reader:
            ts = row.get("timestamp", row.get("ts", ""))
            if ts.startswith(TODAY):
                today_trades.append(row)
            if row.get("status") == "OPEN":
                all_open.append(row)
    total_pnl = sum(float(r.get("pnl", 0) or 0) for r in today_trades if r.get("status") == "CLOSED")
    print(f"[Trades] Today: {len(today_trades)} rows  realized_pnl=Rs.{total_pnl:,.2f}")
    for t in today_trades:
        print(f"  {str(t.get('timestamp',''))[:16]}  {t.get('symbol','?'):12}  {t.get('status','?'):6}  strategy={t.get('strategy','?'):20}  pnl={t.get('pnl','?')}")
    print(f"[Open Positions] {len(all_open)} open")
    for t in all_open:
        print(f"  {t.get('symbol','?'):12}  entry={t.get('entry_price','?')}  qty={t.get('quantity','?')}  strategy={t.get('strategy','?')}")
else:
    print("[Trades] paper_trades.csv NOT FOUND")

print()

# 7. Dhan token freshness
token_file = "/app/data/dhan_token.json"
if os.path.exists(token_file):
    mtime = datetime.fromtimestamp(os.path.getmtime(token_file))
    age_h = (datetime.now() - mtime).total_seconds() / 3600
    valid = "VALID" if age_h <= 24 else "EXPIRED"
    print(f"[Dhan Token] Updated: {mtime.strftime('%Y-%m-%d %H:%M')}  age={age_h:.1f}h  {valid}")
else:
    alt = "/app/data/odm_state.json"
    if os.path.exists(alt):
        with open(alt) as f:
            odm = json.load(f)
        print(f"[ODM State] {list(odm.keys())[:5]}")
    print("[Dhan Token] dhan_token.json NOT FOUND")

# 8. Recent system events (last 48h)
conn = sqlite3.connect("/app/data/trading_brain.db")
recent = conn.execute(
    "SELECT ts, event_type, message FROM system_logs ORDER BY ts DESC LIMIT 10"
).fetchall()
print(f"\n[Recent Events - last 10]")
for r in recent:
    print(f"  {r[0][:16]}  {r[1][:22]:23}  {str(r[2])[:60]}")
conn.close()

# 9. Data files freshness
print("\n[Data Files]")
files = [
    "/app/data/daily_candidates.json",
    "/app/data/nifty500_universe.json",
    "/app/data/sr_levels.json",
    "/app/data/strategy_performance.json",
    "/app/data/regime_probability_history.json",
    "/app/data/paper_trades.csv",
]
for fp in files:
    if os.path.exists(fp):
        mtime = datetime.fromtimestamp(os.path.getmtime(fp))
        age_h = (datetime.now() - mtime).total_seconds() / 3600
        print(f"  {os.path.basename(fp):35}  {mtime.strftime('%Y-%m-%d %H:%M')}  age={age_h:.1f}h")
    else:
        print(f"  {os.path.basename(fp):35}  NOT FOUND")

# end of script

now = datetime.datetime.now()
open_trades = []
closed_today = []

try:
    with open(CSV, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            status = row.get("status", "").upper()
            entry_time_str = row.get("entry_time", "")
            try:
                entry_time = datetime.datetime.fromisoformat(entry_time_str)
                age_days = (now - entry_time).days
            except:
                age_days = "?"

            if status == "OPEN":
                open_trades.append({
                    "id": row.get("trade_id", "?")[-20:],
                    "symbol": row.get("symbol", "?"),
                    "side": row.get("side", "?"),
                    "entry": row.get("entry_price", "?"),
                    "qty": row.get("quantity", "?"),
                    "strategy": row.get("strategy", "?"),
                    "sl": row.get("stop_loss", "?"),
                    "tp": row.get("take_profit", "?"),
                    "max_carry": row.get("max_carry_days", "?"),
                    "age_days": age_days,
                    "entry_time": entry_time_str[:16],
                })
            elif status == "CLOSED":
                try:
                    exit_time = datetime.datetime.fromisoformat(row.get("exit_time", ""))
                    if exit_time.date() == now.date():
                        pnl = float(row.get("pnl", 0))
                        closed_today.append({
                            "symbol": row.get("symbol", "?"),
                            "side": row.get("side", "?"),
                            "pnl": pnl,
                            "reason": row.get("exit_reason", "?"),
                        })
                except:
                    pass
except Exception as e:
    print(f"CSV error: {e}")

print("=" * 60)
print(f"  STATUS REPORT — {now.strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 60)

print(f"\n📂 OPEN POSITIONS ({len(open_trades)})")
if open_trades:
    for t in open_trades:
        print(f"  {t['symbol']:15s} {t['side']:4s}  entry={t['entry']:>8}  qty={t['qty']:>4}"
              f"  SL={t['sl']:>8}  TP={t['tp']:>8}"
              f"  age={t['age_days']}d / {t['max_carry']}d max"
              f"  [{t['strategy']}]")
else:
    print("  None")

print(f"\n📊 CLOSED TODAY ({len(closed_today)})")
if closed_today:
    total_pnl = sum(t["pnl"] for t in closed_today)
    for t in closed_today:
        sign = "+" if t["pnl"] >= 0 else ""
        print(f"  {t['symbol']:15s} {t['side']:4s}  PnL={sign}{t['pnl']:,.0f}  reason={t['reason']}")
    print(f"  {'':15s}       Day PnL total: {'+' if total_pnl >= 0 else ''}{total_pnl:,.0f}")
else:
    print("  None")

# ── Token status ──────────────────────────────────────────────────────────
print("\n🔑 DHAN TOKEN")
try:
    import base64
    for line in open("/app/.env").read().splitlines():
        if line.startswith("DHAN_ACCESS_TOKEN="):
            t = line.split("=", 1)[1].strip()
            parts = t.split(".")
            payload = json.loads(base64.urlsafe_b64decode(parts[1] + "=="))
            exp = datetime.datetime.utcfromtimestamp(payload["exp"])
            iat = datetime.datetime.utcfromtimestamp(payload["iat"])
            utcnow = datetime.datetime.utcnow()
            if exp > utcnow:
                remaining = exp - utcnow
                h, m = divmod(int(remaining.total_seconds()) // 60, 60)
                print(f"  Status  : ✅ VALID  (expires in {h}h {m}m — {exp.strftime('%Y-%m-%d %H:%M')} UTC)")
            else:
                print(f"  Status  : ❌ EXPIRED ({(utcnow - exp).days}d {((utcnow-exp).seconds//3600)}h ago)")
            print(f"  Issued  : {iat.strftime('%Y-%m-%d %H:%M')} UTC")
            break
except Exception as e:
    print(f"  Error reading token: {e}")

# ── Recent log activity ───────────────────────────────────────────────────
print("\n📋 RECENT LOG (last 5 min)")
import subprocess
result = subprocess.run(
    ["python3", "-c",
     "import subprocess, datetime\n"
     "cutoff = (datetime.datetime.now() - datetime.timedelta(minutes=5)).strftime('%Y-%m-%d %H:%M')\n"
     "r = subprocess.run(['tail','-n','200','/app/logs/trading.log'], capture_output=True, text=True)\n"
     "lines = [l for l in r.stdout.splitlines() if l[:16] >= cutoff]\n"
     "for l in lines[-15:]: print(l)"
    ],
    capture_output=True, text=True
)
for line in result.stdout.strip().splitlines()[-15:]:
    # shorten verbose lines
    if len(line) > 110:
        line = line[:107] + "..."
    print(" ", line)
if result.stderr:
    print("  [log err]", result.stderr[:100])

# ── Telegram bot ──────────────────────────────────────────────────────────
print("\n🤖 TELEGRAM BOT")
result2 = subprocess.run(
    ["grep", "-c", "Started polling", "/app/logs/trading.log"],
    capture_output=True, text=True
)
count = result2.stdout.strip()
print(f"  Polling sessions in log: {count}")
print("=" * 60)
