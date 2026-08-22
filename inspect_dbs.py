import sqlite3
import json

# Inspect all SQLite databases
dbs = [
    '/root/ai-trading-brain/data/control_tower.db',
    '/root/ai-trading-brain/data/live_observations.db',
    '/root/ai-trading-brain/data/market_behavior.db',
    '/root/ai-trading-brain/data/phase_d_sft.db',
    '/root/ai-trading-brain/data/recommendations.db',
]

for db_path in dbs:
    try:
        con = sqlite3.connect(db_path)
        tables = con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        print(f"\n=== {db_path.split('/')[-1]} ===")
        print(f"Tables: {[t[0] for t in tables]}")
        for t in tables:
            try:
                cols = con.execute(f"PRAGMA table_info({t[0]})").fetchall()
                cnt = con.execute(f"SELECT COUNT(*) FROM {t[0]}").fetchone()[0]
                print(f"  {t[0]}: rows={cnt}  cols={[c[1] for c in cols]}")
                if cnt > 0:
                    row = con.execute(f"SELECT * FROM {t[0]} LIMIT 1").fetchone()
                    print(f"    sample: {str(row)[:200]}")
            except Exception as e:
                print(f"  {t[0]}: ERROR {e}")
        con.close()
    except Exception as e:
        print(f"{db_path}: ERROR {e}")

# Also check paper_trades.csv
import os
csv_path = '/root/ai-trading-brain/data/paper_trades.csv'
if os.path.exists(csv_path):
    with open(csv_path) as f:
        lines = f.readlines()
    print(f"\n=== paper_trades.csv ===")
    print(f"Lines: {len(lines)}")
    print(f"Header: {lines[0].strip()}")
    if len(lines) > 1:
        print(f"Sample: {lines[1].strip()}")
        print(f"Latest: {lines[-1].strip()}")
