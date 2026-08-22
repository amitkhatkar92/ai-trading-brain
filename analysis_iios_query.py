"""Query IIOS databases to explain top movers on 2026-08-07."""
import sqlite3, json, os
from pathlib import Path
from datetime import datetime, date, timedelta

ROOT   = Path(".")
CT_DB  = ROOT / "data/control_tower.db"
DNA_DB = ROOT / "data/mls/institutional_dna.db"
HYP_F  = ROOT / "data/ars_hypothesis_registry.json"
EDG_F  = ROOT / "data/discovered_edges.json"
TODAY  = "2026-08-07"

# ── Stock data from the CSVs ──────────────────────────────────────────────────
WINNERS = [
    ("TCS",        2433,  2.53),
    ("M&M",        3487,  2.38),
    ("GRASIM",     3264,  1.68),
    ("TATATECH",    877,  9.39),
    ("MOTHERSON",   168,  8.39),
]
LOSERS = [
    ("BAJFINANCE", 1086, -5.13),
    ("BAJAJFINSV", 1995, -4.34),
    ("TRENT",      3016, -2.94),
    ("IXIGO",       183, -9.82),
    ("CROMPTON",    252, -6.50),
]
ALL_SYM = {s for s, _, _ in WINNERS + LOSERS}

# ── Helper: query DB ──────────────────────────────────────────────────────────
def qdb(db_path, sql, params=()):
    if not Path(db_path).exists():
        return []
    with sqlite3.connect(db_path) as c:
        c.row_factory = sqlite3.Row
        try:
            return [dict(r) for r in c.execute(sql, params).fetchall()]
        except Exception as e:
            return [{"error": str(e)}]

# ── CT DB meta ────────────────────────────────────────────────────────────────
print("\n" + "="*70)
print("IIOS DATABASE OVERVIEW")
print("="*70)
tables = qdb(CT_DB, "SELECT name FROM sqlite_master WHERE type='table'")
for t in tables:
    name = t["name"]
    cnt  = qdb(CT_DB, f"SELECT COUNT(*) c FROM {name}")[0]["c"]
    try:
        mx = qdb(CT_DB, f"SELECT MAX(ts) m FROM {name}")[0]["m"]
    except:
        mx = "N/A"
    print(f"  {name:<30} {cnt:>8} rows   latest: {mx}")

# ── CT decisions: all time for our symbols ────────────────────────────────────
print("\n" + "="*70)
print("DECISION LOG (all time, focus symbols)")
print("="*70)
dec_rows = qdb(CT_DB, """
    SELECT d.symbol, d.direction, d.confidence, d.created_at,
           d.strategy, d.score, d.outcome
    FROM ct_decisions d
    WHERE d.symbol IN ('TCS','M&M','GRASIM','TATATECH','MOTHERSON',
                       'BAJFINANCE','BAJAJFINSV','TRENT','IXIGO','CROMPTON',
                       'TCS.NS','M&M.NS','GRASIM.NS','TATATECH.NS','MOTHERSON.NS',
                       'BAJFINANCE.NS','BAJAJFINSV.NS','TRENT.NS','IXIGO.NS','CROMPTON.NS')
    ORDER BY d.created_at DESC
    LIMIT 60
""")
if dec_rows and "error" not in dec_rows[0]:
    for r in dec_rows:
        print(f"  {r.get('created_at','')[:16]} | {r.get('symbol',''):14} | "
              f"{r.get('direction',''):5} | conf={r.get('confidence',''):5} | "
              f"score={r.get('score',''):5} | strategy={r.get('strategy','')[:30]} | "
              f"outcome={r.get('outcome','')}")
else:
    print("  No decisions found or schema differs:", dec_rows[:2] if dec_rows else "empty")
    # Try to see actual columns
    cols = qdb(CT_DB, "PRAGMA table_info(ct_decisions)")
    print("  ct_decisions columns:", [c["name"] for c in cols])

# ── CT events ────────────────────────────────────────────────────────────────
print("\n" + "="*70)
print("CT EVENTS (last 30 days, focus symbols)")
print("="*70)
evt_rows = qdb(CT_DB, """
    SELECT event_type, payload, ts
    FROM ct_events
    WHERE ts >= date('now','-30 days')
    ORDER BY ts DESC
    LIMIT 200
""")
hit_count = 0
for r in evt_rows:
    payload = r.get("payload","") or ""
    if any(s in payload for s in ALL_SYM):
        try:
            p = json.loads(payload)
        except:
            p = {}
        print(f"  {r['ts'][:16]} | {r['event_type'][:30]} | {str(p)[:130]}")
        hit_count += 1
        if hit_count >= 40:
            break
if hit_count == 0:
    print("  (no events for focus symbols in last 30 days)")

