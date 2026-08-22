"""Final deep IIOS evidence query."""
import json, sqlite3
from pathlib import Path

# EDGES
with open("data/discovered_edges.json", encoding="utf-8") as f:
    edges = json.load(f)
print("=== EDGES ===")
for eid, e in list(edges.items()):
    sc = e.get("score") or e.get("edge_score") or e.get("composite_score") or ""
    cat = e.get("category","")
    desc = e.get("description","") or e.get("name","") or ""
    print(f"  {eid}: score={sc} cat={cat} | {str(e)[:160]}")

# DNA SAMPLE
db = sqlite3.connect("data/mls/institutional_dna.db")
db.row_factory = sqlite3.Row
rows = db.execute("SELECT * FROM dna LIMIT 3").fetchall()
print("\n=== DNA SAMPLE (3 rows) ===")
for r in rows:
    d = dict(r)
    print("  " + str({k: str(v)[:35] for k, v in d.items() if v is not None}))

print("\n=== DNA BY LIFECYCLE ===")
for r in db.execute("SELECT lifecycle, COUNT(*) cnt, AVG(confidence) ac FROM dna GROUP BY lifecycle"):
    print(f"  lifecycle={r[0]}  cnt={r[1]}  avg_conf={r[2]:.3f}")

print("\n=== DNA TOP FEATURES ===")
for r in db.execute("SELECT feature_name, COUNT(*) cnt FROM dna GROUP BY feature_name ORDER BY cnt DESC LIMIT 12"):
    print(f"  feature={r[0]}  cnt={r[1]}")

print("\n=== DNA BY CATEGORY ===")
for r in db.execute("SELECT category, COUNT(*) cnt, AVG(confidence) ac FROM dna GROUP BY category ORDER BY cnt DESC"):
    print(f"  cat={r[0]}  cnt={r[1]}  avg_conf={r[2]:.3f}")

print("\n=== DNA BY DIRECTION ===")
for r in db.execute("SELECT direction, COUNT(*) cnt FROM dna GROUP BY direction ORDER BY cnt DESC"):
    print(f"  dir={r[0]}  cnt={r[1]}")

# DNA metadata column
print("\n=== DNA METADATA SAMPLE ===")
for r in db.execute("SELECT feature_name, direction, confidence, metadata FROM dna WHERE metadata IS NOT NULL LIMIT 5"):
    meta = r["metadata"] or ""
    try:
        m = json.loads(meta)
    except:
        m = meta
    print(f"  {r['feature_name']} {r['direction']} conf={r['confidence']:.3f} meta={str(m)[:120]}")

# CT decisions
db2 = sqlite3.connect("data/control_tower.db")
db2.row_factory = sqlite3.Row
print("\n=== DECISIONS BY SYMBOL (all time) ===")
for r in db2.execute("""
    SELECT symbol, COUNT(*) c, AVG(confidence) avg_conf,
           SUM(CASE WHEN decision='APPROVED' THEN 1 ELSE 0 END) approved,
           SUM(CASE WHEN decision='REJECTED' THEN 1 ELSE 0 END) rejected
    FROM ct_decisions
    GROUP BY symbol ORDER BY c DESC LIMIT 30
"""):
    print(f"  {r['symbol']:15} total={r['c']:>4} approved={r['approved']:>3} rejected={r['rejected']:>3} avg_conf={r['avg_conf']:.2f}")

# Paper trades for our focus stocks
print("\n=== PAPER TRADES (focus symbols) ===")
import csv
focus = {"TCS","M&M","GRASIM","TATATECH","MOTHERSON","BAJFINANCE","BAJAJFINSV","TRENT","IXIGO","CROMPTON"}
pt_path = Path("data/paper_trades.csv")
if pt_path.exists():
    with open(pt_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            sym = row.get("symbol","").replace(".NS","")
            if sym in focus:
                print(f"  {row.get('timestamp','')[:16]} | {sym:12} | {row.get('event',''):8} | "
                      f"strategy={row.get('strategy',''):20} | price={row.get('price',''):8} | "
                      f"pnl={row.get('pnl','')}")
else:
    print("  paper_trades.csv not found")

# CT events full payload for BAJFINANCE (most active)
print("\n=== BAJFINANCE EVENTS (detailed, last 5) ===")
evts = db2.execute("""
    SELECT event_type, payload, ts FROM ct_events
    WHERE payload LIKE '%BAJFINANCE%'
    ORDER BY ts DESC LIMIT 5
""").fetchall()
for e in evts:
    try:
        p = json.loads(e["payload"] or "{}")
    except:
        p = {}
    print(f"  {e['ts'][:16]} | {e['event_type']} | {json.dumps(p, default=str)[:200]}")
