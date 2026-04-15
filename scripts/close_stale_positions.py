"""
close_stale_positions.py
========================
One-shot script to close all open positions in paper_trades.csv that have
no matching CLOSE row — except positions opened TODAY (those are live trades).

Usage (inside Docker container):
    python3 scripts/close_stale_positions.py

Usage (on VPS host, pipe into docker):
    cat scripts/close_stale_positions.py | docker exec -i ai-trading-brain python3

Exit codes:
    0 — success (even if nothing to close)
    1 — error
"""

import csv
import datetime
import sys
from collections import defaultdict
from pathlib import Path

CSV_FILE = Path(__file__).resolve().parent.parent / "data" / "paper_trades.csv"

def main() -> int:
    if not CSV_FILE.exists():
        print(f"[ERROR] CSV not found: {CSV_FILE}")
        return 1

    rows = list(csv.DictReader(open(CSV_FILE)))
    # Strip None keys from malformed rows (extra columns)
    rows = [{k: v for k, v in r.items() if k is not None} for r in rows]
    if not rows:
        print("CSV is empty — nothing to do.")
        return 0

    header = list(rows[0].keys())
    counts: dict = defaultdict(lambda: {"OPEN": 0, "CLOSE": 0})
    last_row: dict = {}
    for r in rows:
        oid = r.get("order_id", "")
        ev  = r.get("event", "").upper()
        if ev in ("OPEN", "CLOSE"):
            counts[oid][ev] += 1
        last_row[oid] = r

    today_str = datetime.date.today().isoformat()
    stale = [
        oid for oid, c in counts.items()
        if c["OPEN"] > 0 and c["CLOSE"] == 0
        and not last_row[oid].get("timestamp", "").startswith(today_str)
    ]

    if not stale:
        print("✅ No stale positions found — CSV is clean.")
        return 0

    print(f"Found {len(stale)} stale position(s) to close:")
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    close_rows = []
    for oid in stale:
        r = {k: last_row[oid].get(k, "") for k in header}
        r["timestamp"] = now_str
        r["event"]     = "CLOSE"
        close_rows.append(r)
        print(f"  {oid} | {r.get('symbol','?')} | entry={r.get('entry_price','?')} | opened={last_row[oid].get('timestamp','?')}")

    with open(CSV_FILE, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=header, extrasaction="ignore")
        for cr in close_rows:
            w.writerow(cr)

    print(f"\n✅ Written {len(close_rows)} CLOSE rows.")
    print("   Restart the container for in-memory state to clear:")
    print("   docker restart ai-trading-brain")
    return 0


if __name__ == "__main__":
    sys.exit(main())
