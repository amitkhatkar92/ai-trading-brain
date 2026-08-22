import sqlite3, os
ROOT = r"C:\Users\UCIC\OneDrive\Desktop\ai_trading_brain"

# signal_births time distribution
c = sqlite3.connect(os.path.join(ROOT, "data/replay.db"))
cols = [r[1] for r in c.execute("PRAGMA table_info(signal_births)").fetchall()]
print("signal_births cols:", cols)
print()

# Sample detected_at format
print("Sample detected_at values:")
for r in c.execute("SELECT detected_at FROM signal_births WHERE detected_at IS NOT NULL LIMIT 5").fetchall():
    print(" ", r[0])

# Time-of-day distribution
print("\nSignal time distribution (HH):")
for r in c.execute("""
    SELECT substr(detected_at,12,2) as hh, COUNT(*) as n
    FROM signal_births WHERE detected_at IS NOT NULL
    GROUP BY hh ORDER BY hh
""").fetchall():
    print(f"  {r[0]}:xx  {r[1]} signals")

# Opening window vs post-governance counts
print("\nOpening window (09:10-09:30):")
ow = c.execute("""
    SELECT COUNT(*), AVG(trade_outcome_pct), SUM(CASE WHEN trade_outcome_pct > 0 THEN 1 ELSE 0 END)
    FROM signal_births
    WHERE detected_at IS NOT NULL
      AND substr(detected_at,12,5) BETWEEN '09:10' AND '09:30'
""").fetchone()
print(f"  count={ow[0]}  avg_outcome={ow[1]}  wins={ow[2]}")

print("\nPost-governance (09:45+):")
pg = c.execute("""
    SELECT COUNT(*), AVG(trade_outcome_pct), SUM(CASE WHEN trade_outcome_pct > 0 THEN 1 ELSE 0 END)
    FROM signal_births
    WHERE detected_at IS NOT NULL
      AND substr(detected_at,12,5) >= '09:45'
      AND substr(detected_at,12,5) <= '15:30'
""").fetchone()
print(f"  count={pg[0]}  avg_outcome={pg[1]}  wins={pg[2]}")

# Trades
print("\ntrading_brain::trades (executed) time distribution:")
c2 = sqlite3.connect(os.path.join(ROOT, "data/trading_brain.db"))
for r in c2.execute("""
    SELECT substr(ts_open,12,5) as hhmm, symbol, strategy, pnl, r_multiple, won
    FROM trades ORDER BY ts_open
""").fetchall():
    print(f"  {r[0]}  {r[1]}  {r[2]}  pnl={r[3]}  r={r[4]}  won={r[5]}")
