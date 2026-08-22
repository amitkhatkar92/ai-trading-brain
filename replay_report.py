"""Quick replay report — run after historical_replay.py completes."""
import sqlite3, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

conn = sqlite3.connect("data/replay.db")
conn.row_factory = sqlite3.Row
SEP = "-" * 65

print(SEP)
print("HISTORICAL REPLAY -- PHASE C READINESS ESTIMATE")
print(SEP)

# ── C-Ready-1: signal births ──────────────────────────────────────────
n_signals = conn.execute("SELECT COUNT(*) FROM signal_births").fetchone()[0]
print(f"\nC-Ready-1  signal_births total: {n_signals}  (need>=100  {'READY' if n_signals >= 100 else 'NOT READY'})")
by_arch = conn.execute("""
    SELECT archetype_id, COUNT(*) AS n
    FROM signal_births GROUP BY archetype_id ORDER BY n DESC
""").fetchall()
total_days = conn.execute("SELECT COUNT(DISTINCT detected_at) FROM signal_births").fetchone()[0]
for r in by_arch:
    rate = r["n"] / total_days if total_days else 0
    print(f"  {r['archetype_id']:<42} {r['n']:>6} signals  ({rate:.1f}/day)")

# ── C-Ready-2: sector conviction ─────────────────────────────────────
print(f"\nC-Ready-2  FULL conviction rows per sector (need>=30 per sector):")
by_sec = conn.execute("""
    SELECT sector,
           SUM(CASE WHEN data_quality='FULL' THEN 1 ELSE 0 END) AS full_rows,
           COUNT(*) AS total_rows
    FROM sector_conviction_daily
    GROUP BY sector ORDER BY full_rows DESC
""").fetchall()
sectors_short = [r["sector"] for r in by_sec if r["full_rows"] < 30]
for r in by_sec:
    badge = "READY" if r["full_rows"] >= 30 else "SHORT"
    print(f"  [{badge}] {r['sector']:<22}  FULL={r['full_rows']:>4}  total={r['total_rows']}")
print(f"  -> {'READY' if not sectors_short else f'NOT READY ({len(sectors_short)} sectors below threshold)'}")

# ── C-Ready-3: theme phase history ───────────────────────────────────
n_tph = conn.execute("SELECT COUNT(*) FROM theme_phase_history").fetchone()[0]
print(f"\nC-Ready-3  theme_phase_history records: {n_tph}  (need>=5  {'READY' if n_tph >= 5 else 'NOT READY'})")
by_phase = conn.execute("""
    SELECT phase, COUNT(*) AS n FROM theme_phase_history
    GROUP BY phase ORDER BY n DESC
""").fetchall()
for r in by_phase:
    print(f"  {r['phase']:<15} {r['n']}")

# ── C-Ready-4: archetype firing rates ────────────────────────────────
BOUNDS = {
    "DNA_1A_MOMENTUM_CONT":     (1, 20),
    "DNA_1A_52W_HIGH_EXPAND":   (1, 15),
    "DNA_1A_SECTOR_BKT":        (1, 20),
    "DNA_1A_RESULTS_FOLLOWTHR": (0, 10),
    "DNA_1B_QUIET_ACCUMULATION":(2, 15),
    "DNA_1B_DELIVERY_EXPANSION":(1, 12),
    "DNA_1B_LOW_NOISE_STRENGTH":(1, 15),
    "DNA_1B_SECTOR_PRE_BKT":    (1, 20),
}
print(f"\nC-Ready-4  Archetype firing rates (over {total_days} trading days):")
out_of_bounds = []
for arch, (lo, hi) in BOUNDS.items():
    cnt = conn.execute("SELECT COUNT(*) FROM signal_births WHERE archetype_id=?", (arch,)).fetchone()[0]
    rate = cnt / total_days if total_days else 0
    in_bounds = lo <= rate <= hi
    badge = "OK " if in_bounds else "!! "
    if not in_bounds and cnt > 0:
        out_of_bounds.append(arch)
    never = " (NEVER FIRED)" if cnt == 0 else ""
    print(f"  [{badge}] {arch:<42} {rate:.1f}/day  expected [{lo}-{hi}]{never}")
