import pandas as pd, sqlite3, json, os, sys
from datetime import datetime, timedelta

cutoff = datetime.now() - timedelta(days=12)

# ── paper_trades_legacy.csv ───────────────────────────────────────────────────
try:
    df = pd.read_csv('data/paper_trades_legacy.csv')
    print(f'=== paper_trades_legacy.csv: {len(df)} rows ===')
    if len(df):
        for col in df.columns:
            if 'time' in col.lower() or 'date' in col.lower():
                df[col] = pd.to_datetime(df[col], errors='coerce')
        print(df.tail(20).to_string())
    print()
except Exception as e:
    print(f'legacy csv error: {e}')

# ── paper_trade_log.csv ───────────────────────────────────────────────────────
try:
    df2 = pd.read_csv('data/paper_trade_log.csv')
    print(f'=== paper_trade_log.csv: {len(df2)} rows ===')
    if len(df2):
        for col in df2.columns:
            if 'time' in col.lower() or 'date' in col.lower():
                df2[col] = pd.to_datetime(df2[col], errors='coerce')
        print(df2.tail(20).to_string())
    print()
except Exception as e:
    print(f'trade_log error: {e}')

# ── trading_brain.db ──────────────────────────────────────────────────────────
for dbfile in ['data/trading_brain.db', 'data/trade_quality.db', 'data/replay.db']:
    try:
        con = sqlite3.connect(dbfile)
        tables = [t for t, in con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        print(f'=== {dbfile}: {tables} ===')
        for t in tables:
            n = con.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]
            if n == 0:
                continue
            cols = [d[0] for d in con.execute(f'PRAGMA table_info("{t}")').fetchall()]
            rows = con.execute(f'SELECT * FROM "{t}" ORDER BY rowid DESC LIMIT 20').fetchall()
            tmp = pd.DataFrame(rows, columns=cols)
            print(f'  [{t}] {n} rows — last 20:')
            print(tmp.to_string())
            print()
        con.close()
    except Exception as e:
        print(f'{dbfile} error: {e}')

# ── logs ──────────────────────────────────────────────────────────────────────
log_dir = 'data/logs'
if os.path.isdir(log_dir):
    logs = sorted(os.listdir(log_dir))
    print(f'=== logs: {logs[-10:]} ===')
    for lf in logs[-3:]:
        path = os.path.join(log_dir, lf)
        try:
            with open(path, 'r', errors='replace') as f:
                lines = f.readlines()
            # find LUPIN and recent errors
            for i, line in enumerate(lines):
                if any(kw in line.upper() for kw in ['LUPIN','ERROR','LOSS','EXIT','PNL','FAILED','PRICE']):
                    print(f'{lf}:{i+1}: {line.rstrip()}')
        except Exception as e:
            print(f'{lf}: {e}')
