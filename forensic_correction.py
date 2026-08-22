"""
Forensic correction script — adds nullifying entries to paper_trades.csv
for phantom / duplicate closes.

Phantoms identified today (2026-05-29):
  1. COALINDIA PHANTOM_PRICE_CORRECTION  pnl=-400,752.45  (entry 1000.05 is stale P1 base_ltp; real COALINDIA ~465)
  2. ICICIBANK duplicate CLOSE             pnl=-14,774.00   (same order closed twice in legacy-orphan cleanup)
"""
import csv, os, datetime

CSV = "/app/data/paper_trades.csv"
BACKUP = "/app/data/paper_trades_backup_20260529.csv"

# ── Backup first ──────────────────────────────────────────────────────────────
import shutil
shutil.copy2(CSV, BACKUP)
print(f"Backup saved: {BACKUP}")

# ── Build current cumulative PnL before corrections ────────────────────────────
rows = []
with open(CSV) as f:
    reader = csv.DictReader(f)
    fieldnames = reader.fieldnames
    for row in reader:
        rows.append(row)

# Sum all non-zero CLOSE P&L
total_before = 0.0
for r in rows:
    if r.get("event") == "CLOSE":
        try:
            total_before += float(r["pnl"])
        except (TypeError, ValueError):
            pass

print(f"\nTotal P&L before corrections: {total_before:,.2f}")

# ── Correction 1: Nullify COALINDIA phantom trade ─────────────────────────────
# order id: SIM_COALINDIA_BUY_Q749_P1001.15_1780031205127
# Phantom: entry 1000.05 (stale P1 base_ltp), exit 465.0, pnl=-400,752.45
# The position never existed at 1000.05 — COALINDIA traded ~465 on May 29
coalindia_correction = {
    "timestamp":   "2026-05-29 11:10:01",
    "order_id":    "SIM_COALINDIA_BUY_Q749_P1001.15_1780031205127",
    "symbol":      "COALINDIA",
    "direction":   "BUY",
    "quantity":    "749",
    "entry_price": "1000.05",
    "stop_loss":   "983.61",
    "target":      "1041.15",
    "strategy":    "Trend_Pullback",
    "confidence":  "9.01",
    "rr":          "2.5",
    "event":       "CLOSE",
    "exit_price":  "1000.05",
    "pnl":         "400752.45",
    "reason":      "PHANTOM_VOID(stale_P1_base_ltp=1001.15;real_COALINDIA_was_465;phantom_entry_negated)",
}

# ── Correction 2: Nullify duplicate ICICIBANK close ───────────────────────────
# order id: SIM_ICICIBANK_BUY_178
# Same position closed twice at 17:01:43 and 17:13:02 — the second is duplicate
icicibank_correction = {
    "timestamp":   "2026-05-13 17:13:03",
    "order_id":    "SIM_ICICIBANK_BUY_178",
    "symbol":      "ICICIBANK",
    "direction":   "BUY",
    "quantity":    "178",
    "entry_price": "1318.60",
    "stop_loss":   "1294.60",
    "target":      "1378.60",
    "strategy":    "Mean_Reversion",
    "confidence":  "9.64",
    "rr":          "2.5",
    "event":       "CLOSE",
    "exit_price":  "1235.60",
    "pnl":         "14774.00",
    "reason":      "DUPLICATE_VOID(second_orphan_close_at_17:13:02_nullified;original_17:01:43_retained)",
}

# ── Append corrections ────────────────────────────────────────────────────────
with open(CSV, "a", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writerow(coalindia_correction)
    writer.writerow(icicibank_correction)

print("Correction rows appended to CSV.")

# ── Recompute total ───────────────────────────────────────────────────────────
total_after = 0.0
with open(CSV) as f:
    for row in csv.DictReader(f):
        if row.get("event") == "CLOSE":
            try:
                total_after += float(row["pnl"])
            except (TypeError, ValueError):
                pass

print(f"Total P&L after  corrections: {total_after:,.2f}")
print(f"Correction applied: {total_after - total_before:+,.2f}")
print()

# ── Print corrected summary ───────────────────────────────────────────────────
closed_pnl = []
with open(CSV) as f:
    for row in csv.DictReader(f):
        if row.get("event") == "CLOSE":
            try:
                pnl = float(row["pnl"])
            except (TypeError, ValueError):
                pnl = 0.0
            if abs(pnl) > 0.01:
                closed_pnl.append({
                    "date":   row["timestamp"][:10],
                    "symbol": row["symbol"],
                    "dir":    row["direction"],
                    "qty":    int(row["quantity"]),
                    "entry":  float(row["entry_price"]),
                    "exit":   float(row.get("exit_price","0") or "0"),
                    "pnl":    pnl,
                    "reason": row["reason"],
                })

print("=" * 80)
print("CORRECTED P&L SUMMARY — paper_trades.csv")
print("=" * 80)
phantom_tags = ("PHANTOM", "FALSE_SL", "VOID", "CORRECTED", "CLEANUP", "SESSION_EXPIRED", "ORPHAN")

phantom_total = 0.0
real_total    = 0.0
all_total     = 0.0

for r in sorted(closed_pnl, key=lambda x: x["date"]):
    is_flagged = any(k in r["reason"] for k in phantom_tags)
    flag = " ⚠" if is_flagged else ""
    all_total += r["pnl"]
    if is_flagged:
        phantom_total += r["pnl"]
    else:
        real_total += r["pnl"]
    print(f"  {r['date']} {r['symbol']:<18} {r['dir']:<5} qty={r['qty']:>6} "
          f"entry={r['entry']:>9.2f} exit={r['exit']:>9.2f}  pnl={r['pnl']:>12,.2f}{flag}")

print()
print(f"  {'─'*70}")
print(f"  TOTAL CLOSED P&L (all rows):         {all_total:>12,.2f}")
print(f"  Of which — flagged exits (SESSION/PHANTOM/VOID):  {phantom_total:>12,.2f}")
print(f"  STRUCTURAL P&L (real exits only):    {real_total:>12,.2f}")
print()
print("  ─── FORENSIC VERDICT ───────────────────────────────────────────────")
print(f"  Reported P&L (before correction):    {total_before:>12,.2f}")
print(f"  COALINDIA phantom void:              {400752.45:>12,.2f}")
print(f"  ICICIBANK duplicate void:            {14774.00:>12,.2f}")
print(f"  TRUE CORRECTED CLOSED P&L:           {total_after:>12,.2f}")
print()
print("  KEY FINDINGS:")
print("  1. COALINDIA entry at 1000.05 is impossible (stale P1 base_ltp=1001.15).")
print("     Real COALINDIA was ~465 on May 29. Phantom loss of -400,752 voided.")
print("  2. ICICIBANK SIM_ICICIBANK_BUY_178 was closed twice (17:01 and 17:13).")
print("     Duplicate close of -14,774 voided. Real loss: -14,774 (retained).")
print("  3. LT/ADANIENT/TECHM: stale base_ltp flagged in P1 monitoring but no")
print("     open positions → no CSV P&L impact from those symbols.")
print("  4. HINDALCO: two previous phantom corrections already applied correctly.")
print()
print("  The system shows ~-10 lakh. TRUE figure is ~-5.88 lakh.")
print("  Main driver of real losses: TATASTEEL stop-hit cluster May 18 (-189k)")
print("  and RELIANCE momentum-retest exits May 12-13 (-314k).")
