import json
with open("/app/data/daily_candidates.json") as f:
    d = json.load(f)

if isinstance(d, dict):
    meta = d.get("meta", d.get("scanner_meta", {}))
    cands = d.get("candidates", d.get("prepared", []))
    if not cands:
        cands = [v for k, v in d.items() if isinstance(v, dict) and "symbol" in v]
else:
    meta = {}
    cands = d

print("Meta:", json.dumps(meta, indent=2))
print(f"Candidates: {len(cands)}")
for c in cands[:15]:
    sym = c.get("symbol", "?")
    score = c.get("score", c.get("quality_score", "?"))
    ltp = c.get("ltp", c.get("base_ltp", "?"))
    setup = c.get("setup", c.get("setup_type", "?"))
    print(f"  {sym:<14} ltp={ltp}  score={score}  setup={setup}")
