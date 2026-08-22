import sqlite3, os
ROOT = r"C:\Users\UCIC\OneDrive\Desktop\ai_trading_brain"

# ct_decisions time distribution
c = sqlite3.connect(os.path.join(ROOT, "data/control_tower.db"))
print("ct_decisions time distribution (HH):")
for r in c.execute("""
    SELECT substr(ts,12,2) as hh, COUNT(*) as n
    FROM ct_decisions WHERE ts IS NOT NULL AND ts != ''
    GROUP BY hh ORDER BY hh
""").fetchall():
    print(f"  {r[0]}:xx  {r[1]} decisions")

print("\nohlcv_daily range + count:")
c2 = sqlite3.connect(os.path.join(ROOT, "data/replay.db"))
r = c2.execute("SELECT MIN(trade_date), MAX(trade_date), COUNT(*), COUNT(DISTINCT symbol) FROM ohlcv_daily").fetchone()
print(f"  date_range={r[0]}..{r[1]}  rows={r[2]}  symbols={r[3]}")
print("\nohlcv_daily sample:")
for r in c2.execute("SELECT trade_date, symbol, open, high, low, close, volume FROM ohlcv_daily LIMIT 5").fetchall():
    print(f"  {r}")
