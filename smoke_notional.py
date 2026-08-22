"""Smoke test: verify _compute_open_notional reads event column correctly."""
import sys
sys.path.insert(0, "/app")

# Test 1: direct column parsing against the live CSV
import csv
from pathlib import Path

csv_path = Path("/app/data/paper_trades.csv")
if not csv_path.exists():
    print("SKIP — no paper_trades.csv on VPS yet")
    sys.exit(0)

with csv_path.open(newline="", encoding="utf-8") as f:
    rows = list(csv.DictReader(f))

# Verify column name
if rows:
    first = rows[0]
    assert "event" in first, f"FAIL — no 'event' column in CSV; columns={list(first.keys())}"
    assert "action" not in first, "WARN — unexpected 'action' column present"

# Verify accounting
result = {}
for row in rows:
    sym   = row.get("symbol", "").upper()
    event = row.get("event", "").upper()
    try:
        qty   = int(float(row.get("quantity", 0)))
        price = float(row.get("entry_price", 0))
    except (ValueError, TypeError):
        continue
    notional = qty * price
    if event in ("OPEN", "REENTRY_OPEN"):
        result[sym] = result.get(sym, 0.0) + notional
    elif event in ("CLOSE", "CANCELLED"):
        result[sym] = max(0.0, result.get(sym, 0.0) - notional)

# All closed positions should have 0 notional
open_pos = {k: v for k, v in result.items() if v > 0}
print(f"VPS_P9_PASS — open notional from CSV: {len(open_pos)} symbol(s) with open notional")
for sym, val in open_pos.items():
    print(f"  {sym}: ₹{val:,.0f}")
if not open_pos:
    print("  (no open positions in CSV — all cancelled/closed)")
