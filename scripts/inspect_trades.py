import sqlite3, os
ROOT = r"C:\Users\UCIC\OneDrive\Desktop\ai_trading_brain"

# Check trading_brain.db::trades schema + sample
c = sqlite3.connect(os.path.join(ROOT, "data/trading_brain.db"))
cols = [r[1] for r in c.execute("PRAGMA table_info(trades)").fetchall()]
print("trades cols:", cols)
rows = c.execute("SELECT * FROM trades LIMIT 5").fetchall()
for r in rows: print(r)
print()

# Check control_tower.db::ct_decisions schema + sample  
c2 = sqlite3.connect(os.path.join(ROOT, "data/control_tower.db"))
cols2 = [r[1] for r in c2.execute("PRAGMA table_info(ct_decisions)").fetchall()]
print("ct_decisions cols:", cols2)
rows2 = c2.execute("SELECT * FROM ct_decisions ORDER BY id DESC LIMIT 5").fetchall()
for r in rows2: print(r)
print()

# Check replay.db::signal_births schema
c3 = sqlite3.connect(os.path.join(ROOT, "data/replay.db"))
cols3 = [r[1] for r in c3.execute("PRAGMA table_info(signal_births)").fetchall()]
print("signal_births cols:", cols3)
rows3 = c3.execute("SELECT detected_at, symbol, strategy_archetype FROM signal_births LIMIT 5").fetchall()
for r in rows3: print(r)
