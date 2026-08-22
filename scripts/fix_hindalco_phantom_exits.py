"""
HINDALCO forensic correction script.

Root cause: The .NS stripping bug in dhan_feed.py caused _yf_quote("HINDALCO.NS")
to return None (lookup key "HINDALCO.NS" not in _YF_TICKERS), falling through to
_sim_quote which defaulted to ₹1000 + noise = ₹997.77.

Position 1 (May 12–13, SIM_HINDALCO_BUY_2049):
  - Entry ₹1,023.50 was REAL (actual yfinance May 11 close = ₹1,023.50)
  - SL=₹999.60 was falsely triggered by phantom SIM ₹998.27
  - Actual May 13 market close = ₹1,073.10 (SL never actually breached)
  - Corrected exit: ₹1,073.10 → P&L = +₹101,630.40

Position 2 (May 21–28, SIM_HINDALCO_BUY_Q1147_P1099.92_...):
  - Entry ₹1,097.40 was REAL (actual yfinance May 21 close = ₹1,099.30)
  - May 28 was a market holiday; Dhan rejected all SIDs; SIM price ₹997.77 frozen
  - DataGuard correctly flagged "stale price for 6 consecutive cycles" but exit used it anyway
  - Last valid trading day = May 27 close = ₹1,149.70
  - Corrected exit: ₹1,149.70 → P&L = +₹59,988.10
"""
import csv
import io
import os
import shutil
from datetime import datetime

CSV_PATH = "/app/data/paper_trades.csv"
BACKUP_PATH = "/app/data/paper_trades_backup_hindalco_audit.csv"

CORRECTIONS = {
    "SIM_HINDALCO_BUY_2049": {
        "exit_price":   1073.10,
        "pnl":          round(2049 * (1073.10 - 1023.5), 2),   # +101,630.40
        "close_reason": "FALSE_SL_TRIGGER_CORRECTED(phantom_sim_998.27<sl_999.60;actual_may13_close_1073.10)",
    },
    "SIM_HINDALCO_BUY_Q1147_P1099.92_1779348606983": {
        "exit_price":   1149.70,
        "pnl":          round(1147 * (1149.70 - 1097.4), 2),   # +59,988.10
        "close_reason": "PHANTOM_EXIT_CORRECTED(market_holiday_may28;sim_997.77;actual_may27_close_1149.70)",
    },
}

# ── Backup original ──────────────────────────────────────────────────────────
shutil.copy(CSV_PATH, BACKUP_PATH)
print(f"Backup written: {BACKUP_PATH}")

# ── Read and patch ───────────────────────────────────────────────────────────
with open(CSV_PATH, newline="") as fh:
    reader = csv.reader(fh)
    rows = list(reader)

header = rows[0]
col = {name: i for i, name in enumerate(header)}

# Debug: print actual column names found
print(f"CSV columns: {header}")

patched = 0
for row in rows[1:]:
    if len(row) < 2:
        continue
    oid    = row[col["order_id"]]
    event  = row[col["event"]] if "event" in col else row[col.get("status", -1)]
    if oid in CORRECTIONS and event == "CLOSE":
        correction = CORRECTIONS[oid]
        old_exit = row[col["exit_price"]]
        old_pnl  = row[col["pnl"]]
        row[col["exit_price"]] = str(correction["exit_price"])
        row[col["pnl"]]        = str(correction["pnl"])
        row[col["reason"]]     = correction["close_reason"]
        print(f"\nPatched [{oid}]")
        print(f"  exit_price : {old_exit} → {correction['exit_price']}")
        print(f"  pnl        : {old_pnl}  → {correction['pnl']}")
        print(f"  reason     : {correction['close_reason']}")
        patched += 1

# ── Write back ───────────────────────────────────────────────────────────────
with open(CSV_PATH, "w", newline="") as fh:
    writer = csv.writer(fh)
    writer.writerow(header)
    writer.writerows(rows[1:])

print(f"\n{patched}/{len(CORRECTIONS)} corrections applied to {CSV_PATH}")
