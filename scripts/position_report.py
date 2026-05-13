"""
Position & PnL summary — clean view only.
Shows: current OPEN positions, and closed trades by ledger.
"""
import sys, csv
from collections import defaultdict

sys.path.insert(0, "/app")
CSV = "/app/data/paper_trades.csv"

SKIP_REASONS = {"emergency_close", "REPLACEMENT", "DUPLICATE_CLEANUP", "SESSION_EXPIRED_ZERO"}

# Parse all rows
rows = []
with open(CSV, "r") as f:
    reader = csv.reader(f)
    header = next(reader)
    for r in reader:
        rows.append(r)

# Track open/close per order_id
opens  = {}   # order_id -> row
closes = {}   # order_id -> row

for r in rows:
    if len(r) < 12:
        continue
    oid = r[1]
    # OPEN row: event col (index 11) == "OPEN"
    if r[11] == "OPEN":
        opens[oid] = r
    # CLOSE row: event col (index 11) == "CLOSE"
    elif r[11] == "CLOSE":
        closes[oid] = r

# Current open = opened but not yet closed
open_positions = {oid: r for oid, r in opens.items() if oid not in closes}

# ── OPEN POSITIONS ────────────────────────────────────────────────────────────
print("=" * 70)
print("  OPEN POSITIONS (live, as of now)")
print("=" * 70)
if not open_positions:
    print("  None — all positions are closed.")
else:
    for oid, r in open_positions.items():
        date     = r[0][:10]
        symbol   = r[2]
        side     = r[3]
        qty      = r[4]
        entry    = float(r[5])
        sl       = float(r[6])
        tgt      = float(r[7])
        strategy = r[8] if len(r) > 8 else "?"
        score    = r[9] if len(r) > 9 else "?"
        rr_val   = r[10] if len(r) > 10 else "?"
        print(f"  {symbol:12s} {side:5s}  qty={qty:>6s}  entry=₹{entry:>9.2f}  "
              f"SL=₹{sl:>8.2f}  tgt=₹{tgt:>9.2f}")
        print(f"    strategy={strategy}  score={score}  R:R={rr_val}  opened={date}")

# ── CLOSED TRADES BY LEDGER ───────────────────────────────────────────────────
print()
print("=" * 70)
print("  CLOSED TRADES SUMMARY")
print("=" * 70)

# Group by ledger
LEDGER_A_END = "2026-04-26"
BASELINE     = "2026-04-27"

ledger_a, ledger_b, infra = [], [], []

for oid, r in closes.items():
    close_date = r[0][:10]
    reason     = r[14] if len(r) > 14 else ""
    pnl        = float(r[13]) if len(r) > 13 and r[13] else 0.0
    symbol     = r[2]
    side       = r[3]
    qty        = r[4]
    entry      = float(r[5]) if r[5] else 0.0
    exit_p     = float(r[12]) if len(r) > 12 and r[12] else 0.0
    strategy   = r[8]

    row_str = (f"  {close_date}  {symbol:12s} {side:5s}  qty={qty:>6s}  "
               f"entry=₹{entry:>8.2f}  exit=₹{exit_p:>8.2f}  "
               f"PnL=₹{pnl:>+12,.2f}  [{reason}]")

    if reason in ("SYSTEM_CLEANUP",):
        infra.append((pnl, row_str))
    elif close_date >= BASELINE:
        ledger_b.append((pnl, row_str))
    elif pnl == 0.0 and reason in ("emergency_close",):
        pass  # skip ₹0 engineering-era noise
    else:
        ledger_a.append((pnl, row_str))

# Ledger B — Official (Apr 27+)
print()
print("  ── LEDGER B: Official Evaluation (Apr 27 onward) ──────────────────")
if ledger_b:
    for pnl, s in ledger_b:
        print(s)
    b_total = sum(p for p, _ in ledger_b)
    b_wins  = sum(1 for p, _ in ledger_b if p > 0)
    b_loss  = sum(1 for p, _ in ledger_b if p < 0)
    print(f"\n  Trades: {len(ledger_b)}  |  Wins: {b_wins}  Losses: {b_loss}  "
          f"|  Net PnL: ₹{b_total:+,.2f}")
else:
    print("  No official closed trades yet today.")

# Infrastructure cleanup
print()
print("  ── SYSTEM_CLEANUP (infrastructure only, excluded from evaluation) ──")
if infra:
    for pnl, s in infra:
        print(s)
    i_total = sum(p for p, _ in infra)
    print(f"\n  Count: {len(infra)}  |  Net PnL: ₹{i_total:+,.2f}  (NOT counted in strategy evaluation)")
else:
    print("  None.")

# Ledger A summary only
a_real = [(p, s) for p, s in ledger_a if p != 0.0]
print()
print(f"  ── LEDGER A: Engineering Era (pre Apr 27) ──────────────────────────")
print(f"  {len(a_real)} non-zero trades (archive — excluded from strategy evaluation)")
if a_real:
    a_total = sum(p for p, _ in a_real)
    a_wins  = sum(1 for p, _ in a_real if p > 0)
    a_loss  = sum(1 for p, _ in a_real if p < 0)
    print(f"  Net: ₹{a_total:+,.2f}  |  Wins: {a_wins}  Losses: {a_loss}")

print()
print("=" * 70)
