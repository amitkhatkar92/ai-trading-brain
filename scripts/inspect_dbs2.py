import sqlite3, os, sys
ROOT = r"C:\Users\UCIC\OneDrive\Desktop\ai_trading_brain"
dbs = [
    "data/trade_quality.db", "data/rejection_audit.db",
    "data/real_options_audit.db", "data/live_observations.db",
    "data/trading_brain.db", "data/control_tower.db", "data/replay.db",
    "data/options_audit.db", "data/news_audit.db",
]
for db in dbs:
    path = os.path.join(ROOT, db)
    if not os.path.exists(path):
        print(f"MISSING {db}")
        continue
    c = sqlite3.connect(path)
    tables = [r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    for t in tables:
        n = c.execute(f"SELECT COUNT(*) FROM [{t}]").fetchone()[0]
        cols = [r[1] for r in c.execute(f"PRAGMA table_info([{t}])").fetchall()]
        time_cols = [x for x in cols if any(k in x.lower() for k in ("time","date","_at","traded","entry","ts","created","updated","closed"))]
        print(f"{os.path.basename(db)}::{t}  rows={n}  time_cols={time_cols}")
    c.close()
