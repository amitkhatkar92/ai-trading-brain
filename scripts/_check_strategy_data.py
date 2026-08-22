import sqlite3, json
from pathlib import Path

con = sqlite3.connect("data/study002_replay.db")

# Tables
tbls = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
print("Tables:", tbls)

# Evolved strategies JSON
es = json.loads(Path("data/evolved_strategies.json").read_text())
print("\nevolved_strategies.json keys:", list(es.keys())[:10])
if isinstance(es, list):
    print("  is list, len:", len(es))
    print("  first item keys:", list(es[0].keys()) if es else "empty")
elif isinstance(es, dict):
    for k, v in list(es.items())[:3]:
        print(f"  {k}: {type(v).__name__}")

# Strategy performance JSON
sp = json.loads(Path("data/strategy_performance.json").read_text())
print("\nstrategy_performance.json type:", type(sp).__name__)
if isinstance(sp, dict):
    print("  keys:", list(sp.keys())[:5])
if isinstance(sp, list):
    print("  len:", len(sp), "first:", sp[0] if sp else "")

con.close()
