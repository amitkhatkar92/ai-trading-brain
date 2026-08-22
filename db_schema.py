"""DB schema inspector."""
import sqlite3
conn = sqlite3.connect("/app/data/trading_brain.db")
for (tname,) in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall():
    cols = [c[1] for c in conn.execute(f"PRAGMA table_info({tname})").fetchall()]
    count = conn.execute(f"SELECT COUNT(*) FROM {tname}").fetchone()[0]
    print(f"{tname}: {count} rows  cols={cols}")
    # Show today's rows
    date_cols = [c for c in cols if "time" in c.lower() or "date" in c.lower() or "ts" in c.lower() or c == "created_at"]
    if date_cols:
        dc = date_cols[0]
        rows = conn.execute(f"SELECT * FROM {tname} WHERE {dc} LIKE '2026-05-29%' LIMIT 5").fetchall()
        if rows:
            print(f"  Today's rows ({len(rows)}):")
            for r in rows:
                print(f"    {str(dict(zip(cols, r)))[:150]}")
conn.close()
