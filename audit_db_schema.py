#!/usr/bin/env python3
import sqlite3, sys

for db_path, label in [('/tmp/ct.db', 'control_tower'), ('/tmp/tb.db', 'trading_brain')]:
    try:
        c = sqlite3.connect(db_path)
        tables = [r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")]
        print(f"\n=== {label}: {tables}")
        for t in tables:
            try:
                cols = [r[1] for r in c.execute(f"PRAGMA table_info({t})")]
                count = c.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
                print(f"  {t}: {count} rows | cols: {cols}")
            except Exception as e:
                print(f"  {t}: error {e}")
        c.close()
    except Exception as e:
        print(f"{label}: {e}")
