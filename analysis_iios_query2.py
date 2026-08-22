"""Deep IIOS DNA and decision query with correct schema."""
import sqlite3, json
from pathlib import Path

ROOT   = Path(".")
CT_DB  = ROOT / "data/control_tower.db"
DNA_DB = ROOT / "data/mls/institutional_dna.db"
HYP_F  = ROOT / "data/ars_hypothesis_registry.json"
EDG_F  = ROOT / "data/discovered_edges.json"

ALL_SYM = ["TCS","M&M","GRASIM","TATATECH","MOTHERSON",
           "BAJFINANCE","BAJAJFINSV","TRENT","IXIGO","CROMPTON"]
NS_SYM  = [s + ".NS" for s in ALL_SYM] + ALL_SYM

def qdb(db_path, sql, params=()):
    if not Path(db_path).exists():
        return []
    with sqlite3.connect(db_path) as c:
        c.row_factory = sqlite3.Row
        try:
            return [dict(r) for r in c.execute(sql, params).fetchall()]
        except Exception as e:
            return [{"_error": str(e)}]

# ── 1. CT DECISIONS (all time) ────────────────────────────────────────────────
print("\n" + "="*70)
print("DECISIONS (all time, correct schema)")
print("="*70)
decs = qdb(CT_DB, """
    SELECT symbol, strategy, confidence, decision, rejection_reason,
           technical_score, risk_score, macro_score, sentiment_score,
           regime_score, ts
    FROM ct_decisions
    WHERE symbol IN (%s)
    ORDER BY ts DESC
    LIMIT 60
""" % ",".join("?" * len(NS_SYM)), NS_SYM)

if decs and "_error" not in decs[0]:
    for r in decs:
        sym    = r.get("symbol","").replace(".NS","")
        dec    = r.get("decision","")
        conf   = r.get("confidence","")
        rej    = r.get("rejection_reason","") or ""
        strat  = r.get("strategy","") or ""
        ts     = r.get("ts","")[:16]
        tsc    = r.get("technical_score","") or ""
        rsk    = r.get("risk_score","") or ""
        mscore = r.get("macro_score","") or ""
        print(f"  {ts} | {sym:14} | dec={dec:8} | conf={conf:5} | "
              f"tech={tsc:5} risk={rsk:5} macro={mscore:5} | "
              f"strategy={strat[:25]} | rej={rej[:50]}")
else:
    print("  ERROR or empty:", decs[:2])

print(f"  Total: {len(decs)} rows")

# ── 2. CT EVENTS — all time for focus symbols ────────────────────────────────
print("\n" + "="*70)
print("CT EVENTS (all time, focus symbols, latest 50)")
print("="*70)
evts = qdb(CT_DB, """
    SELECT event_type, payload, ts
    FROM ct_events
    ORDER BY ts DESC
    LIMIT 5000
""")
hits = 0
for r in evts:
    payload = r.get("payload","") or ""
    if any(s in payload for s in ALL_SYM):
        try:
            p = json.loads(payload)
        except:
            p = {}
        sym = p.get("symbol","") or p.get("ticker","") or ""
        print(f"  {r['ts'][:16]} | {r['event_type'][:28]:28} | sym={sym:12} | {str(p)[:100]}")
        hits += 1
        if hits >= 50:
            print("  ... (truncated at 50)")
            break
if hits == 0:
    print("  No events found for focus symbols in last 5000 events")

# ── 3. DNA with correct table name ────────────────────────────────────────────
print("\n" + "="*70)
print("DNA TABLE COLUMNS")
print("="*70)
cols = qdb(DNA_DB, "PRAGMA table_info(dna)")
print("  dna columns:", [c["name"] for c in cols])

print("\nDNA RECORDS (focus symbols)")
dna_recs = qdb(DNA_DB, """
    SELECT *
    FROM dna
    WHERE REPLACE(symbol,'.NS','') IN (%s)
    ORDER BY symbol
    LIMIT 50
""" % ",".join("?" * len(ALL_SYM)), ALL_SYM)
if dna_recs and "_error" not in dna_recs[0]:
    for r in dna_recs:
        print("  " + " | ".join(f"{k}={str(v)[:40]}" for k,v in r.items() if v is not None)[:180])
