import csv
from pathlib import Path

rows   = list(csv.DictReader(open("/app/data/paper_trades.csv")))
opens  = [r for r in rows if r["event"].strip() == "OPEN"]
closes = [r for r in rows if r["event"].strip() == "CLOSE"]
open_ids  = {r["order_id"] for r in opens}
close_ids = {r["order_id"] for r in closes}
orphans   = open_ids - close_ids

print(f"Total rows : {len(rows)}")
print(f"OPEN rows  : {len(opens)}")
print(f"CLOSE rows : {len(closes)}")
print(f"Orphans    : {len(orphans)}")
if orphans:
    for oid in orphans:
        r = next(x for x in opens if x["order_id"] == oid)
        print(f"  {r['symbol']} {r['direction']} {r['quantity']} @ {r['entry_price']}")
else:
    print("  None — all positions closed  ✓")

total_pnl = sum(
    float(r["pnl"]) for r in closes
    if r["pnl"].strip() not in ("", "None")
)
print(f"\nTotal closed P&L: {total_pnl:,.2f}")
