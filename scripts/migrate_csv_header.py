"""One-time migration: expand paper_trades.csv header from 12 to 15 columns.

Run inside container: python3 migrate_csv_header.py
"""
import csv, os, shutil

path    = os.path.join(os.path.dirname(__file__), "..", "data", "paper_trades.csv")
backup  = path.replace(".csv", "_backup_pre_header_fix.csv")

NEW_HEADER = [
    "timestamp", "order_id", "symbol", "direction", "quantity",
    "entry_price", "stop_loss", "target", "strategy",
    "confidence", "rr", "event",
    "exit_price", "pnl", "reason",
]

if not os.path.exists(path):
    print("paper_trades.csv not found — nothing to migrate.")
    raise SystemExit(0)

with open(path, newline="", encoding="utf-8") as f:
    rows = list(csv.reader(f))

if not rows:
    print("Empty file — nothing to migrate.")
    raise SystemExit(0)

current_header = rows[0]
print(f"Current header ({len(current_header)} cols): {current_header}")

if current_header == NEW_HEADER:
    print("Header already correct — no migration needed.")
    raise SystemExit(0)

shutil.copy2(path, backup)
print(f"Backup: {backup}")

with open(path, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(NEW_HEADER)
    for row in rows[1:]:
        # Pad OPEN rows (12 cols) to 15 with empty strings
        while len(row) < len(NEW_HEADER):
            row.append("")
        w.writerow(row[:len(NEW_HEADER)])

# Verify
with open(path, newline="", encoding="utf-8") as f:
    verify = list(csv.DictReader(f))

print(f"Migration complete. {len(verify)} data rows.")
# Spot-check: find a CLOSE row and show pnl/reason
for r in verify:
    if r.get("event", "").upper() == "CLOSE" and r.get("pnl"):
        print(f"Sample CLOSE: {r['symbol']}  pnl={r['pnl']}  reason={r['reason']}")
        break
