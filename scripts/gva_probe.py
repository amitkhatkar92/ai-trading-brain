"""One-shot probe to understand GVA-001 data sources."""
import json, sqlite3
from pathlib import Path

DATA = Path("data")

def js(p):
    try:
        return json.loads(p.read_text(encoding="utf-8", errors="replace"))
    except Exception as e:
        return f"ERROR: {e}"

def db_info(path):
    try:
        conn = sqlite3.connect(str(path))
        tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        info = {}
        for (t,) in tables:
            try:
                cols = [c[1] for c in conn.execute(f"PRAGMA table_info({t})").fetchall()]
                cnt = conn.execute(f"SELECT COUNT(*) FROM [{t}]").fetchone()[0]
                info[t] = {"cols": cols, "rows": cnt}
            except Exception as e:
                info[t] = {"error": str(e)}
        conn.close()
        return info
    except Exception as e:
        return {"error": str(e)}

# Study files
print("=== STUDY FILES ===")
for f in sorted(DATA.glob("study*.json")):
    d = js(f)
    if isinstance(d, dict):
        print(f"{f.name}: keys={list(d.keys())[:6]}")
    else:
        print(f"{f.name}: {d}")

print()
print("=== ARS STUDY FILES ===")
for f in sorted(DATA.glob("ars_study*.json")):
    d = js(f)
    if isinstance(d, dict):
        print(f"{f.name}: keys={list(d.keys())[:6]}")

print()
print("=== PAPER TRADING DAILY ===")
ptd = js(DATA / "paper_trading_daily.json")
if isinstance(ptd, dict):
    print(f"Keys: {list(ptd.keys())[:12]}")
    hist = ptd.get("history", [])
    print(f"History entries: {len(hist)}")
    if hist:
        print(f"First entry keys: {list(hist[0].keys())}")
        print(f"Last entry: {hist[-1]}")

print()
print("=== HYPOTHESIS REGISTRY ===")
reg = js(DATA / "ars_hypothesis_registry.json")
if isinstance(reg, dict):
    hyps = reg.get("hypotheses", {})
    print(f"Count: {len(hyps)}  type={type(hyps).__name__}")
    statuses = {}
    for hid, h in (hyps.items() if isinstance(hyps, dict) else enumerate(hyps)):
        s = h.get("status", "UNKNOWN") if isinstance(h, dict) else "?"
        statuses[s] = statuses.get(s, 0) + 1
    print(f"Status breakdown: {statuses}")

print()
print("=== DISCOVERED EDGES ===")
edges = js(DATA / "discovered_edges.json")
if isinstance(edges, dict):
    print(f"Total edge IDs: {len(edges)}")
    k = list(edges.keys())[0]
    print(f"Edge keys: {list(edges[k].keys())}")
    # Status breakdown
    statuses = {}
    for eid, e in edges.items():
        if isinstance(e, dict):
            s = e.get("status", "UNKNOWN")
            statuses[s] = statuses.get(s, 0) + 1
    print(f"Edge statuses: {statuses}")

print()
print("=== REPLAY SUMMARY ===")
rs = js(DATA / "replay_summary.json")
if isinstance(rs, dict):
    print(f"Keys: {list(rs.keys())[:10]}")

print()
print("=== IKN DB ===")
ikn = db_info(DATA / "ikn" / "ikn.db")
for t, info in ikn.items():
    if "error" in info:
        print(f"  {t}: {info}")
    else:
        print(f"  {t}: rows={info['rows']} cols={info['cols'][:6]}")

print()
print("=== INSTITUTIONAL DNA DB ===")
dna = db_info(DATA / "mls" / "institutional_dna.db")
for t, info in dna.items():
    if "error" in info:
        print(f"  {t}: {info}")
    else:
        print(f"  {t}: rows={info['rows']} cols={info['cols'][:8]}")

print()
print("=== CONTROL TOWER DB ===")
ct = db_info(DATA / "control_tower.db")
for t, info in ct.items():
    if "error" in info:
        print(f"  {t}: {info}")
    else:
        print(f"  {t}: rows={info['rows']} cols={info['cols'][:6]}")

print()
print("=== STRATEGY PERFORMANCE ===")
sp = js(DATA / "strategy_performance.json")
if isinstance(sp, dict):
    print(f"Keys: {list(sp.keys())[:10]}")
    strats = sp.get("strategies", sp)
    if isinstance(strats, dict):
        print(f"Strategies: {len(strats)}")
        if strats:
            k2 = list(strats.keys())[0]
            print(f"First strategy keys: {list(strats[k2].keys()) if isinstance(strats[k2], dict) else strats[k2]}")

print()
print("=== SCANNER MEMORY ===")
sm = js(DATA / "scanner_memory.json")
if isinstance(sm, dict):
    print(f"Keys: {list(sm.keys())[:10]}")
