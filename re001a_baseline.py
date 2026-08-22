"""RE001A baseline snapshot — run before any pipeline step."""
import json, os

def show(label, data):
    print(f"\n=== {label} ===")

# discovered_edges
with open("data/discovered_edges.json") as f:
    edges = json.load(f)
show("discovered_edges.json BASELINE", edges)
print(f"  Total edges: {len(edges)}")
for k, v in edges.items():
    st = v.get("status", "?")
    cf = v.get("confidence", "?")
    tc = v.get("trade_count", "?")
    print(f"  {k}: status={st} confidence={cf} trades={tc}")

# ede_feature_db
with open("data/ede_feature_db.json") as f:
    feat = json.load(f)
show("ede_feature_db.json BASELINE", feat)
print(f"  Total records: {len(feat)}")
if feat:
    print(f"  Sample keys: {list(feat[0].keys())[:10]}")
    syms = set(r.get("symbol", "") for r in feat)
    dates = set(r.get("date", r.get("trade_date", "")) for r in feat)
    print(f"  Unique symbols: {len(syms)}")
    print(f"  Unique dates: {len(dates)}")
    labeled = sum(1 for r in feat if r.get("outcome") is not None or r.get("label") is not None)
    print(f"  Labelled records: {labeled}")

# evolved_strategies
with open("data/evolved_strategies.json") as f:
    strats = json.load(f)
show("evolved_strategies.json BASELINE", strats)
print(f"  Total strategies: {len(strats)}")
for k in strats:
    print(f"  {k}")

# strategy_performance
with open("data/strategy_performance.json") as f:
    sp = json.load(f)
show("strategy_performance.json BASELINE", sp)
print(f"  Total tracked: {len(sp)}")
for k, v in sp.items():
    trades = v.get("total_trades", 0)
    wr = v.get("win_rate", 0)
    print(f"  {k}: trades={trades} win_rate={wr:.3f}")

print("\nDone.")
