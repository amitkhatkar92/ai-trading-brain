"""
Session Metrics — compute core trading metrics from paper_trades.csv (ground truth).

Usage:
    python scripts/session_metrics.py              # today
    python scripts/session_metrics.py 2026-04-17   # specific date

Outputs:
    • Trades executed & swap count
    • Win rate
    • Avg win R / Avg loss R
    • Expectancy
    • Swap impact summary
"""
from __future__ import annotations

import csv
import os
import sys
from collections import defaultdict
from datetime import datetime

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_CSV  = os.path.join(_ROOT, "data", "paper_trades.csv")


def run(date_str: str) -> None:
    if not os.path.exists(_CSV):
        print(f"[ERROR] Journal not found: {_CSV}")
        return

    # ── Load CSV ──────────────────────────────────────────────────────
    open_rows:  dict[str, dict] = {}    # order_id → OPEN row
    close_rows: dict[str, dict] = {}    # order_id → CLOSE row

    EXTENDED_FIELDS = [
        "timestamp", "order_id", "symbol", "direction", "quantity",
        "entry_price", "stop_loss", "target", "strategy", "confidence",
        "rr", "event", "exit_price", "pnl", "reason",
    ]
    with open(_CSV, newline="", encoding="utf-8") as fh:
        reader = csv.reader(fh)
        next(reader)  # skip header
        for parts in reader:
            if not parts or not parts[0].startswith(date_str):
                continue
            row = dict(zip(EXTENDED_FIELDS, parts))
            oid   = row.get("order_id", "").strip()
            event = row.get("event", "").strip().upper()
            if event in ("OPEN", "REENTRY_OPEN"):
                open_rows[oid] = row
            elif event in ("CLOSE", "CANCELLED"):
                close_rows[oid] = row

    # ── Match OPEN→CLOSE pairs ────────────────────────────────────────
    trades = []   # list of dicts with R, swap flag, etc.
    for oid, close_row in close_rows.items():
        open_row = open_rows.get(oid)
        if not open_row:
            continue

        entry      = float(open_row.get("entry_price") or 0)
        stop       = float(open_row.get("stop_loss")   or 0)
        direction  = open_row.get("direction", "BUY")
        exit_px    = float(close_row.get("exit_price") or entry)
        reason     = close_row.get("reason", "").strip().upper()
        is_swap    = (reason == "REPLACEMENT")

        risk = abs(entry - stop) if stop else 0.0
        if risk > 0 and entry > 0:
            if direction == "BUY":
                r = (exit_px - entry) / risk
            else:
                r = (entry - exit_px) / risk
        else:
            r = 0.0

        trades.append({
            "oid":    oid,
            "symbol": open_row.get("symbol", ""),
            "r":      round(r, 3),
            "swap":   is_swap,
            "entry":  entry,
            "exit":   exit_px,
        })

    if not trades:
        print(f"\n  No closed trades found for {date_str}.\n")
        return

    # ── Core metrics ──────────────────────────────────────────────────
    all_r    = [t["r"] for t in trades]
    wins     = [r for r in all_r if r > 0]
    losses   = [r for r in all_r if r <= 0]
    swaps    = [t for t in trades if t["swap"]]
    non_swap = [t for t in trades if not t["swap"]]

    total       = len(all_r)
    win_count   = len(wins)
    loss_count  = len(losses)
    win_rate    = win_count / total * 100 if total else 0.0
    avg_win     = sum(wins)   / len(wins)   if wins   else 0.0
    avg_loss    = sum(losses) / len(losses) if losses else 0.0
    expectancy  = (win_rate/100 * avg_win) + ((1 - win_rate/100) * avg_loss)
    net_r       = sum(all_r)

    # Swap quality: average R of trades that replaced a position
    swap_r_avg  = (sum(t["r"] for t in swaps) / len(swaps)) if swaps else None
    norm_r_avg  = (sum(t["r"] for t in non_swap) / len(non_swap)) if non_swap else None

    # ── Print report ──────────────────────────────────────────────────
    bar = "─" * 52
    print(f"\n{'═'*52}")
    print(f"  SESSION METRICS — {date_str}")
    print(f"{'═'*52}")
    print(f"  Trades (closed)    : {total}")
    print(f"  Swaps (REPLACEMENT): {len(swaps)}")
    print(f"{bar}")
    print(f"  Win rate           : {win_rate:.1f}%   ({win_count}W / {loss_count}L)")
    print(f"  Avg win  R         : {avg_win:+.3f}R")
    print(f"  Avg loss R         : {avg_loss:+.3f}R")
    print(f"  Expectancy         : {expectancy:+.4f}R  {'✅' if expectancy > 0 else '❌'}")
    print(f"  Net R this session : {net_r:+.3f}R")
    print(f"{bar}")
    if swap_r_avg is not None:
        print(f"  Swap trade avg R   : {swap_r_avg:+.3f}R  ({len(swaps)} trades)")
    if norm_r_avg is not None:
        print(f"  Normal trade avg R : {norm_r_avg:+.3f}R  ({len(non_swap)} trades)")
    if swap_r_avg is not None and norm_r_avg is not None:
        diff = swap_r_avg - norm_r_avg
        verdict = "✅ SWAPS HELPING" if diff > 0 else "⚠️  SWAPS HURTING"
        print(f"  Swap vs Normal Δ   : {diff:+.3f}R  → {verdict}")
    print(f"{'═'*52}\n")

    # Per-symbol breakdown
    by_symbol: dict[str, list] = defaultdict(list)
    for t in trades:
        by_symbol[t["symbol"]].append(t["r"])
    print("  Per-symbol summary:")
    for sym, rs in sorted(by_symbol.items()):
        wr = sum(1 for r in rs if r > 0) / len(rs) * 100
        print(f"    {sym:<14} trades={len(rs):2d}  net_R={sum(rs):+.2f}  wr={wr:.0f}%")
    print()


if __name__ == "__main__":
    date_arg = sys.argv[1] if len(sys.argv) > 1 else datetime.now().strftime("%Y-%m-%d")
    run(date_arg)
