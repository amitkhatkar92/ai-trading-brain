import json, os
from datetime import datetime

with open("/app/data/daily_candidates.json") as f:
    d = json.load(f)

print(f"Type: {type(d).__name__}  top_keys={list(d.keys())[:8] if isinstance(d,dict) else 'list'}")

# Handle dict with meta+candidates structure
if isinstance(d, dict):
    m = d.get("meta", {})
    candidates = d.get("candidates", [])
    if not candidates:
        # might be keyed differently
        for k, v in d.items():
            if isinstance(v, list) and v and isinstance(v[0], dict):
                candidates = v
                break
    print(f"Meta: {m}")
    print(f"Candidates count: {len(candidates)}")
    if candidates:
        print(f"Sample keys: {list(candidates[0].keys())}")
        def get_score(x):
            return float(x.get("confidence", x.get("score", x.get("composite_score", 0))) or 0)
        top = sorted(candidates, key=get_score, reverse=True)[:10]
        print("Top 10:")
        for c in top:
            sym = c.get("symbol", c.get("ticker", "?"))
            sc = get_score(c)
            strat = c.get("strategy", c.get("setup", "?"))
            print(f"  {sym:15} score={sc:.3f}  strategy={strat}")
elif isinstance(d, list):
    print(f"List len: {len(d)}")
    if d:
        print(f"Sample keys: {list(d[0].keys()) if isinstance(d[0],dict) else type(d[0])}")
        def get_score(x):
            return float(x.get("confidence", x.get("score", x.get("composite_score", 0))) or 0) if isinstance(x,dict) else 0
        top = sorted(d, key=get_score, reverse=True)[:10]
        print("Top 10:")
        for c in top:
            if isinstance(c, dict):
                sym = c.get("symbol", c.get("ticker", "?"))
                sc = get_score(c)
                strat = c.get("strategy", c.get("setup", "?"))
                print(f"  {sym:15} score={sc:.3f}  strategy={strat}")
            else:
                print(f"  {c}")

# Also check universe age and sr_levels
print()
for fp in ["/app/data/nifty500_universe.json", "/app/data/sr_levels.json"]:
    if os.path.exists(fp):
        mtime = datetime.fromtimestamp(os.path.getmtime(fp))
        age_h = (datetime.now() - mtime).total_seconds() / 3600
        print(f"{os.path.basename(fp)}: age={age_h:.1f}h")
    else:
        print(f"{os.path.basename(fp)}: NOT FOUND")

# Dummy to satisfy old code
for s in []:
    print(f"  {s.get('symbol','?'):<14} score={s.get('score','?')}  ltp={s.get('ltp','?')}  setup={s.get('setup','?')}")