print(f"  -> {'READY' if not out_of_bounds else f'NOT READY ({len(out_of_bounds)} out-of-bounds)'}")

# ── C-Ready-5: lifecycle diversity ───────────────────────────────────
print("\nC-Ready-5  Opportunity lifecycle:")
total_opps = conn.execute("SELECT COUNT(*) FROM opportunities").fetchone()[0]
states = conn.execute("""
    SELECT current_state, COUNT(*) AS n FROM opportunities
    GROUP BY current_state ORDER BY n DESC
""").fetchall()
for r in states:
    pct = r["n"] / total_opps * 100 if total_opps else 0
    bar = "#" * int(pct / 2)
    print(f"  {r['current_state']:<12}  {r['n']:>5}  ({pct:5.1f}%)  {bar}")
dominant = states[0]
dom_pct = dominant["n"] / total_opps * 100 if total_opps else 0
diversity_ok = len(states) >= 2 and dom_pct <= 90
print(f"  Total: {total_opps}   Dominant: {dominant['current_state']} {dom_pct:.1f}%")
print(f"  -> {'READY' if diversity_ok else 'NOT READY'}")

print("\nInvalidation reasons:")
inv_rows = conn.execute("""
    SELECT invalidation_reason, COUNT(*) AS n
    FROM opportunities WHERE invalidation_reason IS NOT NULL
    GROUP BY invalidation_reason ORDER BY n DESC
""").fetchall()
total_inv = sum(r["n"] for r in inv_rows)
for r in inv_rows:
    pct = r["n"] / total_inv * 100 if total_inv else 0
    print(f"  {r['invalidation_reason']:<30}  {r['n']:>5}  ({pct:.1f}%)")

# ── Merge quality ────────────────────────────────────────────────────
avg_sig = conn.execute("""
    SELECT AVG(n) FROM (
        SELECT COUNT(*) AS n FROM opportunity_signals GROUP BY opportunity_id
    )
""").fetchone()[0]
print(f"\nAvg signals per opportunity: {avg_sig:.2f}  (healthy range: 1.3-2.5)")

# ── Symbol concentration ─────────────────────────────────────────────
print("\nTop 10 symbols by signal count:")
top_syms = conn.execute("""
    SELECT symbol, COUNT(*) AS n FROM signal_births
    GROUP BY symbol ORDER BY n DESC LIMIT 10
""").fetchall()
for r in top_syms:
    pct = r["n"] / n_signals * 100 if n_signals else 0
    warn = "  <-- WARNING >15%" if pct > 15 else ""
    print(f"  {r['symbol']:<18}  {r['n']:>4}  ({pct:.1f}%){warn}")

# ── Sector distribution ───────────────────────────────────────────────
print("\nOpportunities by sector:")
sec_opps = conn.execute("""
    SELECT sector, COUNT(*) AS n FROM opportunities
    GROUP BY sector ORDER BY n DESC
""").fetchall()
for r in sec_opps:
    pct = r["n"] / total_opps * 100 if total_opps else 0
    bar = "#" * int(pct / 2)
    print(f"  {r['sector']:<22}  {r['n']:>4}  ({pct:4.1f}%)  {bar}")

# ── Summary ───────────────────────────────────────────────────────────
print()
print(SEP)
print("SUMMARY")
print(SEP)
gates = [
    ("C-Ready-1: signal_births >= 100",                  n_signals >= 100),
    ("C-Ready-2: all sectors 30+ FULL rows",             not sectors_short),
    ("C-Ready-3: theme_phase_history >= 5",              n_tph >= 5),
    ("C-Ready-4: archetypes in frequency bounds",        not out_of_bounds),
    ("C-Ready-5: lifecycle diversity",                   diversity_ok),
]
for label, ok in gates:
    print(f"  {'READY    ' if ok else 'NOT READY'}  {label}")
all_ready = all(ok for _, ok in gates)
print()
print(f"  -> {'PHASE C MAY BEGIN (replay evidence)' if all_ready else 'PHASE C BLOCKED on replay evidence'}")
print(f"     (live gates in check_phase_c_ready.py remain authoritative)")
print(SEP)

conn.close()
