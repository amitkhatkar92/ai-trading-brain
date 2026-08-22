import sqlite3
con = sqlite3.connect("data/study002_replay.db")

schema = con.execute("SELECT sql FROM sqlite_master WHERE name='opportunities'").fetchone()
print("Schema:", schema[0][:600] if schema else "N/A")

print()
schema2 = con.execute("SELECT sql FROM sqlite_master WHERE name='decision_log'").fetchone()
print("decision_log schema:", schema2[0][:600] if schema2 else "N/A")

# What strategy data is in the replay.json or other files?
from pathlib import Path
import json

rj = Path("data/replay_summary.json")
if rj.exists():
    d = json.loads(rj.read_text())
    print("\nreplay_summary.json keys:", list(d.keys())[:10])
    
rt = Path("data/replay_trades.json")
if rt.exists():
    d = json.loads(rt.read_text())
    print("replay_trades.json:", type(d).__name__, len(d) if isinstance(d, list) else list(d.keys())[:5])

con.close()
