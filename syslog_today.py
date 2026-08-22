import sqlite3
conn = sqlite3.connect("/app/data/trading_brain.db")
rows = conn.execute("SELECT ts, level, component, event_type, message FROM system_logs WHERE ts LIKE '2026-05-29%' ORDER BY ts").fetchall()
print(f"Today's system log entries: {len(rows)}")
for r in rows:
    print(f"  {r[0][:16]}  {r[1][:5]:5}  {r[2][:14]:15}  {r[3][:22]:23}  {str(r[4])[:75]}")
conn.close()