# ── DNA records ──────────────────────────────────────────────────────────────
print("\n" + "="*70)
print("INSTITUTIONAL DNA (focus symbols)")
print("="*70)
dna_rows = qdb(DNA_DB, """
    SELECT symbol, pattern_type, direction, confidence_score, status,
           supporting_instances, pattern_description, created_at
    FROM consensus_dna
    WHERE REPLACE(symbol,'.NS','') IN
      ('TCS','M&M','GRASIM','TATATECH','MOTHERSON',
       'BAJFINANCE','BAJAJFINSV','TRENT','IXIGO','CROMPTON')
    ORDER BY symbol, confidence_score DESC
""")
if dna_rows and "error" not in dna_rows[0]:
    for r in dna_rows:
        print(f"  {r.get('symbol',''):15} | {r.get('pattern_type',''):20} | "
              f"{r.get('direction',''):5} | conf={r.get('confidence_score',0):.2f} | "
              f"status={r.get('status',''):10} | instances={r.get('supporting_instances',0)} | "
              f"{str(r.get('pattern_description',''))[:60]}")
else:
    print("  No DNA found or schema differs:", dna_rows[:2] if dna_rows else "empty")
    cols = qdb(DNA_DB, "SELECT name FROM sqlite_master WHERE type='table'")
    print("  DNA DB tables:", [c["name"] for c in cols])

# ── ALL DNA for sectors these stocks belong to ────────────────────────────────
print("\n" + "="*70)
print("DNA COVERAGE (all symbols, count by status)")
print("="*70)
dna_summary = qdb(DNA_DB, """
    SELECT REPLACE(symbol,'.NS','') sym, status, COUNT(*) cnt,
           AVG(confidence_score) avg_conf
    FROM consensus_dna
    GROUP BY symbol, status
    ORDER BY cnt DESC
    LIMIT 30
""")
for r in dna_summary:
    print(f"  {r.get('sym',''):15} | {r.get('status',''):12} | {r.get('cnt',0):>4} records | "
          f"avg_conf={r.get('avg_conf',0):.3f}")

# ── Hypotheses ────────────────────────────────────────────────────────────────
print("\n" + "="*70)
print("ACTIVE HYPOTHESES (containing focus symbols)")
print("="*70)
if HYP_F.exists():
    with open(HYP_F) as f:
        hyp_data = json.load(f)
    hypotheses = hyp_data.get("hypotheses", []) if isinstance(hyp_data, dict) else hyp_data
    found = 0
    for h in hypotheses:
        if not isinstance(h, dict):
            continue
        title = h.get("title","") + " " + h.get("description","") + " " + str(h.get("tags",""))
        if any(s.upper() in title.upper() for s in ALL_SYM) or \
           h.get("status","") in ("CONFIRMED","PARTIALLY_CONFIRMED"):
            print(f"  [{h.get('status',''):20}] {h.get('hypothesis_id','')}: {h.get('title','')[:80]}")
            found += 1
    print(f"  Total hypotheses: {len(hypotheses)}, relevant shown: {found}")
else:
    print("  Hypothesis registry not found")

# ── Discovered edges ──────────────────────────────────────────────────────────
print("\n" + "="*70)
print("DISCOVERED EDGES (focus symbols)")
print("="*70)
if EDG_F.exists():
    with open(EDG_F) as f:
        edges = json.load(f)
    if isinstance(edges, list):
        found = 0
        for e in edges:
            edge_str = str(e)
            if any(s in edge_str for s in ALL_SYM):
                print(f"  {str(e)[:140]}")
                found += 1
                if found >= 20: break
        print(f"  Total edges: {len(edges)}, relevant shown: {found}")
    else:
        print("  Edges format:", type(edges))
else:
    print("  Edges file not found")

# ── IRP/HKAP study data ───────────────────────────────────────────────────────
print("\n" + "="*70)
print("HISTORICAL STUDY DATA (HKAP/IRP — recent reports)")
print("="*70)
irp_dir = ROOT / "data/irp002"
if irp_dir.exists():
    dates = sorted(irp_dir.iterdir(), reverse=True)[:5]
    for d in dates:
        print(f"  {d.name}/")
        for f in sorted(d.iterdir())[:8]:
            print(f"    {f.name} ({f.stat().st_size} bytes)")

# ── GVA latest ────────────────────────────────────────────────────────────────
print("\n" + "="*70)
print("GVA LATEST SCORES")
print("="*70)
gva_dir = ROOT / "data/gva"
if gva_dir.exists():
    dates = sorted(gva_dir.iterdir(), reverse=True)[:3]
    for d in dates:
        score_f = d / "OVERALL_GROWTH_SCORE.md"
        if score_f.exists():
            lines = score_f.read_text(encoding="utf-8", errors="replace").splitlines()[:15]
            print(f"\n  === {d.name} ===")
            for l in lines:
                print(f"  {l}")

print("\n" + "="*70)
print("QUERY COMPLETE")
print("="*70)
