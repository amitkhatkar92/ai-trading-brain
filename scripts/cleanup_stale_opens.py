"""
Cleanup stale OPEN positions in paper_trades.csv.

Finds any OPEN row with no matching CLOSE row from a date before today,
and appends a synthetic CLOSE row (exit_price=entry_price, pnl=0,
reason=SYSTEM_CLEANUP). Does NOT delete or modify any existing rows.

Usage:
    python scripts/cleanup_stale_opens.py           # dry-run (safe preview)
    python scripts/cleanup_stale_opens.py --apply   # write CLOSE rows
"""
from __future__ import annotations

import csv
import os
import sys
from datetime import datetime

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_CSV  = os.path.join(_ROOT, "data", "paper_trades.csv")

EXTENDED_FIELDS = [
    "timestamp", "order_id", "symbol", "direction", "quantity",
    "entry_price", "stop_loss", "target", "strategy", "confidence",
    "rr", "event", "exit_price", "pnl", "reason",
]

_JOURNAL_HEADER = [
    "timestamp", "order_id", "symbol", "direction", "quantity",
    "entry_price", "stop_loss", "target", "strategy", "confidence",
    "rr", "event",
]


def main() -> None:
    apply = "--apply" in sys.argv
    today = datetime.now().strftime("%Y-%m-%d")

    if not os.path.exists(_CSV):
        print(f"[ERROR] Not found: {_CSV}")
        sys.exit(1)

    # ── Pass 1: build open/close maps across ALL dates ────────────────
    open_rows: dict[str, dict] = {}   # order_id → OPEN row

    with open(_CSV, newline="", encoding="utf-8") as fh:
        reader = csv.reader(fh)
        next(reader)  # skip header
        for parts in reader:
            if not parts:
                continue
            row   = dict(zip(EXTENDED_FIELDS, parts))
            oid   = row.get("order_id", "").strip()
            event = row.get("event", "").strip().upper()
            if not oid:
                continue
            if event in ("OPEN", "REENTRY_OPEN"):
                open_rows[oid] = row
            elif event in ("CLOSE", "CANCELLED"):
                open_rows.pop(oid, None)

    # ── Filter: only stale (not today) ───────────────────────────────
    stale = {
        oid: row for oid, row in open_rows.items()
        if not row.get("timestamp", "").startswith(today)
    }

    if not stale:
        print("No stale OPEN positions found. CSV is clean.")
        return

    print(f"\nFound {len(stale)} stale OPEN position(s) to close:\n")
    for oid, row in sorted(stale.items(), key=lambda x: x[1]["timestamp"]):
        print(f"  {row['timestamp']:20s}  {oid:35s}  {row['symbol']:12s}  entry={row['entry_price']}")

    if not apply:
        print(f"\n[DRY RUN] No changes written.")
        print(f"          Re-run with --apply to append CLOSE rows.\n")
        return

    # ── Pass 2: append CLOSE rows ─────────────────────────────────────
    now_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    written = 0
    with open(_CSV, "a", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=_JOURNAL_HEADER + ["exit_price", "pnl", "reason"])
        for oid, row in sorted(stale.items(), key=lambda x: x[1]["timestamp"]):
            entry_px = float(row.get("entry_price") or 0)
            w.writerow({
                "timestamp":   now_ts,
                "order_id":    oid,
                "symbol":      row.get("symbol", ""),
                "direction":   row.get("direction", ""),
                "quantity":    row.get("quantity", ""),
                "entry_price": row.get("entry_price", ""),
                "stop_loss":   row.get("stop_loss", ""),
                "target":      row.get("target", ""),
                "strategy":    row.get("strategy", ""),
                "confidence":  row.get("confidence", ""),
                "rr":          row.get("rr", ""),
                "event":       "CLOSE",
                "exit_price":  round(entry_px, 2),
                "pnl":         0.0,
                "reason":      "SYSTEM_CLEANUP",
            })
            written += 1

    print(f"\n[APPLIED] Appended {written} CLOSE rows (reason=SYSTEM_CLEANUP).")
    print(f"          CSV is now clean.\n")


if __name__ == "__main__":
    main()
