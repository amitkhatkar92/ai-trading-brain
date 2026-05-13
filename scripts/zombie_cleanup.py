"""
Surgical closure of 3 zombie OPEN positions from engineering era.
Reason: SYSTEM_CLEANUP — excluded from learning pipeline and official_trades.
Must NOT be counted as strategy evaluation trades.

Positions to close:
  SIM_COALINDIA_BUY_4000_1776917706784  COALINDIA BUY  4000 @ 447.20
  SIM_NTPC_BUY_4927_1777002633179       NTPC      BUY  4927 @ 402.25
  SIM_NTPC_BUY_4950_1777008570983       NTPC      BUY  4950 @ 400.40
"""

import sys
import csv
import shutil
from datetime import datetime

sys.path.insert(0, "/app")

CSV_PATH    = "/app/data/paper_trades.csv"
BACKUP_PATH = "/app/data/paper_trades.csv.bak_zombie_cleanup_apr28"

ZOMBIES = {
    "SIM_COALINDIA_BUY_4000_1776917706784": {
        "symbol": "COALINDIA", "side": "BUY",  "qty": 4000,  "entry": 447.20,
        "sl": 431.6, "target": 486.2, "strategy": "Momentum_Retest",
    },
    "SIM_NTPC_BUY_4927_1777002633179": {
        "symbol": "NTPC",      "side": "BUY",  "qty": 4927,  "entry": 402.25,
        "sl": 388.45, "target": 436.75, "strategy": "Momentum_Retest",
    },
    "SIM_NTPC_BUY_4950_1777008570983": {
        "symbol": "NTPC",      "side": "BUY",  "qty": 4950,  "entry": 400.40,
        "sl": 386.6, "target": 434.9, "strategy": "Momentum_Retest",
    },
}

# ── 1. Fetch live LTP ─────────────────────────────────────────────────────────
print("Fetching live LTP...")
ltp = {}
try:
    import yfinance as yf
    for ticker, yf_sym in [("COALINDIA", "COALINDIA.NS"), ("NTPC", "NTPC.NS")]:
        data = yf.download(yf_sym, period="1d", interval="1m", timeout=10, progress=False)
        if data is not None and not data.empty:
            price = round(float(data["Close"].dropna().iloc[-1]), 2)
            ltp[ticker] = price
            print(f"  {ticker}: ₹{price} (live)")
        else:
            raise ValueError(f"No data for {yf_sym}")
except Exception as e:
    print(f"  WARNING: yfinance failed ({e}) — using last known monitor prices")
    ltp = {"COALINDIA": 470.55, "NTPC": 411.50}
    print(f"  Fallback: COALINDIA=₹{ltp['COALINDIA']}  NTPC=₹{ltp['NTPC']}")

# ── 2. Check no CLOSE row already exists for these IDs ────────────────────────
print("\nChecking CSV for existing CLOSE rows...")
already_closed = set()
with open(CSV_PATH, "r", encoding="utf-8") as f:
    reader = csv.reader(f)
    for row in reader:
        if len(row) >= 12 and row[11] == "CLOSE" and row[1] in ZOMBIES:
            already_closed.add(row[1])

if already_closed:
    print(f"  Already closed: {already_closed} — skipping those.")

# ── 3. Backup ─────────────────────────────────────────────────────────────────
shutil.copy2(CSV_PATH, BACKUP_PATH)
print(f"\nBackup created: {BACKUP_PATH}")

# ── 4. Build CLOSE rows ───────────────────────────────────────────────────────
now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
close_rows = []

for order_id, pos in ZOMBIES.items():
    if order_id in already_closed:
        continue
    exit_price = ltp[pos["symbol"]]
    if pos["side"] == "BUY":
        pnl = round((exit_price - pos["entry"]) * pos["qty"], 2)
    else:
        pnl = round((pos["entry"] - exit_price) * pos["qty"], 2)

    row = [
        now_str,
        order_id,
        pos["symbol"],
        pos["side"],
        str(pos["qty"]),
        str(pos["entry"]),
        str(pos["sl"]),
        str(pos["target"]),
        pos["strategy"],
        "",          # score — empty for CLOSE rows
        "",          # rr    — empty for CLOSE rows
        "CLOSE",
        str(exit_price),
        str(pnl),
        "SYSTEM_CLEANUP",
    ]
    close_rows.append(row)
    print(f"\n  CLOSE → {order_id}")
    print(f"    {pos['symbol']} {pos['side']} {pos['qty']} @ entry={pos['entry']}")
    print(f"    exit={exit_price}  pnl=₹{pnl:+,.2f}  reason=SYSTEM_CLEANUP")

# ── 5. Append to CSV ──────────────────────────────────────────────────────────
with open(CSV_PATH, "a", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    for row in close_rows:
        writer.writerow(row)

print(f"\n✅ {len(close_rows)} CLOSE row(s) appended.")

# ── 6. Verify: count remaining OPEN zombies ───────────────────────────────────
print("\nVerification — scanning for still-open zombie IDs...")
open_ids = set()
close_ids = set()
with open(CSV_PATH, "r", encoding="utf-8") as f:
    reader = csv.reader(f)
    for row in reader:
        if len(row) < 12:
            continue
        oid = row[1]
        if oid not in ZOMBIES:
            continue
        if row[11] == "CLOSE":
            close_ids.add(oid)
        elif row[-1] == "OPEN" or row[11] == "OPEN":
            open_ids.add(oid)

remaining = open_ids - close_ids
if remaining:
    print(f"  ⚠️  Still open: {remaining}")
else:
    print("  ✅ All 3 zombie positions now have CLOSE rows.")

# ── 7. Net PnL summary ────────────────────────────────────────────────────────
total_pnl = sum(float(r[13]) for r in close_rows)
print(f"\n  Total cleanup PnL: ₹{total_pnl:+,.2f}")
print("  (SYSTEM_CLEANUP — excluded from strategy evaluation, official_trades, ValidationEngine)")
print("\nDone.")
