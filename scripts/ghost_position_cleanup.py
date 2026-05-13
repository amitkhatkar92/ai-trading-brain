"""
Ghost Position Cleanup Script — runs ONCE on VPS to close legacy orphan positions.

Repairs:
  1. SIM_ICICIBANK_BUY_178   — malformed CLOSE row (no exit_price/pnl) + missing registry
  2. SIM_ICICIBANK_BUY_1753  — CLOSE row present (SYSTEM_CLEANUP) but missing registry
  3. SIM_NIFTY_SELL_43_20260507 — OPEN only, no CLOSE row + missing registry
     reason: STRUCTURAL_MISMATCH (entry=864.91 is options premium, not NIFTY spot)

Usage (on VPS, with container stopped):
  docker stop ai-trading-brain
  python scripts/ghost_position_cleanup.py
"""

import csv
import datetime
import os
import sys

DATA_DIR  = os.path.join(os.path.dirname(__file__), "..", "data")
CSV_PATH  = os.path.join(DATA_DIR, "paper_trades.csv")
TODAY_STR = datetime.datetime.now().strftime("%Y-%m-%d")
REGISTRY  = os.path.join(DATA_DIR, f"closed_orders_{TODAY_STR}.txt")

# CSV header
HEADER = ["timestamp", "order_id", "symbol", "direction", "quantity",
          "entry_price", "stop_loss", "target", "strategy", "confidence",
          "rr", "event", "exit_price", "pnl", "reason"]

ICICIBANK_EXIT = 1235.60   # yfinance 2026-05-13 close
ITC_EXIT       = 304.45    # yfinance 2026-05-13 close

# ── Positions to repair ────────────────────────────────────────────────────────
# Each entry: (order_id, symbol, direction, qty, entry, sl, target, strategy,
#              conf, rr, exit_price, pnl, reason, needs_close_row)
REPAIRS = [
    {
        "order_id":      "SIM_ICICIBANK_BUY_178",
        "symbol":        "ICICIBANK",
        "direction":     "BUY",
        "quantity":      178,
        "entry_price":   1318.60,
        "stop_loss":     1294.60,
        "target":        1378.60,
        "strategy":      "Mean_Reversion",
        "confidence":    9.64,
        "rr":            2.5,
        "exit_price":    ICICIBANK_EXIT,
        "pnl":           round((ICICIBANK_EXIT - 1318.60) * 178, 2),
        "reason":        "SESSION_EXPIRED_LEGACY_ORPHAN_CLEANUP",
        "needs_close_row": True,   # existing CLOSE row is malformed
        "add_to_registry": True,
    },
    {
        "order_id":      "SIM_ICICIBANK_BUY_1753",
        "symbol":        "ICICIBANK",
        "direction":     "BUY",
        "quantity":      1753,
        "entry_price":   1345.50,
        "stop_loss":     1321.50,
        "target":        1405.50,
        "strategy":      "Momentum_Retest",
        "confidence":    10.0,
        "rr":            2.5,
        "exit_price":    ICICIBANK_EXIT,
        "pnl":           round((ICICIBANK_EXIT - 1345.50) * 1753, 2),
        "reason":        "SESSION_EXPIRED_LEGACY_ORPHAN_CLEANUP",
        "needs_close_row": False,  # CLOSE row already exists (SYSTEM_CLEANUP 2026-04-17)
        "add_to_registry": True,
    },
    # STEP 5 — NIFTY legacy close: entry is options/futures premium (~865),
    # not NIFTY spot (~23400). Actual P&L is unknowable; force to 0.
    {
        "order_id":      "SIM_NIFTY_SELL_43_20260507",
        "symbol":        "NIFTY",
        "direction":     "SELL",
        "quantity":      43,
        "entry_price":   864.91,
        "stop_loss":     1729.82,
        "target":        172.98,
        "strategy":      "Bull_Call_Spread",
        "confidence":    8.87,
        "rr":            0.8,
        "exit_price":    864.91,
        "pnl":           0.0,
        "reason":        "STRUCTURAL_MISMATCH_EXCLUDE_LEARNING_GOVERNANCE",
        "needs_close_row": True,
        "add_to_registry": True,
    },
]


def main() -> int:
    if not os.path.exists(CSV_PATH):
        print(f"[ERROR] CSV not found: {CSV_PATH}", file=sys.stderr)
        return 1

    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    rows_written = []
    ids_registered = []

    # ── 1. Write additive CLOSE rows to CSV ─────────────────────────────────
    with open(CSV_PATH, "a", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=HEADER)
        for rep in REPAIRS:
            if rep["needs_close_row"]:
                row = {
                    "timestamp":   now_str,
                    "order_id":    rep["order_id"],
                    "symbol":      rep["symbol"],
                    "direction":   rep["direction"],
                    "quantity":    rep["quantity"],
                    "entry_price": rep["entry_price"],
                    "stop_loss":   rep["stop_loss"],
                    "target":      rep["target"],
                    "strategy":    rep["strategy"],
                    "confidence":  rep["confidence"],
                    "rr":          rep["rr"],
                    "event":       "CLOSE",
                    "exit_price":  rep["exit_price"],
                    "pnl":         rep["pnl"],
                    "reason":      rep["reason"],
                }
                writer.writerow(row)
                rows_written.append(rep["order_id"])
                print(f"[GhostCleanup] Wrote CLOSE row  {rep['order_id']}  "
                      f"exit={rep['exit_price']}  pnl={rep['pnl']:.0f}  "
                      f"reason={rep['reason']}")
        fh.flush()
        os.fsync(fh.fileno())

    # ── 2. Register all repaired positions in closed_orders registry ─────────
    # Read existing entries to avoid duplicates.
    existing = set()
    if os.path.exists(REGISTRY):
        with open(REGISTRY, "r", encoding="utf-8") as rf:
            existing = {line.strip() for line in rf if line.strip()}

    with open(REGISTRY, "a", encoding="utf-8") as rf:
        for rep in REPAIRS:
            if rep["add_to_registry"] and rep["order_id"] not in existing:
                rf.write(rep["order_id"] + "\n")
                ids_registered.append(rep["order_id"])
                print(f"[GhostCleanup] Registered     {rep['order_id']}  → {REGISTRY}")
            elif rep["order_id"] in existing:
                print(f"[GhostCleanup] Already in reg {rep['order_id']}")
        rf.flush()
        os.fsync(rf.fileno())

    print(f"\n[GhostCleanup] DONE — CLOSE rows written: {len(rows_written)}, "
          f"registry entries added: {len(ids_registered)}")
    print("[GhostCleanup] Positions marked LEGACY_ORPHAN_CLEANUP will be excluded from "
          "learning and governance on next restore.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
