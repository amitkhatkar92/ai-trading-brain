import sqlite3, os, sys

db_path = "data/study002_replay.db"
if not os.path.exists(db_path):
    print("DB NOT FOUND"); sys.exit(1)

con = sqlite3.connect(db_path)
cur = con.cursor()
tables = cur.execute('SELECT name FROM sqlite_master WHERE type="table" ORDER BY name').fetchall()
print("=== TABLES ===")
for t in tables:
    cnt = cur.execute(f'SELECT COUNT(*) FROM "{t[0]}"').fetchone()[0]
    print(f"  {t[0]}: {cnt:,} rows")

print()
for t in tables:
    cols = cur.execute(f'PRAGMA table_info("{t[0]}")').fetchall()
    print(f"[{t[0]}] cols: {[c[1] for c in cols]}")
    # sample a row
    row = cur.execute(f'SELECT * FROM "{t[0]}" LIMIT 1').fetchone()
    if row:
        for c, v in zip([c[1] for c in cols], row):
            print(f"    {c}: {repr(v)}")
    print()

# date range of ohlcv_daily
try:
    r = cur.execute("SELECT MIN(date), MAX(date), COUNT(DISTINCT symbol), COUNT(*) FROM ohlcv_daily").fetchone()
    print(f"ohlcv_daily: min={r[0]} max={r[1]} symbols={r[2]} rows={r[3]:,}")
except Exception as e:
    print(f"ohlcv_daily error: {e}")

# check for intraday tables
intra = cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%intra%'").fetchall()
print(f"intraday tables: {intra}")

# check bulk_block_deals
try:
    bbd = cur.execute("PRAGMA table_info('bulk_block_deals')").fetchall()
    if bbd:
        cnt = cur.execute("SELECT COUNT(*) FROM bulk_block_deals").fetchone()[0]
        print(f"bulk_block_deals columns: {[c[1] for c in bbd]}, rows={cnt:,}")
        sample = cur.execute("SELECT * FROM bulk_block_deals LIMIT 5").fetchall()
        for row in sample:
            print(f"  {row}")
    else:
        print("bulk_block_deals: NOT FOUND")
except Exception as e:
    print(f"bulk_block_deals error: {e}")

# check signal_births
try:
    sb = cur.execute("PRAGMA table_info('signal_births')").fetchall()
    if sb:
        cnt = cur.execute("SELECT COUNT(*) FROM signal_births").fetchone()[0]
        print(f"signal_births cols: {[c[1] for c in sb]}, rows={cnt:,}")
        sample = cur.execute("SELECT * FROM signal_births LIMIT 3").fetchall()
        for row in sample:
            print(f"  {row}")
except Exception as e:
    print(f"signal_births error: {e}")

con.close()
