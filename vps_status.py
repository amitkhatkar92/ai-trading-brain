"""Full status report: positions, PnL, recent signals, token, bot."""
import os, sys, csv, datetime, json

# ── Positions from paper_trades.csv ──────────────────────────────────────
CSV = "/app/data/paper_trades.csv"
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
