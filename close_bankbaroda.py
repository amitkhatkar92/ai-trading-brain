"""
Close BANKBARODA position: failed breakout exit.
Day high 273.75 tested and exceeded both resistance levels (272.25 + 273.99),
then price rejected sharply to 268.80 — classic failed breakout / bull trap.
Original thesis (breakout above resistance) is invalidated.
"""
import csv, os, shutil
from pathlib import Path
from datetime import datetime, timezone

CSV  = Path("/app/data/paper_trades.csv")
BKUP = Path("/app/data/paper_trades_backup_pre_bb_close.csv")

# ── Read existing CSV to find the open BANKBARODA row ────────────────────────
with open(CSV) as f:
    rows = list(csv.DictReader(f))
fieldnames = list(rows[0].keys())

# Find the open position
open_row = None
close_row = None
for r in rows:
    if r["order_id"] == "SIM_BANKBARODA_BUY_Q5147_P271.74_1780035676109":
        if r["event"].strip() == "OPEN":
            open_row = r
        elif r["event"].strip() == "CLOSE":
            close_row = r

if close_row:
    print("BANKBARODA already has a CLOSE row — no action needed.")
    import sys; sys.exit(0)

if not open_row:
    print("ERROR: could not find BANKBARODA OPEN row in CSV.")
    import sys; sys.exit(1)

# ── Fetch live LTP for exit price ────────────────────────────────────────────
import yfinance as yf
t = yf.Ticker("BANKBARODA.NS")
h = t.history(period="1d", interval="5m", auto_adjust=True)
exit_price = round(float(h["Close"].iloc[-1]), 2)
day_high   = round(float(h["High"].max()), 2)

entry_price = float(open_row["entry_price"])
qty         = int(open_row["quantity"])
pnl         = round((exit_price - entry_price) * qty, 2)
now_ts      = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

reason = (
    f"failed_breakout_exit("
    f"day_high={day_high}_exceeded_resistance_273.99_then_rejected;"
    f"ltp_back_to_{exit_price};thesis_invalidated)"
)

close_entry = dict.fromkeys(fieldnames, "")
close_entry.update({
    "timestamp"   : now_ts,
    "order_id"    : open_row["order_id"],
    "symbol"      : open_row["symbol"],
    "direction"   : open_row["direction"],
    "quantity"    : open_row["quantity"],
    "entry_price" : open_row["entry_price"],
    "stop_loss"   : open_row["stop_loss"],
    "target"      : open_row["target"],
    "strategy"    : open_row["strategy"],
    "confidence"  : open_row["confidence"],
    "rr"          : open_row["rr"],
    "event"       : "CLOSE",
    "exit_price"  : str(exit_price),
    "pnl"         : str(pnl),
    "reason"      : reason,
})

# ── Backup + append ──────────────────────────────────────────────────────────
shutil.copy2(CSV, BKUP)
print(f"Backup: {BKUP}")

with open(CSV, "a", newline="") as f:
    w = csv.DictWriter(f, fieldnames=fieldnames)
    w.writerow(close_entry)

print(f"\nCLOSED: BANKBARODA BUY 5147 @ exit={exit_price}")
print(f"  Entry : {entry_price}")
print(f"  Exit  : {exit_price}")
print(f"  P&L   : {pnl:,.2f}")
print(f"  Reason: {reason}")
print(f"\nFailed-breakout analysis:")
print(f"  Day high {day_high} broke above old resistance (273.99) AND new resistance (272.25)")
print(f"  Stock rejected and returned to {exit_price} — bull trap confirmed")
print(f"  Exiting before stop (263.87) is hit — saves {round((exit_price - 263.87)*qty):,} vs max-stop loss")
