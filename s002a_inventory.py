import sqlite3, json

# Check replay.db
conn = sqlite3.connect('data/replay.db')
tbls = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
print('replay.db tables:', tbls)
for t in ['ohlcv_daily', 'signal_births', 'opportunities']:
    try:
        n = conn.execute(f"SELECT COUNT(1) FROM {t}").fetchone()[0]
        if t == 'ohlcv_daily':
            d = conn.execute(f"SELECT MIN(trade_date), MAX(trade_date) FROM {t}").fetchone()
            print(f"  {t}: {n} rows  dates={d[0]} to {d[1]}")
        else:
            print(f"  {t}: {n} rows")
    except Exception as e:
        print(f"  {t}: N/A ({e})")
conn.close()

print()

# Check regime_probability_history.json
with open('data/regime_probability_history.json') as f:
    rph = json.load(f)
print(f"regime_probability_history: type={type(rph).__name__}  len={len(rph) if isinstance(rph, list) else 'dict'}")
if isinstance(rph, list) and rph:
    print("  sample:", str(rph[0])[:200])
elif isinstance(rph, dict):
    print("  keys:", list(rph.keys())[:10])

print()

# Check paper_trades.csv
with open('data/paper_trades.csv') as f:
    lines = f.readlines()
print(f"paper_trades.csv: {len(lines)} lines")
if lines:
    print("  header:", lines[0].strip())
    if len(lines) > 1:
        print("  sample:", lines[1].strip())

# Check strategy_performance.json
with open('data/strategy_performance.json') as f:
    sp = json.load(f)
print(f"\nstrategy_performance.json: {len(sp)} entries")
for k, v in sp.items():
    print(f"  {k}: {v}")
