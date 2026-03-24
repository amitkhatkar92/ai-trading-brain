"""VPS health check — run on VPS to see dashboard DB contents."""
import sqlite3, os, json
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB   = os.path.join(ROOT, "data", "control_tower.db")
CSV  = os.path.join(ROOT, "data", "paper_trades.csv")

print("=== CONTROL TOWER DB ===")
conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
c = conn.cursor()
c.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [r[0] for r in c.fetchall()]
print("Tables:", tables)

for tbl in tables:
    c.execute(f"SELECT COUNT(*) FROM {tbl}")
    cnt = c.fetchone()[0]
    print(f"  {tbl}: {cnt} rows")

print("\n=== LAST 3 CYCLES ===")
try:
    c.execute("SELECT * FROM ct_cycles ORDER BY id DESC LIMIT 3")
    for r in c.fetchall():
        print(dict(r))
except Exception as e:
    print(f"  (no ct_cycles: {e})")

print("\n=== LAST 5 EVENTS ===")
try:
    c.execute("SELECT ts, event_type, source_agent FROM ct_events ORDER BY id DESC LIMIT 5")
    for r in c.fetchall():
        print(dict(r))
except Exception as e:
    print(f"  (no ct_events: {e})")

print("\n=== PAPER TRADES CSV ===")
if os.path.exists(CSV):
    with open(CSV) as f:
        lines = f.readlines()
    print(f"  {len(lines)-1} trades logged")
    if len(lines) > 1:
        print("  Last 3 lines:")
        for ln in lines[-3:]:
            print("   ", ln.strip())
else:
    print("  No paper_trades.csv yet")
