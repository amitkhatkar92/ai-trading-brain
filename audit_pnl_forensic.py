"""Forensic P&L audit — reads paper_trades.csv and produces clean summary."""
import csv, os

CSV = "/app/data/paper_trades.csv"

trades = []
with open(CSV) as f:
    for row in csv.DictReader(f):
        trades.append(row)

open_t = {}   # order_id -> opening row
closed_pnl = []

for t in trades:
    oid = t["order_id"]
    ev  = t.get("event", "")
    if "OPEN" in ev and "REENTRY" not in ev and "CANCELLED" not in ev:
        open_t[oid] = t
    elif ev == "CLOSE":
        raw = t.get("pnl", "")
        try:
            pnl = float(raw)
        except (TypeError, ValueError):
            pnl = 0.0
        ep_raw = t.get("exit_price", "") or ""
        try:
            ep = float(ep_raw)
        except (TypeError, ValueError):
            ep = 0.0
        if abs(pnl) > 0.01:
            closed_pnl.append({
                "date":   t["timestamp"][:10],
                "symbol": t["symbol"],
                "dir":    t["direction"],
                "qty":    int(t["quantity"]),
                "entry":  float(t["entry_price"]),
                "exit":   ep,
                "pnl":    pnl,
                "reason": t["reason"],
            })
        if oid in open_t:
            del open_t[oid]

# ── Open positions ───────────────────────────────────────────────────────────
print("=" * 80)
print("OPEN POSITIONS")
print("=" * 80)
print(f"{'Date':<12} {'Symbol':<18} {'Dir':<6} {'Qty':>7} {'Entry':>10}")
print("-" * 60)
for oid, t in sorted(open_t.items(), key=lambda x: x[1]["timestamp"]):
    print(f"{t['timestamp'][:10]:<12} {t['symbol']:<18} {t['direction']:<6} "
          f"{int(t['quantity']):>7} {float(t['entry_price']):>10.2f}")

# ── Closed trades ────────────────────────────────────────────────────────────
print()
print("=" * 80)
print("CLOSED TRADES (non-zero P&L)")
print("=" * 80)
print(f"{'Date':<12} {'Symbol':<18} {'Dir':<6} {'Qty':>7} {'Entry':>9} {'Exit':>9} {'PnL':>12}  Reason")
print("-" * 100)

total_closed = 0.0
wins = 0
losses = 0
phantom_count = 0
phantom_pnl = 0.0

for r in sorted(closed_pnl, key=lambda x: x["date"]):
    tag = ""
    if any(k in r["reason"] for k in ("PHANTOM", "FALSE_SL", "CORRECTED", "SESSION_EXPIRED", "CLEANUP")):
        tag = " ⚠"
        phantom_count += 1
        phantom_pnl += r["pnl"]
    print(f"{r['date']:<12} {r['symbol']:<18} {r['dir']:<6} {r['qty']:>7} "
          f"{r['entry']:>9.2f} {r['exit']:>9.2f} {r['pnl']:>12.2f}  {r['reason'][:55]}{tag}")
    total_closed += r["pnl"]
    if r["pnl"] > 0:
        wins += 1
    else:
        losses += 1

print("-" * 100)
print(f"{'TOTAL CLOSED P&L':>70}  {total_closed:>12,.2f}")
print()
print(f"  Trades: {wins+losses}  |  Wins: {wins}  |  Losses: {losses}  |  "
      f"Win Rate: {100*wins/(wins+losses):.1f}%")
print()

# Separate phantom/bad exits from real results
real_pnl = total_closed - phantom_pnl
print(f"  ⚠  Flagged exits (PHANTOM/FALSE_SL/SESSION_EXPIRED/CLEANUP): {phantom_count}")
print(f"  ⚠  P&L from flagged exits: {phantom_pnl:,.2f}")
print(f"  ✅ Structural P&L (real exits only): {real_pnl:,.2f}")
print()

# Worst exits by size
print("=" * 80)
print("LARGEST LOSSES (top 10)")
print("=" * 80)
top_losses = sorted([r for r in closed_pnl if r["pnl"] < 0], key=lambda x: x["pnl"])[:10]
for r in top_losses:
    print(f"  {r['date']} {r['symbol']:<18} {r['dir']:<5} qty={r['qty']:>6} "
          f"entry={r['entry']:>9.2f} exit={r['exit']:>9.2f}  pnl={r['pnl']:>12,.2f}  {r['reason'][:50]}")

print()
print("=" * 80)
print("LARGEST WINS (top 10)")
print("=" * 80)
top_wins = sorted([r for r in closed_pnl if r["pnl"] > 0], key=lambda x: -x["pnl"])[:10]
for r in top_wins:
    print(f"  {r['date']} {r['symbol']:<18} {r['dir']:<5} qty={r['qty']:>6} "
          f"entry={r['entry']:>9.2f} exit={r['exit']:>9.2f}  pnl={r['pnl']:>12,.2f}  {r['reason'][:50]}")
