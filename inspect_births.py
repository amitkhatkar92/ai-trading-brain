import sqlite3
con = sqlite3.connect('/root/ai-trading-brain/data/market_behavior.db')
rows = con.execute("""
  SELECT detected_at, current_state, final_state, actual_move_pct, COUNT(*) as n
  FROM signal_births
  GROUP BY detected_at, current_state, final_state
  ORDER BY detected_at ASC
  LIMIT 20
""").fetchall()
for r in rows:
    print(r)

tc = con.execute('SELECT COUNT(*) FROM trading_calendar').fetchone()[0]
print(f'trading_calendar rows: {tc}')
oldest = con.execute('SELECT MIN(detected_at), MAX(detected_at) FROM signal_births').fetchone()
print(f'signal_births date range: {oldest[0]} to {oldest[1]}')
ohlcv_max = con.execute('SELECT MAX(trade_date) FROM ohlcv_daily').fetchone()[0]
print(f'ohlcv_daily max date: {ohlcv_max}')
past_ttl = con.execute("""
  SELECT COUNT(*) FROM signal_births
  WHERE julianday(date('now')) - julianday(detected_at) > expected_ttl_days
    AND final_state IS NULL
""").fetchone()[0]
print(f'signals past TTL with no final_state: {past_ttl}')

# Sample oldest signals with price data
print('\nOldest 5 signals with birth prices:')
old_sigs = con.execute("""
  SELECT signal_id, symbol, detected_at, birth_price, expected_move_direction, 
         expected_ttl_days, current_state, final_state, actual_move_pct
  FROM signal_births ORDER BY detected_at ASC LIMIT 5
""").fetchall()
for r in old_sigs:
    print(f'  {r[2]} {r[1]} dir={r[4]} price={r[3]} ttl={r[5]} state={r[6]} final={r[7]} move={r[8]}')

# Check what price exists for oldest symbol in ohlcv
sym = old_sigs[0][1] if old_sigs else 'RELIANCE.NS'
det = old_sigs[0][2] if old_sigs else '2026-04-01'
prices = con.execute("""
  SELECT trade_date, close FROM ohlcv_daily 
  WHERE symbol=? AND trade_date >= ?
  ORDER BY trade_date LIMIT 5
""", (sym, det)).fetchall()
print(f'\nohlcv for {sym} from {det}: {prices}')

# TTL distribution
print('\nTTL distribution:')
for r in con.execute("""
  SELECT expected_ttl_days, COUNT(*) as n
  FROM signal_births GROUP BY expected_ttl_days ORDER BY expected_ttl_days
""").fetchall():
    print(f'  ttl={r[0]}: {r[1]} signals')

# Check archetype distribution
print('\nArchetype distribution (top 10):')
for r in con.execute("""
  SELECT archetype_id, COUNT(*) as n
  FROM signal_births GROUP BY archetype_id ORDER BY n DESC LIMIT 10
""").fetchall():
    print(f'  {r[0]}: {r[1]}')

con.close()