else:
    print("  " + str(dna_recs[:2]))

# ── 4. DNA summary — all symbols ─────────────────────────────────────────────
print("\n" + "="*70)
print("DNA TOP 30 BY SYMBOL (any status)")
print("="*70)
dna_sum = qdb(DNA_DB, """
    SELECT REPLACE(symbol,'.NS','') sym, COUNT(*) cnt, MAX(created_at) latest
    FROM dna GROUP BY symbol ORDER BY cnt DESC LIMIT 30
""")
for r in dna_sum:
    print(f"  {r.get('sym',''):20} {r.get('cnt',0):>5} records  latest={r.get('latest','')[:10]}")

# ── 5. HYPOTHESES ────────────────────────────────────────────────────────────
print("\n" + "="*70)
print("HYPOTHESIS REGISTRY (all 16)")
print("="*70)
if HYP_F.exists():
    with open(HYP_F, encoding="utf-8") as f:
        hyp_data = json.load(f)
    hypotheses = hyp_data.get("hypotheses", []) if isinstance(hyp_data, dict) else hyp_data
    for h in hypotheses:
        if not isinstance(h, dict):
            print(f"  Non-dict entry: {str(h)[:80]}")
            continue
        status = h.get("status","")
        hid    = h.get("hypothesis_id","")
        title  = h.get("title","") or h.get("description","")
        tags   = h.get("tags",[])
        print(f"  [{status:25}] {hid}: {title[:80]}")
        if tags:
            print(f"    tags: {tags}")

# ── 6. EDGES ─────────────────────────────────────────────────────────────────
print("\n" + "="*70)
print("DISCOVERED EDGES (structure)")
print("="*70)
if EDG_F.exists():
    with open(EDG_F, encoding="utf-8") as f:
        edges = json.load(f)
    if isinstance(edges, dict):
        print("  Top-level keys:", list(edges.keys())[:10])
        # Try to find sub-lists
        for k, v in edges.items():
            if isinstance(v, list):
                print(f"  [{k}]: {len(v)} items")
                for e in v[:3]:
                    print(f"    {str(e)[:120]}")
    elif isinstance(edges, list):
        print(f"  {len(edges)} edges total")
        for e in edges[:5]:
            print(f"  {str(e)[:120]}")

# ── 7. IRP SCIENTIFIC DIRECTOR ────────────────────────────────────────────────
print("\n" + "="*70)
print("IRP SCIENTIFIC DIRECTOR VERDICT (latest)")
print("="*70)
sd_f = ROOT / "data/irp002/2026-08-06/SCIENTIFIC_DIRECTOR_VERDICT.md"
if sd_f.exists():
    print(sd_f.read_text(encoding="utf-8", errors="replace"))

# ── 8. WINNER DNA REPORT ─────────────────────────────────────────────────────
print("\n" + "="*70)
print("WINNER DNA CROSS-YEAR REPORT (latest)")
print("="*70)
wd_f = ROOT / "data/irp002/2026-08-06/WINNER_DNA_CROSS_YEAR_REPORT.md"
if wd_f.exists():
    print(wd_f.read_text(encoding="utf-8", errors="replace"))

# ── 9. PGA reports ────────────────────────────────────────────────────────────
print("\n" + "="*70)
print("PGA ROOT CAUSE REPORT (latest)")
print("="*70)
pga_dir = ROOT / "data/pga"
if pga_dir.exists():
    dates = sorted(pga_dir.iterdir(), reverse=True)[:2]
    for d in dates:
        rcf = d / "ROOT_CAUSE_REPORT.md"
        if rcf.exists():
            print(f"\n--- {d.name} ---")
            print(rcf.read_text(encoding="utf-8", errors="replace")[:3000])
