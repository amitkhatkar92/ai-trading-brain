import sqlite3, json
conn = sqlite3.connect('data/replay.db')
syms = conn.execute('SELECT DISTINCT symbol FROM ohlcv_daily').fetchall()
nifty_like = [s[0] for s in syms if 'NIFTY' in s[0].upper() or 'NSEI' in s[0].upper()]
print('NIFTY-like:', nifty_like[:5])
print('Total unique symbols:', len(syms))
r2 = conn.execute('SELECT sector, COUNT(*) as n FROM universe_stocks GROUP BY sector ORDER BY n DESC').fetchall()
print('Sectors:')
for row in r2: print(' ', row)
r3 = conn.execute('SELECT COUNT(*) FROM ohlcv_daily').fetchone()
print('ohlcv total rows:', r3[0])
r4 = conn.execute('SELECT MIN(trade_date), MAX(trade_date), COUNT(DISTINCT trade_date) FROM ohlcv_daily').fetchone()
print('ohlcv date range:', r4)
# Check signal_births schema fully
cols = [r[1] for r in conn.execute('PRAGMA table_info(signal_births)').fetchall()]
print('signal_births cols:', cols)
# Check if there is any archetype_versions data
arch = conn.execute('SELECT archetype_id, version_number FROM archetype_versions LIMIT 5').fetchall()
print('archetype_versions sample:', arch)
conn.close()
with open('top_mover_missed_opportunities.json') as f:
    missed = json.load(f)
print('missed json len:', len(missed))
print('sample:', missed[0])
