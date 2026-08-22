import pandas as pd, sqlite3, json, os
from datetime import datetime, timedelta

pd.set_option('display.max_columns', None)
pd.set_option('display.max_colwidth', 40)
pd.set_option('display.width', 200)

# ── trading_brain.db trades ───────────────────────────────────────────────────
con = sqlite3.connect('data/trading_brain.db')
cols = [d[0] for d in con.execute('PRAGMA table_info("trades")').fetchall()]
print('TRADES columns:', cols)
rows = con.execute('SELECT * FROM trades ORDER BY rowid').fetchall()
df = pd.DataFrame(rows, columns=cols)
print(f'\n=== ALL {len(df)} TRADES ===')
print(df.to_string())
con.close()

print('\n\n')

# ── strategy_performance.json ─────────────────────────────────────────────────
try:
    with open('data/strategy_performance.json') as f:
        sp = json.load(f)
    print('=== strategy_performance.json ===')
    for k, v in sp.items():
        print(f'  {k}: {v}')
except Exception as e:
    print(f'strategy_performance error: {e}')

# ── control_tower.db ─────────────────────────────────────────────────────────
try:
    con = sqlite3.connect('data/control_tower.db')
    tables = [t for t, in con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    print(f'\n=== control_tower.db tables: {tables} ===')
    for t in tables:
        n = con.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]
        c = [d[0] for d in con.execute(f'PRAGMA table_info("{t}")').fetchall()]
        print(f'\n  [{t}] {n} rows, cols={c}')
        if n > 0 and n <= 50:
            r = con.execute(f'SELECT * FROM "{t}" ORDER BY rowid DESC LIMIT 30').fetchall()
            print(pd.DataFrame(r, columns=c).to_string())
        elif n > 50:
            r = con.execute(f'SELECT * FROM "{t}" ORDER BY rowid DESC LIMIT 20').fetchall()
            print(pd.DataFrame(r, columns=c).to_string())
    con.close()
except Exception as e:
    print(f'control_tower error: {e}')
