"""SQLite signals and system logs for today."""
import sqlite3, sys
sys.path.insert(0, "/app")
conn = sqlite3.connect("/app/data/trading_brain.db")
conn.row_factory = sqlite3.Row

print("SIGNALS TODAY")
sigs = conn.execute("SELECT * FROM signals WHERE timestamp LIKE '2026-05-29%' ORDER BY timestamp").fetchall()
print(f"  Count: {len(sigs)}")
for s in sigs[:15]:
    d = dict(s)
    print(f"  {str(d.get('timestamp',''))[:16]}  {d.get('symbol','?'):12}  {d.get('direction','?'):5}"
          f"  conf={d.get('confidence','?')}  strat={str(d.get('strategy','?'))[:22]:23}"
          f"  decision={d.get('decision','?')}")

print("\nSYSTEM LOGS TODAY (latest 12)")
logs = conn.execute("SELECT * FROM system_logs WHERE timestamp LIKE '2026-05-29%' ORDER BY timestamp DESC LIMIT 12").fetchall()
print(f"  Count: {len(logs)}")
for l in logs:
    d = dict(l)
    print(f"  {str(d.get('timestamp',''))[:16]}  {str(d.get('level','?')):8}  {str(d.get('message',''))[:90]}")

print("\nSTRATEGIES TABLE")
strats = conn.execute("SELECT * FROM strategies ORDER BY win_rate DESC LIMIT 10").fetchall()
for s in strats:
    d = dict(s)
    print(f"  {str(d.get('name','?'))[:35]:36}  trades={d.get('trades',d.get('total_trades','?'))}  wr={d.get('win_rate','?')}")

conn.close()
print("\nDONE")
